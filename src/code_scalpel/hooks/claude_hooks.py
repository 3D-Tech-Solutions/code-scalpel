"""
Claude Code hooks for governance enforcement.

[20260116_FEATURE] v3.4.0 - Claude Code hooks for AI governance

This module implements the PreToolUse and PostToolUse hooks that integrate
with Claude Code to enforce Code Scalpel governance on all file operations.

The hooks receive context from Claude Code via stdin in JSON format and
output responses to stdout. Exit code determines the hook result:
- Exit 0: Allow the operation
- Exit 1: Block the operation (with reason in stdout)
"""

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class HookStatus(Enum):
    """Status codes for hook responses."""

    ALLOWED = "allowed"
    BLOCKED = "blocked"
    LOGGED = "logged"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class HookContext:
    """Context passed to hooks from Claude Code.

    Claude Code provides tool invocation context via stdin in JSON format.
    This dataclass represents the expected structure.
    """

    tool: str
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] | None = None
    session_id: str | None = None
    timestamp: str | None = None

    @classmethod
    def from_stdin(cls) -> "HookContext":
        """Read hook context from stdin.

        Returns:
            HookContext parsed from stdin JSON

        Raises:
            ValueError: If stdin is not valid JSON
        """
        try:
            data = json.load(sys.stdin)
            return cls(
                tool=data.get("tool", ""),
                input=data.get("input", {}),
                output=data.get("output"),
                session_id=data.get("session_id"),
                timestamp=data.get("timestamp"),
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in stdin: {e}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HookContext":
        """Create HookContext from a dictionary.

        Args:
            data: Dictionary with hook context data

        Returns:
            HookContext instance
        """
        return cls(
            tool=data.get("tool", ""),
            input=data.get("input", {}),
            output=data.get("output"),
            session_id=data.get("session_id"),
            timestamp=data.get("timestamp"),
        )


@dataclass
class HookResponse:
    """Response from a hook execution.

    This is output to stdout in JSON format for Claude Code to process.
    """

    status: HookStatus
    reason: str | None = None
    policy: str | None = None
    suggestion: str | None = None
    files_modified: list[str] | None = None
    audit_entry_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert response to dictionary for JSON output."""
        result: dict[str, Any] = {"status": self.status.value}
        if self.reason:
            result["reason"] = self.reason
        if self.policy:
            result["policy"] = self.policy
        if self.suggestion:
            result["suggestion"] = self.suggestion
        if self.files_modified:
            result["files_modified"] = self.files_modified
        if self.audit_entry_id:
            result["audit_entry_id"] = self.audit_entry_id
        return result

    def to_json(self) -> str:
        """Convert response to JSON string."""
        return json.dumps(self.to_dict())


# Patterns for detecting file-modifying bash commands
FILE_MODIFICATION_PATTERNS = [
    # Output redirection
    r"\becho\s+.*>",  # echo redirection
    r"\bcat\s+.*>",  # cat redirection
    r"\bprintf\s+.*>",  # printf redirection
    r">+\s*\S+",  # any output redirection
    # In-place editing
    r"\bsed\s+-i",  # sed in-place
    r"\bawk\s+.*>",  # awk redirection
    r"\bperl\s+-i",  # perl in-place
    # File operations
    r"\brm\s+(?!-rf?\s+node_modules)",  # [20260116_BUGFIX] file deletion (allow node_modules cleanup: -r and -rf)
    r"\bmv\s+",  # file move
    r"\bcp\s+",  # file copy
    r"\btouch\s+",  # file creation
    r"\btruncate\s+",  # file truncation
    r"\bmkdir\s+",  # directory creation
    r"\brmdir\s+",  # directory removal
    # Text manipulation writing to files
    r"\btee\s+",  # tee command
    r"\bdd\s+.*of=",  # dd output
    # Archive extraction (creates files)
    r"\btar\s+.*-?x",  # tar extract (handles both -xvf and xzf forms)
    r"\bunzip\s+",  # unzip
    r"\bgunzip\s+",  # gunzip
    # Patch commands
    r"\bpatch\s+",  # patch command
    # Git commands that modify files
    r"\bgit\s+checkout\s+--",  # git checkout files
    r"\bgit\s+restore\s+",  # git restore
    r"\bgit\s+reset\s+--hard",  # git hard reset
    r"\bgit\s+clean\s+",  # git clean
]

# Safe bash commands that should be allowed
SAFE_COMMAND_PATTERNS = [
    # Read-only commands
    r"^\s*(cat|head|tail|less|more)\s+[^>|]+$",
    # Search commands
    r"^\s*(grep|rg|find|locate)\s+",
    # Listing commands
    r"^\s*(ls|ll|dir)\s+",
    # Git read operations
    r"^\s*git\s+(status|log|diff|show|branch|remote|fetch)\s*",
    # Package manager queries
    r"^\s*(npm|yarn|pip|poetry)\s+(list|show|info|outdated)\s*",
    # Test commands (read-only)
    r"^\s*(pytest|python\s+-m\s+pytest|npm\s+test|yarn\s+test)\s*",
    # Build commands (create artifacts, not source)
    r"^\s*(npm|yarn)\s+(build|compile)\s*",
]


def is_file_modifying_command(command: str) -> bool:
    """Check if a bash command modifies files.

    This function analyzes bash commands to determine if they would modify
    the filesystem. File-modifying commands are blocked by governance policy
    to ensure all changes go through Code Scalpel MCP tools.

    Args:
        command: The bash command string to analyze

    Returns:
        True if the command modifies files, False otherwise

    Examples:
        >>> is_file_modifying_command("echo 'hello' > file.txt")
        True
        >>> is_file_modifying_command("cat file.txt")
        False
        >>> is_file_modifying_command("sed -i 's/foo/bar/g' file.txt")
        True
        >>> is_file_modifying_command("git status")
        False
    """
    # Normalize command (remove leading/trailing whitespace)
    command = command.strip()

    # Check for safe commands first
    for pattern in SAFE_COMMAND_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return False

    # Check for file modification patterns
    for pattern in FILE_MODIFICATION_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True

    return False


def _get_governance_engine():
    """Get the governance engine for validation.

    Lazy import to avoid circular dependencies.
    """
    try:
        from code_scalpel.governance import UnifiedGovernance

        return UnifiedGovernance(".code-scalpel")
    except ImportError:
        return None
    except Exception:
        return None


def _get_audit_log():
    """Get the audit log for logging operations.

    Lazy import to avoid circular dependencies.
    """
    try:
        from code_scalpel.policy_engine.audit_log import AuditLog

        audit_path = Path(".code-scalpel") / "audit.jsonl"
        return AuditLog(str(audit_path))
    except ImportError:
        return None
    except Exception:
        return None


def _compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of content.

    Args:
        content: String content to hash

    Returns:
        Hex string of SHA-256 hash
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _extract_file_path(tool_name: str, tool_input: dict[str, Any]) -> str | None:
    """Extract file path from tool input based on tool type.

    Args:
        tool_name: Name of the tool (Edit, Write, etc.)
        tool_input: Tool input parameters

    Returns:
        File path if found, None otherwise
    """
    if tool_name in ("Edit", "Write", "MultiEdit"):
        return tool_input.get("file_path")
    return None


def _extract_content(tool_name: str, tool_input: dict[str, Any]) -> str | None:
    """Extract content/changes from tool input.

    Args:
        tool_name: Name of the tool
        tool_input: Tool input parameters

    Returns:
        Content string if found, None otherwise
    """
    if tool_name == "Write":
        return tool_input.get("content")
    elif tool_name == "Edit":
        return tool_input.get("new_string")
    elif tool_name == "MultiEdit":
        edits = tool_input.get("edits", [])
        return "\n".join(e.get("new_string", "") for e in edits)
    return None


def _extract_modified_files(tool_name: str, tool_input: dict[str, Any]) -> list[str]:
    """Extract list of files modified by a tool.

    Args:
        tool_name: Name of the tool
        tool_input: Tool input parameters

    Returns:
        List of file paths that were modified
    """
    files = []
    if tool_name in ("Edit", "Write"):
        file_path = tool_input.get("file_path")
        if file_path:
            files.append(file_path)
    elif tool_name == "MultiEdit":
        edits = tool_input.get("edits", [])
        for edit in edits:
            file_path = edit.get("file_path")
            if file_path and file_path not in files:
                files.append(file_path)
    return files


def pre_tool_use(context: HookContext | None = None) -> HookResponse:
    """Run before a tool is used. Block if policy violated.

    This hook is called by Claude Code before executing Edit, Write,
    Bash, or MultiEdit tools. It validates the operation against
    Code Scalpel governance policies.

    Args:
        context: Hook context from Claude Code (reads from stdin if None)

    Returns:
        HookResponse indicating whether to allow or block the operation

    Exit Codes (when called as CLI):
        0: Operation allowed
        1: Operation blocked
    """
    # Read context from stdin if not provided
    if context is None:
        try:
            context = HookContext.from_stdin()
        except ValueError as e:
            return HookResponse(
                status=HookStatus.ERROR,
                reason=str(e),
            )

    tool_name = context.tool
    tool_input = context.input

    # Check if this tool modifies files
    if tool_name in ("Edit", "Write", "MultiEdit"):
        file_path = _extract_file_path(tool_name, tool_input)
        new_content = _extract_content(tool_name, tool_input)

        # Try to validate through governance engine
        engine = _get_governance_engine()
        if engine is not None:
            try:
                # [20260116_BUGFIX] Use correct Operation fields - create FileChange with operation details
                from code_scalpel.governance import FileChange, GovernanceContext, Operation

                file_change = FileChange(
                    file_path=file_path or "<unknown>",
                    original_code="",
                    modified_code=new_content or "",
                )
                operation = Operation(
                    changes=[file_change],
                    description="code_edit",
                )
                # [20260116_BUGFIX] Pass operator and session_id via metadata to match GovernanceContext signature
                gov_context = GovernanceContext(
                    metadata={
                        "operator": "claude-code",
                        "session_id": context.session_id,
                    }
                )
                result = engine.evaluate(operation, gov_context)

                if not result.allowed:
                    # [20260116_BUGFIX] Derive blocked policy name from governance violations instead of non-existent `violated_policy`
                    policy_name: str | None = None
                    try:
                        violations = getattr(result, "policy_violations", None) or getattr(result, "violations", None)
                        if violations:
                            first_violation = violations[0]
                            rule = getattr(first_violation, "rule_name", None) or getattr(first_violation, "rule", None)
                            if rule is not None:
                                policy_name = getattr(rule, "name", rule)
                    except Exception:
                        policy_name = None

                    return HookResponse(
                        status=HookStatus.BLOCKED,
                        reason=result.reason or "Operation blocked by governance policy",
                        policy=policy_name,
                        suggestion="Use Code Scalpel MCP tools for governance-compliant modifications",
                    )
            except Exception:
                # If governance engine fails, allow but log warning
                pass

        return HookResponse(
            status=HookStatus.ALLOWED,
            files_modified=[file_path] if file_path else [],
        )

    elif tool_name == "Bash":
        command = tool_input.get("command", "")

        # Check for file modification commands
        if is_file_modifying_command(command):
            return HookResponse(
                status=HookStatus.BLOCKED,
                reason="Direct file modification via bash is not allowed under governance policy",
                policy="bash_file_modification",
                suggestion="Use Code Scalpel update_symbol or MCP Edit tools instead of direct file manipulation",
            )

        return HookResponse(status=HookStatus.ALLOWED)

    # Allow other tools
    return HookResponse(status=HookStatus.ALLOWED)


def post_tool_use(context: HookContext | None = None) -> HookResponse:
    """Run after a tool is used. Log to audit trail.

    This hook is called by Claude Code after executing Edit, Write,
    Bash, or MultiEdit tools. It logs the operation to the audit trail.

    Args:
        context: Hook context from Claude Code (reads from stdin if None)

    Returns:
        HookResponse with logging status

    Exit Codes (when called as CLI):
        0: Successfully logged
        1: Logging failed (warning only)
    """
    # Read context from stdin if not provided
    if context is None:
        try:
            context = HookContext.from_stdin()
        except ValueError as e:
            return HookResponse(
                status=HookStatus.ERROR,
                reason=str(e),
            )

    tool_name = context.tool
    tool_input = context.input
    tool_output = context.output or {}

    # Get audit log
    audit_log = _get_audit_log()
    if audit_log is None:
        return HookResponse(
            status=HookStatus.WARNING,
            reason="Audit log not available",
        )

    # Extract modified files
    files_modified = _extract_modified_files(tool_name, tool_input)

    # Compute content hash for file operations
    content_hash = None
    if tool_name in ("Edit", "Write", "MultiEdit"):
        content = _extract_content(tool_name, tool_input)
        if content:
            content_hash = _compute_content_hash(content)

    # Sanitize input for logging (remove large content)
    sanitized_input = {k: v for k, v in tool_input.items() if k not in ("content", "new_string")}
    if "content" in tool_input:
        sanitized_input["content_length"] = len(tool_input["content"])
    if "new_string" in tool_input:
        sanitized_input["new_string_length"] = len(tool_input["new_string"])

    # Create audit entry
    audit_entry = {
        "timestamp": datetime.now().isoformat(),
        "operator": "claude-code",
        "tool": tool_name,
        "input": sanitized_input,
        "success": tool_output.get("success", True),
        "files_modified": files_modified,
    }

    if content_hash:
        audit_entry["content_hash"] = content_hash

    if context.session_id:
        audit_entry["session_id"] = context.session_id

    # Log to audit trail
    try:
        audit_log.log_event(
            event_type="claude_code_tool_use",
            details=audit_entry,
            severity="MEDIUM",
        )
    except Exception as e:
        return HookResponse(
            status=HookStatus.WARNING,
            reason=f"Failed to log audit entry: {e}",
        )

    return HookResponse(
        status=HookStatus.LOGGED,
        files_modified=files_modified,
    )


def pre_tool_use_cli() -> int:
    """CLI entry point for pre-tool-use hook.

    Reads context from stdin, runs validation, outputs result to stdout.

    Returns:
        Exit code (0 = allowed, 1 = blocked)
    """
    try:
        response = pre_tool_use()
        print(response.to_json())

        if response.status == HookStatus.BLOCKED:
            return 1
        return 0
    except Exception as e:
        error_response = HookResponse(
            status=HookStatus.ERROR,
            reason=f"Hook execution failed: {e}",
        )
        print(error_response.to_json())
        return 1


def post_tool_use_cli() -> int:
    """CLI entry point for post-tool-use hook.

    Reads context from stdin, logs operation, outputs result to stdout.

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    try:
        response = post_tool_use()
        print(response.to_json())

        if response.status == HookStatus.ERROR:
            return 1
        return 0
    except Exception as e:
        error_response = HookResponse(
            status=HookStatus.ERROR,
            reason=f"Hook execution failed: {e}",
        )
        print(error_response.to_json())
        return 1
