import argparse
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from day20_multiagents.benchmarking import run_benchmark
from day20_multiagents.observability import configure_logging
from day20_multiagents.runtime import live_factory, offline_factory
from day20_multiagents.system import MultiAgentSystem


def main():
    parser = argparse.ArgumentParser(description="Independent extension benchmark; live mode calls paid APIs")
    parser.add_argument("--mode", choices=["offline", "live"], default="offline")
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--load-requests", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True, help="New directory, never overwrite old results")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    handler = configure_logging(args.output / "events.jsonl")
    try:
        system = MultiAgentSystem(live_factory if args.mode == "live" else offline_factory, args.mode, args.concurrency,
                                  artifact_dir=args.output / "artifacts")
        result = asyncio.run(run_benchmark(system, args.iterations, args.load_requests))
        result.update({"timestamp_utc": datetime.now(timezone.utc).isoformat(),
                       "model": os.getenv("AZURE_OPENAI_DEPLOYMENT_MODEL") if args.mode == "live" else "scripted fixture"})
        (args.output / "benchmark_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        for case in result["cases"] + ([result["load"]] if result["load"] else []):
            summary = case["summary"]
            print(f"{summary['name']}: {summary['successes']}/{summary['requests']} verified, "
                  f"avg={summary['avg']:.3f}s p50={summary['p50']:.3f}s p99={summary['p99']:.3f}s "
                  f"throughput={summary['throughput_per_minute']:.2f}/min tokens={summary['tokens']}")
        print(f"Results saved: {args.output / 'benchmark_results.json'}")
    finally:
        logging.getLogger().removeHandler(handler)
        handler.close()


if __name__ == "__main__":
    main()
