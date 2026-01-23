"""
Git hooks for Code Scalpel governance enforcement.

[20260116_FEATURE] v3.4.0 - Git hooks for commit-time audit verification

This module implements git hooks that verify audit coverage for all staged
changes before allowing commits. This provides a safety net to ensure no
code changes escape the audit trail.

Usage:
    # Install git hooks
    code-scalpel install-git-hooks

    # Verify audit coverage for a file
    code-scalpel verify-audit-coverage <file>

    # Run pre-commit hook (called by git)
    code-scalpel git-hook pre-commit

    # Run commit-msg hook (called by git)
    code-scalpel git-hook commit-msg <msg-file>
"""

import hashlib
import json
import subprocess

# [20260116_REFACTOR] Removed unused 'sys' import flagged by static analysis
from datetime import datetime
from pathlib import Path

# Code file extensions that require audit coverage
CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".scala",
    ".sh",
    ".bash",
}


def _compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of file contents.

    Args:
        file_path: Path to the file

    Returns:
        Hex string of SHA-256 hash
    """
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _is_code_file(file_path: str) -> bool:
    """Check if a file is a code file that requires audit coverage.

    Args:
        file_path: Path to the file

    Returns:
        True if the file is a code file, False otherwise
    """
    path = Path(file_path)
    return path.suffix.lower() in CODE_EXTENSIONS


def _get_audit_log_path() -> Path:
    """Get the path to the audit log file.

    Returns:
        Path to audit.jsonl file
    """
    return Path(".code-scalpel") / "audit.jsonl"


def _get_audit_entries_for_file(file_path: str, audit_log_path: Path | None = None) -> list[dict]:
    """Get all audit entries for a specific file.

    Args:
        file_path: Path to the file to check
        audit_log_path: Path to audit log (defaults to .code-scalpel/audit.jsonl)

    Returns:
        List of audit entries for the file
    """
    if audit_log_path is None:
        audit_log_path = _get_audit_log_path()

    if not audit_log_path.exists():
        return []

    entries = []
    abs_path = str(Path(file_path).resolve())
    rel_path = file_path

    with open(audit_log_path) as f:
        for line in f:
            try:
                entry = json.loads(line)
                details = entry.get("details", {})

                # Check if this entry relates to the file
                files_modified = details.get("files_modified", [])
                file_in_entry = details.get("file")

                # Match by absolute or relative path
                if any(f == abs_path or f == rel_path or f.endswith(rel_path) for f in files_modified):
                    entries.append(entry)
                elif file_in_entry and (
                    file_in_entry == abs_path or file_in_entry == rel_path or file_in_entry.endswith(rel_path)
                ):
                    entries.append(entry)
            except json.JSONDecodeError:
                continue

    return entries


def verify_audit_coverage(file_path: str, within_seconds: int = 3600) -> bool:
    """Check if file changes have corresponding audit entries.

    This function verifies that recent changes to a file have been logged
    to the audit trail. It's used by the git pre-commit hook to ensure
    all staged changes have audit coverage.

    Args:
        file_path: Path to the file to verify
        within_seconds: Time window to look for audit entries (default: 1 hour)

    Returns:
        True if the file has audit coverage, False otherwise
    """
    path = Path(file_path)

    # Skip if file doesn't exist (might be deleted)
    if not path.exists():
        return True

    # Skip non-code files
    if not _is_code_file(file_path):
        return True

    # Get current file hash
    current_hash = _compute_file_hash(path)

    # Get audit entries for this file
    entries = _get_audit_entries_for_file(file_path)

    # Check if any entry covers the current hash
    for entry in entries:
        details = entry.get("details", {})

        # Check content hash match
        entry_hash = details.get("content_hash")
        if entry_hash and entry_hash == current_hash:
            return True

        # Check new_content_hash match
        new_content_hash = details.get("new_content_hash")
        if new_content_hash and new_content_hash == current_hash:
            return True

    # Check time-based coverage (recent entries for this file)
    cutoff_time = datetime.now().timestamp() - within_seconds

    for entry in entries:
        try:
            timestamp_str = entry.get("timestamp", "")
            entry_time = datetime.fromisoformat(timestamp_str).timestamp()

            if entry_time >= cutoff_time:
                # Recent audit entry exists for this file
                return True
        except (ValueError, TypeError):
            continue

    return False


def _get_staged_files() -> list[str]:
    """Get list of staged files from git.

    Returns:
        List of staged file paths
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True,
        )
        files = result.stdout.strip().split("\n")
        return [f for f in files if f]  # Filter empty strings
    except subprocess.CalledProcessError:
        return []


