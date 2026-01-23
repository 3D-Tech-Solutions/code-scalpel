"""
Claude Code hooks installer.

[20260116_FEATURE] v3.4.0 - Claude Code hooks installer

This module provides functions to install and configure Claude Code hooks
for Code Scalpel governance enforcement.

Usage:
    # Install Claude Code hooks
    code-scalpel install-hooks

    # Install to custom location
    code-scalpel install-hooks --settings-path /path/to/.claude/settings.json
"""

# [20260116_REFACTOR] Removed unused os import flagged by static analysis
import json
import platform
from pathlib import Path
from typing import Any

# Default hook configuration for Claude Code
DEFAULT_HOOK_CONFIG = {
    "hooks": {
        "PreToolUse": [
            {
                "name": "code-scalpel-governance",
                "match": {"tools": ["Edit", "Write", "Bash", "MultiEdit"]},
                "command": "code-scalpel hook pre-tool-use",
                "timeout": 10000,
                "onFailure": "block",
            }
        ],
        "PostToolUse": [
            {
                "name": "code-scalpel-audit",
                "match": {"tools": ["Edit", "Write", "Bash", "MultiEdit"]},
                "command": "code-scalpel hook post-tool-use",
                "timeout": 5000,
                "onFailure": "warn",
            }
        ],
    }
}

# Enterprise managed settings configuration
ENTERPRISE_MANAGED_CONFIG = {
    "hooks": {
        "PreToolUse": [
            {
                "name": "enterprise-governance",
                "match": {"tools": ["Edit", "Write", "Bash", "MultiEdit"]},
                "command": "code-scalpel hook pre-tool-use",
                "timeout": 10000,
                "onFailure": "block",
            }
        ],
        "PostToolUse": [
            {
                "name": "enterprise-audit",
                "match": {"tools": ["Edit", "Write", "Bash", "MultiEdit"]},
                "command": "code-scalpel hook post-tool-use",
                "timeout": 5000,
                "onFailure": "warn",
            }
        ],
    },
    "allowManagedHooksOnly": True,
}


def get_claude_settings_path(project_path: str | None = None) -> Path:
    """Get the path to Claude Code settings.json.

    Claude Code looks for settings in:
    1. Project-local: .claude/settings.json
    2. User-level: ~/.claude/settings.json
    3. Enterprise managed: /etc/claude-code/managed-settings.json (Linux)
                          C:\\ProgramData\\claude-code\\managed-settings.json (Windows)

    Args:
        project_path: Path to project directory (defaults to current directory)

    Returns:
        Path to the settings.json file (project-local by default)
    """
    if project_path is None:
        project_path = "."

    return Path(project_path) / ".claude" / "settings.json"


def get_user_settings_path() -> Path:
    """Get the path to user-level Claude Code settings.

    Returns:
        Path to user-level settings.json
    """
    return Path.home() / ".claude" / "settings.json"


def get_managed_settings_path() -> Path:
    """Get the path to enterprise managed settings.

    Returns:
        Path to managed settings file (platform-specific)
    """
    system = platform.system()
    if system == "Windows":
        return Path("C:/ProgramData/claude-code/managed-settings.json")
    else:
        return Path("/etc/claude-code/managed-settings.json")


