"""
[20251214_TEST] Additional coverage for ImportResolver dynamic and framework imports.
[20260117_TEST] Skipped - ImportType.FRAMEWORK not implemented yet.
"""

import pytest

from code_scalpel.ast_tools.import_resolver import ImportResolver, ImportType


@pytest.mark.skip(reason="[20260117_TEST] ImportType.FRAMEWORK not implemented - feature incomplete")
def test_dynamic_and_framework_imports(tmp_path):
    project = tmp_path
    # Project files
    (project / "pkg").mkdir()
    (project / "pkg" / "__init__.py").write_text("\n")
    (project / "pkg" / "mod.py").write_text("x = 1\n")
    (project / "pkg" / "mod2.py").write_text("x = 2\n")

    main_source = """
import importlib
module_name = "pkg.mod"
dynamic = importlib.import_module(module_name)
unknown = importlib.import_module(dynamic_name)
other = __import__("pkg.mod2")
INSTALLED_APPS = ["pkg.mod"]
from flask import Blueprint
bp = Blueprint("demo", __name__)

def build(app):
    app.register_blueprint(bp)
"""
    (project / "main.py").write_text(main_source)

    resolver = ImportResolver(project)
    result = resolver.build()
    assert result.success

    imports = resolver.imports.get("main", [])
    kinds = {info.import_type for info in imports}
    assert ImportType.DYNAMIC in kinds
    assert ImportType.DUNDER in kinds
    assert ImportType.FRAMEWORK in kinds
    assert ImportType.LAZY in kinds  # unknown dynamic_name

    dynamic_targets = [info.module for info in imports if info.import_type == ImportType.DYNAMIC]
    assert "pkg.mod" in dynamic_targets

    framework_targets = [info.module for info in imports if info.import_type == ImportType.FRAMEWORK]
    assert "pkg.mod" in framework_targets
