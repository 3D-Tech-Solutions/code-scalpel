from unittest.mock import AsyncMock

import pytest

from code_scalpel.agents.base_agent import BaseCodeAnalysisAgent
from code_scalpel.agents.code_review_agent import CodeReviewAgent
from code_scalpel.agents.optimazation_agent import OptimizationAgent
from code_scalpel.agents.security_agent import SecurityAgent


class _DummyAgent(BaseCodeAnalysisAgent):
    """Minimal agent for exercising base OODA logic."""

    async def observe(self, target: str):
        # [20251215_TEST] Success path for OODA orchestration
        return {"success": True, "observed": target}

    async def orient(self, observations):
        return {"success": True, "oriented": observations}

    async def decide(self, analysis):
        return {"success": True, "decisions": analysis}

    async def act(self, decisions):
        return {"success": True, "actions": decisions}


class _FailingAgent(BaseCodeAnalysisAgent):
    """Agent that fails during observe to cover short-circuit."""

    async def observe(self, target: str):
        # [20251215_TEST] Force early failure path
        return {"success": False, "error": "boom", "target": target}

    async def orient(self, observations):  # pragma: no cover - not invoked
        return {"success": True}

    async def decide(self, analysis):  # pragma: no cover - not invoked
        return {"success": True}

    async def act(self, decisions):  # pragma: no cover - not invoked
        return {"success": True}


@pytest.mark.asyncio
async def test_base_agent_ooda_success_and_context(monkeypatch, tmp_path):
    agent = _DummyAgent(workspace_root=str(tmp_path))

    # [20251215_TEST] Stub MCP hooks to avoid network/file IO
    monkeypatch.setattr(
        "code_scalpel.agents.base_agent.get_file_context",
        AsyncMock(return_value=AsyncMock(success=True, model_dump=lambda: {"success": True})),
    )

    result = await agent.execute_ooda_loop("demo.py")
    assert result["success"] is True
    summary = agent.get_context_summary()
    assert summary["workspace_root"] == str(tmp_path)
    assert summary["recent_operations_count"] >= 0


@pytest.mark.asyncio
async def test_base_agent_ooda_failure_short_circuits(tmp_path):
    agent = _FailingAgent(workspace_root=str(tmp_path))
    result = await agent.execute_ooda_loop("demo.py")
    assert result == {"success": False, "phase": "observe", "error": "boom"}


@pytest.mark.asyncio
async def test_base_agent_observe_file_error(monkeypatch):
    # [20251215_TEST] Cover observe_file exception handling
    async def _raise(_):
        raise ValueError("file-error")

    monkeypatch.setattr("code_scalpel.agents.base_agent.get_file_context", _raise)
    agent = _DummyAgent()
    response = await agent.observe_file("missing.py")
    assert response == {"success": False, "error": "file-error"}


@pytest.mark.asyncio
async def test_code_review_agent_end_to_end(monkeypatch):
    agent = CodeReviewAgent(workspace_root="/workspace")

    agent.observe_file = AsyncMock(
        return_value={
            "success": True,
            "functions": ["main", "helper", "unused"],
            "complexity_score": 25,
        }
    )
    agent.analyze_code_security = AsyncMock(
        return_value={
            "success": True,
            "vulnerabilities": [{"severity": "high", "description": "sql", "type": "security"}],
        }
    )
    agent.find_symbol_usage = AsyncMock(return_value={"success": True, "total_references": 0})

    observations = await agent.observe("sample.py")
    assert observations["success"] is True

    analysis = await agent.orient(
        {
            "file_info": observations["file_info"],
            "security_info": observations["security_scan"],
            "symbol_analysis": observations["symbol_analysis"],
        }
    )
    assert analysis["issues"]

    decisions = await agent.decide(analysis)
    assert decisions["actionable_items"]

    actions = await agent.act(decisions)
    assert actions["success"] is True
    assert actions["success_rate"] >= 0


@pytest.mark.asyncio
async def test_optimization_agent_flow(monkeypatch):
    agent = OptimizationAgent()

    agent.observe_file = AsyncMock(
        return_value={
            "success": True,
            "functions": ["hot_path"],
            "classes": [],
            "complexity_score": 40,
        }
    )
    agent.find_symbol_usage = AsyncMock(return_value={"success": True, "total_references": 25})

    observations = await agent.observe("perf.py")
    assert observations["success"] is True

    analysis = await agent.orient(observations)
    assert analysis["bottlenecks"]
    assert analysis["recommendations"]

    decisions = await agent.decide(analysis)
    assert decisions["prioritized_actions"]

    actions = await agent.act(decisions)
    assert actions["success"] is True


@pytest.mark.asyncio
async def test_security_agent_flow(monkeypatch):
    agent = SecurityAgent()

    agent.observe_file = AsyncMock(
        return_value={
            "success": True,
            "functions": ["dangerous"],
        }
    )
    agent.analyze_code_security = AsyncMock(
        return_value={
            "success": True,
            "vulnerabilities": [
                {
                    "severity": "critical",
                    "type": "sql_injection",
                    "location": {"function": "dangerous"},
                }
            ],
        }
    )
    agent.find_symbol_usage = AsyncMock(return_value={"success": True, "total_references": 12})

    observations = await agent.observe("insecure.py")
    assert observations["success"] is True

    analysis = await agent.orient(observations)
    assert analysis["vulnerabilities"]
    assert analysis["risk_assessment"]["overall_level"] in {
        "critical",
        "high",
        "medium",
        "low",
    }

    decisions = await agent.decide(analysis)
    assert decisions["total_actions"] >= 0

    actions = await agent.act(decisions)
    assert actions["success"] is True
