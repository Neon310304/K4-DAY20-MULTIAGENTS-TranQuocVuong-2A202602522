import copy
import hashlib
import json
import time
from collections import OrderedDict
from uuid import uuid4

from .communication import MessageQueue
from .observability import RequestMetrics


class CachedDataSystem:
    """Opt-in cache for verified, read-only fixture requests in one event loop."""

    def __init__(self, system, namespace: str, ttl_seconds: float = 60, max_entries: int = 128,
                 max_entry_bytes: int = 65536, clock=time.monotonic):
        self._identity(namespace)
        MessageQueue._timeout(ttl_seconds)
        if ttl_seconds is None or ttl_seconds > 3600:
            raise ValueError("Cache TTL must be finite and at most one hour")
        if isinstance(max_entries, bool) or not isinstance(max_entries, int) or not 1 <= max_entries <= 1024:
            raise ValueError("max_entries must be within 1-1024")
        if isinstance(max_entry_bytes, bool) or not isinstance(max_entry_bytes, int) or not 1 <= max_entry_bytes <= 65536:
            raise ValueError("max_entry_bytes must be within 1-65536")
        self.system = system
        self.namespace = namespace
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.max_entry_bytes = max_entry_bytes
        self.clock = clock
        self._entries = OrderedDict()
        self._counts = dict.fromkeys(("hits", "misses", "bypasses", "stores", "evictions", "expirations", "rejections"), 0)

    @staticmethod
    def _identity(value: str) -> None:
        if not isinstance(value, str) or not value.strip() or len(value) > 256:
            raise ValueError("Cache scope, namespace and dataset revision must be nonempty strings up to 256 characters")

    def _key(self, request, scope: str, dataset_revision: str, debug: bool) -> str | None:
        if debug or not isinstance(request, dict) or set(request) - {"task_type", "content", "parameters", "priority"}:
            return None
        if request.get("task_type") != "data_analysis" or request.get("parameters", {}) != {}:
            return None
        if not isinstance(request.get("content"), str) or not request["content"].strip() or len(request["content"]) > 10000:
            return None
        if request.get("priority", "normal") not in ("normal", "low", "high"):
            return None
        payload = {"namespace": self.namespace, "scope": scope, "dataset_revision": dataset_revision, "request": request}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode("utf-8")).hexdigest()

    def _prune(self) -> None:
        expired = [key for key, entry in self._entries.items() if entry["expires"] <= self.clock()]
        for key in expired:
            del self._entries[key]
            self._counts["expirations"] += 1

    def _store(self, key: str, result: dict) -> None:
        checks = result.get("checks", {})
        if result.get("status") != "success" or result.get("validation_passed") is not True or not checks \
                or any(value is not True for value in checks.values()) or not result.get("data") \
                or result.get("code") or result.get("evaluation") or result.get("artifacts"):
            self._counts["rejections"] += 1
            return
        value = {"data": copy.deepcopy(result["data"]), "checks": copy.deepcopy(checks),
                 "source_request_id": result["request_id"]}
        size = len(json.dumps(value, allow_nan=False).encode("utf-8"))
        if size > self.max_entry_bytes:
            self._counts["rejections"] += 1
            return
        self._prune()
        self._entries[key] = {"value": value, "bytes": size, "expires": self.clock() + self.ttl_seconds}
        self._entries.move_to_end(key)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)
            self._counts["evictions"] += 1
        self._counts["stores"] += 1

    async def process(self, request, *, scope: str, dataset_revision: str, timeout: float = 90,
                      debug: bool = False) -> dict:
        """Scope/revision are trusted caller metadata, not an authentication mechanism."""
        self._identity(scope)
        self._identity(dataset_revision)
        MessageQueue._timeout(timeout)
        if timeout is None:
            raise ValueError("A finite request deadline is required")
        started = time.perf_counter()
        request = copy.deepcopy(request)
        key = self._key(request, scope, dataset_revision, debug)
        self._prune()
        if key is not None and key in self._entries:
            self._counts["hits"] += 1
            self._entries.move_to_end(key)
            value = copy.deepcopy(self._entries[key]["value"])
            return {"request_id": str(uuid4()), "status": "success", "validation_passed": True,
                    "data": value["data"], "code": [], "evaluation": [], "errors": [], "stages": [],
                    "checks": value["checks"], "metrics": RequestMetrics(self.system.mode).snapshot(),
                    "cache": {"outcome": "hit", "source_request_id": value["source_request_id"],
                              "validation": "reused verified result; no tools executed for this request"},
                    "latency_seconds": time.perf_counter() - started}
        outcome = "bypass" if key is None else "miss"
        self._counts["bypasses" if key is None else "misses"] += 1
        result = copy.deepcopy(await self.system.process(request, timeout=timeout, debug=debug))
        if key is not None:
            self._store(key, result)
        result["cache"] = {"outcome": outcome, "source_request_id": result["request_id"]}
        result["latency_seconds"] = time.perf_counter() - started
        return result

    def clear(self) -> None:
        self._entries.clear()

    def statistics(self) -> dict:
        self._prune()
        return {**self._counts, "entries": len(self._entries),
                "payload_bytes": sum(entry["bytes"] for entry in self._entries.values())}
