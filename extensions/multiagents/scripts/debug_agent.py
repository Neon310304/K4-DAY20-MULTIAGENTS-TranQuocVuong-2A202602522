import argparse
import asyncio
import json
import tempfile
from pathlib import Path

from day20_multiagents.agents import CodeAgent, DataAgent, EvaluatorAgent
from day20_multiagents.runtime import live_factory, offline_factory
from day20_multiagents.system import REFERENCE, prepare_workspace


def main():
    parser = argparse.ArgumentParser(description="Run a single worker on disposable local fixtures")
    parser.add_argument("--agent", choices=["data_agent", "code_agent", "evaluator_agent"], default="data_agent")
    parser.add_argument("--task", default="Calculate Q3 revenue, using the supplied fixture tools")
    parser.add_argument("--mode", choices=["offline", "live"], default="offline")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="day20-debug-worker-") as directory:
        workspace = Path(directory)
        prepare_workspace(workspace)
        model = (live_factory if args.mode == "live" else offline_factory)(args.agent, workspace)
        worker = DataAgent(model, workspace, db_path="sales.db") if args.agent == "data_agent" else \
            CodeAgent(model, workspace) if args.agent == "code_agent" else EvaluatorAgent(model, workspace=workspace)
        parameters = {"actual": REFERENCE, "expected": REFERENCE,
                      "ratings": {"accuracy": 85, "completeness": 90, "clarity": 80, "performance": 85}}
        try:
            result = asyncio.run(asyncio.wait_for(worker.process_async(args.task, parameters), timeout=90))
            print(json.dumps(result, ensure_ascii=False, indent=2))
        finally:
            if args.agent == "data_agent":
                worker.close()


if __name__ == "__main__":
    main()
