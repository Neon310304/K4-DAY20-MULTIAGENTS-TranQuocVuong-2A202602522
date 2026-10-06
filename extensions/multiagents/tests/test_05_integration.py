import asyncio
import json
import logging
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from day20_multiagents.benchmarking import CASES, percentile, run_benchmark, summarize
from day20_multiagents.observability import MeasuredModel, RequestMetrics, configure_logging
from day20_multiagents.runtime import OfflineModel, environment_value, live_factory
from day20_multiagents.system import MultiAgentSystem


def test_user_request_to_data_result():
    result = asyncio.run(MultiAgentSystem().process(CASES[0][1], debug=True))
    assert result["status"] == "success" and result["validation_passed"]
    assert json.loads(result["data"][0]) == {"revenue": 150, "rows": 3}
    assert result["metrics"]["api_calls"] == 0 and result["metrics"]["model_calls"] == 2
    assert result["metrics"]["tokens"]["total_tokens"] == 0
    assert len(result["communication"]) == 2


def test_full_pipeline_orders_handoffs_and_verifies_files():
    result = asyncio.run(MultiAgentSystem().process(CASES[2][1], debug=True))
    assert result["status"] == "success" and all(result["checks"].values())
    assert [stage["worker"] for stage in result["stages"]] == ["data_agent", "code_agent", "evaluator_agent"]
    assert result["evaluation"][0]["score"] == 85.5
    assert len(result["communication"]) == 6
    code_task = next(message for message in result["communication"] if message["type"] == "task" and message["to"] == "code_agent")
    assert code_task["parameters"]["data_result"] == result["data"]
    assert code_task["parameters"]["csv_columns"] == ["quarter", "amount"]
    data_task = next(message for message in result["communication"] if message["type"] == "task" and message["to"] == "data_agent")
    assert "COUNT(*)" in data_task["content"] and data_task["parameters"]["quarter_filter"] == 3
    assert result["checks"]["script_executed"] and result["checks"]["chart_decodes"]
    assert all(event["seconds"] >= 0 for event in result["metrics"]["events"])


