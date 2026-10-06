import argparse
import asyncio
import hashlib
import json
import logging
import sqlite3
import tempfile
from pathlib import Path

from langchain_core.messages import AIMessage, ToolMessage

from day20_multiagents.agents import CodeAgent, DataAgent, EvaluatorAgent
from day20_multiagents.coordinator import Coordinator


class ScriptedModel:
    """Offline tool-call driver, not a real LLM or quality judge."""

    def __init__(self, actions, finish):
        self.actions = list(actions)
        self.finish = finish
        self.identity = 0

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        outputs = {message.name: json.loads(message.content) for message in messages
                   if isinstance(message, ToolMessage)}
        if self.actions:
            name, arguments = self.actions.pop(0)(outputs)
            self.identity += 1
            return AIMessage(content="", tool_calls=[{"name": name, "args": arguments, "id": str(self.identity)}])
        return AIMessage(content=json.dumps(self.finish(outputs)))

    async def ainvoke(self, messages):
        return self.invoke(messages)


async def run_demo(workspace: Path) -> dict:
    workspace = Path(workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(workspace / "sales.db") as connection:
        connection.execute("CREATE TABLE sales (id INTEGER, year INTEGER, amount INTEGER)")
        connection.executemany("INSERT INTO sales VALUES (?, 2026, ?)", [(value, value) for value in range(1, 51)])
        connection.execute("INSERT INTO sales VALUES (51, 2025, 999)")
    query = "SELECT id, amount FROM sales WHERE year=2026 ORDER BY id"
    data_model = ScriptedModel([lambda outputs: ("query_database", {"query": query})],
                              lambda outputs: outputs["query_database"])
    data_worker = DataAgent(data_model, workspace, db_path="sales.db")
    coordinator = Coordinator(None, [data_worker])
    try:
        result = await coordinator.execute_tasks([{"id": "data", "worker": "data_agent", "content": "Query 2026 sales"}], timeout=10)
        if result[0]["status"] != "success":
            raise RuntimeError(result[0].get("error", "Data worker failed"))
        data = json.loads(result[0]["result"])
        assert len(data["rows"]) == 50 and not data["truncated"]
        amounts = [row[1] for row in data["rows"]]
        total = sum(amounts)
        assert total == 1275
        print(f"Test: Data Agent queries database\n  SQL: {query}\n  Result: {len(amounts)} rows; total={total} - PASS")

        code = (
            "import json\nimport matplotlib\nmatplotlib.use('Agg')\nimport matplotlib.pyplot as plt\n"
            f"amounts = {amounts!r}\n"
            "figure, axis = plt.subplots(figsize=(4, 2.5))\n"
            "axis.plot(range(1, len(amounts) + 1), amounts)\n"
            "axis.set(xlabel='Sale', ylabel='Amount', title='2026 sales')\n"
            "figure.tight_layout()\nfigure.savefig('outputs/sales_chart.png', dpi=90)\nplt.close(figure)\n"
            "print(json.dumps({'total': sum(amounts), 'rows': len(amounts)}))\n"
        )
        code_model = ScriptedModel([
            lambda outputs: ("create_file", {"filename": "outputs/chart.py", "content": code}),
            lambda outputs: ("run_script", {"filename": "outputs/chart.py"}),
        ], lambda outputs: outputs["run_script"])
        code_worker = CodeAgent(code_model, workspace, timeout=15)
        coordinator.workers[code_worker.name] = code_worker
        coordinator.task_queue.register_agent(code_worker.name)
        result = await coordinator.execute_tasks([{"id": "chart", "worker": "code_agent", "content": "Visualize the Data Agent result",
                                                   "parameters": {"source_task": "data", "amounts": amounts}}], timeout=20)
        if result[0]["status"] != "success":
            raise RuntimeError(result[0].get("error", "Code worker failed"))
        execution = json.loads(result[0]["result"])
        observed = json.loads(execution["stdout"])
        chart = workspace / "outputs/sales_chart.png"
        from PIL import Image

        with Image.open(chart) as image:
            image.verify()
        chart_bytes = chart.read_bytes()
        assert chart_bytes.startswith(b"\x89PNG\r\n\x1a\n") and observed["total"] == total
        print(f"Test: Code Agent creates visualization\n  Artifact: outputs/sales_chart.png ({len(chart_bytes)} bytes)\n  Verified total={observed['total']} - PASS")

        ratings = {"accuracy": 85, "completeness": 90, "clarity": 80, "performance": 85}
        reference = {"rows": len(amounts), "total": total}

        def evaluation(outputs):
            matches = outputs["comparison"]["valid"]
            return {"score": outputs["scoring"]["score"], "feedback": "SQL/code totals match" if matches else "Reference mismatch",
                    "issues": [] if matches else ["Output does not match SQL reference"],
                    "suggestions": ["Criterion ratings are supplied demo inputs, not measured model quality."]}

        evaluator_model = ScriptedModel([
            lambda outputs: ("scoring", ratings),
            lambda outputs: ("comparison", {"actual": observed, "expected": reference}),
            lambda outputs: ("report_generator", {
                "filename": "outputs/evaluation.md", "title": "Offline tool collaboration",
                "evaluation": evaluation(outputs),
                "evidence": {"sql": reference, "code": observed, "ratings": ratings,
                             "comparison": outputs["comparison"], "chart": "outputs/sales_chart.png"}}),
        ], evaluation)
        evaluator_worker = EvaluatorAgent(evaluator_model, workspace=workspace)
        coordinator.workers[evaluator_worker.name] = evaluator_worker
        coordinator.task_queue.register_agent(evaluator_worker.name)
        result = await coordinator.execute_tasks([{"id": "evaluation", "worker": "evaluator_agent", "content": "Compare verified output and generate report",
                                                   "parameters": {"sql_reference": reference, "observed": observed}}], timeout=10)
        if result[0]["status"] != "success":
            raise RuntimeError(result[0].get("error", "Evaluator worker failed"))
        score = result[0]["result"]
        assert score["score"] == 85.5 and not score["issues"]
        report = (workspace / "outputs/evaluation.md").read_text(encoding="utf-8")
        assert "85.5/100 (B)" in report and '"total": 1275' in report
        messages = coordinator.task_queue.get_message_log()
        assert len([message for message in messages if message["type"] == "task"]) == 3
        assert len([message for message in messages if message["type"] == "result"]) == 3
        (workspace / "communication.json").write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8")
        summary = {"database_rows": len(amounts), "sql_total": total, "code_total": observed["total"],
                   "score_from_supplied_ratings": score["score"], "grade": "B", "messages": len(messages),
                   "chart_bytes": len(chart_bytes), "chart_sha256": hashlib.sha256(chart_bytes).hexdigest(),
                   "offline_scripted_models": True, "api_calls": 0}
        (workspace / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print("Test: Evaluator compares and writes report\n  Score from supplied ratings: 85.5/100 (B)\n  SQL/code comparison: matches; outputs/evaluation.md verified - PASS")
        print("All tool integration tests passed! (3/3; real local tools, scripted models, no API)")
        return summary
    finally:
        data_worker.close()


def main():
    parser = argparse.ArgumentParser(description="Offline real-tool collaboration; no API calls")
    parser.add_argument("--output", type=Path, help="New directory to retain demo artifacts (must not exist)")
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    if arguments.output:
        arguments.output.mkdir(parents=True, exist_ok=False)
        asyncio.run(run_demo(arguments.output))
    else:
        with tempfile.TemporaryDirectory(prefix="day20-tools-demo-") as directory:
            asyncio.run(run_demo(Path(directory)))


if __name__ == "__main__":
    main()
