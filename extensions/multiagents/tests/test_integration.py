import asyncio
import json

from day20_multiagents.agents import CodeAgent, DataAgent, EvaluatorAgent
from day20_multiagents.coordinator import Coordinator


def test_real_workers_and_tools_through_queue(tmp_path, fake_model, ai_response):
    (tmp_path / "sales.csv").write_text("amount\n10\n20\n")
    data_model = fake_model(ai_response("", ("pandas_analysis", {
        "filename": "sales.csv", "column": "amount", "operation": "sum"})), ai_response("Total: 30"))
    code = "import csv\nwith open('sales.csv') as source:\n    total = sum(int(row['amount']) for row in csv.DictReader(source))\nwith open('report.txt', 'w') as output:\n    output.write(str(total))\nprint(total)"
    code_model = fake_model(ai_response("", ("create_file", {"filename": "report.py", "content": code})),
                           ai_response("", ("run_script", {"filename": "report.py"})), ai_response("report.txt verified: 30"))
    evaluator_model = fake_model(ai_response(json.dumps({"score": 90, "feedback": "Verified output 30",
                                                         "issues": [], "suggestions": []})))
    coordinator = Coordinator(None, [DataAgent(data_model, tmp_path), CodeAgent(code_model, tmp_path),
                                     EvaluatorAgent(evaluator_model)])

    async def scenario():
        tasks = [{"id": "sum", "worker": "data_agent", "content": "Sum sales.csv"},
                 {"id": "report", "worker": "code_agent", "content": "Compute and save report.txt from sales.csv"}]
        result = coordinator.aggregate_results(await coordinator.execute_tasks(tasks, timeout=2))
        assert result["status"] == "success"
        assert result["data"][0]["result"] == "Total: 30"
        assert result["code"][0]["result"] == "report.txt verified: 30"
        assert (tmp_path / "report.txt").read_text() == "30"
        evaluation = await coordinator.execute_tasks([
            {"id": "review", "worker": "evaluator_agent", "content": "Evaluate verified report",
             "parameters": {"observed_total": 30}}], timeout=1)
        assert evaluation[0]["result"]["score"] == 90
        messages = coordinator.task_queue.get_message_log()
        assert len([message for message in messages if message["type"] == "task"]) == 3
        assert len([message for message in messages if message["type"] == "result"]) == 3
    asyncio.run(scenario())
