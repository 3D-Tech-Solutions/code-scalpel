"""Stub-based tests for JavaScriptNormalizer without tree-sitter runtime.

These tests exercise error-handling and noise/unknown node branches that do
not require the actual tree-sitter-javascript dependency.
"""

import warnings


class StubNode:
    """Minimal stand-in for tree-sitter nodes used in tests."""

    def __init__(self, node_type: str, *, is_named: bool = True, children=None):
        self.type = node_type
        self.is_named = is_named
        self.children = children or []
        self.start_point = (0, 0)
        self.end_point = (0, 1)
        self.has_error = node_type == "program"

    def child_by_field_name(self, field: str):  # pragma: no cover - unused in stubs
        return None


class StubTree:
    def __init__(self, root_node):
        self.root_node = root_node


class StubParser:
    def __init__(self, root_node):
        self._tree = StubTree(root_node)

    def parse(self, _source: bytes):
        return self._tree


def test_normalize_reports_syntax_error_when_root_has_error(monkeypatch):
    from code_scalpel.ir.normalizers.javascript_normalizer import JavaScriptNormalizer

    # [20251214_TEST] Cover parse-error path without real tree-sitter parser.
    monkeypatch.setattr(JavaScriptNormalizer, "_ensure_parser", lambda self: None)

    error_node = StubNode("ERROR")
    root = StubNode("program", children=[error_node])

    normalizer = JavaScriptNormalizer.__new__(JavaScriptNormalizer)
    normalizer._parser = StubParser(root)
    normalizer._language = None
    normalizer._filename = "inline.js"
    normalizer._source = "const x = ;"

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            normalizer.normalize("const x = ;", filename="inline.js")
        except SyntaxError as exc:
            assert "Parse error" in str(exc)
        else:  # pragma: no cover - defensive guard
            raise AssertionError("Expected SyntaxError")


def test_normalize_node_skips_noise_and_warns_unknown(monkeypatch):
    from code_scalpel.ir.normalizers.javascript_normalizer import JavaScriptNormalizer

    # [20251214_TEST] Ensure noise nodes are skipped and unknowns warn instead of crashing.
    monkeypatch.setattr(JavaScriptNormalizer, "_ensure_parser", lambda self: None)

    normalizer = JavaScriptNormalizer.__new__(JavaScriptNormalizer)
    normalizer._parser = None
    normalizer._language = None
    normalizer._filename = "stub.js"
    normalizer._source = ""

    noise_node = StubNode("comment", is_named=False)
    assert normalizer.normalize_node(noise_node) is None

    unknown_node = StubNode("future_syntax")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert normalizer.normalize_node(unknown_node) is None
        assert any("not yet supported" in str(w.message) for w in caught)
