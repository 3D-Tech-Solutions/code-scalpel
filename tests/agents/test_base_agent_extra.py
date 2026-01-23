import asyncio

import code_scalpel.agents.base_agent as base_agent


class DummyAgent(base_agent.BaseCodeAnalysisAgent):
    """Minimal agent used for testing the OODA loop."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.called = []

    async def observe(self, target):
        self.called.append("observe")
        return {"success": True, "target": target}

    async def orient(self, observations):
        self.called.append("orient")
        return {"success": True, "observations": observations}

    async def decide(self, analysis):
        self.called.append("decide")
        return {"success": True, "plan": analysis}

    async def act(self, decisions):
        self.called.append("act")
        return {"success": True, "result": decisions}


# [20260118_TEST] Ensure execute_ooda_loop runs through all phases and returns combined result.
def test_execute_ooda_loop_success():
    agent = DummyAgent()
    result = asyncio.run(agent.execute_ooda_loop("foo.py"))

    assert result["success"] is True
    assert result["phases"]["observe"]["target"] == "foo.py"
    assert agent.called == ["observe", "orient", "decide", "act"]


# [20260118_TEST] Cover failure path when observation fails early.
def test_execute_ooda_loop_observe_failure():
    class FailingAgent(DummyAgent):
        async def observe(self, target):  # type: ignore[override]
            return {"success": False, "error": "nope"}

    agent = FailingAgent()
    result = asyncio.run(agent.execute_ooda_loop("foo.py"))

    assert result["success"] is False
    assert result["phase"] == "observe"


# [20260118_TEST] Verify observe_file logs operations and handles tool errors.
def test_observe_file_records_context(monkeypatch):
    agent = DummyAgent()

    class FakeResult:
        def __init__(self, success: bool):
            self.success = success

        def model_dump(self):
            return {"success": self.success}

    async def fake_get_file_context(path):
        return FakeResult(True)

    async def fake_get_file_context_fail(path):
        raise RuntimeError("boom")

    # Successful observation adds operation
    monkeypatch.setattr(base_agent, "get_file_context", fake_get_file_context)
    result = asyncio.run(agent.observe_file("ok.py"))
    assert result["success"] is True
    assert agent.context.get_recent_context()[-1]["operation"] == "observe_file"
    assert agent.context.get_recent_context()[-1]["success"] is True

    # Failure path recorded with success False
    monkeypatch.setattr(base_agent, "get_file_context", fake_get_file_context_fail)
    result_fail = asyncio.run(agent.observe_file("bad.py"))
    assert result_fail["success"] is False
    assert agent.context.get_recent_context()[-1]["operation"] == "observe_file"
    assert agent.context.get_recent_context()[-1]["success"] is False


# [20260118_TEST] Ensure execute_ooda_loop surfaces unexpected exceptions.
def test_execute_ooda_loop_exception_handling():
    class ExplodingAgent(DummyAgent):
        async def orient(self, observations):  # type: ignore[override]
            raise RuntimeError("kaboom")

    agent = ExplodingAgent()
    result = asyncio.run(agent.execute_ooda_loop("foo.py"))

    assert result["success"] is False
    assert "kaboom" in result["error"]


# [20260118_TEST] Verify context summary reflects initial state.
def test_get_context_summary_defaults():
    agent = DummyAgent()
    summary = agent.get_context_summary()

    assert summary["workspace_root"] is None
    assert summary["recent_operations_count"] == 0
    assert summary["knowledge_base_keys"] == []
