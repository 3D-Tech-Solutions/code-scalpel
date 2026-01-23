import tempfile
from typing import Any

# [20251214_REFACTOR] Remove unused test imports flagged by ruff.
import pytest

import code_scalpel.agents.base_agent as base_agent
from code_scalpel.agents.base_agent import BaseCodeAnalysisAgent


class DummyResult:
    def __init__(self, success: bool, payload: dict[str, Any] | None = None):
        self.success = success
        self._payload = payload or {"success": success}

    def model_dump(self) -> dict[str, Any]:
        return dict(self._payload, success=self.success)


class DummyAgent(BaseCodeAnalysisAgent):
    def __init__(self, workspace_root: str | None = None):
        root = workspace_root or tempfile.mkdtemp(prefix="scalpel-agent-")
        super().__init__(workspace_root=root)
        self.calls: list[str] = []

    async def observe(self, target: str) -> dict[str, Any]:
        self.calls.append("observe")
        return {"success": True, "target": target}

    async def orient(self, observations: dict[str, Any]) -> dict[str, Any]:
        self.calls.append("orient")
        return {"success": True, "observations": observations}

    async def decide(self, analysis: dict[str, Any]) -> dict[str, Any]:
        self.calls.append("decide")
        return {"success": True, "analysis": analysis}

    async def act(self, decisions: dict[str, Any]) -> dict[str, Any]:
        self.calls.append("act")
        return {"success": True, "decisions": decisions}


class FailingAgent(DummyAgent):
    def __init__(self, fail_phase: str):
        super().__init__()
        self.fail_phase = fail_phase

    async def observe(self, target: str) -> dict[str, Any]:
        if self.fail_phase == "observe":
            return {"success": False, "error": "observe failed"}
        return await super().observe(target)

    async def orient(self, observations: dict[str, Any]) -> dict[str, Any]:
        if self.fail_phase == "orient":
            return {"success": False, "error": "orient failed"}
        return await super().orient(observations)

    async def decide(self, analysis: dict[str, Any]) -> dict[str, Any]:
        if self.fail_phase == "decide":
            return {"success": False, "error": "decide failed"}
        return await super().decide(analysis)

    async def act(self, decisions: dict[str, Any]) -> dict[str, Any]:
        if self.fail_phase == "act":
            return {"success": False, "error": "act failed"}
        return await super().act(decisions)


# [20251214_TEST] Cover BaseCodeAnalysisAgent OODA loop success path.
@pytest.mark.asyncio
async def test_execute_ooda_loop_success():
    agent = DummyAgent()
    result = await agent.execute_ooda_loop("target-file")
    assert result["success"] is True
    assert set(agent.calls) == {"observe", "orient", "decide", "act"}
    assert result["phases"]["observe"]["target"] == "target-file"
    summary = agent.get_context_summary()
    assert summary["workspace_root"] == agent.workspace_root
    assert summary["recent_operations_count"] == 0


# [20251214_TEST] Cover BaseCodeAnalysisAgent failure handling per phase.
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "phase",
    ["observe", "orient", "decide", "act"],
)
async def test_execute_ooda_loop_failure_phases(phase: str):
    agent = FailingAgent(phase)
    result = await agent.execute_ooda_loop("target")
    assert result["success"] is False
    if phase == "act":
        assert "phases" in result
        assert result["phases"]["act"]["success"] is False
    else:
        assert result["phase"] == phase
        assert phase in result["error"]


# [20251214_TEST] Cover tool wrapper success paths with monkeypatched MCP tools.
@pytest.mark.asyncio
async def test_tool_wrappers_success(monkeypatch):
    async def success_tool(*_args, **_kwargs):
        return DummyResult(True, {"payload": "ok"})

    agent = DummyAgent()

    monkeypatch.setattr(base_agent, "get_file_context", success_tool)
    monkeypatch.setattr(base_agent, "get_symbol_references", success_tool)
    # [20260116_TEST] security_scan is lazy-imported; patch at the source module
    from code_scalpel.mcp.tools import security as security_module

    monkeypatch.setattr(security_module, "security_scan", success_tool)
    monkeypatch.setattr(base_agent, "extract_code", success_tool)
    monkeypatch.setattr(base_agent, "simulate_refactor", success_tool)
    monkeypatch.setattr(base_agent, "update_symbol", success_tool)

    assert (await agent.observe_file("file.py"))["success"] is True
    assert (await agent.find_symbol_usage("Foo"))["success"] is True
    assert (await agent.analyze_code_security("print('hi')"))["success"] is True
    assert (await agent.extract_function("file.py", "foo"))["success"] is True
    assert (await agent.simulate_code_change("old", "new"))["success"] is True
    assert (await agent.apply_safe_change("f.py", "function", "foo", "code"))["success"] is True


# [20251214_TEST] Cover wrapper error path to capture exceptions.
@pytest.mark.asyncio
async def test_tool_wrapper_failure(monkeypatch):
    async def failing_tool(*_args, **_kwargs):
        raise RuntimeError("boom")

    agent = DummyAgent()
    monkeypatch.setattr(base_agent, "get_file_context", failing_tool)

    result = await agent.observe_file("file.py")
    assert result["success"] is False
    assert "boom" in result["error"]
    summary = agent.get_context_summary()
    assert summary["recent_operations_count"] == 1
