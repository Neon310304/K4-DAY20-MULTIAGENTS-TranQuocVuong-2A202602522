import asyncio
import copy
import json
import math
from collections import deque
from datetime import datetime, timezone
from uuid import uuid4


class MessageQueue:
    """Bounded in-memory queues owned by one asyncio event loop."""

    def __init__(self, maxsize: int = 64, log_limit: int = 1000, max_message_bytes: int = 65536):
        if isinstance(maxsize, bool) or not isinstance(maxsize, int) or maxsize < 1:
            raise ValueError("maxsize must be a positive integer")
        if isinstance(log_limit, bool) or not isinstance(log_limit, int) or log_limit < 1:
            raise ValueError("log_limit must be a positive integer")
        if isinstance(max_message_bytes, bool) or not isinstance(max_message_bytes, int) or max_message_bytes < 1:
            raise ValueError("max_message_bytes must be a positive integer")
        self.maxsize = maxsize
        self.max_message_bytes = max_message_bytes
        self.queues: dict[str, asyncio.Queue] = {}
        self.message_log = deque(maxlen=log_limit)

    def register_agent(self, agent_name: str) -> None:
        if not isinstance(agent_name, str) or not agent_name.strip():
            raise ValueError("agent_name must be nonempty")
        self.queues.setdefault(agent_name, asyncio.Queue(maxsize=self.maxsize))

    @staticmethod
    def _timeout(timeout: float | None) -> None:
        if timeout is not None and (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
                                    or not math.isfinite(timeout) or timeout <= 0):
            raise ValueError("timeout must be positive and finite, or None")

    def _queue(self, agent_name: str) -> asyncio.Queue:
        if agent_name not in self.queues:
            raise ValueError(f"Agent {agent_name!r} not registered")
        return self.queues[agent_name]

    async def send_message(self, from_agent: str, to_agent: str, message: dict,
                           timeout: float | None = 30) -> str:
        self._timeout(timeout)
        self._queue(from_agent)
        destination = self._queue(to_agent)
        if not isinstance(message, dict):
            raise ValueError("message must be a dictionary")
        if len(json.dumps(message, allow_nan=False).encode("utf-8")) > self.max_message_bytes:
            raise ValueError("Message exceeds the configured size limit")
        envelope = copy.deepcopy(message)
        envelope.update({"from": from_agent, "to": to_agent,
                         "timestamp": datetime.now(timezone.utc).isoformat(), "id": str(uuid4())})
        try:
            await asyncio.wait_for(destination.put(envelope), timeout=timeout)
        except TimeoutError as error:
            raise TimeoutError(f"Queue for {to_agent!r} is full") from error
        self.message_log.append(copy.deepcopy(envelope))
        return envelope["id"]

    async def receive_message(self, agent_name: str, timeout: float | None = 30) -> dict:
        self._timeout(timeout)
        source = self._queue(agent_name)
        try:
            message = await asyncio.wait_for(source.get(), timeout=timeout)
        except TimeoutError as error:
            raise TimeoutError(f"No message for {agent_name!r} within {timeout}s") from error
        source.task_done()
        return message

    def get_message_log(self, agent_name: str | None = None) -> list[dict]:
        if agent_name is not None:
            self._queue(agent_name)
        return copy.deepcopy([message for message in self.message_log
                              if agent_name is None or agent_name in (message["from"], message["to"])])