def git_hook_pre_commit() -> int:
    """Run pre-commit audit verification.

    This hook is called by git before committing. It verifies that all
    staged code files have audit coverage.

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    print("Code Scalpel: Verifying audit coverage...")

    staged_files = _get_staged_files()

    if not staged_files:
        print("No staged files to check.")
        return 0

    uncovered_files = []
    for file_path in staged_files:
        # Skip non-code files
        if not _is_code_file(file_path):
            continue

        if not verify_audit_coverage(file_path):
            uncovered_files.append(file_path)

    if uncovered_files:
        print("")
        print("COMMIT BLOCKED: Files modified without Code Scalpel audit trail:")
        for file_path in uncovered_files:
            print(f"  - {file_path}")
        print("")
        # [20260116_BUGFIX] Updated remediation guidance to avoid referencing non-existent CLI command.
        print("To fix this:")
        print("  1. Make changes through Code Scalpel MCP tools so an audit entry is created, OR")
        print("  2. Add an audit entry for these changes according to your governance workflow, OR")
        print("  3. Use 'git commit --no-verify' with justification (logged)")
        print("")

        # Log the blocked commit attempt
        _log_blocked_commit(uncovered_files)

        return 1

    print("All changes have audit coverage")
    return 0


def git_hook_commit_msg(msg_file: str | None = None) -> int:
    """Run commit-msg hook to log commit to audit trail.

    This hook is called by git after the commit message is entered.
    It logs the commit to the audit trail.

    Args:
        msg_file: Path to the commit message file (from git)

    Returns:
        Exit code (0 = success)
    """
    commit_msg = ""
    if msg_file and Path(msg_file).exists():
        commit_msg = Path(msg_file).read_text().strip()

    # Get staged files
    staged_files = _get_staged_files()

    # Log to audit trail
    try:
        from code_scalpel.policy_engine.audit_log import AuditLog

        audit_log = AuditLog(str(_get_audit_log_path()))
        audit_log.log_event(
            event_type="git_commit",
            details={
                "files": staged_files,
                "message_preview": commit_msg[:100] if commit_msg else "",
                "timestamp": datetime.now().isoformat(),
            },
            severity="LOW",
        )
    except Exception:
        # Don't block commit if audit logging fails
        pass

    return 0


def _log_blocked_commit(uncovered_files: list[str]) -> None:
    """Log a blocked commit attempt to the audit trail.

    Args:
        uncovered_files: List of files without audit coverage
    """
    try:
        from code_scalpel.policy_engine.audit_log import AuditLog

        audit_log = AuditLog(str(_get_audit_log_path()))
        audit_log.log_event(
            event_type="blocked_commit",
            details={
                "uncovered_files": uncovered_files,
                "timestamp": datetime.now().isoformat(),
                "reason": "Missing audit coverage",
            },
            severity="HIGH",
        )
    except Exception:
        # [20260116_BUGFIX] Do not block commit if audit logging fails, but emit a warning.
        import sys

        print(
            "Code Scalpel git hook: failed to log blocked commit to audit trail.",
            file=sys.stderr,
        )


def install_git_hooks(repo_path: str | None = None, force: bool = False) -> tuple[bool, str]:
    """Install Code Scalpel git hooks.

    This function installs pre-commit and commit-msg hooks that enforce
    audit coverage for all commits.

    Args:
        repo_path: Path to git repository (defaults to current directory)
        force: Overwrite existing hooks if True

    Returns:
        Tuple of (success, message)
    """
    if repo_path is None:
        repo_path = "."

    repo_root = Path(repo_path).resolve()

    # Check if it's a git repository
    git_dir = repo_root / ".git"
    if not git_dir.exists():
        return False, f"Not a git repository: {repo_root}"

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    installed_hooks = []
    skipped_hooks = []

    # Pre-commit hook content
    pre_commit_content = """#!/bin/bash
