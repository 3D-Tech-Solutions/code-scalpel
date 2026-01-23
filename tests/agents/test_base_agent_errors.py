from typing import Any

import pytest

from code_scalpel.agents.base_agent import BaseCodeAnalysisAgent


class _DummyAgent(BaseCodeAnalysisAgent):
    async def observe(self, target: str) -> dict[str, Any]:
        return {"success": True}

    async def orient(self, observations: dict[str, Any]) -> dict[str, Any]:
        return {"success": True}

    async def decide(self, analysis: dict[str, Any]) -> dict[str, Any]:
        return {"success": True}

    async def act(self, decisions: dict[str, Any]) -> dict[str, Any]:
        return {"success": True}


# [20251214_TEST] Ensure BaseCodeAnalysisAgent logs failures from MCP tool wrappers.
@pytest.mark.asyncio
async def test_observe_file_failure_records_context(monkeypatch):
    agent = _DummyAgent()

    async def _raise(file_path):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "code_scalpel.agents.base_agent.get_file_context",
        _raise,
    )

    result = await agent.observe_file("missing.py")
    assert result["success"] is False
    assert agent.context.recent_operations[-1]["success"] is False


# [20251214_TEST] Exercise OODA loop exception handling path.
@pytest.mark.asyncio
async def test_execute_ooda_loop_handles_action_error(monkeypatch):
    agent = _DummyAgent()

    async def _explode(decisions: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("oops")

    agent.act = _explode  # type: ignore[assignment]

    result = await agent.execute_ooda_loop("target")
    assert result["success"] is False
    assert result["error"].startswith("oops")


# [20251214_TEST] Cover failure paths for all MCP wrapper methods.
@pytest.mark.asyncio
async def test_wrapper_methods_capture_errors(monkeypatch):
    agent = _DummyAgent()

    async def boom(*_args, **_kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr("code_scalpel.agents.base_agent.get_symbol_references", boom)
    # [20260116_TEST] security_scan is lazy-imported; patch at source module
    monkeypatch.setattr("code_scalpel.mcp.tools.security.security_scan", boom)
    monkeypatch.setattr("code_scalpel.agents.base_agent.extract_code", boom)
    monkeypatch.setattr("code_scalpel.agents.base_agent.simulate_refactor", boom)
    monkeypatch.setattr("code_scalpel.agents.base_agent.update_symbol", boom)

    refs = await agent.find_symbol_usage("name")
    sec = await agent.analyze_code_security("code")
    ext = await agent.extract_function("p", "fn")
    sim = await agent.simulate_code_change("a", "b")
    upd = await agent.apply_safe_change("p", "function", "fn", "new")

    assert refs["success"] is False
    assert sec["success"] is False
    assert ext["success"] is False
    assert sim["success"] is False
    assert upd["success"] is False


# [20251214_TEST] Ensure OODA loop returns phase-specific error on observe failure.
@pytest.mark.asyncio
async def test_execute_ooda_loop_observe_failure():
    class _FailingAgent(_DummyAgent):
        async def observe(self, target: str) -> dict[str, Any]:
            return {"success": False, "error": "nope"}

    agent = _FailingAgent()
    result = await agent.execute_ooda_loop("target")

    assert result["success"] is False
    assert result["phase"] == "observe"
    assert result["error"] == "nope"
