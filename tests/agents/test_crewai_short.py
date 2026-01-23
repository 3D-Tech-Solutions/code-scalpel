from typing import Any

# [20251214_REFACTOR] Remove unused test imports flagged by ruff.
import pytest

from code_scalpel.integrations.crewai import CrewAIScalpel


class StubAnalyzer:
    def __init__(self, should_raise: bool = False):
        self.should_raise = should_raise
        self.calls: list[str] = []

    def parse_to_ast(self, code: str) -> Any:
        self.calls.append("parse")
        if self.should_raise:
            raise SyntaxError("bad syntax")
        return {"tree": code}

    def analyze_code_style(self, tree: Any) -> dict[str, list[str]]:
        self.calls.append("style")
        return {"style": ["issue"], "complexity": []}

    def find_security_issues(self, tree: Any) -> list[dict[str, Any]]:
        self.calls.append("security")
        return [{"issue": "xss"}]

    def ast_to_code(self, tree: Any) -> str:
        self.calls.append("codegen")
        return "refactored"


# [20251214_TEST] Cover CrewAIScalpel analysis happy path.
@pytest.mark.asyncio
async def test_crewai_analyze_and_refactor_success():
    scalpel = CrewAIScalpel()
    scalpel.analyzer = StubAnalyzer()

    result = scalpel.analyze("print('hi')")
    assert result.success is True
    assert result.analysis["total_issues"] == 2
    assert any(issue["type"] == "security" for issue in result.issues)

    refactored = scalpel.refactor("print('hi')")
    assert refactored.refactored_code == "refactored"
    assert refactored.success is True

    async_result = await scalpel.analyze_async("print('async')")
    assert async_result.success is True

    async_refactor = await scalpel.refactor_async("print('async')")
    assert async_refactor.refactored_code == "refactored"


# [20251214_TEST] Cover CrewAIScalpel syntax error handling.
@pytest.mark.asyncio
async def test_crewai_analyze_syntax_error():
    scalpel = CrewAIScalpel()
    scalpel.analyzer = StubAnalyzer(should_raise=True)

    result = scalpel.analyze("bad syntax")
    assert result.success is False
    assert "Syntax error" in result.error

    async_result = await scalpel.analyze_async("bad syntax")
    assert async_result.success is False
    assert async_result.error.startswith("Syntax error")
