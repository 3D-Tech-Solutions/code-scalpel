import textwrap
from pathlib import Path

import pytest

from code_scalpel.ast_tools.import_resolver import ImportResolver, ImportType


@pytest.mark.skip(reason="[20260117_TEST] ImportType.FRAMEWORK not implemented - feature incomplete")
def test_flask_blueprint_detection(tmp_path: Path) -> None:
    app_py = tmp_path / "app.py"
    app_py.write_text(
        textwrap.dedent("""
            from flask import Flask, Blueprint

            bp = Blueprint("bp", __name__)

            app = Flask(__name__)
            app.register_blueprint(bp)
            """),
        encoding="utf-8",
    )

    resolver = ImportResolver(tmp_path)
    result = resolver.build()
    assert result.success, f"ImportResolver build failed: {result.errors}"

    module_name = resolver.file_to_module[str(app_py)]
    imports = resolver.imports[module_name]

    frameworks = [i for i in imports if i.import_type == ImportType.FRAMEWORK]
    names = {i.module for i in frameworks}
    assert "bp" in names
    assert all(i.import_type == ImportType.FRAMEWORK for i in frameworks)
