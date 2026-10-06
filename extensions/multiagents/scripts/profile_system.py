import argparse
import asyncio
import cProfile
import io
import json
import pstats
from pathlib import Path

from day20_multiagents.benchmarking import CASES
from day20_multiagents.system import MultiAgentSystem


def main():
    parser = argparse.ArgumentParser(description="Offline cProfile; no paid APIs or production latency claim")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    records = []

    async def run():
        system = MultiAgentSystem()
        for index in range(5):
            records.append(await system.process(CASES[index % 3][1]))

    profiler = cProfile.Profile()
    profiler.enable()
    asyncio.run(run())
    profiler.disable()
    profiler.dump_stats(args.output / "profile.pstats")
    buffer = io.StringIO()
    pstats.Stats(profiler, stream=buffer).sort_stats("cumulative").print_stats(25)
    (args.output / "profile.txt").write_text(buffer.getvalue(), encoding="utf-8")
    (args.output / "requests.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(buffer.getvalue())


if __name__ == "__main__":
    main()
