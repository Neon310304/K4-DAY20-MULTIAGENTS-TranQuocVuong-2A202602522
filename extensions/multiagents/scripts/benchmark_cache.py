import argparse
import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from day20_multiagents.benchmarking import CASES, summarize
from day20_multiagents.caching import CachedDataSystem
from day20_multiagents.system import CSV_INPUT, MultiAgentSystem


async def measure(iterations: int) -> dict:
    request = {"task_type": "data_analysis", "parameters": {}, "content": CASES[0][1]}
    revision = hashlib.sha256(CSV_INPUT.encode("utf-8")).hexdigest()
    cached = CachedDataSystem(MultiAgentSystem(), "offline-q3-policy-v1", ttl_seconds=60)
    cases = []
    for name, system in (("Uncached", MultiAgentSystem()), ("Cached including cold miss", cached)):
        records = []
        started = time.perf_counter()
        for index in range(iterations):
            options = {"scope": "lab-student", "dataset_revision": revision} if system is cached else {}
            record = await system.process(request, **options)
            record["iteration"] = index + 1
            records.append(record)
        cases.append({"summary": summarize(name, records, time.perf_counter() - started), "records": records})
    return {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "mode": "offline", "iterations": iterations,
            "request": request, "dataset_revision": revision, "cases": cases, "cache_statistics": cached.statistics(),
            "cost_usd": None, "note": "Same verified fixture, sequential repeated read-only request; includes first cold miss. "
            "No paid API or live latency/cost claim; no single-flight or cross-process cache."}


def main():
    parser = argparse.ArgumentParser(description="Offline controlled bonus cache comparison, no paid API")
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 3 <= args.iterations <= 100:
        parser.error("iterations must be within 3-100")
    args.output.mkdir(parents=True, exist_ok=False)
    result = asyncio.run(measure(args.iterations))
    (args.output / "cache_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for case in result["cases"]:
        value = case["summary"]
        print(f"{value['name']}: {value['successes']}/{value['requests']} verified, avg={value['avg']:.6f}s "
              f"p50={value['p50']:.6f}s p99={value['p99']:.6f}s calls={value['model_calls']}")
    print(json.dumps(result["cache_statistics"]))


if __name__ == "__main__":
    main()
