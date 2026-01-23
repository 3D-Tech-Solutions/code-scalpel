import types

import pytest

import code_scalpel.ast_tools as ast_tools


def test_visualize_ast_raises_when_visualizer_missing(monkeypatch):
    # [20251214_TEST] Ensure visualize_ast fails fast without ASTVisualizer
    monkeypatch.setattr(ast_tools, "ASTVisualizer", None, raising=False)
    with pytest.raises(ImportError):
        ast_tools.visualize_ast(object())


def test_build_ast_uses_default_builder(monkeypatch):
    # [20251214_TEST] Verify build_ast delegates to _default_builder
    calls = {}

    def fake_build_ast(code: str, preprocess: bool, validate: bool):
        calls["args"] = (code, preprocess, validate)
        return "built"

    fake_builder = types.SimpleNamespace(build_ast=fake_build_ast)
    monkeypatch.setattr(ast_tools, "_default_builder", fake_builder)

    result = ast_tools.build_ast("code", preprocess=False, validate=False)

    assert result == "built"
    assert calls["args"] == ("code", False, False)
