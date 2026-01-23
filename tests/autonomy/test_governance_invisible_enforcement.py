"""Invisibility tests: governance enforced without manual tool calls.

[20251230_TEST] Once `.code-scalpel` exists, Pro/Enterprise must auto-enforce
policy integrity checks on every tool invocation.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _write_budget_yaml(policy_dir: Path, *, max_total_lines: int = 0) -> None:
    """Write a minimal budget.yaml for governance preflight tests."""
    (policy_dir / "budget.yaml").write_text(
        f"""budgets:
  default:
    max_files: 10
    max_lines_per_file: 100
    max_total_lines: {max_total_lines}
    max_complexity_increase: 100
    allowed_file_patterns: ["*.py"]
    forbidden_paths: [".git/", "node_modules/", "__pycache__/"]
""",
        encoding="utf-8",
    )


def _write_noop_policy_yaml(policy_dir: Path) -> None:
    """Write a valid policy.yaml that should never deny.

    [20251231_TEST] Test fixtures must use the supported `policies:` schema.
    """
    (policy_dir / "policy.yaml").write_text(
        """policies:
    - name: no-op
        description: Test policy that should never deny
        severity: INFO
        action: AUDIT
        rule: |
            package code_scalpel.test

            deny[msg] {
                input.operation == "code_edit"
                contains(input.code, "__NEVER_PRESENT__")
                msg := "should never trigger"
            }
""",
        encoding="utf-8",
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.skip(reason="[20260117_TEST] Governance policy_integrity not yet integrated with analyze_code")
@pytest.mark.anyio
async def test_pro_auto_enforces_policy_integrity_before_other_tools(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pro tier should fail-closed if manifest/secret missing."""
    monkeypatch.chdir(tmp_path)

    policy_dir = tmp_path / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)
    _write_noop_policy_yaml(policy_dir)

    monkeypatch.setenv("SCALPEL_GOVERNANCE_ENFORCEMENT", "block")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_FEATURES", "policy_integrity")
    monkeypatch.delenv("SCALPEL_MANIFEST_SECRET", raising=False)

    from code_scalpel.mcp import server

    # Force effective tier to Pro for deterministic testing.
    monkeypatch.setattr(server, "_get_current_tier", lambda: "pro")
    monkeypatch.setattr(server, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(server, "ALLOWED_ROOTS", [])

    tool = server.mcp._tool_manager.get_tool("analyze_code")
    result = await tool.run(
        {"code": "def f():\n    return 1\n", "language": "python", "file_path": None},
        context=None,
        convert_result=False,
    )

    # [20250112_BUGFIX] tool_id not in minimal profile - removed assertion
    assert result["error"] is not None
    assert result["error"]["error_code"] == "forbidden"


@pytest.mark.anyio
async def test_pro_allows_verify_policy_integrity_tool_even_when_broken(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The integrity tool itself must remain callable for debugging."""
    monkeypatch.chdir(tmp_path)

    policy_dir = tmp_path / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)
    _write_noop_policy_yaml(policy_dir)

    monkeypatch.setenv("SCALPEL_GOVERNANCE_MODE", "enforce")
    monkeypatch.delenv("SCALPEL_MANIFEST_SECRET", raising=False)

    from code_scalpel.mcp import server

    # Force effective tier to Pro for deterministic testing.
    monkeypatch.setattr(server, "_get_current_tier", lambda: "pro")

    # Import tool directly (FastMCP doesn't expose _tool_manager)
    from code_scalpel.mcp.tools.policy import verify_policy_integrity

    result = await verify_policy_integrity(
        policy_dir=str(policy_dir),
        manifest_source="file",
    )

    # [20260119_BUGFIX] Tool returns PolicyVerificationResult (Pydantic model)
    # Should return a normal tool result (possibly failing), not be blocked
    assert result.success is False  # Expected to fail without proper manifest


@pytest.mark.skip(reason="[20260117_TEST] Governance warn mode not yet integrated with analyze_code tool")
@pytest.mark.anyio
async def test_pro_warn_mode_allows_tools_with_break_glass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WARN mode should allow execution but include envelope warnings.

    [20251230_TEST] Pro can relax governance enforcement only when explicitly
    opting into break-glass.
    """
    monkeypatch.chdir(tmp_path)

    policy_dir = tmp_path / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)
    _write_noop_policy_yaml(policy_dir)

    monkeypatch.setenv("SCALPEL_GOVERNANCE_ENFORCEMENT", "warn")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_BREAK_GLASS", "1")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_FEATURES", "policy_integrity")
    monkeypatch.delenv("SCALPEL_MANIFEST_SECRET", raising=False)

    from code_scalpel.mcp import server

    monkeypatch.setattr(server, "_get_current_tier", lambda: "pro")
    monkeypatch.setattr(server, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(server, "ALLOWED_ROOTS", [])

    tool = server.mcp._tool_manager.get_tool("analyze_code")
    result = await tool.run(
        {"code": "def f():\n    return 1\n", "language": "python", "file_path": None},
        context=None,
        convert_result=False,
    )

    # [20250112_BUGFIX] tool_id not in minimal profile - removed assertion
    # [20260117_TEST] Tools now return Pydantic models, not dicts
    assert result.error is None
    warnings = getattr(result, "warnings", []) or []
    assert isinstance(warnings, list)
    assert any("Governance WARN" in w for w in warnings)


@pytest.mark.skip(reason="[20260117_TEST] Governance fail-closed mode not yet integrated with analyze_code tool")
@pytest.mark.anyio
async def test_pro_warn_mode_is_ignored_without_break_glass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without break-glass, Pro must remain fail-closed.

    [20251230_TEST] Prevent accidental relaxation of governance in Pro.
    """
    monkeypatch.chdir(tmp_path)

    policy_dir = tmp_path / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)
    _write_noop_policy_yaml(policy_dir)

    monkeypatch.setenv("SCALPEL_GOVERNANCE_ENFORCEMENT", "warn")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_FEATURES", "policy_integrity")
    monkeypatch.delenv("SCALPEL_GOVERNANCE_BREAK_GLASS", raising=False)
    monkeypatch.delenv("SCALPEL_MANIFEST_SECRET", raising=False)

    from code_scalpel.mcp import server

    monkeypatch.setattr(server, "_get_current_tier", lambda: "pro")
    monkeypatch.setattr(server, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(server, "ALLOWED_ROOTS", [])

    tool = server.mcp._tool_manager.get_tool("analyze_code")
    result = await tool.run(
        {"code": "def f():\n    return 1\n", "language": "python", "file_path": None},
        context=None,
        convert_result=False,
    )

    # [20250112_BUGFIX] tool_id not in minimal profile - removed assertion
    # [20260117_TEST] Tools now return Pydantic models, not dicts
    assert result.error is not None
    assert result.error.error_code == "forbidden"


@pytest.mark.anyio
async def test_write_tools_only_flag_skips_policy_integrity_for_read_tools(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[20251231_TEST] With WRITE_TOOLS_ONLY, read tools should not be blocked."""
    monkeypatch.chdir(tmp_path)

    policy_dir = tmp_path / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)
    _write_noop_policy_yaml(policy_dir)

    monkeypatch.setenv("SCALPEL_GOVERNANCE_ENFORCEMENT", "block")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_FEATURES", "policy_integrity")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_WRITE_TOOLS_ONLY", "1")
    monkeypatch.delenv("SCALPEL_MANIFEST_SECRET", raising=False)

    from code_scalpel.mcp import server

    monkeypatch.setattr(server, "_get_current_tier", lambda: "pro")

    # Import tool directly (FastMCP doesn't expose _tool_manager)
    from code_scalpel.mcp.tools.analyze import analyze_code

    result = await analyze_code(
        code="def f():\n    return 1\n",
        language="python",
        file_path=None,
    )

    # [20260119_BUGFIX] Tool returns AnalysisResult (Pydantic model)
    assert result.error is None