def _read_settings(settings_path: Path) -> dict[str, Any]:
    """Read existing settings from file.

    Args:
        settings_path: Path to settings file

    Returns:
        Settings dictionary (empty dict if file doesn't exist)
    """
    if not settings_path.exists():
        return {}

    try:
        with open(settings_path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _write_settings(settings_path: Path, settings: dict[str, Any]) -> None:
    """Write settings to file.

    Args:
        settings_path: Path to settings file
        settings: Settings dictionary to write
    """
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")


def _merge_hooks(existing: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Merge hook configurations, avoiding duplicates.

    Args:
        existing: Existing hooks configuration
        new: New hooks to add

    Returns:
        Merged hooks configuration
    """
    result = existing.copy()

    for hook_type, hooks in new.items():
        if hook_type not in result:
            result[hook_type] = []

        existing_names = {h.get("name") for h in result[hook_type]}

        for hook in hooks:
            if hook.get("name") not in existing_names:
                result[hook_type].append(hook)

    return result


def install_claude_hooks(
    project_path: str | None = None,
    user_level: bool = False,
    enterprise: bool = False,
    force: bool = False,
) -> tuple[bool, str]:
    """Install Claude Code hooks for Code Scalpel governance.

    This function adds PreToolUse and PostToolUse hooks to the Claude Code
    settings file. The hooks intercept file operations and enforce governance.

    Args:
        project_path: Path to project directory (for project-local settings)
        user_level: Install to user-level settings instead of project
        enterprise: Install enterprise managed settings (requires admin)
        force: Overwrite existing hooks with same name

    Returns:
        Tuple of (success, message)
    """
    # Determine target settings file
    if enterprise:
        settings_path = get_managed_settings_path()
        hook_config = ENTERPRISE_MANAGED_CONFIG
    elif user_level:
        settings_path = get_user_settings_path()
        hook_config = DEFAULT_HOOK_CONFIG
    else:
        settings_path = get_claude_settings_path(project_path)
        hook_config = DEFAULT_HOOK_CONFIG

    # Check for enterprise settings requiring admin
    if enterprise:
        # Check if we can write to the managed settings path
        try:
            settings_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            return (
                False,
                f"Administrator privileges required to install enterprise hooks at {settings_path}",
            )

    # Read existing settings
    settings = _read_settings(settings_path)

    # Check if hooks already exist
    existing_hooks = settings.get("hooks", {})
    if existing_hooks and not force:
        # Check for our hooks
        pre_hooks = existing_hooks.get("PreToolUse", [])
        post_hooks = existing_hooks.get("PostToolUse", [])

        our_pre_hooks = [h for h in pre_hooks if "code-scalpel" in h.get("name", "").lower()]
        our_post_hooks = [h for h in post_hooks if "code-scalpel" in h.get("name", "").lower()]

        if our_pre_hooks or our_post_hooks:
            return True, f"Code Scalpel hooks already installed in {settings_path}"

    # Merge hooks
    if "hooks" not in settings:
        settings["hooks"] = {}

    if force:
        # Remove existing Code Scalpel hooks first
        for hook_type in ["PreToolUse", "PostToolUse"]:
            if hook_type in settings["hooks"]:
                settings["hooks"][hook_type] = [
                    h
                    for h in settings["hooks"][hook_type]
                    if "code-scalpel" not in h.get("name", "").lower() and "governance" not in h.get("name", "").lower()
                ]

    settings["hooks"] = _merge_hooks(settings["hooks"], hook_config["hooks"])

    # Copy enterprise-specific settings
    if enterprise and "allowManagedHooksOnly" in hook_config:
        settings["allowManagedHooksOnly"] = hook_config["allowManagedHooksOnly"]

    # Write settings
    try:
        _write_settings(settings_path, settings)
    except PermissionError:
        return False, f"Permission denied writing to {settings_path}"
    except OSError as e:
        return False, f"Error writing settings: {e}"

    return True, f"Claude Code hooks installed to {settings_path}"


def uninstall_claude_hooks(
    project_path: str | None = None,
    user_level: bool = False,
    enterprise: bool = False,
) -> tuple[bool, str]:
    """Uninstall Claude Code hooks for Code Scalpel.

    Args:
        project_path: Path to project directory
        user_level: Remove from user-level settings
        enterprise: Remove from enterprise managed settings

    Returns:
        Tuple of (success, message)
    """
    # Determine target settings file
    if enterprise:
        settings_path = get_managed_settings_path()
    elif user_level:
        settings_path = get_user_settings_path()
    else:
        settings_path = get_claude_settings_path(project_path)

    if not settings_path.exists():
        return True, f"Settings file does not exist: {settings_path}"

    # Read existing settings
    settings = _read_settings(settings_path)

    if "hooks" not in settings:
        return True, "No hooks found in settings"

    # Remove Code Scalpel hooks
    removed_count = 0
    for hook_type in ["PreToolUse", "PostToolUse"]:
        if hook_type in settings["hooks"]:
            original_count = len(settings["hooks"][hook_type])
            settings["hooks"][hook_type] = [
                h
                for h in settings["hooks"][hook_type]
                if "code-scalpel" not in h.get("name", "").lower() and "governance" not in h.get("name", "").lower()
            ]
            removed_count += original_count - len(settings["hooks"][hook_type])

    if removed_count == 0:
        return True, "No Code Scalpel hooks found to remove"

    # Remove allowManagedHooksOnly if we installed it
    if enterprise and "allowManagedHooksOnly" in settings:
        del settings["allowManagedHooksOnly"]

    # Write settings
    try:
        _write_settings(settings_path, settings)
    except PermissionError:
        return False, f"Permission denied writing to {settings_path}"
    except OSError as e:
        return False, f"Error writing settings: {e}"

    return True, f"Removed {removed_count} Code Scalpel hooks from {settings_path}"


def check_hooks_installed(project_path: str | None = None) -> tuple[bool, str]:
    """Check if Claude Code hooks are installed.

    Args:
        project_path: Path to project directory

    Returns:
        Tuple of (installed, message)
    """
    settings_path = get_claude_settings_path(project_path)

    if not settings_path.exists():
        return False, f"No settings file found at {settings_path}"

    settings = _read_settings(settings_path)
    hooks = settings.get("hooks", {})

    pre_hooks = hooks.get("PreToolUse", [])
    post_hooks = hooks.get("PostToolUse", [])

    our_pre = [h for h in pre_hooks if "code-scalpel" in h.get("name", "").lower()]
    our_post = [h for h in post_hooks if "code-scalpel" in h.get("name", "").lower()]

    if our_pre and our_post:
        return True, "Claude Code hooks are fully installed"
    elif our_pre or our_post:
        return True, "Claude Code hooks are partially installed"
    else:
        return False, "Claude Code hooks are not installed"


def get_settings_template() -> str:
    """Get the Claude Code settings.json template with hooks.

    Returns:
        JSON string template for settings.json
    """
    return json.dumps(DEFAULT_HOOK_CONFIG, indent=2)


def install_claude_hooks_cli(
    project_path: str | None = None,
    user_level: bool = False,
    enterprise: bool = False,
    force: bool = False,
) -> int:
    """CLI entry point for installing Claude Code hooks.

    Args:
        project_path: Path to project directory
        user_level: Install to user-level settings
        enterprise: Install enterprise managed settings
        force: Overwrite existing hooks

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    success, message = install_claude_hooks(
        project_path=project_path,
        user_level=user_level,
        enterprise=enterprise,
        force=force,
    )
    print(message)
    return 0 if success else 1


def uninstall_claude_hooks_cli(
    project_path: str | None = None,
    user_level: bool = False,
    enterprise: bool = False,
) -> int:
    """CLI entry point for uninstalling Claude Code hooks.

    Args:
        project_path: Path to project directory
        user_level: Remove from user-level settings
        enterprise: Remove from enterprise managed settings

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    success, message = uninstall_claude_hooks(
        project_path=project_path,
        user_level=user_level,
        enterprise=enterprise,
    )
    print(message)
    return 0 if success else 1
