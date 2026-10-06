import asyncio

import pytest

from day20_multiagents.communication import MessageQueue
from day20_multiagents.coordinator import Coordinator


class MockWorker:
    def __init__(self, name, fail=False, delay=0):
        self.name = name
        self.fail = fail
        self.delay = delay
        self.calls = []
        self.cancelled = False

    async def process_async(self, content, parameters=None):
        self.calls.append((content, parameters))
        try:
            await asyncio.sleep(self.delay)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        if self.fail:
            raise RuntimeError("mock failure")
        return {"status": "success", "result": content, "metadata": {"mock": True}}


def test_coordinator_init():
    queue = MessageQueue()
    worker = MockWorker("data_agent")
    coordinator = Coordinator(None, [worker], queue)
    assert coordinator.workers == {"data_agent": worker}
    assert coordinator.task_queue is queue and coordinator.active_tasks == {}
    assert {"coordinator", "data_agent"} <= queue.queues.keys()
    with pytest.raises(ValueError):
        Coordinator(None, [worker, worker])


def test_parse_request(fake_model, ai_response):
    coordinator = Coordinator(None, [])
    assert coordinator.parse_request("Analyze sales data")["task_type"] == "data_analysis"
    assert coordinator.parse_request("Analyze AND create report")["task_type"] == "complex"
    assert coordinator.parse_request("Review code")["task_type"] == "evaluation"
    assert coordinator.parse_request({"task_type": "code_generation", "content": "Build", "parameters": {"limit": 1}})["parameters"] == {"limit": 1}
    coordinator.model = fake_model(ai_response('{"task_type":"evaluation","parameters":{},"priority":"high"}'))
    assert coordinator.parse_request("Inspect this result")["priority"] == "high"
    with pytest.raises(ValueError):
        coordinator.parse_request("")
    with pytest.raises(ValueError):
        coordinator.parse_request({"task_type": "bad", "content": "x"})


def test_route_task():
    workers = [MockWorker(name) for name in ("data_agent", "code_agent", "evaluator_agent")]
    coordinator = Coordinator(None, workers)
    assert coordinator.route_task("complex") == ["data_agent", "code_agent"]
    assert coordinator.route_task("evaluation") == ["evaluator_agent"]
    with pytest.raises(ValueError):
        coordinator.route_task("unknown")
    with pytest.raises(ValueError):
        Coordinator(None, []).route_task("data_analysis")


def test_execute_tasks_parallel_and_correlated():
    async def scenario():
        started = set()
        ready = asyncio.Event()

        class BarrierWorker(MockWorker):
            async def process_async(self, content, parameters=None):
                started.add(self.name)
                if len(started) == 2:
                    ready.set()
                await ready.wait()
                if self.name == "data_agent":
                    await asyncio.sleep(0.01)
                return {"status": "success", "result": content}

        coordinator = Coordinator(None, [BarrierWorker("data_agent"), BarrierWorker("code_agent")])
        tasks = [{"id": "data", "worker": "data_agent", "content": "value 30"},
                 {"id": "code", "worker": "code_agent", "content": "report.py"}]
        results = await coordinator.execute_tasks(tasks, timeout=1)
        assert [result["task_id"] for result in results] == ["data", "code"]
        assert [result["result"] for result in results] == ["value 30", "report.py"]
        responses = [message for message in coordinator.task_queue.get_message_log() if message.get("type") == "result"]
        assert responses[0]["task_id"] == "code"
        assert coordinator.active_tasks == {}
        assert set(coordinator.task_queue.queues) == {"coordinator", "data_agent", "code_agent"}
    asyncio.run(scenario())


def test_aggregate_results():
    coordinator = Coordinator(None, [])
    result = coordinator.aggregate_results([
        {"task_id": "one", "worker": "data_agent", "status": "success", "result": 30},
        {"task_id": "two", "worker": "data_agent", "status": "success", "result": 40},
        {"task_id": "three", "worker": "code_agent", "status": "error", "error": "cannot execute"},
    ])
    assert result["status"] == "partial"
    assert [item["result"] for item in result["data"]] == [30, 40]
    assert result["errors"][0]["task_id"] == "three"


