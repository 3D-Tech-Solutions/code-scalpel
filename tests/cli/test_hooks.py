"""
Unit tests for Claude Code hooks.

[20260116_FEATURE] v3.4.0 - Tests for Claude Code governance hooks

These tests verify the functionality of:
- PreToolUse hook (governance validation)
- PostToolUse hook (audit logging)
- File modification detection for bash commands
- Audit coverage verification
- Hook installation
"""

import json
import tempfile

# [20260116_TEST] Removed unused datetime import flagged by static analysis
from pathlib import Path
from unittest.mock import MagicMock, patch

from code_scalpel.hooks.claude_hooks import (
    HookContext,
    HookResponse,
    HookStatus,
    is_file_modifying_command,
    post_tool_use,
    pre_tool_use,
)
from code_scalpel.hooks.git_hooks import (
    _is_code_file,
    install_git_hooks,
    uninstall_git_hooks,
    verify_audit_coverage,
)
from code_scalpel.hooks.installer import (
    check_hooks_installed,
    get_claude_settings_path,
    install_claude_hooks,
    uninstall_claude_hooks,
)


class TestIsFileModifyingCommand:
    """Tests for is_file_modifying_command function."""

    def test_echo_redirection_is_modifying(self):
        """Test that echo with redirection is detected."""
        assert is_file_modifying_command("echo 'hello' > file.txt") is True
        assert is_file_modifying_command("echo hello >> file.txt") is True

    def test_cat_redirection_is_modifying(self):
        """Test that cat with redirection is detected."""
        assert is_file_modifying_command("cat foo > bar.txt") is True
        assert is_file_modifying_command("cat << EOF > file.txt") is True

    def test_sed_inplace_is_modifying(self):
        """Test that sed -i is detected."""
        assert is_file_modifying_command("sed -i 's/foo/bar/g' file.txt") is True
        assert is_file_modifying_command("sed -i.bak 's/foo/bar/' file.txt") is True

    def test_rm_is_modifying(self):
        """Test that rm is detected."""
        assert is_file_modifying_command("rm file.txt") is True
        assert is_file_modifying_command("rm -rf directory") is True

    def test_mv_is_modifying(self):
        """Test that mv is detected."""
        assert is_file_modifying_command("mv old.txt new.txt") is True

    def test_cp_is_modifying(self):
        """Test that cp is detected."""
        assert is_file_modifying_command("cp source.txt dest.txt") is True

    def test_touch_is_modifying(self):
        """Test that touch is detected."""
        assert is_file_modifying_command("touch newfile.txt") is True

    def test_mkdir_is_modifying(self):
        """Test that mkdir is detected."""
        assert is_file_modifying_command("mkdir new_directory") is True

    def test_tee_is_modifying(self):
        """Test that tee is detected."""
        assert is_file_modifying_command("echo hello | tee output.txt") is True

    def test_tar_extract_is_modifying(self):
        """Test that tar extraction is detected."""
        assert is_file_modifying_command("tar -xvf archive.tar") is True
        assert is_file_modifying_command("tar xzf archive.tar.gz") is True

    def test_patch_is_modifying(self):
        """Test that patch is detected."""
        assert is_file_modifying_command("patch -p1 < changes.patch") is True

    def test_git_checkout_is_modifying(self):
        """Test that git checkout of files is detected."""
        assert is_file_modifying_command("git checkout -- file.txt") is True
        assert is_file_modifying_command("git restore file.txt") is True
        assert is_file_modifying_command("git reset --hard HEAD") is True

    def test_safe_commands_not_modifying(self):
        """Test that safe read-only commands are not flagged."""
        assert is_file_modifying_command("cat file.txt") is False
        assert is_file_modifying_command("ls -la") is False
        assert is_file_modifying_command("grep pattern file.txt") is False
        assert is_file_modifying_command("git status") is False
        assert is_file_modifying_command("git log") is False
        assert is_file_modifying_command("git diff") is False
        assert is_file_modifying_command("head -n 10 file.txt") is False
        assert is_file_modifying_command("tail -f log.txt") is False
        assert is_file_modifying_command("find . -name '*.py'") is False

    def test_pytest_is_safe(self):
        """Test that pytest/test commands are safe."""
        assert is_file_modifying_command("pytest tests/") is False
        assert is_file_modifying_command("python -m pytest") is False
        assert is_file_modifying_command("npm test") is False

    def test_build_commands_are_safe(self):
        """Test that build commands are safe."""
        assert is_file_modifying_command("npm build") is False
        assert is_file_modifying_command("yarn build") is False


