import asyncio
import sqlite3
import sys

import pytest

from day20_multiagents.agents import CodeAgent, DataAgent, EvaluatorAgent
from day20_multiagents.tools import PythonSandbox


def test_csv_preview_validation_and_grouped_aggregate(tmp_path, fake_model):
    (tmp_path / "input.csv").write_text("region,amount\nNorth,10\nNorth,20\nSouth,\n")
    agent = DataAgent(fake_model(), tmp_path)
    preview = agent.tools["csv_parser"].invoke({"filename": "input.csv", "limit": 1})
    assert preview["rows_total"] == 3 and len(preview["rows"]) == 1 and preview["preview_truncated"]
    validation = agent.tools["data_validation"].invoke({"filename": "input.csv", "required_columns": ["missing"]})
    assert not validation["valid"] and validation["empty_cells"] == 1
    result = agent.tools["pandas_analysis"].invoke({"filename": "input.csv", "column": "amount", "operation": "sum"})
    assert result["value"] == 30


def test_csv_and_tool_argument_limits(tmp_path, fake_model):
    (tmp_path / "bad.csv").write_text("field,other\none\n")
    agent = DataAgent(fake_model(), tmp_path)
    with pytest.raises(ValueError):
        agent.tools["csv_parser"].invoke({"filename": "bad.csv"})
    with pytest.raises(ValueError):
        agent.tools["csv_parser"].invoke({"filename": "bad.csv", "limit": -1})
    with pytest.raises(ValueError):
        agent.tools["csv_parser"].invoke({"filename": "bad.csv", "limit": True})
    with pytest.raises(ValueError):
        agent.tools["pandas_analysis"].invoke({"filename": "bad.csv", "column": "field", "operation": "eval"})


def test_sql_is_read_only_and_bounded(tmp_path, fake_model):
    database = tmp_path / "data.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE records (amount INTEGER)")
        connection.executemany("INSERT INTO records VALUES (?)", [(10,), (20,)])
    agent = DataAgent(fake_model(), tmp_path, db_path="data.db")
    tool = agent.tools["query_database"]
    assert tool.invoke({"query": "SELECT SUM(amount) AS total FROM records"})["rows"] == [[30]]
    for query in ("DELETE FROM records", "WITH source AS (SELECT 1) DELETE FROM records", "SELECT 1; DELETE FROM records"):
        with pytest.raises((ValueError, sqlite3.DatabaseError)):
            tool.invoke({"query": query})
    assert tool.invoke({"query": "SELECT COUNT(*) FROM records"})["rows"] == [[2]]


def test_file_tools_reject_escape_symlink_and_overwrite(tmp_path, fake_model):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside.txt"
    outside.write_text("private")
    agent = CodeAgent(fake_model(), workspace)
    tool = agent.tools["create_file"]
    with pytest.raises(ValueError):
        tool.invoke({"filename": "../outside.txt", "content": "changed"})
    (workspace / "link.txt").symlink_to(outside)
    with pytest.raises(ValueError):
        agent.tools["edit_file"].invoke({"filename": "link.txt", "old_text": "private", "new_text": "changed"})
    tool.invoke({"filename": "new.txt", "content": "hello"})
    with pytest.raises(FileExistsError):
        tool.invoke({"filename": "new.txt", "content": "overwrite"})
    assert outside.read_text() == "private" and (workspace / "new.txt").read_text() == "hello"


def test_edit_matches_once(tmp_path, fake_model):
    (tmp_path / "file.txt").write_text("hello hello")
    agent = CodeAgent(fake_model(), tmp_path)
    with pytest.raises(ValueError):
        agent.tools["edit_file"].invoke({"filename": "file.txt", "old_text": "hello", "new_text": "bye"})
    agent.tools["edit_file"].invoke({"filename": "file.txt", "old_text": "hello hello", "new_text": "bye"})
    assert (tmp_path / "file.txt").read_text() == "bye"


@pytest.mark.skipif(sys.platform != "linux", reason="Execution tools intentionally require Linux")
def test_python_limits_and_secret_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_ONLY_SECRET", "must-not-be-inherited")
    sandbox = PythonSandbox(tmp_path, timeout=0.3)
    result = sandbox.execute("import os; print(os.environ.get('TEST_ONLY_SECRET', 'absent'))")
    assert result["stdout"].strip() == "absent"
    with pytest.raises(TimeoutError):
        sandbox.execute("import time; time.sleep(10)")
    with pytest.raises(RuntimeError):
        sandbox.execute("raise ValueError('expected failure')")


def test_evaluation_score_and_validation(fake_model):
    agent = EvaluatorAgent(fake_model())
    score = agent.tools["scoring"].invoke({"accuracy": 90, "completeness": 80, "clarity": 100, "performance": 50})
    assert score["score"] == 81 and score["grade"] == "B"
    with pytest.raises(ValueError):
        agent.tools["scoring"].invoke({"accuracy": 101, "completeness": 80, "clarity": 100, "performance": 50})
    assert not agent.tools["validation"].invoke({"value": {}, "required_fields": ["score"]})["valid"]
    assert agent.tools["quality_check"].invoke({"content": "TOTAL: 30", "required_items": ["total"]})["valid"]
    assert agent.tools["feedback_generator"].invoke({"issues": ["missing test"]})["suggestions"]
