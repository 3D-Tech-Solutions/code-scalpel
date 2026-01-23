import types

from code_scalpel.integrations.autogen import AutogenScalpel


class _DummyAnalyzer:
    def __init__(self):
        self.parsed = []

    def parse_to_ast(self, code: str):
        self.parsed.append(code)
        return types.SimpleNamespace()

    def analyze_code_style(self, _tree):
        return {
            "long_functions": ["f"],
            "deep_nesting": ["g"],
            "naming_conventions": ["bad_name"],
        }

    def find_security_issues(self, _tree):
        return [
            {"type": "dangerous_function", "function": "eval"},
            {"type": "sql_injection"},
        ]

    def ast_to_code(self, _tree):
        return "refactored"


# [20260118_TEST] Exercise AutogenScalpel suggestion and refactor helpers with stub analyzer.
def test_autogen_scalpel_generates_suggestions_and_refactor():
    scalpel = AutogenScalpel(cache_enabled=False)
    scalpel.analyzer = _DummyAnalyzer()

    analysis = scalpel._analyze_sync("def f():\n    return 1")
    assert analysis.error is None
    assert analysis.ast_analysis["parsed"] is True
    assert any("breaking down long functions" in s for s in analysis.suggestions)
    assert any("reducing nesting" in s for s in analysis.suggestions)
    assert any("PEP 8" in s for s in analysis.suggestions)
    assert any("dangerous function" in s for s in analysis.suggestions)
    assert any("SQL injection" in s for s in analysis.suggestions)

    refactored = scalpel._refactor_sync("def f():\n    return 1", "auto")
    assert refactored.refactored_code == "refactored"


def test_get_tool_description_fields():
    scalpel = AutogenScalpel(cache_enabled=False)
    desc = scalpel.get_tool_description()
    assert desc["name"] == "code_scalpel_analyzer"
    assert "description" in desc
    assert "parameters" in desc
