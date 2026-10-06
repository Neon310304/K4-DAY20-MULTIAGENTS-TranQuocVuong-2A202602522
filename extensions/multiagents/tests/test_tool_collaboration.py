import asyncio
import importlib.util
import json
from pathlib import Path


def test_sql_chart_evaluation_collaboration(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts/test_tool_integration.py"
    spec = importlib.util.spec_from_file_location("tool_collaboration", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    summary = asyncio.run(module.run_demo(tmp_path))
    assert summary["database_rows"] == 50
    assert summary["sql_total"] == summary["code_total"] == 1275
    assert summary["offline_scripted_models"] and summary["api_calls"] == 0
    assert (tmp_path / "outputs/sales_chart.png").stat().st_size == summary["chart_bytes"]
    messages = json.loads((tmp_path / "communication.json").read_text(encoding="utf-8"))
    assert [message["task_id"] for message in messages if message["type"] == "result"] == ["data", "chart", "evaluation"]
    assert len({message["run_id"] for message in messages}) == 3
