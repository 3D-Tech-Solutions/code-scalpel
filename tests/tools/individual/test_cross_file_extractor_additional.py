"""
[20251214_TEST] Extra coverage for CrossFileExtractor extraction paths.
"""

from code_scalpel.ast_tools.cross_file_extractor import CrossFileExtractor


def test_extract_with_dependencies(tmp_path):
    project = tmp_path
    (project / "__init__.py").write_text("\n")
    (project / "b.py").write_text("""
CONST = 7

def helper():
    return CONST
""")
    (project / "a.py").write_text("""
from b import helper

def foo():
    return helper()
""")

    extractor = CrossFileExtractor(str(project))
    result = extractor.extract("a.py", "foo", depth=1)
    assert result.success
    assert result.target is not None
    dep_names = {dep.name for dep in result.dependencies}
    assert "helper" in dep_names
    assert "helper" in result.combined_code


def test_extract_missing_symbol_returns_error(tmp_path):
    (tmp_path / "c.py").write_text("x = 1\n")
    extractor = CrossFileExtractor(str(tmp_path))
    result = extractor.extract("c.py", "not_here")
    assert not result.success
    assert any("not_here" in err for err in result.errors)
