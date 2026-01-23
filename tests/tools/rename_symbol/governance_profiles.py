# [20260108_TEST] Governance profile fixtures for rename_symbol testing
"""Reusable governance profile fixtures across permissive, minimal, default, restrictive.

Each profile fixture:
- Creates policy_dir with corresponding budget.yaml
- Sets SCALPEL_GOVERNANCE_* environment variables
- Monkeypatches MCP server configuration
- Scopes file system operations to temp_path to prevent repo-wide scans
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def governance_permissive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Permissive governance: No limits, no enforcement (solo/hobby devs)."""
    monkeypatch.chdir(tmp_path)
    policy_dir = tmp_path / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)

    # No budget.yaml = permissive by default
    monkeypatch.setenv("SCALPEL_GOVERNANCE_ENFORCEMENT", "off")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_FEATURES", "")

    yield tmp_path


@pytest.fixture
def governance_minimal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Minimal governance: Basic audit, generous limits (1-5 devs, budget-constrained)."""
    monkeypatch.chdir(tmp_path)
    policy_dir = tmp_path / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)

    (policy_dir / "budget.yaml").write_text(
        """budgets:
  default:
    max_files: 50
    max_lines_per_file: 500
    max_total_lines: 2000
    max_complexity_increase: 50
    allowed_file_patterns: ["*.py", "*.js", "*.ts"]
    forbidden_paths: [".git/", "node_modules/", "__pycache__/"]
""",
        encoding="utf-8",
    )

    monkeypatch.setenv("SCALPEL_GOVERNANCE_ENFORCEMENT", "warn")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_FEATURES", "budget")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_AUDIT", "1")

    yield tmp_path


@pytest.fixture
def governance_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Default governance: Balanced security/productivity (5-20 devs, standard teams)."""
    monkeypatch.chdir(tmp_path)
    policy_dir = tmp_path / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)

    (policy_dir / "budget.yaml").write_text(
        """budgets:
  default:
    max_files: 20
    max_lines_per_file: 300
    max_total_lines: 1000
    max_complexity_increase: 30
    allowed_file_patterns: ["*.py", "*.js", "*.ts"]
    forbidden_paths: [".git/", "node_modules/", "__pycache__/"]
""",
        encoding="utf-8",
    )

    monkeypatch.setenv("SCALPEL_GOVERNANCE_ENFORCEMENT", "block")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_FEATURES", "budget,integrity")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_AUDIT", "1")

    yield tmp_path


@pytest.fixture
def governance_restrictive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Restrictive governance: Strict controls (20+ devs, enterprise/SOC2/ISO)."""
    monkeypatch.chdir(tmp_path)
    policy_dir = tmp_path / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)

    (policy_dir / "budget.yaml").write_text(
        """budgets:
  default:
    max_files: 5
    max_lines_per_file: 100
    max_total_lines: 200
    max_complexity_increase: 10
    allowed_file_patterns: ["*.py"]
    forbidden_paths: [".git/", "node_modules/", "__pycache__/", "vendor/"]
""",
        encoding="utf-8",
    )

    monkeypatch.setenv("SCALPEL_GOVERNANCE_ENFORCEMENT", "block")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_FEATURES", "budget,integrity,policy")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_AUDIT", "1")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_APPROVAL_REQUIRED", "1")

    yield tmp_path


@pytest.fixture
def scope_filesystem(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Scope Path.rglob and symbol references to temp_path to prevent repo-wide scans."""
    original_rglob = Path.rglob

    def _scoped_rglob(self: Path, pattern: str):
        if tmp_path in self.parents or self == tmp_path:
            return original_rglob(self, pattern)
        return []

    monkeypatch.setattr(Path, "rglob", _scoped_rglob)

    from code_scalpel.mcp import server

    monkeypatch.setattr(
        server,
        "_get_symbol_references_sync",
        lambda symbol_name, *_, **__: server.SymbolReferencesResult(
            success=True,
            symbol_name=symbol_name,
            definition_file=None,
            definition_line=None,
            references=[],
            total_references=0,
            files_scanned=1,
            total_files=1,
        ),
    )

    monkeypatch.setattr(
        server,
        "_update_cross_file_references",
        lambda *_, **__: {"files_updated": 0, "updated_files": [], "errors": []},
    )
