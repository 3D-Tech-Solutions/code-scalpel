import types

import pytest

import code_scalpel.ast_tools as ast_tools


# [20260118_TEST] Add coverage for ast_tools convenience wrappers and visualization guard.
def test_build_ast_uses_default_builder(monkeypatch):
    calls = {}

    class DummyBuilder:
        def build_ast(self, code, preprocess=True, validate=True):
            calls["build"] = (code, preprocess, validate)
            return "tree"

        def build_ast_from_file(self, path, preprocess=True, validate=True):
            calls["file"] = (path, preprocess, validate)
            return "file-tree"

    dummy = DummyBuilder()
    monkeypatch.setattr(ast_tools, "_default_builder", dummy)

    assert ast_tools.build_ast("x = 1") == "tree"
    assert calls["build"] == ("x = 1", True, True)

    assert ast_tools.build_ast_from_file("some.py") == "file-tree"
    assert calls["file"] == ("some.py", True, True)


def test_visualize_ast_requires_visualizer(monkeypatch):
    monkeypatch.setattr(ast_tools, "ASTVisualizer", None)
    with pytest.raises(ImportError):
        ast_tools.visualize_ast(types.SimpleNamespace())


# [20260118_TEST] Ensure __all__ exposes expected convenience symbols.
def test_ast_tools_exports_expected_symbols():
    exports = set(ast_tools.__all__)

    assert "ASTBuilder" in exports
    assert "build_ast" in exports
    assert "build_ast_from_file" in exports
