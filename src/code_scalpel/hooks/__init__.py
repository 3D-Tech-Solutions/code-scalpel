"""
Claude Code Hooks for Code Scalpel Governance Enforcement.

[20260116_FEATURE] v3.4.0 - Claude Code hooks for governance enforcement

This module provides hooks that integrate with Claude Code's PreToolUse and
PostToolUse hook system to enforce governance policies on all file operations.

The hooks ensure that:
1. All file modifications go through Code Scalpel governance validation
2. Direct file modification via bash is blocked (must use MCP tools)
3. All operations are logged to the audit trail
4. Audit coverage is tracked for git commits

Usage:
    Claude Code hooks are configured in .claude/settings.json:

    {
        "hooks": {
            "PreToolUse": [{
                "name": "code-scalpel-governance",
                "match": {"tools": ["Edit", "Write", "Bash", "MultiEdit"]},
                "command": "code-scalpel hook pre-tool-use",
                "onFailure": "block"
            }],
            "PostToolUse": [{
                "name": "code-scalpel-audit",
                "match": {"tools": ["Edit", "Write", "Bash", "MultiEdit"]},
                "command": "code-scalpel hook post-tool-use",
                "onFailure": "warn"
            }]
        }
    }

CLI Commands:
    code-scalpel hook pre-tool-use    - Run governance validation (reads stdin)
    code-scalpel hook post-tool-use   - Log operation to audit trail (reads stdin)
    code-scalpel verify-audit-coverage <file>  - Check audit coverage for a file
    code-scalpel install-hooks        - Install Claude Code hooks
    code-scalpel install-git-hooks    - Install git hooks for commit-time validation
    code-scalpel git-hook pre-commit  - Run pre-commit audit verification
    code-scalpel git-hook commit-msg  - Run commit-msg hook

See docs/architecture/IDE_ENFORCEMENT_GOVERNANCE.md for full documentation.
"""

from code_scalpel.hooks.claude_hooks import (
    HookContext,
    HookResponse,
    HookStatus,
    is_file_modifying_command,
    post_tool_use,
    pre_tool_use,
)
from code_scalpel.hooks.git_hooks import (
    git_hook_commit_msg,
    git_hook_pre_commit,
    install_git_hooks,
    verify_audit_coverage,
)
from code_scalpel.hooks.installer import (
    get_claude_settings_path,
    install_claude_hooks,
    uninstall_claude_hooks,
)

__all__ = [
    # Core hook functions
    "pre_tool_use",
    "post_tool_use",
    "is_file_modifying_command",
    # Hook data structures
    "HookContext",
    "HookResponse",
    "HookStatus",
    # Git hooks
    "verify_audit_coverage",
    "install_git_hooks",
    "git_hook_pre_commit",
    "git_hook_commit_msg",
    # Installer
    "install_claude_hooks",
    "uninstall_claude_hooks",
    "get_claude_settings_path",
]
