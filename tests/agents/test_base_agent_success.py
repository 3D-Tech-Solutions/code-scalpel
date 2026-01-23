from types import SimpleNamespace

import pytest

from code_scalpel.agents.base_agent import BaseCodeAnalysisAgent

# [20251214_REFACTOR] Drop unused imports to satisfy lint.


class DummyAgent(BaseCodeAnalysisAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def observe(self, target):
        return {"success": True, "observed": target}

    async def orient(self, observations):
        return {"success": True, "oriented": observations["observed"]}

    async def decide(self, analysis):
        return {"success": True, "decision": f"act_on_{analysis['oriented']}"}

    async def act(self, decisions):
        return {"success": True, "acted": decisions["decision"]}


@pytest.mark.asyncio
async def test_execute_ooda_loop_success(monkeypatch):
    # [20251214_TEST] Verify happy-path OODA loop succeeds
    agent = DummyAgent(workspace_root="/root")

    result = await agent.execute_ooda_loop("file.py")

    assert result["success"] is True
    assert result["phases"]["observe"]["observed"] == "file.py"
    assert agent.get_context_summary()["workspace_root"] == "/root"


@pytest.mark.asyncio
async def test_tool_wrappers_record_success(monkeypatch):
    # [20251214_TEST] Ensure tool wrapper adds operations and returns model dump
    success = SimpleNamespace(success=True, model_dump=lambda: {"ok": True})

    async def fake_tool(*args, **kwargs):
        return success

    agent = DummyAgent()

    monkeypatch.setattr("code_scalpel.agents.base_agent.get_file_context", fake_tool)
    monkeypatch.setattr("code_scalpel.agents.base_agent.get_symbol_references", fake_tool)
    # [20260116_TEST] security_scan is lazy-imported; patch at source module
    monkeypatch.setattr("code_scalpel.mcp.tools.security.security_scan", fake_tool)
    monkeypatch.setattr("code_scalpel.agents.base_agent.extract_code", fake_tool)
    monkeypatch.setattr("code_scalpel.agents.base_agent.simulate_refactor", fake_tool)
    monkeypatch.setattr("code_scalpel.agents.base_agent.update_symbol", fake_tool)

    obs = await agent.observe_file("path.py")
    refs = await agent.find_symbol_usage("name")
    sec = await agent.analyze_code_security("code")
    func = await agent.extract_function("path", "fn")
    sim = await agent.simulate_code_change("old", "new")
    upd = await agent.apply_safe_change("p", "function", "f", "new code")

    assert obs == refs == sec == func == sim == upd == {"ok": True}
    assert agent.context.get_recent_context(limit=6)[-1]["operation"] == "apply_change"
