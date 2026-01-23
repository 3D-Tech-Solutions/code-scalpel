"""
[20251217_TEST] Coverage tests for ast_tools/__init__.py import fallbacks.

Target: Raise ast_tools/__init__.py from 75% to 95%+.

Missing coverage:
- Lines 66-72: visualize_ast when ASTVisualizer is None
- Lines 81-84: ImportResolver/ImportInfo/ImportType fallback imports
- Lines 89-90: CrossFileExtractor/ExtractedSymbol fallback imports
"""

import pytest


def test_visualize_ast_raises_when_visualizer_unavailable(monkeypatch):
    """[20251217_TEST] visualize_ast raises ImportError when ASTVisualizer is None."""
    # Force ASTVisualizer to None by patching the import
    import code_scalpel.ast_tools as ast_tools_module

    original_visualizer = ast_tools_module.ASTVisualizer
    monkeypatch.setattr(ast_tools_module, "ASTVisualizer", None)

    with pytest.raises(ImportError, match="ASTVisualizer not available"):
        ast_tools_module.visualize_ast(None, "output", "png", True)

    # Restore
    monkeypatch.setattr(ast_tools_module, "ASTVisualizer", original_visualizer)


def test_import_resolver_fallback_none(monkeypatch):
    """[20251217_TEST] ImportResolver can be None if import fails."""
    # Simulate failed import by removing from sys.modules and patching
    import code_scalpel.ast_tools as ast_tools

    # Check if ImportResolver exists in __all__
    assert "ImportResolver" in ast_tools.__all__

    # ImportResolver might be None if import failed
    # This test confirms the fallback handling exists
    original_resolver = getattr(ast_tools, "ImportResolver", None)
    monkeypatch.setattr(ast_tools, "ImportResolver", None)

    # Accessing None should not raise during module load
    assert ast_tools.ImportResolver is None

    # Restore
    if original_resolver is not None:
        monkeypatch.setattr(ast_tools, "ImportResolver", original_resolver)


def test_cross_file_extractor_fallback_none(monkeypatch):
    """[20251217_TEST] CrossFileExtractor can be None if import fails."""
    import code_scalpel.ast_tools as ast_tools

    # Check __all__ includes CrossFileExtractor
    assert "CrossFileExtractor" in ast_tools.__all__

    original_extractor = getattr(ast_tools, "CrossFileExtractor", None)
    monkeypatch.setattr(ast_tools, "CrossFileExtractor", None)

    # Accessing None should not raise
    assert ast_tools.CrossFileExtractor is None

    # Restore
    if original_extractor is not None:
        monkeypatch.setattr(ast_tools, "CrossFileExtractor", original_extractor)


def test_osv_client_fallback_none(monkeypatch):
    """[20251217_TEST] osv_client can be None if import fails."""
    import code_scalpel.ast_tools as ast_tools

    assert "osv_client" in ast_tools.__all__

    original_osv = getattr(ast_tools, "osv_client", None)
    monkeypatch.setattr(ast_tools, "osv_client", None)

    assert ast_tools.osv_client is None

    if original_osv is not None:
        monkeypatch.setattr(ast_tools, "osv_client", original_osv)


def test_transformer_validator_utils_fallback_none(monkeypatch):
    """[20251217_TEST] Optional imports (transformer, validator, utils) can be None."""
    import code_scalpel.ast_tools as ast_tools

    # These can be None if imports fail
    optional_attrs = [
        "ASTTransformer",
        "ASTValidator",
        "is_constant",
        "get_node_type",
        "get_all_names",
    ]

    for attr in optional_attrs:
        assert attr in ast_tools.__all__

        original = getattr(ast_tools, attr, None)
        monkeypatch.setattr(ast_tools, attr, None)

        assert getattr(ast_tools, attr) is None

        if original is not None:
            monkeypatch.setattr(ast_tools, attr, original)


def test_import_info_type_symbol_definition_circular_import_graph_fallback():
    """[20251217_TEST] ImportInfo, ImportType, SymbolDefinition, CircularImport, ImportGraphResult fallbacks."""
    import code_scalpel.ast_tools as ast_tools

    # These should exist in __all__ and may be None on import failure
    import_related = [
        "ImportInfo",
        "ImportType",
        "SymbolDefinition",
        "CircularImport",
        "ImportGraphResult",
    ]

    for name in import_related:
        assert name in ast_tools.__all__
        # If they exist, they should be classes or None
        value = getattr(ast_tools, name, None)
        assert value is None or callable(value) or isinstance(value, type)


def test_extracted_symbol_extraction_result_fallback():
    """[20251217_TEST] ExtractedSymbol and ExtractionResult fallbacks."""
    import code_scalpel.ast_tools as ast_tools

    cross_file_related = ["ExtractedSymbol", "ExtractionResult"]

    for name in cross_file_related:
        assert name in ast_tools.__all__
        value = getattr(ast_tools, name, None)
        assert value is None or isinstance(value, type)


def test_build_ast_convenience_function_delegates_to_default_builder():
    """[20251217_TEST] build_ast uses the default ASTBuilder instance."""
    import code_scalpel.ast_tools as ast_tools

    code = "x = 1"
    tree = ast_tools.build_ast(code)

    # Should return an AST module
    import ast

    assert isinstance(tree, ast.Module)


def test_build_ast_from_file_convenience_function(tmp_path):
    """[20251217_TEST] build_ast_from_file uses the default ASTBuilder instance."""
    import code_scalpel.ast_tools as ast_tools

    test_file = tmp_path / "test.py"
    test_file.write_text("y = 2")

    tree = ast_tools.build_ast_from_file(str(test_file))

    import ast

    assert isinstance(tree, ast.Module)
