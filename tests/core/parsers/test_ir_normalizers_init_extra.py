import builtins
import importlib
import sys
import types

import code_scalpel.ir.normalizers as normalizers

# [20260118_TEST] Ensure __all__ excludes JavaScriptNormalizer when import fails.


def test_normalizers_without_javascript(monkeypatch):
    original_import = builtins.__import__

    def fail_js_import(name, *args, **kwargs):  # pragma: no cover - explicit patch behavior
        if name.endswith("javascript_normalizer"):
            raise ImportError("js missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_js_import)
    monkeypatch.delitem(sys.modules, "code_scalpel.ir.normalizers.javascript_normalizer", raising=False)

    module = importlib.reload(normalizers)
    assert "JavaScriptNormalizer" not in module.__all__

    # Restore baseline module state
    importlib.reload(normalizers)


# [20260118_TEST] Ensure __all__ includes JavaScriptNormalizer when available.


def test_normalizers_with_javascript(monkeypatch):
    dummy_module = types.SimpleNamespace(JavaScriptNormalizer=object)
    monkeypatch.setitem(sys.modules, "code_scalpel.ir.normalizers.javascript_normalizer", dummy_module)

    module = importlib.reload(normalizers)
    assert "JavaScriptNormalizer" in module.__all__
    assert module.JavaScriptNormalizer is dummy_module.JavaScriptNormalizer

    # Restore baseline module state
    monkeypatch.delitem(sys.modules, "code_scalpel.ir.normalizers.javascript_normalizer", raising=False)
    importlib.reload(normalizers)