# Code Scalpel pre-commit hook
# Verifies audit coverage for all staged changes
exec code-scalpel git-hook pre-commit "$@"
"""

    # Commit-msg hook content
    commit_msg_content = """#!/bin/bash
# Code Scalpel commit-msg hook
# Logs commit to audit trail
exec code-scalpel git-hook commit-msg "$@"
"""

    hooks_to_install = [
        ("pre-commit", pre_commit_content),
        ("commit-msg", commit_msg_content),
    ]

    for hook_name, hook_content in hooks_to_install:
        hook_path = hooks_dir / hook_name

        if hook_path.exists() and not force:
            # Check if it's already our hook
            existing_content = hook_path.read_text()
            if "Code Scalpel" in existing_content:
                skipped_hooks.append(f"{hook_name} (already installed)")
                continue
            else:
                skipped_hooks.append(f"{hook_name} (exists, use --force to overwrite)")
                continue

        # Write hook
        hook_path.write_text(hook_content)
        hook_path.chmod(0o755)
        installed_hooks.append(hook_name)

    # Build result message
    messages = []
    if installed_hooks:
        messages.append(f"Installed hooks: {', '.join(installed_hooks)}")
    if skipped_hooks:
        messages.append(f"Skipped: {', '.join(skipped_hooks)}")

    if not messages:
        messages.append("All hooks already installed")

    return True, "; ".join(messages)


def uninstall_git_hooks(repo_path: str | None = None) -> tuple[bool, str]:
    """Uninstall Code Scalpel git hooks.

    Args:
        repo_path: Path to git repository (defaults to current directory)

    Returns:
        Tuple of (success, message)
    """
    if repo_path is None:
        repo_path = "."

    repo_root = Path(repo_path).resolve()
    git_dir = repo_root / ".git"

    if not git_dir.exists():
        return False, f"Not a git repository: {repo_root}"

    hooks_dir = git_dir / "hooks"
    removed_hooks = []

    for hook_name in ["pre-commit", "commit-msg"]:
        hook_path = hooks_dir / hook_name

        if hook_path.exists():
            content = hook_path.read_text()
            if "Code Scalpel" in content:
                hook_path.unlink()
                removed_hooks.append(hook_name)

    if removed_hooks:
        return True, f"Removed hooks: {', '.join(removed_hooks)}"
    else:
        return True, "No Code Scalpel hooks found to remove"


def verify_audit_coverage_cli(file_path: str) -> int:
    """CLI entry point for verifying audit coverage.

    Args:
        file_path: Path to the file to verify

    Returns:
        Exit code (0 = has coverage, 1 = no coverage)
    """
    if verify_audit_coverage(file_path):
        print(f"Audit coverage verified for: {file_path}")
        return 0
    else:
        print(f"No audit coverage found for: {file_path}")
        return 1


def install_git_hooks_cli(force: bool = False) -> int:
    """CLI entry point for installing git hooks.

    Args:
        force: Overwrite existing hooks if True

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    success, message = install_git_hooks(force=force)
    print(message)
    return 0 if success else 1


def git_hook_pre_commit_cli() -> int:
    """CLI entry point for pre-commit hook.

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    return git_hook_pre_commit()


def git_hook_commit_msg_cli(msg_file: str | None = None) -> int:
    """CLI entry point for commit-msg hook.

    Args:
        msg_file: Path to commit message file

    Returns:
        Exit code (0 = success)
    """
    return git_hook_commit_msg(msg_file)
