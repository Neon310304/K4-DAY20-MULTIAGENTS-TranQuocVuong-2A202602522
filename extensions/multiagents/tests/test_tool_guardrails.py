import asyncio
import json
import logging
import sqlite3

import pytest

from day20_multiagents.agents import EvaluatorAgent
from day20_multiagents.toolkits import AggregationTool, ComparisonTool, CreateFileTool, PythonREPLTool, QueryDatabaseTool, ReportGeneratorTool, RunScriptTool
from day20_multiagents.tools import BaseTool


def test_tool_contract_and_payload_free_logging(tmp_path, caplog):
    with pytest.raises(TypeError):
        BaseTool("abstract", "Cannot execute", {})
    tool = CreateFileTool(tmp_path)
    with caplog.at_level(logging.INFO, logger="day20_multiagents.tools"):
        tool.invoke({"filename": "private.txt", "content": "private-payload-marker"})
        with pytest.raises(ValueError):
            tool.invoke({"filename": "../private-path-marker", "content": "private-payload-marker"})
    assert "tool_start tool=create_file" in caplog.text and "status=success" in caplog.text
    assert "status=error" in caplog.text and "seconds=" in caplog.text
    assert "private-payload-marker" not in caplog.text and "private-path-marker" not in caplog.text


def test_sql_limits_authorizer_and_connection_recovery(tmp_path):
    with sqlite3.connect(tmp_path / "data.db") as connection:
        connection.execute("CREATE TABLE records (amount INTEGER)")
        connection.executemany("INSERT INTO records VALUES (?)", [(value,) for value in range(6)])
    tool = QueryDatabaseTool(tmp_path, "data.db", timeout=0.1)
    try:
        result = tool.invoke({"query": "SELECT amount FROM records ORDER BY amount LIMIT 4", "limit": 2})
        assert result["rows"] == [[0], [1]] and result["truncated"]
        for query in ("WITH source AS (SELECT 1) DELETE FROM records", "SELECT 1; DROP TABLE records",
                      "SELECT load_extension('not-allowed')"):
            with pytest.raises(sqlite3.DatabaseError):
                tool.invoke({"query": query})
        with pytest.raises(sqlite3.DatabaseError):
            tool.invoke({"query": "WITH RECURSIVE sequence(value) AS (SELECT 1 UNION ALL SELECT value+1 FROM sequence) SELECT SUM(value) FROM sequence"})
        assert tool.invoke({"query": "SELECT COUNT(*) FROM records"})["rows"] == [[6]]
        assert tool.invoke({"query": "SELECT 'DROP is data'"})["rows"] == [["DROP is data"]]
        with pytest.raises(ValueError):
            tool.invoke({"query": "SELECT 1", "limit": 1001})
    finally:
        tool.close()


def test_cached_sql_connection_serializes_async_calls(tmp_path):
    with sqlite3.connect(tmp_path / "data.db") as connection:
        connection.execute("CREATE TABLE records (amount INTEGER)")
        connection.execute("INSERT INTO records VALUES (30)")
    tool = QueryDatabaseTool(tmp_path, "data.db")

    async def scenario():
        results = await asyncio.gather(*[tool.ainvoke({"query": "SELECT SUM(amount) FROM records"}) for unused in range(6)])
        assert all(result["rows"] == [[30]] for result in results)

    try:
        asyncio.run(scenario())
        first = tool.connect()
        tool.close()
        assert tool.connect() is not first
    finally:
        tool.close()


def test_aggregation_and_comparison_require_real_reference_values():
    aggregation = AggregationTool()
    assert aggregation.invoke({"values": [10, 20], "operation": "mean"})["value"] == 15
    for values, operation in (([float("nan")], "sum"), ([True], "sum"), ([], "mean"), (["10"], "sum")):
        with pytest.raises(ValueError):
            aggregation.invoke({"values": values, "operation": operation})
    comparison = ComparisonTool()
    assert comparison.invoke({"actual": {"total": 30.001}, "expected": {"total": 30}, "tolerance": 0.01})["valid"]
    result = comparison.invoke({"actual": {"count": True}, "expected": {"count": 1, "total": 30}})
    assert not result["valid"] and len(result["mismatches"]) == 2
    with pytest.raises(ValueError):
        comparison.invoke({"actual": {}, "expected": {}})