def test_timeout_cancels_pending_and_preserves_completed():
    async def scenario():
        slow = MockWorker("code_agent", delay=10)
        fast = MockWorker("data_agent")
        coordinator = Coordinator(None, [slow, fast])
        tasks = [{"id": "fast", "worker": "data_agent", "content": "data"},
                 {"id": "slow", "worker": "code_agent", "content": "code"}]
        results = await coordinator.execute_tasks(tasks, timeout=0.03)
        assert [result["status"] for result in results] == ["success", "timeout"]
        assert slow.cancelled and coordinator.active_tasks == {}
        assert not [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
    asyncio.run(scenario())


def test_worker_failure_and_same_worker_tasks():
    async def scenario():
        coordinator = Coordinator(None, [MockWorker("data_agent"), MockWorker("code_agent", fail=True)])
        tasks = [{"id": "one", "worker": "data_agent", "content": "one"},
                 {"id": "two", "worker": "data_agent", "content": "two"},
                 {"id": "failed", "worker": "code_agent", "content": "fail"}]
        results = await coordinator.execute_tasks(tasks, timeout=1)
        assert [result["status"] for result in results] == ["success", "success", "error"]
        assert "mock failure" in results[-1]["error"]
    asyncio.run(scenario())


def test_retry_only_explicitly_idempotent_tasks():
    async def scenario():
        class FlakyWorker(MockWorker):
            async def process_async(self, content, parameters=None):
                self.calls.append(content)
                if len(self.calls) == 1:
                    raise RuntimeError("temporary failure")
                return {"status": "success", "result": content}

        worker = FlakyWorker("data_agent")
        coordinator = Coordinator(None, [worker])
        task = {"id": "retry", "worker": "data_agent", "content": "data", "idempotent": True}
        result = await coordinator.execute_tasks_with_retry([task], timeout=1)
        assert result[0]["status"] == "success" and result[0]["attempts"] == 2
        worker.calls.clear()
        task.pop("idempotent")
        result = await coordinator.execute_tasks_with_retry([task], timeout=1)
        assert result[0]["status"] == "error" and len(worker.calls) == 1
    asyncio.run(scenario())


def test_invalid_tasks_and_resource_limits():
    async def scenario():
        coordinator = Coordinator(None, [MockWorker("data_agent")], max_tasks=1)
        task = {"id": "one", "worker": "data_agent", "content": "x"}
        for tasks in ([], [task, task], [{**task, "worker": "missing"}], [{**task, "content": ""}]):
            with pytest.raises(ValueError):
                await coordinator.execute_tasks(tasks)
        with pytest.raises(ValueError):
            await coordinator.execute_tasks([task], timeout=None)
        assert coordinator.active_tasks == {} and not coordinator._executing
    asyncio.run(scenario())


def test_caller_cancellation_and_reuse_with_stale_messages():
    async def scenario():
        slow = MockWorker("data_agent", delay=10)
        coordinator = Coordinator(None, [slow])
        task = {"id": "slow", "worker": "data_agent", "content": "data"}
        batch = asyncio.create_task(coordinator.execute_tasks([task], timeout=1))
        for unused in range(100):
            if slow.calls:
                break
            await asyncio.sleep(0.001)
        assert slow.calls
        batch.cancel()
        with pytest.raises(asyncio.CancelledError):
            await batch
        assert slow.cancelled and not coordinator._executing and coordinator.active_tasks == {}
        await coordinator.task_queue.send_message("coordinator", "data_agent",
                                                  {"type": "task", "task_id": "old", "run_id": "previous"})
        slow.delay = 0
        results = await coordinator.execute_tasks([task], timeout=1)
        assert results[0]["status"] == "success"
    asyncio.run(scenario())
