import asyncio
import copy

import pytest

from day20_multiagents.benchmarking import CASES
from day20_multiagents.caching import CachedDataSystem
from day20_multiagents.observability import RequestMetrics
from day20_multiagents.system import MultiAgentSystem


REQUEST = {"task_type": "data_analysis", "content": CASES[0][1], "parameters": {}}


class CountingSystem:
    mode = "live"

    def __init__(self):
        self.calls = 0
        self.failure = False
        self.invalid = False
        self.artifacts = {}
        self.delay = 0

    async def process(self, request, **options):
        self.calls += 1
        await asyncio.sleep(self.delay)
        return {"request_id": "source-" + str(self.calls), "status": "error" if self.failure else "success",
                "validation_passed": not self.invalid, "data": ['{"revenue":150,"rows":3}'],
                "code": [], "evaluation": [], "errors": [], "stages": [{"worker": "data_agent"}],
                "checks": {"data_numbers": not self.invalid}, "communication": [{"content": "private trace"}],
                "artifacts": self.artifacts, "metrics": RequestMetrics(self.mode).snapshot()}


def test_cache_hit_has_new_identity_zero_work_and_no_previous_trace():
    async def scenario():
        system = CountingSystem()
        cached = CachedDataSystem(system, "fixture-model-prompt-v1")
        first = await cached.process(REQUEST, scope="alice", dataset_revision="v1")
        first["data"].clear()
        second = await cached.process(REQUEST, scope="alice", dataset_revision="v1")
        assert system.calls == 1 and second["cache"]["outcome"] == "hit"
        assert second["cache"]["source_request_id"] == first["request_id"]
        assert second["request_id"] != first["request_id"] and second["data"]
        assert not second["stages"] and "communication" not in second and "artifacts" not in second
        assert second["metrics"]["model_calls"] == second["metrics"]["api_calls"] == 0
        assert second["metrics"]["tokens"]["total_tokens"] == 0
        second["checks"].clear()
        third = await cached.process(REQUEST, scope="alice", dataset_revision="v1")
        assert third["checks"] and cached.statistics()["hits"] == 2
    asyncio.run(scenario())


def test_real_readonly_workflow_is_cached_after_independent_checks():
    async def scenario():
        cached = CachedDataSystem(MultiAgentSystem(), "offline-fixture-v1")
        first = await cached.process(REQUEST, scope="alice", dataset_revision="fixture-sha")
        second = await cached.process(REQUEST, scope="alice", dataset_revision="fixture-sha")
        assert first["validation_passed"] and first["metrics"]["model_calls"] == 2
        assert second["data"] == first["data"] and second["metrics"]["model_calls"] == 0
    asyncio.run(scenario())


def test_scope_revision_and_request_are_separate_keys():
    async def scenario():
        system = CountingSystem()
        cached = CachedDataSystem(system, "model-policy-v1")
        for scope, revision, content in (("alice", "v1", "A"), ("bob", "v1", "A"),
                                         ("alice", "v2", "A"), ("alice", "v1", "B")):
            result = await cached.process({**REQUEST, "content": content}, scope=scope, dataset_revision=revision)
            assert result["cache"]["outcome"] == "miss"
        assert system.calls == 4
    asyncio.run(scenario())


def test_expiry_and_clear_require_fresh_execution():
    async def scenario():
        now = [100.0]
        system = CountingSystem()
        cached = CachedDataSystem(system, "v1", ttl_seconds=2, clock=lambda: now[0])
        await cached.process(REQUEST, scope="alice", dataset_revision="v1")
        now[0] += 2
        assert (await cached.process(REQUEST, scope="alice", dataset_revision="v1"))["cache"]["outcome"] == "miss"
        cached.clear()
        await cached.process(REQUEST, scope="alice", dataset_revision="v1")
        assert system.calls == 3 and cached.statistics()["expirations"] == 1
    asyncio.run(scenario())


