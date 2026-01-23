"""Additional coverage for BaseCodeAnalysisAgent behavior and error paths."""

import asyncio
import tempfile


class HappyAgent:
    """Simple agent that succeeds through all OODA stages."""

    def __init__(self):
        from code_scalpel.agents.base_agent import BaseCodeAnalysisAgent

        class _Agent(BaseCodeAnalysisAgent):
            async def observe(self, target):
                return {"success": True, "observed": target}

            async def orient(self, observations):
                return {"success": True, "analysis": observations}

            async def decide(self, analysis):
                return {"success": True, "plan": analysis}

            async def act(self, decisions):
                return {"success": True, "done": decisions}

        self.impl = _Agent(workspace_root=tempfile.mkdtemp(prefix="scalpel-ws-"))


def test_execute_ooda_loop_success():
    # [20251214_TEST] Ensure the OODA loop completes when all phases succeed.
    agent = HappyAgent().impl
    result = asyncio.run(agent.execute_ooda_loop("target.py"))

    assert result["success"] is True
    assert set(result["phases"].keys()) == {"observe", "orient", "decide", "act"}
    assert isinstance(result["context"], list)


def test_execute_ooda_loop_halts_on_failed_observe():
    from code_scalpel.agents.base_agent import BaseCodeAnalysisAgent

    # [20251214_TEST] Cover early exit when observe phase fails.
    class FailingAgent(BaseCodeAnalysisAgent):
        async def observe(self, target):
            return {"success": False, "error": "no sight"}

        async def orient(self, observations):
            return {"success": True}

        async def decide(self, analysis):
            return {"success": True}

        async def act(self, decisions):
            return {"success": True}

    agent = FailingAgent()
    result = asyncio.run(agent.execute_ooda_loop("target.py"))

    assert result["success"] is False
    assert result.get("phase") == "observe"
    assert "error" in result


def test_observe_file_records_failed_operation(monkeypatch):
    from code_scalpel.agents import base_agent

    # [20251214_TEST] Simulate tool error to ensure context logs failure.
    async def boom(_path):
        raise RuntimeError("explode")

    monkeypatch.setattr(base_agent, "get_file_context", boom)

    class StubAgent(base_agent.BaseCodeAnalysisAgent):
        async def observe(self, target):  # pragma: no cover - not used here
            return {"success": True}

        async def orient(self, observations):  # pragma: no cover - not used here
            return {"success": True}

        async def decide(self, analysis):  # pragma: no cover - not used here
            return {"success": True}

        async def act(self, decisions):  # pragma: no cover - not used here
            return {"success": True}

    agent = StubAgent(workspace_root=tempfile.mkdtemp(prefix="scalpel-ws-"))
    missing = tempfile.NamedTemporaryFile(prefix="scalpel-missing-", delete=True)
    missing.close()
    result = asyncio.run(agent.observe_file(missing.name))

    assert result["success"] is False
    assert "error" in result
    assert agent.context.recent_operations[-1]["success"] is False
