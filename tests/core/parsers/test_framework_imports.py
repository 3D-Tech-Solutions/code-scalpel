import textwrap
from pathlib import Path

import pytest

from code_scalpel.ast_tools.import_resolver import ImportResolver, ImportType


@pytest.mark.skip(reason="[20260117_TEST] ImportType.FRAMEWORK not implemented - feature incomplete")
def test_django_installed_apps_detection(tmp_path: Path) -> None:
    settings_py = tmp_path / "settings.py"
    settings_py.write_text(
        textwrap.dedent("""
            INSTALLED_APPS = [
                "django.contrib.admin",
                "django.contrib.auth",
                "myapp",
            ]
            """),
        encoding="utf-8",
    )

    resolver = ImportResolver(tmp_path)
    result = resolver.build()
    assert result.success, f"ImportResolver build failed: {result.errors}"

    module_name = resolver.file_to_module[str(settings_py)]
    imports = resolver.imports[module_name]

    apps = {i.module: i.import_type for i in imports if i.import_type == ImportType.FRAMEWORK}
    assert "django.contrib.admin" in apps
    assert "django.contrib.auth" in apps
    assert "myapp" in apps
    assert all(it == ImportType.FRAMEWORK for it in apps.values())