class TestHookContext:
    """Tests for HookContext dataclass."""

    def test_from_dict_basic(self):
        """Test creating HookContext from dictionary."""
        data = {
            "tool": "Edit",
            "input": {
                "file_path": "/path/to/file.py",
                "old_string": "foo",
                "new_string": "bar",
            },
            "session_id": "test-session-123",
        }
        context = HookContext.from_dict(data)

        assert context.tool == "Edit"
        assert context.input["file_path"] == "/path/to/file.py"
        assert context.session_id == "test-session-123"

    def test_from_dict_with_output(self):
        """Test creating HookContext with output data."""
        data = {
            "tool": "Write",
            "input": {"file_path": "/path/to/file.py", "content": "code"},
            "output": {"success": True, "bytes_written": 100},
        }
        context = HookContext.from_dict(data)

        assert context.tool == "Write"
        assert context.output is not None
        assert context.output["success"] is True

    def test_from_dict_empty_input(self):
        """Test HookContext with missing input."""
        data = {"tool": "Bash"}
        context = HookContext.from_dict(data)

        assert context.tool == "Bash"
        assert context.input == {}


class TestHookResponse:
    """Tests for HookResponse dataclass."""

    def test_to_dict_allowed(self):
        """Test HookResponse serialization for allowed operations."""
        response = HookResponse(status=HookStatus.ALLOWED)
        data = response.to_dict()

        assert data["status"] == "allowed"
        assert "reason" not in data

    def test_to_dict_blocked(self):
        """Test HookResponse serialization for blocked operations."""
        response = HookResponse(
            status=HookStatus.BLOCKED,
            reason="Policy violation",
            policy="no_direct_file_modification",
            suggestion="Use MCP tools instead",
        )
        data = response.to_dict()

        assert data["status"] == "blocked"
        assert data["reason"] == "Policy violation"
        assert data["policy"] == "no_direct_file_modification"
        assert data["suggestion"] == "Use MCP tools instead"

    def test_to_json(self):
        """Test HookResponse JSON serialization."""
        response = HookResponse(status=HookStatus.LOGGED, files_modified=["/path/to/file.py"])
        json_str = response.to_json()
        data = json.loads(json_str)

        assert data["status"] == "logged"
        assert data["files_modified"] == ["/path/to/file.py"]


class TestPreToolUse:
    """Tests for pre_tool_use hook function."""

    def test_edit_tool_allowed(self):
        """Test that Edit tool is allowed with valid input."""
        context = HookContext(
            tool="Edit",
            input={
                "file_path": "/path/to/file.py",
                "old_string": "foo",
                "new_string": "bar",
            },
        )
        response = pre_tool_use(context)

        assert response.status == HookStatus.ALLOWED
        assert response.files_modified == ["/path/to/file.py"]

    def test_write_tool_allowed(self):
        """Test that Write tool is allowed with valid input."""
        context = HookContext(
            tool="Write",
            input={
                "file_path": "/path/to/file.py",
                "content": "def hello(): pass",
            },
        )
        response = pre_tool_use(context)

        assert response.status == HookStatus.ALLOWED
        assert response.files_modified == ["/path/to/file.py"]

    def test_bash_safe_command_allowed(self):
        """Test that safe bash commands are allowed."""
        context = HookContext(
            tool="Bash",
            input={"command": "git status"},
        )
        response = pre_tool_use(context)

        assert response.status == HookStatus.ALLOWED

    def test_bash_modifying_command_blocked(self):
        """Test that file-modifying bash commands are blocked."""
        context = HookContext(
            tool="Bash",
            input={"command": "echo 'malicious' > /etc/passwd"},
        )
        response = pre_tool_use(context)

        assert response.status == HookStatus.BLOCKED
        assert "bash" in response.reason.lower()
        assert response.policy == "bash_file_modification"

    def test_other_tools_allowed(self):
        """Test that non-file-modifying tools are allowed."""
        context = HookContext(
            tool="Read",
            input={"file_path": "/path/to/file.py"},
        )
        response = pre_tool_use(context)

        assert response.status == HookStatus.ALLOWED


class TestPostToolUse:
    """Tests for post_tool_use hook function."""

    def test_logs_edit_tool(self):
        """Test that Edit tool usage is logged."""
        context = HookContext(
            tool="Edit",
            input={
                "file_path": "/path/to/file.py",
                "old_string": "foo",
                "new_string": "bar",
            },
            output={"success": True},
            session_id="test-session",
        )

        # Mock the audit log
        with patch("code_scalpel.hooks.claude_hooks._get_audit_log") as mock_get_log:
            mock_log = MagicMock()
            mock_get_log.return_value = mock_log

            response = post_tool_use(context)

            assert response.status == HookStatus.LOGGED
            assert response.files_modified == ["/path/to/file.py"]
            mock_log.log_event.assert_called_once()

    def test_logs_write_tool(self):
        """Test that Write tool usage is logged."""
        context = HookContext(
            tool="Write",
            input={
                "file_path": "/path/to/file.py",
                "content": "def hello(): pass",
            },
            output={"success": True},
        )

        with patch("code_scalpel.hooks.claude_hooks._get_audit_log") as mock_get_log:
            mock_log = MagicMock()
            mock_get_log.return_value = mock_log

            response = post_tool_use(context)

            assert response.status == HookStatus.LOGGED

    def test_warning_when_no_audit_log(self):
        """Test warning response when audit log is unavailable."""
        context = HookContext(
            tool="Edit",
            input={"file_path": "/path/to/file.py"},
        )

        with patch("code_scalpel.hooks.claude_hooks._get_audit_log") as mock_get_log:
            mock_get_log.return_value = None

            response = post_tool_use(context)

            assert response.status == HookStatus.WARNING
            assert "not available" in response.reason


