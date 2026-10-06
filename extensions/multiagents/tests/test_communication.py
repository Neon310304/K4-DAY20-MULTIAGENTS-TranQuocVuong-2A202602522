import asyncio
from datetime import datetime
from uuid import UUID

import pytest

from day20_multiagents.communication import MessageQueue


def test_message_round_trip_and_immutable_log():
    async def scenario():
        queue = MessageQueue()
        queue.register_agent("main")
        queue.register_agent("worker")
        original = {"content": {"values": [1]}}
        identity = await queue.send_message("main", "worker", original)
        original["content"]["values"].append(2)
        queue.register_agent("worker")
        message = await queue.receive_message("worker")
        assert message["content"]["values"] == [1]
        assert str(UUID(identity)) == identity
        assert datetime.fromisoformat(message["timestamp"]).tzinfo is not None
        assert message["from"] == "main" and message["to"] == "worker"
        message["content"]["values"].append(3)
        history = queue.get_message_log("worker")
        assert history[0]["content"]["values"] == [1]
        history.clear()
        assert len(queue.get_message_log()) == 1
        assert "from" not in original
    asyncio.run(scenario())


def test_unknown_agents_invalid_payload_and_timeout():
    async def scenario():
        queue = MessageQueue()
        queue.register_agent("main")
        with pytest.raises(ValueError):
            await queue.send_message("main", "missing", {})
        with pytest.raises(ValueError):
            await queue.receive_message("missing")
        with pytest.raises(ValueError):
            await queue.receive_message("main", timeout=0)
        with pytest.raises(ValueError):
            await queue.send_message("main", "main", {"value": float("nan")})
        with pytest.raises(TimeoutError):
            await queue.receive_message("main", timeout=0.01)
    asyncio.run(scenario())


def test_bounded_queue_backpressure_and_log():
    async def scenario():
        queue = MessageQueue(maxsize=1, log_limit=2)
        queue.register_agent("main")
        await queue.send_message("main", "main", {"value": 1})
        with pytest.raises(TimeoutError):
            await queue.send_message("main", "main", {"value": 2}, timeout=0.01)
        assert len(queue.get_message_log()) == 1
        for value in (2, 3):
            await queue.receive_message("main")
            await queue.send_message("main", "main", {"value": value})
        assert [message["value"] for message in queue.get_message_log()] == [2, 3]
    asyncio.run(scenario())


def test_message_size_limit():
    async def scenario():
        queue = MessageQueue(max_message_bytes=32)
        queue.register_agent("main")
        with pytest.raises(ValueError):
            await queue.send_message("main", "main", {"content": "large" * 100})
        assert queue.get_message_log() == []
    asyncio.run(scenario())
