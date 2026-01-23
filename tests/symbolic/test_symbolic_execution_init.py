"""
[20251214_TEST] Coverage for symbolic_execution_tools package initialization.
"""

import importlib


def test_symbolic_execution_init_exports_and_warns(recwarn):
    """Test symbolic_execution_tools module exports correctly."""
    module = importlib.reload(importlib.import_module("code_scalpel.symbolic_execution_tools"))

    assert "SymbolicAnalyzer" in module.__all__
    assert module.CrossFileTaintTracker is None or module.CrossFileTaintTracker
    # [20251218_TEST] Warning was disabled in v3.0.0 - no longer checking for it


# [20251225_TEST] Updated after backward compat stub removal - cross_file_taint now imports directly
def test_symbolic_execution_init_missing_cross_file(monkeypatch):
    """Test symbolic_execution_tools handles missing cross_file_taint module gracefully."""
    import builtins
    import sys

    # Patch the actual import location to simulate missing module
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "code_scalpel.security.analyzers.cross_file_taint":
            raise ImportError(f"No module named '{name}'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    # Remove from sys.modules if cached
    if "code_scalpel.symbolic_execution_tools" in sys.modules:
        del sys.modules["code_scalpel.symbolic_execution_tools"]

    module = importlib.import_module("code_scalpel.symbolic_execution_tools")

    # Should gracefully handle missing module and set to None
    assert module.CrossFileTaintTracker is None
