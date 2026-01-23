"""Governance config profile precedence tests.

[20251231_TEST] Ensure `GovernanceConfigLoader` selects profile config files
via `SCALPEL_CONFIG_PROFILE` and respects precedence rules.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from code_scalpel.governance import GovernanceConfigLoader


def _write_config(path: Path, *, max_lines_per_change: int) -> None:
    path.write_text(
        json.dumps(
            {
                "version": "3.0.0",
                "profile": "test",
                "governance": {"change_budgeting": {"max_lines_per_change": max_lines_per_change}},
            }
        ),
        encoding="utf-8",
    )


def test_profile_env_selects_profile_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    policy_dir = tmp_path / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)

    _write_config(policy_dir / "config.json", max_lines_per_change=500)
    _write_config(policy_dir / "config.restrictive.json", max_lines_per_change=123)

    monkeypatch.setenv("SCALPEL_CONFIG_PROFILE", "restrictive")

    loader = GovernanceConfigLoader()
    cfg = loader.load()

    assert cfg.change_budgeting.max_lines_per_change == 123


def test_explicit_constructor_path_beats_profile_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    policy_dir = tmp_path / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)

    default_path = policy_dir / "config.json"
    restrictive_path = policy_dir / "config.restrictive.json"

    _write_config(default_path, max_lines_per_change=500)
    _write_config(restrictive_path, max_lines_per_change=123)

    monkeypatch.setenv("SCALPEL_CONFIG_PROFILE", "restrictive")

    loader = GovernanceConfigLoader(default_path)
    cfg = loader.load()

    assert cfg.change_budgeting.max_lines_per_change == 500


def test_scalpel_config_env_beats_profile_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    policy_dir = tmp_path / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)

    default_path = policy_dir / "config.json"
    restrictive_path = policy_dir / "config.restrictive.json"

    _write_config(default_path, max_lines_per_change=500)
    _write_config(restrictive_path, max_lines_per_change=123)

    monkeypatch.setenv("SCALPEL_CONFIG_PROFILE", "restrictive")
    monkeypatch.setenv("SCALPEL_CONFIG", str(default_path))

    loader = GovernanceConfigLoader()
    cfg = loader.load()

    assert cfg.change_budgeting.max_lines_per_change == 500