def test_report_schema_path_validation_and_worker_integration(tmp_path, fake_model, ai_response):
    evaluation = {"score": 81, "feedback": "Provided evidence checked", "issues": [], "suggestions": []}
    arguments = {"filename": "reports/evaluation.md", "title": "Local evaluation", "evaluation": evaluation,
                 "evidence": {"sql_total": 30, "code_total": 30}}
    tool = ReportGeneratorTool(tmp_path)
    with pytest.raises(ValueError):
        tool.invoke({**arguments, "filename": "../outside.md"})
    with pytest.raises(ValueError):
        tool.invoke({**arguments, "evaluation": {**evaluation, "score": 101}})
    assert not (tmp_path / "reports/evaluation.md").exists()
    model = fake_model(ai_response("", ("report_generator", arguments)), ai_response(json.dumps(evaluation)))
    result = EvaluatorAgent(model, workspace=tmp_path).process("Write the evidence report")
    assert result["status"] == "success" and result["metadata"]["tools_used"] == 1
    content = (tmp_path / "reports/evaluation.md").read_text(encoding="utf-8")
    assert "81/100 (B)" in content and '"sql_total": 30' in content
    with pytest.raises(FileExistsError):
        tool.invoke(arguments)


def test_new_tool_failures_are_worker_errors(tmp_path, fake_model, ai_response):
    model = fake_model(ai_response("", ("comparison", {"actual": {}, "expected": {}})))
    result = EvaluatorAgent(model, workspace=tmp_path).process("Compare output")
    assert result["status"] == "error" and result["result"] is None


def test_python_resource_configuration_and_bounded_output(tmp_path):
    for timeout, memory in ((True, 512), (float("inf"), 512), (1, 63), (1, 64.5)):
        with pytest.raises(ValueError):
            PythonREPLTool(tmp_path, timeout=timeout, memory_mb=memory)
    tool = PythonREPLTool(tmp_path, timeout=2, memory_mb=64)
    output = tool.invoke({"code": "import json, resource; print(json.dumps([resource.getrlimit(resource.RLIMIT_AS), resource.getrlimit(resource.RLIMIT_FSIZE), resource.getrlimit(resource.RLIMIT_NOFILE)]))"})
    assert json.loads(output["stdout"]) == [[64 * 1024 * 1024] * 2, [65536] * 2, [64] * 2]
    output = tool.invoke({"code": "print('x' * 20000)"})
    assert len(output["stdout"]) == 8192 and output["stdout_truncated"] and not output["stderr_truncated"]
    with pytest.raises(ValueError):
        tool.invoke({"code": "x" * 65537})
    with pytest.raises(RuntimeError, match="MemoryError"):
        tool.invoke({"code": "data = bytearray(128 * 1024 * 1024)"})


def test_run_script_preserves_file_main_and_sibling_imports(tmp_path):
    directory = tmp_path / "scripts"
    directory.mkdir()
    (directory / "helper.py").write_text("TOTAL = 30\n", encoding="utf-8")
    script = directory / "main.py"
    script.write_text("import helper, json, sys\nif __name__ == '__main__':\n    print(json.dumps({'file': __file__, 'argv': sys.argv, 'total': helper.TOTAL}))\n", encoding="utf-8")
    python_tool = PythonREPLTool(tmp_path)
    tool = RunScriptTool(python_tool.sandbox)
    output = tool.invoke({"filename": "scripts/main.py"})
    assert json.loads(output["stdout"]) == {"file": str(script), "argv": [str(script)], "total": 30}
