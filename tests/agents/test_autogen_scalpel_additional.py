import pytest

from code_scalpel.integrations.autogen import AutogenScalpel

# [20251214_TEST] Cover AutogenScalpel analysis/refactor paths using stub analyzers.


class _StubAnalyzer:
    def __init__(self, *, raise_parse: bool = False, raise_refactor: bool = False):
        self._raise_parse = raise_parse
        self._raise_refactor = raise_refactor

    def parse_to_ast(self, code: str):
        if self._raise_parse:
            raise SyntaxError("boom")
        if code == "explode":
            raise RuntimeError("explode")
        return {"ast": True}

    def analyze_code_style(self, tree):
        return {"deep_nesting": ["f"], "naming_conventions": ["g"]}

    def find_security_issues(self, tree):
        return [{"type": "dangerous_function", "function": "exec"}]

    def ast_to_code(self, tree):
        if self._raise_refactor:
            raise RuntimeError("refactor-fail")
        return "refactored"


# [20251214_TEST] Validate AutogenScalpel analysis and refactor paths including failures.
def test_analyze_sync_success_and_suggestions(monkeypatch):
    wrapper = AutogenScalpel()
    wrapper.analyzer = _StubAnalyzer()

    result = wrapper._analyze_sync("print('hi')")

    assert result.ast_analysis["parsed"] is True
    assert result.security_issues
    assert any("nesting" in s.lower() for s in result.suggestions)
    assert any("dangerous function" in s.lower() for s in result.suggestions)


def test_analyze_sync_handles_syntax_and_runtime_errors(monkeypatch):
    wrapper = AutogenScalpel()
    wrapper.analyzer = _StubAnalyzer(raise_parse=True)

    syntax_result = wrapper._analyze_sync("bad code")
    assert syntax_result.error.startswith("Syntax error")

    wrapper.analyzer = _StubAnalyzer()
    runtime_result = wrapper._analyze_sync("explode")
    assert runtime_result.error.startswith("Analysis error")


@pytest.mark.asyncio
async def test_refactor_async_covers_happy_and_error_paths(monkeypatch):
    wrapper = AutogenScalpel()
    wrapper.analyzer = _StubAnalyzer()

    ok = await wrapper.refactor_async("print('ok')")
    assert ok.refactored_code == "refactored"

    wrapper.analyzer = _StubAnalyzer(raise_refactor=True)
    failed = await wrapper.refactor_async("print('ok')")
    assert failed.error.startswith("Refactoring error")
