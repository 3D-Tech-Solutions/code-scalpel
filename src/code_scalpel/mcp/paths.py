"""Path resolution and config dir helpers for MCP server."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_file_path(path: str, check_exists: bool = False) -> Path:
    """Resolve file path to absolute Path object.

    Args:
        path: File path string to resolve
        check_exists: If True, raise FileNotFoundError if path doesn't exist

    Returns:
        Resolved absolute Path object

    Raises:
        FileNotFoundError: If check_exists=True and path doesn't exist
    """
    resolved = Path(path).resolve()
    if check_exists and not resolved.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return resolved


def scalpel_home_dir() -> Path:
    """Return the Code Scalpel home directory under the user's home."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config)
    return Path.home() / ".config"


def env_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def maybe_auto_init_config_dir(
    *,
    project_root: Path,
    tier: str,
    enabled: bool | None = None,
    mode: str | None = None,
    target: str | None = None,
) -> dict[str, object] | None:
    """Optionally initialize config directory scaffolding."""
    from code_scalpel.mcp import governance

    auto_init_mode = mode or os.environ.get("CODE_SCALPEL_CONFIG_AUTO_INIT", "safe")
    auto_init_target = target or os.environ.get("CODE_SCALPEL_CONFIG_AUTO_TARGET", "project")

    if enabled is None:
        enabled = env_truthy(os.environ.get("CODE_SCALPEL_CONFIG_AUTO_INIT"))

    if not enabled:
        return None

    return governance.auto_init_config_dir(
        project_root=project_root,
        tier=tier,
        mode=auto_init_mode,
        target=auto_init_target,
    )
