import argparse
import asyncio
import json
import logging
from pathlib import Path

from day20_multiagents.observability import configure_logging
from day20_multiagents.runtime import live_factory, offline_factory
from day20_multiagents.system import MultiAgentSystem


def main():
    parser = argparse.ArgumentParser(description="Debug a fixture request; no secrets in CLI arguments")
    parser.add_argument("--mode", choices=["offline", "live"], default="offline")
    parser.add_argument("--request", default="Analyze Q3 sales data and create chart and evaluate result")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    handler = configure_logging(args.output / "events.jsonl")
    try:
        factory = live_factory if args.mode == "live" else offline_factory
        result = asyncio.run(MultiAgentSystem(factory, args.mode, artifact_dir=args.output / "artifacts").process(args.request, debug=True))
        (args.output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": result["status"], "checks": result["checks"], "stages": result["stages"]}, indent=2))
    finally:
        logging.getLogger().removeHandler(handler)
        handler.close()


if __name__ == "__main__":
    main()
