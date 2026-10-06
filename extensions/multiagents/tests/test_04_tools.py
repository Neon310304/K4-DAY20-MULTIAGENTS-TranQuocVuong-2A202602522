import sqlite3

import pytest

from day20_multiagents.toolkits import CreateFileTool, PythonREPLTool, QueryDatabaseTool, ScoringTool


def test_query_database_tool(tmp_path):
    with sqlite3.connect(tmp_path / "sales.db") as connection:
        connection.execute("CREATE TABLE sales (year INTEGER, amount INTEGER)")
        connection.executemany("INSERT INTO sales VALUES (?, ?)", [(2026, 10), (2026, 20), (2025, 5)])
    tool = QueryDatabaseTool(tmp_path, "sales.db")
    try:
        assert tool.validate_input({"query": "SELECT amount FROM sales"})
        result = tool.invoke({"query": "SELECT amount FROM sales WHERE year=2026 ORDER BY amount"})
        assert result["columns"] == ["amount"] and result["rows"] == [[10], [20]]
        cached = tool.connect()
        assert tool.invoke({"query": "SELECT SUM(amount) FROM sales WHERE year=2026"})["rows"] == [[30]]
        assert tool.connect() is cached
        with pytest.raises(ValueError):
            tool.invoke({"query": "DROP TABLE sales"})
    finally:
        tool.close()
    assert tool.connection is None


def test_python_repl_tool(tmp_path):
    tool = PythonREPLTool(tmp_path, timeout=1)
    assert tool.validate_input({"code": "print(sum([10, 20]))"})
    result = tool.invoke({"code": "print(sum([10, 20]))"})
    assert result["exit_code"] == 0 and result["stdout"].strip() == "30"
    with pytest.raises(TimeoutError):
        tool.invoke({"code": "import time; time.sleep(10)"})


def test_create_file_tool(tmp_path):
    tool = CreateFileTool(tmp_path)
    result = tool.invoke({"filename": "outputs/report.txt", "content": "Doanh thu: 30"})
    assert (tmp_path / result["path"]).read_text(encoding="utf-8") == "Doanh thu: 30"
    assert result["bytes"] == len("Doanh thu: 30".encode("utf-8"))
    with pytest.raises(ValueError):
        tool.invoke({"filename": "../outside.txt", "content": "no"})
    with pytest.raises(FileExistsError):
        tool.invoke({"filename": "outputs/report.txt", "content": "overwrite"})


def test_scoring_tool():
    tool = ScoringTool()
    result = tool.invoke({"accuracy": 85, "completeness": 90, "clarity": 80, "performance": 85})
    assert result["score"] == 85.5 and result["grade"] == "B"
    assert sum(result["weights"].values()) == 1
    for arguments in ({"accuracy": 101, "completeness": 90, "clarity": 80, "performance": 85},
                      {"accuracy": True, "completeness": 90, "clarity": 80, "performance": 85},
                      {"accuracy": "85", "completeness": 90, "clarity": 80, "performance": 85}):
        with pytest.raises(ValueError):
            tool.invoke(arguments)
