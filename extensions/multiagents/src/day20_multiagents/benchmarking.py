import asyncio
import math
import statistics
import time


CASES = [("Simple data query", "Calculate total Q3 revenue from sales data"),
         ("Code generation", "Write a Python script to read CSV and save a report"),
         ("Complex workflow", "Analyze Q3 sales data and create chart and evaluate result")]


def percentile(values: list[float], fraction: float) -> float:
    if not values or not 0 <= fraction <= 1:
        raise ValueError("Percentile requires values and a fraction in [0, 1]")
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summarize(name: str, records: list[dict], elapsed: float) -> dict:
    if not records or elapsed <= 0:
        raise ValueError("Cannot summarize an empty or invalid measurement")
    latencies = [record["latency_seconds"] for record in records]
    failures = sum(record["status"] != "success" or not record["validation_passed"] for record in records)
    complete = all(record["metrics"]["usage_complete"] for record in records)
    known = {key: sum(record["metrics"]["known_tokens"][key] for record in records)
             for key in ("input_tokens", "output_tokens", "total_tokens")}
    busy = {}
    for record in records:
        for stage in record["stages"]:
            busy[stage["worker"]] = busy.get(stage["worker"], 0) + stage["seconds"]
    capacity = max(record.get("capacity", 1) for record in records)
    return {"name": name, "requests": len(records), "successes": len(records) - failures,
            "min": min(latencies), "max": max(latencies), "avg": statistics.mean(latencies),
            "median": statistics.median(latencies), "p50": percentile(latencies, 0.5), "p99": percentile(latencies, 0.99),
            "wall_seconds": elapsed, "throughput_per_minute": 60 * len(records) / elapsed,
            "error_rate": failures / len(records), "usage_complete": complete, "known_tokens": known,
            "tokens": known if complete else None,
            "tokens_per_100_requests": 100 * known["total_tokens"] / len(records) if complete else None,
            "model_calls": sum(record["metrics"]["model_calls"] for record in records),
            "api_calls": sum(record["metrics"]["api_calls"] for record in records),
            "worker_utilization": {name: seconds / (elapsed * capacity) for name, seconds in busy.items()},
            "utilization_definition": "sum stage wall-time / (batch wall-time * max_concurrency); includes API waiting, not CPU usage"}


async def run_benchmark(system, iterations: int = 3, load_requests: int = 10, timeout: float = 90) -> dict:
    if isinstance(iterations, bool) or not isinstance(iterations, int) or not 3 <= iterations <= 10:
        raise ValueError("iterations must be within 3-10")
    if isinstance(load_requests, bool) or not isinstance(load_requests, int) or not 0 <= load_requests <= 20:
        raise ValueError("load_requests must be within 0-20")
    cases = []
    for name, request in CASES:
        started = time.perf_counter()
        records = []
        for iteration in range(iterations):
            record = await system.process(request, timeout=timeout, debug=True)
            record["iteration"] = iteration + 1
            record["capacity"] = 1
            records.append(record)
        cases.append({"summary": summarize(name, records, time.perf_counter() - started), "records": records})
    load = None
    if load_requests:
        started = time.perf_counter()
        records = await asyncio.gather(*[system.process(CASES[0][1], timeout=timeout, debug=True)
                                        for unused in range(load_requests)])
        for record in records:
            record["capacity"] = system.max_concurrency
        load = {"summary": summarize("Concurrent data requests", records, time.perf_counter() - started), "records": records}
    return {"mode": system.mode, "iterations": iterations, "max_concurrency": system.max_concurrency,
            "cases": cases, "load": load, "cost_usd": None,
            "cost_note": "No verified YesScale tariff/invoice; no fabricated USD. API counts are logical model invocations, not SDK retries.",
            "percentile_method": "linear interpolation at (n-1)*fraction; 3 iterations are not a reliable tail/SLO estimate"}
