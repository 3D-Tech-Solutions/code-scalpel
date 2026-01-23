import ast

# [20251214_REFACTOR] Remove unused test imports flagged by ruff.
from code_scalpel.ast_tools.builder import ASTBuilder


# [20260118_TEST] Add coverage for ASTBuilder hooks, caching, and error handling.
def test_build_ast_applies_hooks_and_cache(monkeypatch):
    builder = ASTBuilder()
    seen_validation = []

    def custom_hook(code: str) -> str:
        return code + "\n# added"

    def validate(tree: ast.AST) -> None:
        seen_validation.append(tree)

    builder.add_preprocessing_hook(custom_hook)
    builder.add_validation_hook(validate)

    code = "x = 1"
    # Use the builder's preprocessing to match the cache key it stores.
    processed_code = builder._preprocess_code(code)

    tree_first = builder.build_ast(code)
    tree_second = builder.build_ast(processed_code, preprocess=False)

    assert tree_first is tree_second
    assert seen_validation, "validation hook should run on parsed tree"
    builder.remove_preprocessing_hook(custom_hook)
    builder.remove_validation_hook(validate)


# [20260118_TEST] Cover syntax error path and comment stripping logic.
def test_build_ast_handles_syntax_error():
    builder = ASTBuilder()
    assert builder.build_ast("def broken(") is None


def test_remove_comments_preserves_strings_and_drops_hash_comments():
    builder = ASTBuilder()
    source = """x = 1  # inline comment\n'''docstring'''\n# standalone\n"""
    cleaned = builder._remove_comments(source)
    assert "inline comment" not in cleaned
    assert "standalone" not in cleaned
    assert "docstring" in cleaned


# [20260118_TEST] Ensure file-based parsing handles missing paths gracefully.
def test_build_ast_from_file_missing(tmp_path):
    builder = ASTBuilder()
    missing = tmp_path / "does_not_exist.py"
    assert builder.build_ast_from_file(str(missing)) is None
