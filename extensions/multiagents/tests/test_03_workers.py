import asyncio
import json

from langchain_core.messages import ToolMessage

from day20_multiagents.agents import BaseWorker, CodeAgent, DataAgent, EvaluatorAgent
from day20_multiagents.tools import Tool, schema


def test_data_agent_init(tmp_path, fake_model):
    worker = DataAgent(fake_model(), tmp_path)
    assert worker.name == "data_agent"
    assert set(worker.tools) == {"csv_parser", "pandas_analysis", "query_database", "data_validation", "aggregation"}
    assert "data analysis" in worker.system_prompt
    assert len(worker.model.tools) == 5


def test_data_agent_process(tmp_path, fake_model, ai_response):
    (tmp_path / "sales.csv").write_text("region,amount\nNorth,10\nNorth,20\nSouth,5\n")
    model = fake_model(ai_response("", ("pandas_analysis", {
        "filename": "sales.csv", "column": "amount", "operation": "sum", "group_by": "region"})),
        ai_response("North total: 30; South total: 5"))
    result = DataAgent(model, tmp_path).process("Analyze regional revenue")
    assert result["status"] == "success" and "30" in result["result"]
    assert result["metadata"]["tools_used"] == 1
    feedback = [message for message in model.calls[-1] if isinstance(message, ToolMessage)]
    assert json.loads(feedback[0].content)["groups"] == {"North": 30, "South": 5}


def test_code_agent_process(tmp_path, fake_model, ai_response):
    model = fake_model(ai_response("", ("create_file", {"filename": "report.py", "content": "print(2 + 3)"})),
                       ai_response("", ("run_script", {"filename": "report.py"})), ai_response("report.py verified: 5"))
    worker = CodeAgent(model, tmp_path)
    result = asyncio.run(worker.process_async("Create and run a report"))
    assert result["status"] == "success" and result["metadata"]["tools_used"] == 2
    assert (tmp_path / "report.py").read_text() == "print(2 + 3)"
    feedback = [message for message in model.calls[-1] if isinstance(message, ToolMessage)]
    assert json.loads(feedback[-1].content)["stdout"].strip() == "5"


def test_evaluator_agent(fake_model, ai_response):
    content = json.dumps({"score": 84, "feedback": "Check supported inputs", "issues": ["Missing boundary test"],
                          "suggestions": ["Add a boundary test"]})
    model = fake_model(ai_response("", ("scoring", {
        "accuracy": 90, "completeness": 80, "clarity": 85, "performance": 80})), ai_response(content))
    result = asyncio.run(EvaluatorAgent(model).process_async("Evaluate this supplied test evidence"))
    assert result["status"] == "success" and result["result"]["score"] == 84
    feedback = [message for message in model.calls[-1] if isinstance(message, ToolMessage)]
    assert json.loads(feedback[0].content)["score"] == 84


def test_multiple_tool_calls_keep_conversation(tmp_path, fake_model, ai_response):
    (tmp_path / "data.csv").write_text("value\n2\n3\n")
    model = fake_model(ai_response("", ("csv_parser", {"filename": "data.csv"}),
                                    ("data_validation", {"filename": "data.csv", "required_columns": ["value"]})),
                       ai_response("validated"))
    result = DataAgent(model, tmp_path).process("Inspect the input")
    assert result["metadata"]["tools_used"] == 2
    assert [message.tool_call_id for message in model.calls[-1] if isinstance(message, ToolMessage)] == ["0", "1"]
    assert len(model.calls[-1]) == 5


def test_unknown_tool_and_model_error_are_structured(tmp_path, fake_model, ai_response):
    worker = DataAgent(fake_model(ai_response("", ("unknown", {}))), tmp_path)
    assert "Unknown tool" in worker.process("Analyze")["error"]
    worker = DataAgent(fake_model(RuntimeError("model unavailable")), tmp_path)
    result = asyncio.run(worker.process_async("Analyze"))
    assert result["status"] == "error" and "model unavailable" in result["error"]


def test_iteration_limit_and_request_local_counts(fake_model, ai_response):
    tool = Tool("ping", "Ping", schema({}, []), lambda: "pong")
    worker = BaseWorker("worker", fake_model(ai_response("", ("ping", {}))), [tool], "Test", max_iterations=1)
    result = worker.process("Run")
    assert result["status"] == "error" and "iteration limit" in result["error"]
    assert result["metadata"]["tools_used"] == 1
    model = fake_model(ai_response("", ("ping", {})), ai_response("first"), ai_response("second"))
    worker = BaseWorker("worker", model, [tool], "Test")
    assert worker.process("One")["metadata"]["tools_used"] == 1
    assert worker.process("Two")["metadata"]["tools_used"] == 0


def test_invalid_input_and_evaluation_schema(tmp_path, fake_model, ai_response):
    worker = DataAgent(fake_model(), tmp_path)
    assert worker.process("")["status"] == "error"
    assert worker.process("Analyze", parameters=[])["status"] == "error"
    for content in ['not JSON', '{"score": 101}', '{"score": true, "feedback": "x", "issues": [], "suggestions": []}']:
        result = EvaluatorAgent(fake_model(ai_response(content))).process("Evaluate")
        assert result["status"] == "error" and result["result"] is None