class TestIsCodeFile:
    """Tests for _is_code_file function."""

    def test_python_files(self):
        """Test Python file detection."""
        assert _is_code_file("app.py") is True
        assert _is_code_file("/path/to/module.py") is True

    def test_javascript_files(self):
        """Test JavaScript file detection."""
        assert _is_code_file("app.js") is True
        assert _is_code_file("component.jsx") is True
        assert _is_code_file("app.ts") is True
        assert _is_code_file("component.tsx") is True

    def test_other_languages(self):
        """Test other language file detection."""
        assert _is_code_file("Main.java") is True
        assert _is_code_file("main.go") is True
        assert _is_code_file("lib.rs") is True
        assert _is_code_file("program.cpp") is True
        assert _is_code_file("program.c") is True

    def test_non_code_files(self):
        """Test non-code files are not flagged."""
        assert _is_code_file("README.md") is False
        assert _is_code_file("config.json") is False
        assert _is_code_file("style.css") is False
        assert _is_code_file("image.png") is False


class TestVerifyAuditCoverage:
    """Tests for verify_audit_coverage function."""

    def test_non_code_file_always_covered(self):
        """Test that non-code files are always considered covered."""
        result = verify_audit_coverage("README.md")
        assert result is True

    def test_non_existent_file_covered(self):
        """Test that non-existent files are considered covered."""
        result = verify_audit_coverage("/path/to/nonexistent.py")
        assert result is True


class TestInstallGitHooks:
    """Tests for install_git_hooks function."""

    def test_install_in_git_repo(self):
        """Test installing hooks in a git repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .git directory
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()
            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir()

            success, message = install_git_hooks(tmpdir)

            assert success is True
            assert "Installed hooks" in message

            # Check hooks were created
            assert (hooks_dir / "pre-commit").exists()
            assert (hooks_dir / "commit-msg").exists()

    def test_install_not_git_repo(self):
        """Test installing hooks in non-git directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            success, message = install_git_hooks(tmpdir)

            assert success is False
            assert "Not a git repository" in message

    def test_uninstall_hooks(self):
        """Test uninstalling git hooks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .git directory with hooks
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()
            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir()

            # Install first
            install_git_hooks(tmpdir)

            # Then uninstall
            success, message = uninstall_git_hooks(tmpdir)

            assert success is True
            assert (hooks_dir / "pre-commit").exists() is False
            assert (hooks_dir / "commit-msg").exists() is False


class TestInstallClaudeHooks:
    """Tests for install_claude_hooks function."""

    def test_install_project_level(self):
        """Test installing Claude hooks at project level."""
        with tempfile.TemporaryDirectory() as tmpdir:
            success, message = install_claude_hooks(project_path=tmpdir)

            assert success is True
            assert "installed" in message.lower()

            # Check settings file was created
            settings_path = Path(tmpdir) / ".claude" / "settings.json"
            assert settings_path.exists()

            # Verify hooks content
            with open(settings_path) as f:
                settings = json.load(f)

            assert "hooks" in settings
            assert "PreToolUse" in settings["hooks"]
            assert "PostToolUse" in settings["hooks"]

    def test_install_already_installed(self):
        """Test that installing when already installed reports correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Install first time
            install_claude_hooks(project_path=tmpdir)

            # Try to install again
            success, message = install_claude_hooks(project_path=tmpdir)

            assert success is True
            assert "already installed" in message.lower()

    def test_uninstall_hooks(self):
        """Test uninstalling Claude hooks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Install first
            install_claude_hooks(project_path=tmpdir)

            # Uninstall
            success, message = uninstall_claude_hooks(project_path=tmpdir)

            assert success is True

            # Verify hooks were removed
            settings_path = Path(tmpdir) / ".claude" / "settings.json"
            with open(settings_path) as f:
                settings = json.load(f)

            # Should have empty hook arrays
            pre_hooks = settings.get("hooks", {}).get("PreToolUse", [])
            post_hooks = settings.get("hooks", {}).get("PostToolUse", [])
            scalpel_hooks = [h for h in pre_hooks + post_hooks if "code-scalpel" in h.get("name", "")]
            assert len(scalpel_hooks) == 0

    def test_check_hooks_installed(self):
        """Test checking if hooks are installed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Check before install
            installed, message = check_hooks_installed(tmpdir)
            assert installed is False

            # Install hooks
            install_claude_hooks(project_path=tmpdir)

            # Check after install
            installed, message = check_hooks_installed(tmpdir)
            assert installed is True


class TestGetClaudeSettingsPath:
    """Tests for get_claude_settings_path function."""

    def test_project_level_path(self):
        """Test getting project-level settings path."""
        path = get_claude_settings_path("/my/project")
        assert str(path) == "/my/project/.claude/settings.json"

    def test_current_directory_path(self):
        """Test getting settings path for current directory."""
        path = get_claude_settings_path()
        assert str(path).endswith(".claude/settings.json")
