import argparse
import asyncio
import json
import platform
import resource
import time
from datetime import datetime, timezone
from pathlib import Path

from day20_multiagents.benchmarking import CASES
from day20_multiagents.system import MultiAgentSystem


def resident_kib() -> int:
    values = Path("/proc/self/status").read_text(encoding="utf-8").splitlines()
    return int(next(value for value in values if value.startswith("VmRSS:")).split()[1])


def snapshot() -> dict:
    parent = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {"parent_rss_kib": resident_kib(), "parent_peak_rss_kib": parent.ru_maxrss,
            "children_max_peak_rss_kib": children.ru_maxrss, "parent_user_seconds": parent.ru_utime,
            "parent_system_seconds": parent.ru_stime, "children_user_seconds": children.ru_utime,
            "children_system_seconds": children.ru_stime}


async def measure() -> dict:
    system = MultiAgentSystem()
    phases = []
    for name, request, count in [(name, request, 1) for name, request in CASES] + [("Concurrent data", CASES[0][1], 10)]:
        samples = []
        finished = asyncio.Event()

        async def sample():
            while not finished.is_set():
                samples.append(resident_kib())
                await asyncio.sleep(0.005)

        before = snapshot()
        samples.append(before["parent_rss_kib"])
        sampler = asyncio.create_task(sample())
        started = time.perf_counter()
        try:
            records = await asyncio.gather(*[system.process(request) for unused in range(count)])
            elapsed = time.perf_counter() - started
        finally:
            finished.set()
            await sampler
        after = snapshot()
        cpu = {key: after[key] - before[key] for key in before if key.endswith("seconds")}
        phases.append({"name": name, "requests": count, "successes": sum(record["validation_passed"] for record in records),
                       "wall_seconds": elapsed, "before": before, "after": after, "cpu_delta_seconds": cpu,
                       "parent_cpu_percent_one_core": 100 * (cpu["parent_user_seconds"] + cpu["parent_system_seconds"]) / elapsed,
                       "sampled_parent_peak_rss_kib": max(samples + [after["parent_rss_kib"]]), "rss_samples": len(samples),
                       "records": [{"request_id": record["request_id"], "status": record["status"],
                                    "latency_seconds": record["latency_seconds"]} for record in records]})
    return {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
            "platform": platform.platform(), "mode": "offline", "max_concurrency": system.max_concurrency, "phases": phases,
            "method": "Linux /proc/self/status VmRSS sampled every 5ms; getrusage self/terminated children CPU deltas. "
            "ru_maxrss is a process-lifetime high-water mark; children value is max, not sum or concurrent peak. "
            "Sampling misses sub-5ms peaks, excludes child RSS; parent baseline includes imported packages. "
            "CPU percent uses one-core wall normalization, includes worker threads; no LLM service/container-wide measurement."}


def main():
    parser = argparse.ArgumentParser(description="Offline Linux parent/child CPU and RSS probe; no paid API")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if platform.system() != "Linux":
        parser.error("Run in the Linux lab container")
    args.output.mkdir(parents=True, exist_ok=False)
    result = asyncio.run(measure())
    (args.output / "resource_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for phase in result["phases"]:
        print(f"{phase['name']}: {phase['successes']}/{phase['requests']}, wall={phase['wall_seconds']:.4f}s "
              f"parent peak={phase['sampled_parent_peak_rss_kib']} KiB, parent CPU={phase['parent_cpu_percent_one_core']:.1f}%")


if __name__ == "__main__":
    main()
