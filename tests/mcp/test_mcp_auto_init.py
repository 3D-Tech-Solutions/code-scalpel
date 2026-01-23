"""MCP startup auto-init tests.

[20251230_TEST] Ensure the MCP server can optionally auto-generate `.code-scalpel/`
so users don't need to run `code-scalpel init` manually.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def test_auto_init_disabled_creates_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from code_scalpel.mcp import server

    monkeypatch.delenv("SCALPEL_AUTO_INIT", raising=False)

    result = server._maybe_auto_init_config_dir(
        project_root=tmp_path,
        tier="community",
        enabled=False,
    )

    assert result is None
    assert not (tmp_path / ".code-scalpel").exists()


def test_auto_init_templates_only_creates_code_scalpel_dir_without_env_or_manifest(
    tmp_path: Path,
) -> None:
    from code_scalpel.mcp import server

    result = server._maybe_auto_init_config_dir(
        project_root=tmp_path,
        tier="community",
        enabled=True,
        mode="templates_only",
    )

    assert result is not None
    assert result["created"] is True
    assert (tmp_path / ".code-scalpel").exists()
    assert not (tmp_path / ".env").exists()
    assert not (tmp_path / ".code-scalpel" / "policy.manifest.json").exists()


def test_auto_init_full_creates_manifest_and_env(tmp_path: Path) -> None:
    from code_scalpel.mcp import server

    result = server._maybe_auto_init_config_dir(
        project_root=tmp_path,
        tier="pro",
        enabled=True,
        mode="full",
    )

    assert result is not None
    assert result["created"] is True
    assert (tmp_path / ".code-scalpel").exists()
    assert (tmp_path / ".code-scalpel" / "policy.manifest.json").exists()
    assert (tmp_path / ".env").exists()


def test_auto_init_user_target_uses_xdg_config_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """User target should create policies under XDG config home.

    [20251230_TEST] This enables non-IDE MCP clients (Claude Desktop/ChatGPT)
    to have a stable home for governance files without running the CLI.
    """
    from code_scalpel.mcp import server

    xdg_home = tmp_path / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_home))
    monkeypatch.delenv("SCALPEL_HOME", raising=False)

    result = server._maybe_auto_init_config_dir(
        project_root=tmp_path,
        tier="community",
        enabled=True,
        mode="templates_only",
        target="user",
    )

    assert result is not None
    assert result["created"] is True

    expected = xdg_home / "code-scalpel" / ".code-scalpel"
    assert expected.exists()
    assert not (tmp_path / ".code-scalpel").exists()