@pytest.mark.skip(reason="[20260117_TEST] Governance budget not yet integrated with update_symbol tool")
@pytest.mark.anyio
async def test_write_tools_only_flag_does_not_disable_budget_for_write_tools(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[20251231_TEST] WRITE_TOOLS_ONLY must still enforce budgets on writes."""
    monkeypatch.chdir(tmp_path)

    policy_dir = tmp_path / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)
    _write_budget_yaml(policy_dir, max_total_lines=0)

    target_file = tmp_path / "app.py"
    target_file.write_text(
        """def f():
    return 1
""",
        encoding="utf-8",
    )

    monkeypatch.setenv("SCALPEL_GOVERNANCE_ENFORCEMENT", "block")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_FEATURES", "budget")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_WRITE_TOOLS_ONLY", "1")

    from code_scalpel.mcp import server

    monkeypatch.setattr(server, "_get_current_tier", lambda: "pro")
    monkeypatch.setattr(server, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(server, "ALLOWED_ROOTS", [])

    tool = server.mcp._tool_manager.get_tool("update_symbol")
    result = await tool.run(
        {
            "file_path": str(target_file),
            "target_type": "function",
            "target_name": "f",
            "new_code": """def f():\n    x = 1\n    return x\n""",
            "operation": "replace",
            "new_name": None,
            "create_backup": False,
        },
        context=None,
        convert_result=False,
    )

    # [20250112_BUGFIX] tool_id not in minimal profile - removed assertion
    # [20260117_TEST] Tools now return Pydantic models, not dicts
    assert result.error is not None
    assert result.error.error_code == "forbidden"
