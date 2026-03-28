"""Tests that shipped install manifests retain required runtime dependencies.

[20260311_TEST] Guard root install manifests so Go support remains available in
package installs and Docker/manual requirements-based installs.
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = PROJECT_ROOT / "pyproject.toml"
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"

_SHIPPED_ANALYZE_CODE_TREE_SITTER_DEPS = {
    "tree-sitter",
    "tree-sitter-java",
    "tree-sitter-javascript",
    "tree-sitter-typescript",
    "tree-sitter-c",
    "tree-sitter-cpp",
    "tree-sitter-c-sharp",
    "tree-sitter-go",
    "tree-sitter-kotlin",
    "tree-sitter-ruby",
    "tree-sitter-php",
    "tree-sitter-swift",
    "tree-sitter-rust",
}

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore[import-not-found]
    except ImportError:
        import tomllib  # type: ignore[no-redef]


def _load_pyproject() -> dict:
    with open(PYPROJECT, "rb") as fh:
        return tomllib.load(fh)


def _normalize_requirement_names(requirements: list[str]) -> set[str]:
    normalized: set[str] = set()
    for requirement in requirements:
        token = requirement.split(";", 1)[0].strip()
        token = token.split("[", 1)[0]
        for separator in (">=", "<=", "==", "~=", "!=", ">", "<"):
            if separator in token:
                token = token.split(separator, 1)[0].strip()
                break
        if token:
            normalized.add(token)
    return normalized


def _load_requirements_names() -> set[str]:
    requirement_lines = [
        line.split("#", 1)[0].strip()
        for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    return _normalize_requirement_names(requirement_lines)


class TestInstallManifests:
    """Release guards for runtime dependency manifests."""

    def test_pyproject_core_install_includes_tree_sitter_go(self) -> None:
        """[20260311_TEST] Core package install should pull in tree-sitter-go."""
        pyproject = _load_pyproject()
        dependencies = pyproject["project"]["dependencies"]
        assert "tree-sitter-go" in _normalize_requirement_names(dependencies)

    def test_pyproject_core_install_includes_all_shipped_analyze_code_parsers(self) -> None:
        """[20260314_TEST] Core installs should include every tree-sitter runtime claimed by analyze_code."""
        pyproject = _load_pyproject()
        dependencies = pyproject["project"]["dependencies"]
        assert _SHIPPED_ANALYZE_CODE_TREE_SITTER_DEPS <= _normalize_requirement_names(
            dependencies
        )

    def test_pyproject_polyglot_extra_includes_tree_sitter_go(self) -> None:
        """[20260311_TEST] Polyglot extra should retain tree-sitter-go support."""
        pyproject = _load_pyproject()
        dependencies = pyproject["project"]["optional-dependencies"]["polyglot"]
        assert "tree-sitter-go" in _normalize_requirement_names(dependencies)

    def test_pyproject_polyglot_extra_includes_all_shipped_analyze_code_parsers(self) -> None:
        """[20260314_TEST] Polyglot extra should include every tree-sitter runtime claimed by analyze_code."""
        pyproject = _load_pyproject()
        dependencies = pyproject["project"]["optional-dependencies"]["polyglot"]
        assert _SHIPPED_ANALYZE_CODE_TREE_SITTER_DEPS <= _normalize_requirement_names(
            dependencies
        )

    def test_requirements_txt_includes_tree_sitter_go(self) -> None:
        """[20260311_TEST] Docker/manual requirements install should include tree-sitter-go."""
        requirement_names = _load_requirements_names()
        assert "tree-sitter-go" in requirement_names

    def test_requirements_txt_includes_core_polyglot_runtime_dependencies(self) -> None:
        """[20260311_TEST] Docker/manual requirements install should retain shipped parser/runtime deps."""
        requirement_names = _load_requirements_names()
        expected = {"tomli", *_SHIPPED_ANALYZE_CODE_TREE_SITTER_DEPS}
        assert expected <= requirement_names