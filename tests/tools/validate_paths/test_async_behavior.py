"""Async/offload behavior tests for validate_paths."""

import asyncio
import time

import pytest

from code_scalpel.mcp import server as mcp_server


@pytest.mark.asyncio
async def test_validate_paths_offloads_and_does_not_block_loop(monkeypatch):
    """Slow sync work should run in a thread so the event loop stays responsive."""
    call_started = asyncio.Event()

    def slow_validate_paths_sync(paths, project_root, tier, capabilities):
        call_started.set()
        time.sleep(0.2)
        return mcp_server.PathValidationResult(
            success=False,
            accessible=[],
            inaccessible=list(paths),
            suggestions=[],
            workspace_roots=[],
            is_docker=False,
            alias_resolutions=[],
            dynamic_imports=[],
            traversal_vulnerabilities=[],
            boundary_violations=[],
            security_score=None,
        )

    monkeypatch.setattr(mcp_server, "_validate_paths_sync", slow_validate_paths_sync)

    slow_task = asyncio.create_task(mcp_server.validate_paths(paths=["/tmp/slow"]))
    heartbeat = asyncio.create_task(asyncio.sleep(0.05))

    await call_started.wait()
    # If the loop were blocked by the sync work, this would time out
    await asyncio.wait_for(heartbeat, timeout=0.2)

    result = await asyncio.wait_for(slow_task, timeout=1.0)
    assert result.inaccessible == ["/tmp/slow"]


@pytest.mark.asyncio
async def test_validate_paths_handles_concurrent_requests():
    """Concurrent calls should succeed without shared-state corruption."""
    batches = [
        ["/tmp/a", "/tmp/b"],
        ["/tmp/c"],
        ["/tmp/d", "/tmp/e", "/tmp/f"],
    ]

    results = await asyncio.gather(*(mcp_server.validate_paths(paths=batch) for batch in batches))

    for batch, result in zip(batches, results, strict=False):
        total = len(result.accessible) + len(result.inaccessible)
        assert total == len(batch)


@pytest.mark.asyncio
async def test_validate_paths_timeout_propagates_cleanly(monkeypatch):
    """Long-running sync work should be cancellable via asyncio timeouts."""

    def very_slow_validate_paths_sync(paths, project_root, tier, capabilities):
        time.sleep(1.0)
        return mcp_server.PathValidationResult(
            success=False,
            accessible=[],
            inaccessible=list(paths),
            suggestions=[],
            workspace_roots=[],
            is_docker=False,
            alias_resolutions=[],
            dynamic_imports=[],
            traversal_vulnerabilities=[],
            boundary_violations=[],
            security_score=None,
        )

    monkeypatch.setattr(mcp_server, "_validate_paths_sync", very_slow_validate_paths_sync)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(mcp_server.validate_paths(paths=["/tmp/very-slow"]), timeout=0.05)


@pytest.mark.asyncio
async def test_validate_paths_timeout_respects_tier_limit(monkeypatch):
    """Tier timeout limit can be enforced by callers via wait_for using capability limits."""

    def very_slow_validate_paths_sync(paths, project_root, tier, capabilities):
        time.sleep(1.0)
        return mcp_server.PathValidationResult(
            success=False,
            accessible=[],
            inaccessible=list(paths),
            suggestions=[],
            workspace_roots=[],
            is_docker=False,
            alias_resolutions=[],
            dynamic_imports=[],
            traversal_vulnerabilities=[],
            boundary_violations=[],
            security_score=None,
        )

    monkeypatch.setattr(mcp_server, "_validate_paths_sync", very_slow_validate_paths_sync)

    tier_limits = {
        "capabilities": [],
        "limits": {"timeout_seconds": 0.05},
    }
    monkeypatch.setattr(mcp_server, "get_tool_capabilities", lambda tool, tier: tier_limits)

    timeout_seconds = tier_limits["limits"]["timeout_seconds"]

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            mcp_server.validate_paths(paths=["/tmp/very-slow-tiered"]),
            timeout=timeout_seconds,
        )


@pytest.mark.asyncio
async def test_validate_paths_10_concurrent_requests(monkeypatch):
    """Ten concurrent calls should complete and return the right counts."""

    def fast_validate_paths_sync(paths, project_root, tier, capabilities):
        return mcp_server.PathValidationResult(
            success=False,
            accessible=[],
            inaccessible=list(paths),
            suggestions=[],
            workspace_roots=[],
            is_docker=False,
            alias_resolutions=[],
            dynamic_imports=[],
            traversal_vulnerabilities=[],
            boundary_violations=[],
            security_score=None,
        )

    monkeypatch.setattr(mcp_server, "_validate_paths_sync", fast_validate_paths_sync)

    batches = [[f"/tmp/p-{i}-{j}" for j in range(3)] for i in range(10)]
    results = await asyncio.gather(*(mcp_server.validate_paths(paths=batch) for batch in batches))

    for batch, result in zip(batches, results, strict=False):
        total = len(result.accessible) + len(result.inaccessible)
        assert total == len(batch)


@pytest.mark.asyncio
async def test_validate_paths_100_sequential_requests(monkeypatch):
    """One hundred sequential calls should not degrade or leak state."""

    def fast_validate_paths_sync(paths, project_root, tier, capabilities):
        return mcp_server.PathValidationResult(
            success=False,
            accessible=[],
            inaccessible=list(paths),
            suggestions=[],
            workspace_roots=[],
            is_docker=False,
            alias_resolutions=[],
            dynamic_imports=[],
            traversal_vulnerabilities=[],
            boundary_violations=[],
            security_score=None,
        )

    monkeypatch.setattr(mcp_server, "_validate_paths_sync", fast_validate_paths_sync)

    for i in range(100):
        batch = [f"/tmp/seq-{i}"]
        result = await mcp_server.validate_paths(paths=batch)
        total = len(result.accessible) + len(result.inaccessible)
        assert total == len(batch)


@pytest.mark.asyncio
async def test_validate_paths_response_time_small_medium_large(monkeypatch):
    """Small/medium/large batches should complete within generous bounds."""

    def fast_validate_paths_sync(paths, project_root, tier, capabilities):
        return mcp_server.PathValidationResult(
            success=False,
            accessible=[],
            inaccessible=list(paths),
            suggestions=[],
            workspace_roots=[],
            is_docker=False,
            alias_resolutions=[],
            dynamic_imports=[],
            traversal_vulnerabilities=[],
            boundary_violations=[],
            security_score=None,
        )

    monkeypatch.setattr(mcp_server, "_validate_paths_sync", fast_validate_paths_sync)
    monkeypatch.setattr(
        mcp_server,
        "get_tool_capabilities",
        lambda tool, tier: {"capabilities": [], "limits": {"max_paths": None}},
    )

    batches = {
        "small": ["/tmp/small-1", "/tmp/small-2"],
        "medium": [f"/tmp/med-{i}" for i in range(1000)],
        "large": [f"/tmp/large-{i}" for i in range(10000)],
    }

    thresholds = {"small": 0.5, "medium": 1.0, "large": 2.0}

    for key, paths in batches.items():
        start = time.monotonic()
        result = await mcp_server.validate_paths(paths=paths)
        duration = time.monotonic() - start
        total = len(result.accessible) + len(result.inaccessible)
        assert total == len(paths)
        assert duration < thresholds[key], f"{key} batch exceeded threshold: {duration:.2f}s"
