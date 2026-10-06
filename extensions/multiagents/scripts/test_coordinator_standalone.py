import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from day20_multiagents.coordinator import Coordinator


class MockWorker:
    def __init__(self, name, slow=False):
        self.name = name
        self.slow = slow
        self.cancelled = False

    async def process_async(self, content, parameters=None):
        try:
            await asyncio.sleep(10 if self.slow else 0)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        return {"status": "success", "result": f"mock {self.name}: {content}"}


async def main():
    coordinator = Coordinator(None, [MockWorker("data_agent"), MockWorker("code_agent")])
    simple = await coordinator.handle_request("Analyze sales data", timeout=1)
    assert simple["status"] == "success" and len(simple["data"]) == 1
    print("Test 1: simple task - PASS")
    complex_result = await coordinator.handle_request("Analyze data and create report", timeout=1)
    assert complex_result["status"] == "success" and complex_result["data"] and complex_result["code"]
    print("Test 2: multiple workers via correlated queue - PASS")
    slow = MockWorker("data_agent", slow=True)
    timed = await Coordinator(None, [slow]).handle_request("Analyze data", timeout=0.02)
    assert timed["status"] == "error" and timed["errors"][0]["status"] == "timeout" and slow.cancelled
    print("Test 3: timeout cancellation, explicit failure (no fabricated fallback) - PASS")
    print("All coordinator standalone tests passed! (3/3; mock workers, no API)")


if __name__ == "__main__":
    asyncio.run(main())
