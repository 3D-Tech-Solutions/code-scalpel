from pathlib import Path

from code_scalpel.ast_tools.import_resolver import ImportResolver, ImportType


def test_dynamic_imports_not_detected_yet():
    """Verify that dynamic imports are currently NOT detected."""
    # Setup
    repro_file = Path(__file__).parent / "repro_dynamic_imports.py"
    project_root = repro_file.parent

    resolver = ImportResolver(project_root)

    # Manually trigger analysis of the single file
    # We need to mock the file discovery or just call _analyze_file directly
    # But _analyze_file expects the file to be in file_to_module map

    module_name = "repro_dynamic_imports"
    resolver.file_to_module[str(repro_file)] = module_name
    resolver.module_to_file[module_name] = str(repro_file)

    resolver._analyze_file(repro_file)

    imports = resolver.imports[module_name]

    # Check static imports
    static_modules = {imp.module for imp in imports}
    assert "os" in static_modules
    assert "sys" in static_modules  # from sys import path -> module="sys"

    # Check dynamic imports (should be detected now)
    {imp.module for imp in imports}

    # importlib.import_module("math") -> module="math", type=DYNAMIC
    math_imports = [i for i in imports if i.module == "math" and i.import_type == ImportType.DYNAMIC]
    assert len(math_imports) == 1, "Failed to detect importlib.import_module('math')"

    # __import__("json") -> module="json", type=DUNDER
    # We expect 2 json imports: one literal and one variable
    json_imports = [i for i in imports if i.module == "json" and i.import_type == ImportType.DUNDER]
    assert len(json_imports) == 2, "Failed to detect __import__('json') (literal + variable)"

    # Variable import -> module="datetime", type=DYNAMIC
    # Note: This requires Phase 2 implementation
    dt_imports = [i for i in imports if i.module == "datetime" and i.import_type == ImportType.DYNAMIC]
    assert len(dt_imports) == 1, "Failed to resolve variable import 'datetime'"


if __name__ == "__main__":
    test_dynamic_imports_not_detected_yet()
    print("Verified: Dynamic imports are successfully detected!")