def test_ten_concurrent_requests_are_isolated():
    async def scenario():
        system = MultiAgentSystem(max_concurrency=3)
        results = await asyncio.gather(*[system.process(CASES[0][1]) for unused in range(10)])
        assert len({result["request_id"] for result in results}) == 10
        assert all(result["status"] == "success" for result in results)
        assert all(result["metrics"]["model_calls"] == 2 for result in results)
        assert not [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
    asyncio.run(scenario())


def test_deadline_cancels_model_and_system_can_be_reused():
    async def scenario():
        cancelled = []

        class SlowModel(OfflineModel):
            async def ainvoke(self, messages):
                try:
                    await asyncio.sleep(10)
                except asyncio.CancelledError:
                    cancelled.append(True)
                    raise

        system = MultiAgentSystem(lambda role, workspace: SlowModel(role), max_concurrency=1)
        result = await system.process(CASES[0][1], timeout=0.02)
        assert result["status"] == "timeout" and cancelled
        system.model_factory = lambda role, workspace: OfflineModel(role)
        assert (await system.process(CASES[0][1]))["status"] == "success"
    asyncio.run(scenario())


def test_caller_cancellation_propagates():
    async def scenario():
        started = asyncio.Event()

        class WaitingModel(OfflineModel):
            async def ainvoke(self, messages):
                started.set()
                await asyncio.sleep(10)

        system = MultiAgentSystem(lambda role, workspace: WaitingModel(role))
        task = asyncio.create_task(system.process(CASES[0][1]))
        await asyncio.wait_for(started.wait(), timeout=1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(scenario())


def test_worker_failures_and_empty_request_are_not_success():
    class CrashedModel(OfflineModel):
        def invoke(self, messages):
            raise RuntimeError("fixture model unavailable")

    result = asyncio.run(MultiAgentSystem(lambda role, workspace: CrashedModel(role)).process(CASES[0][1], debug=True))
    assert result["status"] == "error" and not result["validation_passed"]
    assert result["stages"][0]["status"] == "error" and result["communication"]
    assert asyncio.run(MultiAgentSystem().process(""))["status"] == "error"


def test_fluent_wrong_data_is_rejected():
    class WrongModel(OfflineModel):
        def invoke(self, messages):
            return AIMessage(content='{"revenue":900,"rows":1}')

    result = asyncio.run(MultiAgentSystem(lambda role, workspace: WrongModel(role)).process(CASES[0][1]))
    assert result["status"] == "error" and not result["checks"]["data_numbers"]
    assert not result["checks"]["data_tool_evidence"]


def test_usage_measurement_does_not_fabricate_missing_tokens():
    class Model:
        def invoke(self, messages):
            return AIMessage(content="OK", usage_metadata={"input_tokens": 8, "output_tokens": 2, "total_tokens": 10})

    metrics = RequestMetrics("live")
    wrapper = MeasuredModel(Model(), metrics, "test")
    wrapper.invoke([])
    assert metrics.snapshot()["tokens"]["total_tokens"] == 10
    assert metrics.snapshot()["api_calls"] == 1
    metrics.finish(metrics.begin("model", "test", "unknown"), 0, "error")
    record = metrics.snapshot()
    assert not record["usage_complete"] and record["tokens"] is None
    assert record["known_tokens"]["total_tokens"] == 10 and record["missing_usage_calls"] == 1


def test_statistics_use_even_median_percentiles_and_actual_failures():
    assert percentile([1, 2, 3, 4], 0.5) == 2.5
    assert percentile([1, 2, 3, 4], 0.99) == pytest.approx(3.97)
    records = [{"status": "success" if index < 3 else "error", "validation_passed": index < 3,
                "latency_seconds": index + 1, "stages": [], "metrics": {
                    "usage_complete": True, "known_tokens": {"input_tokens": 8, "output_tokens": 2, "total_tokens": 10},
                    "model_calls": 1, "api_calls": 1}} for index in range(4)]
    summary = summarize("example", records, 10)
    assert summary["median"] == 2.5 and summary["error_rate"] == 0.25
    assert summary["throughput_per_minute"] == 24 and summary["tokens_per_100_requests"] == 1000
    with pytest.raises(ValueError):
        percentile([], 0.5)


def test_benchmark_runs_three_iterations_and_keeps_failures():
    class FakeSystem:
        mode = "offline"
        max_concurrency = 2

        async def process(self, request, **parameters):
            return {"status": "error", "validation_passed": False, "latency_seconds": 0.001, "stages": [],
                    "metrics": {"usage_complete": True, "known_tokens": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                                "model_calls": 0, "api_calls": 0}}

    result = asyncio.run(run_benchmark(FakeSystem(), iterations=3, load_requests=0))
    assert len(result["cases"]) == 3 and all(case["summary"]["requests"] == 3 for case in result["cases"])
    assert all(case["summary"]["error_rate"] == 1 for case in result["cases"])
    assert result["cost_usd"] is None


def test_json_logs_do_not_capture_payload_or_environment(tmp_path):
    handler = configure_logging(tmp_path / "events.jsonl")
    try:
        result = asyncio.run(MultiAgentSystem().process(CASES[0][1]))
        assert result["status"] == "success"
    finally:
        logging.getLogger().removeHandler(handler)
        handler.close()
    lines = (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert all("logger" in json.loads(line) and "event" in json.loads(line) for line in lines)
    assert "SELECT" not in "\n".join(lines) and "sales.csv" not in "\n".join(lines)


def test_live_config_requires_credentials_without_calling_network(monkeypatch, tmp_path):
    for variable in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_KEY", "AZURE_OPENAI_API_KEY", "OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT_MODEL", "LLM_MODEL"):
        monkeypatch.delenv(variable, raising=False)
    with pytest.raises(ValueError):
        live_factory("data_agent", tmp_path)
    with pytest.raises(ValueError):
        MultiAgentSystem(max_concurrency=0)


def test_docker_quoted_environment_is_normalized_without_exposing_key(monkeypatch, tmp_path):
    constructed = []
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", '"https://gateway.example/v1"')
    monkeypatch.setenv("AZURE_OPENAI_KEY", '"fixture-credential"')
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_MODEL", "'fixture-model'")
    monkeypatch.setattr("langchain_openai.ChatOpenAI", lambda **settings: constructed.append(settings) or object())
    live_factory("data_agent", tmp_path)
    assert constructed[0]["base_url"] == "https://gateway.example/v1"
    assert constructed[0]["api_key"] == "fixture-credential" and constructed[0]["model"] == "fixture-model"
    monkeypatch.setenv("RAW_VALUE", "not-quoted")
    assert environment_value("RAW_VALUE") == "not-quoted"


def test_artifacts_are_verified_before_temporary_workspace_cleanup(tmp_path):
    result = asyncio.run(MultiAgentSystem(artifact_dir=tmp_path).process(CASES[1][1]))
    assert result["status"] == "success"
    directory = tmp_path / result["request_id"]
    assert json.loads((directory / "outputs/answer.json").read_text()) == {"revenue": 150, "rows": 3}
    assert set(result["artifacts"]) == {"outputs/report.py", "outputs/answer.json"}