def test_lru_limit_preserves_recently_used_result():
    async def scenario():
        system = CountingSystem()
        cached = CachedDataSystem(system, "v1", max_entries=2)
        for content in ("A", "B", "A", "C", "A", "B"):
            await cached.process({**REQUEST, "content": content}, scope="alice", dataset_revision="v1")
        assert system.calls == 4 and cached.statistics()["entries"] == 2
        assert cached.statistics()["evictions"] == 2
    asyncio.run(scenario())


def test_side_effects_parameters_strings_and_debug_bypass_cache():
    async def scenario():
        cached = CachedDataSystem(CountingSystem(), "v1")
        for request, debug in (({**REQUEST, "task_type": "code_generation"}, False),
                               ({**REQUEST, "task_type": "complex"}, False),
                               ({**REQUEST, "task_type": "evaluation"}, False),
                               ({**REQUEST, "parameters": {"output": "answer.json"}}, False),
                               ({**REQUEST, "unknown": 1}, False), (CASES[0][1], False), (REQUEST, True)):
            for unused in range(2):
                assert (await cached.process(request, scope="alice", dataset_revision="v1", debug=debug))["cache"]["outcome"] == "bypass"
        assert cached.statistics()["entries"] == 0 and cached.system.calls == 14
    asyncio.run(scenario())


def test_failures_invalid_results_and_artifacts_are_not_cached():
    async def scenario():
        for attribute, value in (("failure", True), ("invalid", True), ("artifacts", {"answer.json": "digest"})):
            system = CountingSystem()
            setattr(system, attribute, value)
            cached = CachedDataSystem(system, "v1")
            for unused in range(2):
                await cached.process(REQUEST, scope="alice", dataset_revision="v1")
            assert system.calls == 2 and cached.statistics()["rejections"] == 2
            assert cached.statistics()["entries"] == 0
    asyncio.run(scenario())


def test_payload_limit_prevents_oversized_cache_entries():
    async def scenario():
        cached = CachedDataSystem(CountingSystem(), "v1", max_entry_bytes=1)
        await cached.process(REQUEST, scope="alice", dataset_revision="v1")
        assert cached.statistics()["entries"] == 0 and cached.statistics()["rejections"] == 1
    asyncio.run(scenario())


def test_cancellation_is_not_cached_and_wrapper_can_be_reused():
    async def scenario():
        system = CountingSystem()
        system.delay = 10
        cached = CachedDataSystem(system, "v1")
        task = asyncio.create_task(cached.process(REQUEST, scope="alice", dataset_revision="v1"))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert cached.statistics()["entries"] == 0
        system.delay = 0
        assert (await cached.process(REQUEST, scope="alice", dataset_revision="v1"))["cache"]["outcome"] == "miss"
    asyncio.run(scenario())


def test_simultaneous_cold_misses_are_independent_not_single_flight():
    async def scenario():
        system = CountingSystem()
        cached = CachedDataSystem(system, "v1")
        results = await asyncio.gather(*[cached.process(copy.deepcopy(REQUEST), scope="alice", dataset_revision="v1")
                                         for unused in range(3)])
        assert system.calls == 3 and all(result["cache"]["outcome"] == "miss" for result in results)
        assert cached.statistics()["entries"] == 1
    asyncio.run(scenario())


def test_configuration_and_hit_timeout_are_validated():
    for options in ({"ttl_seconds": None}, {"ttl_seconds": 0}, {"ttl_seconds": float("inf")},
                    {"ttl_seconds": 3601}, {"max_entries": True}, {"max_entries": 0},
                    {"max_entry_bytes": 65537}, {"max_entry_bytes": 0}):
        with pytest.raises(ValueError):
            CachedDataSystem(CountingSystem(), "v1", **options)
    with pytest.raises(ValueError):
        CachedDataSystem(CountingSystem(), "")

    async def scenario():
        cached = CachedDataSystem(CountingSystem(), "v1")
        await cached.process(REQUEST, scope="alice", dataset_revision="v1")
        for options in ({"scope": ""}, {"dataset_revision": ""}, {"timeout": None}, {"timeout": -1}):
            with pytest.raises(ValueError):
                await cached.process(REQUEST, **{"scope": "alice", "dataset_revision": "v1", **options})
    asyncio.run(scenario())
