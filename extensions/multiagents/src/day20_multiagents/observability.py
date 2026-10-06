import asyncio
import copy
import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from .tools import BaseTool


class RequestMetrics:
    def __init__(self, mode: str):
        self.mode = mode
        self.events = []
        self._lock = threading.Lock()

    def begin(self, kind: str, worker: str, name: str) -> dict:
        event = {"kind": kind, "worker": worker, "name": name, "status": "running", "seconds": None, "tokens": None}
        with self._lock:
            self.events.append(event)
        return event

    def finish(self, event: dict, started: float, status: str, response=None) -> None:
        usage = getattr(response, "usage_metadata", None)
        tokens = None
        if isinstance(usage, dict):
            keys = ("input_tokens", "output_tokens", "total_tokens")
            if all(isinstance(usage.get(key), int) and not isinstance(usage[key], bool) and usage[key] >= 0 for key in keys):
                if usage["input_tokens"] + usage["output_tokens"] == usage["total_tokens"]:
                    tokens = {key: usage[key] for key in keys}
        with self._lock:
            event.update({"status": status, "seconds": time.perf_counter() - started, "tokens": tokens})

    def snapshot(self) -> dict:
        with self._lock:
            events = copy.deepcopy(self.events)
        model_events = [event for event in events if event["kind"] == "model"]
        known = [event["tokens"] for event in model_events if event["tokens"] is not None]
        complete = self.mode == "offline" or len(known) == len(model_events)
        totals = {key: sum(usage[key] for usage in known) for key in ("input_tokens", "output_tokens", "total_tokens")}
        return {"events": events, "model_calls": len(model_events), "api_calls": len(model_events) if self.mode == "live" else 0,
                "usage_complete": complete, "tokens": totals if complete else None, "known_tokens": totals,
                "missing_usage_calls": len(model_events) - len(known) if self.mode == "live" else 0}


class MeasuredModel:
    def __init__(self, model, metrics: RequestMetrics, worker: str):
        self.model = model
        self.metrics = metrics
        self.worker = worker

    def bind_tools(self, tools):
        return MeasuredModel(self.model.bind_tools(tools), self.metrics, self.worker)

    def invoke(self, messages):
        event = self.metrics.begin("model", self.worker, "invoke")
        started = time.perf_counter()
        try:
            response = self.model.invoke(messages)
        except BaseException:
            self.metrics.finish(event, started, "error")
            raise
        self.metrics.finish(event, started, "success", response)
        return response

    async def ainvoke(self, messages):
        event = self.metrics.begin("model", self.worker, "ainvoke")
        started = time.perf_counter()
        try:
            response = await self.model.ainvoke(messages) if hasattr(self.model, "ainvoke") \
                else await asyncio.to_thread(self.model.invoke, messages)
        except BaseException as error:
            self.metrics.finish(event, started, "cancelled" if isinstance(error, asyncio.CancelledError) else "error")
            raise
        self.metrics.finish(event, started, "success", response)
        return response


class MeasuredTool(BaseTool):
    def __init__(self, tool: BaseTool, metrics: RequestMetrics, worker: str):
        super().__init__(tool.name, tool.description, tool.parameters)
        self.tool = tool
        self.metrics = metrics
        self.worker = worker

    def _execute(self, arguments: dict):
        return self.tool.invoke(arguments)

    def invoke(self, arguments: dict):
        event = self.metrics.begin("tool", self.worker, self.name)
        started = time.perf_counter()
        try:
            output = self.tool.invoke(arguments)
        except BaseException:
            self.metrics.finish(event, started, "error")
            raise
        self.metrics.finish(event, started, "success")
        return output


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), "level": record.levelname,
                           "logger": record.name, "event": record.getMessage()}, ensure_ascii=False)


def configure_logging(path: Path) -> logging.Handler:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(JsonFormatter())
    allowed = ("coordinator", "data_agent", "code_agent", "evaluator_agent", "day20_multiagents")
    handler.addFilter(lambda record: record.name.startswith(allowed))
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return handler
