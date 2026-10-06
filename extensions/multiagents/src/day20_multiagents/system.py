import asyncio
import hashlib
import json
import logging
import math
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path
from uuid import uuid4

from .agents import CodeAgent, DataAgent, EvaluatorAgent
from .communication import MessageQueue
from .coordinator import Coordinator
from .observability import MeasuredModel, MeasuredTool, RequestMetrics
from .runtime import offline_factory
from .tools import resolve_path


REFERENCE = {"revenue": 150, "rows": 3}
CSV_INPUT = "quarter,amount\n3,40\n3,50\n3,60\n1,900\n"


def prepare_workspace(workspace: Path) -> dict:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "sales.csv").write_text(CSV_INPUT, encoding="utf-8")
    with sqlite3.connect(workspace / "sales.db") as connection:
        connection.execute("CREATE TABLE sales (quarter INTEGER, amount INTEGER)")
        connection.executemany("INSERT INTO sales VALUES (?, ?)", [(3, 40), (3, 50), (3, 60), (1, 900)])
    return {name: hashlib.sha256((workspace / name).read_bytes()).hexdigest() for name in ("sales.csv", "sales.db")}


class MultiAgentSystem:
    """Request-isolated fixture workflow; complex tasks run data -> code -> evaluator."""

    def __init__(self, model_factory=offline_factory, mode: str = "offline", max_concurrency: int = 4,
                 artifact_dir: Path | None = None):
        if mode not in {"offline", "live"} or isinstance(max_concurrency, bool) or not isinstance(max_concurrency, int) or not 1 <= max_concurrency <= 16:
            raise ValueError("Invalid system configuration")
        self.model_factory = model_factory
        self.mode = mode
        self.max_concurrency = max_concurrency
        self.artifact_dir = Path(artifact_dir).resolve() if artifact_dir is not None else None
        self._capacity = asyncio.Semaphore(max_concurrency)
        self.logger = logging.getLogger("day20_multiagents.system")

    async def process(self, request: str | dict, timeout: float = 90, debug: bool = False) -> dict:
        MessageQueue._timeout(timeout)
        if timeout is None:
            raise ValueError("System requires a finite deadline")
        identity = str(uuid4())
        metrics = RequestMetrics(self.mode)
        result = {"request_id": identity, "status": "error", "data": [], "code": [], "evaluation": [],
                  "errors": [], "stages": [], "checks": {}, "validation_passed": False}
        started = time.perf_counter()
        try:
            async with asyncio.timeout(timeout):
                async with self._capacity:
                    with tempfile.TemporaryDirectory(prefix="day20-request-") as directory:
                        await self._run(request, Path(directory), identity, metrics, result, debug, timeout)
        except TimeoutError:
            result["status"] = "timeout"
            result["errors"].append({"type": "TimeoutError", "message": "Request deadline exceeded"})
        except Exception as error:
            result["errors"].append({"type": type(error).__name__, "message": "Request failed; inspect stage results and safe logs"})
        result["latency_seconds"] = time.perf_counter() - started
        result["metrics"] = metrics.snapshot()
        self.logger.info("request_end request_id=%s status=%s seconds=%.4f", identity, result["status"], result["latency_seconds"])
        return result

    async def _run(self, request, workspace: Path, identity: str, metrics: RequestMetrics, result: dict, debug: bool, timeout: float):
        hashes = prepare_workspace(workspace)
        workers = []
        data_worker = None
        try:
            for name in ("data_agent", "code_agent", "evaluator_agent"):
                model = MeasuredModel(self.model_factory(name, workspace), metrics, name)
                worker = DataAgent(model, workspace, db_path="sales.db") if name == "data_agent" else \
                    CodeAgent(model, workspace, timeout=15) if name == "code_agent" else EvaluatorAgent(model, workspace=workspace)
                worker.tools = {tool.name: MeasuredTool(tool, metrics, name) for tool in worker.tools.values()}
                workers.append(worker)
                if name == "data_agent":
                    data_worker = worker
            coordinator = Coordinator(None, workers)
            parsed = coordinator.parse_request(request)
            kind = parsed["task_type"]
            names = coordinator.route_task(kind)
            if kind == "complex":
                names.append("evaluator_agent")
            for name in names:
                parameters = {"database": "sales.db", "csv": "sales.csv", "chart": kind == "complex",
                              "schema": {"sales": {"quarter": "INTEGER", "amount": "INTEGER"}},
                              "csv_columns": ["quarter", "amount"], "quarter_filter": 3}
                content = "Original user request: " + parsed["content"] + "\nYour delegated assignment only: "
                if name == "data_agent":
                    content += ("Calculate Q3 revenue using query_database on table sales with the supplied schema. "
                                "WHERE quarter=3; SUM(amount) is revenue, COUNT(*) is rows. Return ONLY a JSON object "
                                "with revenue (numeric sum of matching amounts) and rows (integer COUNT of matching Q3 sales, "
                                "not the full CSV row count or a list). Do not implement charts or evaluation; those belong "
                                "to other workers. Do not assume date/revenue columns exist or invent values.")
                elif name == "code_agent":
                    parameters["data_result"] = result["data"]
                    content += ("Create outputs/report.py, run it using run_script, read sales.csv using csv.DictReader. "
                                "CSV headers are quarter and amount; quarter has numeric quarter values (no date column), "
                                "amount is revenue per sale. Filter int(row['quarter']) == 3 and sum int(row['amount']); "
                                "and write outputs/answer.json with revenue and rows. Return JSON with script, answer, chart paths. "
                                "Do not change source files, access secrets or network. "
                                + ("Also create outputs/sales_chart.png with matplotlib Agg, small figure. " if kind == "complex" else "No chart is needed. "))
                else:
                    parameters.update({"actual": self._actual(result, workspace), "expected": dict(REFERENCE),
                                       "ratings": {"accuracy": 85, "completeness": 90, "clarity": 80, "performance": 85}})
                    content += ("Use comparison with actual and expected parameters, scoring with supplied ratings, "
                                "and report_generator to write outputs/evaluation.md with evidence before returning exact evaluation JSON. "
                                "report_generator evaluation and your final JSON must have EXACTLY score (number), feedback (string), "
                                "issues (list of strings), suggestions (list of strings), no additional grade/scores/weights fields. "
                                "Supplied ratings test the formula, not measured model quality.")
                stage_started = time.perf_counter()
                stage = (await coordinator.execute_tasks([{"id": identity + ":" + name, "worker": name,
                                                          "content": content, "parameters": parameters}], timeout=timeout))[0]
                result["stages"].append({"worker": name, "status": stage["status"], "seconds": time.perf_counter() - stage_started})
                if stage["status"] != "success":
                    result["errors"].append({"worker": name, "status": stage["status"], "error": stage.get("error", "Worker failed")})
                    if debug:
                        result["communication"] = coordinator.task_queue.get_message_log()
                    return
                group = {"data_agent": "data", "code_agent": "code", "evaluator_agent": "evaluation"}[name]
                result[group].append(stage["result"])
            self._verify(result, workspace, kind, hashes, metrics)
            result["status"] = "success" if result["validation_passed"] else "error"
            if debug:
                result["communication"] = coordinator.task_queue.get_message_log()
        finally:
            if data_worker is not None:
                data_worker.close()
            if self.artifact_dir is not None:
                directory = self.artifact_dir / identity
                directory.mkdir(parents=True, exist_ok=False)
                result["artifacts"] = {}
                for filename in ("outputs/report.py", "outputs/answer.json", "outputs/sales_chart.png", "outputs/evaluation.md"):
                    source = resolve_path(workspace, filename)
                    if source.is_file() and source.stat().st_size <= 65536:
                        destination = directory / filename
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(source, destination)
                        result["artifacts"][filename] = hashlib.sha256(destination.read_bytes()).hexdigest()

    @staticmethod
    def _actual(result: dict, workspace: Path) -> dict:
        answer = resolve_path(workspace, "outputs/answer.json")
        if answer.is_file():
            return json.loads(answer.read_text(encoding="utf-8"))
        return json.loads(result["data"][-1]) if result["data"] else {}

    @staticmethod
    def _numbers(value) -> bool:
        return isinstance(value, dict) and all(isinstance(value.get(name), (int, float))
                                              and not isinstance(value[name], bool) and math.isfinite(value[name])
                                              and value[name] == expected for name, expected in REFERENCE.items())

    def _verify(self, result: dict, workspace: Path, kind: str, hashes: dict, metrics: RequestMetrics) -> None:
        checks = result["checks"]
        events = metrics.snapshot()["events"]
        checks["sources_unchanged"] = all(hashlib.sha256((workspace / name).read_bytes()).hexdigest() == digest for name, digest in hashes.items())
        if kind in {"data_analysis", "complex"}:
            checks["data_numbers"] = self._numbers(json.loads(result["data"][-1]))
            checks["data_tool_evidence"] = any(event["kind"] == "tool" and event["name"] in {"query_database", "pandas_analysis"}
                                                and event["status"] == "success" for event in events)
        if kind in {"code_generation", "complex"}:
            checks["script_exists"] = resolve_path(workspace, "outputs/report.py").is_file()
            checks["code_numbers"] = self._numbers(self._actual(result, workspace))
            checks["script_executed"] = any(event["name"] == "run_script" and event["status"] == "success" for event in events)
        if kind == "complex":
            from PIL import Image

            with Image.open(resolve_path(workspace, "outputs/sales_chart.png")) as chart:
                chart.verify()
            checks["chart_decodes"] = True
        if kind in {"evaluation", "complex"}:
            checks["evaluation_score"] = result["evaluation"][-1]["score"] == 85.5
            checks["report_exists"] = resolve_path(workspace, "outputs/evaluation.md").is_file()
            checks["comparison_executed"] = any(event["name"] == "comparison" and event["status"] == "success" for event in events)
        result["validation_passed"] = bool(checks) and all(checks.values())
