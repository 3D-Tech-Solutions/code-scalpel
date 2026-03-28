"""Tests for Java import resolution.

[20260309_TEST] Verify Java package and import discovery for the first
cross-file Java resolver slice.
"""

import tempfile
from pathlib import Path

import pytest

from code_scalpel.ast_tools.java_import_resolver import JavaImportResolver
from code_scalpel.ast_tools.import_resolver import ImportType


@pytest.fixture
def temp_project():
    """Create a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def java_project(temp_project: Path) -> Path:
    """Create a small Java project with package and import relationships."""
    service_dir = temp_project / "src" / "com" / "example" / "service"
    repo_dir = temp_project / "src" / "com" / "example" / "repo"
    util_dir = temp_project / "src" / "com" / "example" / "util"
    service_dir.mkdir(parents=True)
    repo_dir.mkdir(parents=True)
    util_dir.mkdir(parents=True)

    (service_dir / "UserService.java").write_text(
        """
package com.example.service;

import com.example.repo.UserRepository;
import static com.example.util.Sql.raw;
import com.example.util.*;
import java.util.List;

public class UserService {
    public String load(String id) {
        return raw(UserRepository.find(id));
    }
}
""".strip() + "\n",
        encoding="utf-8",
    )

    (repo_dir / "UserRepository.java").write_text(
        """
package com.example.repo;

public class UserRepository {
    public static String find(String id) {
        return id;
    }
}
""".strip() + "\n",
        encoding="utf-8",
    )

    (util_dir / "Sql.java").write_text(
        """
package com.example.util;

public class Sql {
    public static String raw(String value) {
        return value;
    }
}
""".strip() + "\n",
        encoding="utf-8",
    )

    (util_dir / "Strings.java").write_text(
        """
package com.example.util;

public class Strings {
    public static String trim(String value) {
        return value.trim();
    }
}
""".strip() + "\n",
        encoding="utf-8",
    )

    ignored_dir = temp_project / ".venv" / "lib"
    ignored_dir.mkdir(parents=True)
    (ignored_dir / "Ignored.java").write_text(
        "package ignored;\npublic class Ignored {}\n",
        encoding="utf-8",
    )

    return temp_project


class TestJavaImportResolver:
    """Tests for JavaImportResolver."""

    def test_build_discovers_java_modules(self, java_project: Path) -> None:
        """Build should discover fully qualified Java module names."""
        resolver = JavaImportResolver(java_project)

        result = resolver.build()

        assert result.success is True
        assert result.modules == 4
        assert "com.example.service.UserService" in resolver.module_to_file
        assert "com.example.repo.UserRepository" in resolver.module_to_file
        assert "ignored.Ignored" not in resolver.module_to_file

    def test_build_extracts_java_imports(self, java_project: Path) -> None:
        """Build should parse direct, static, and wildcard Java imports."""
        resolver = JavaImportResolver(java_project)
        resolver.build()

        imports = resolver.imports["com.example.service.UserService"]
        imports_by_name = {imp.effective_name: imp for imp in imports}

        assert imports_by_name["UserRepository"].module == "com.example.repo"
        assert imports_by_name["UserRepository"].import_type == ImportType.DIRECT
        assert imports_by_name["raw"].module == "com.example.util.Sql"
        assert imports_by_name["raw"].import_type == ImportType.FROM
        assert imports_by_name["*"].module == "com.example.util"
        assert imports_by_name["*"].import_type == ImportType.WILDCARD

    def test_build_records_local_edges_for_java_imports(
        self, java_project: Path
    ) -> None:
        """Build should add edges for local class and static imports."""
        resolver = JavaImportResolver(java_project)
        resolver.build()

        assert resolver.edges["com.example.service.UserService"] >= {
            "com.example.repo.UserRepository",
            "com.example.util.Sql",
        }

    def test_build_expands_wildcard_imports_to_local_package_modules(
        self, java_project: Path
    ) -> None:
        """[20260315_TEST] Wildcard Java imports should expand to local package classes for cross-file analysis."""
        resolver = JavaImportResolver(java_project)
        resolver.build()

        assert resolver.edges["com.example.service.UserService"] >= {
            "com.example.util.Sql",
            "com.example.util.Strings",
        }
