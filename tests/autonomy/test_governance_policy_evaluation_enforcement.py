"""Governance policy evaluation enforcement tests.

[20251231_TEST] Ensure policy evaluation is enforced at the MCP boundary for
write tools (e.g., update_symbol) using `.code-scalpel/policy.yaml`.

These tests intentionally use the PolicyEngine fallback evaluator (no OPA
required) by defining simple `contains(input.code, ...)` rules.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _write_policy_yaml_deny_eval(policy_dir: Path) -> None:
    (policy_dir / "policy.yaml").write_text(
        """policies:
  - name: deny-eval
    description: Deny any code edit introducing eval()
    severity: HIGH
    action: DENY
    rule: |
      package code_scalpel.security

      deny[msg] {
        input.operation == \"code_edit\"
        contains(input.code, \"eval(\")
        msg := \"eval() is forbidden\"
      }
""",
        encoding="utf-8",
    )


@pytest.mark.skip(reason="[20260117_TEST] Governance policy_evaluation not yet integrated with update_symbol tool")
@pytest.mark.anyio
async def test_pro_block_mode_denies_update_symbol_when_policy_denies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    policy_dir = tmp_path / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)
    _write_policy_yaml_deny_eval(policy_dir)

    target_file = tmp_path / "app.py"
    target_file.write_text(
        """def f():
    return 1
""",
        encoding="utf-8",
    )

    monkeypatch.setenv("SCALPEL_GOVERNANCE_ENFORCEMENT", "block")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_FEATURES", "policy_evaluation")

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
            "new_code": """def f():\n    return eval(\"1+1\")\n""",
            "operation": "replace",
            "new_name": None,
            "create_backup": False,
        },
        context=None,
        convert_result=False,
    )

    assert result["tool_id"] == "update_symbol"
    assert result["error"] is not None
    assert result["error"]["error_code"] == "forbidden"

    # Ensure file was not modified.
    assert target_file.read_text(encoding="utf-8") == """def f():
    return 1
"""


@pytest.mark.skip(reason="[20250112_TEST] Test hangs - needs cross-file reference scanning mocks")
@pytest.mark.anyio
async def test_pro_warn_mode_allows_update_symbol_with_break_glass_and_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    policy_dir = tmp_path / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)
    _write_policy_yaml_deny_eval(policy_dir)

    target_file = tmp_path / "app.py"
    target_file.write_text(
        """def f():
    return 1
""",
        encoding="utf-8",
    )

    monkeypatch.setenv("SCALPEL_GOVERNANCE_ENFORCEMENT", "warn")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_BREAK_GLASS", "1")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_FEATURES", "policy_evaluation")

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
            "new_code": """def f():\n    return eval(\"1+1\")\n""",
            "operation": "replace",
            "new_name": None,
            "create_backup": False,
        },
        context=None,
        convert_result=False,
    )

    assert result["tool_id"] == "update_symbol"
    assert result["error"] is None
    assert isinstance(result.get("warnings"), list)
    assert any("Governance WARN" in w for w in result["warnings"])

    # Ensure file was modified.
    assert "eval(" in target_file.read_text(encoding="utf-8")


@pytest.mark.skip(reason="[20260117_TEST] Governance policy_evaluation not yet integrated with update_symbol tool")
@pytest.mark.anyio
async def test_pro_block_mode_emits_audit_event_on_policy_deny(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[20251231_TEST] Policy denies should produce an audit.jsonl entry."""
    monkeypatch.chdir(tmp_path)

    policy_dir = tmp_path / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)
    _write_policy_yaml_deny_eval(policy_dir)

    target_file = tmp_path / "app.py"
    target_file.write_text(
        """def f():
    return 1
""",
        encoding="utf-8",
    )

    monkeypatch.setenv("SCALPEL_GOVERNANCE_ENFORCEMENT", "block")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_FEATURES", "policy_evaluation")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_AUDIT", "1")

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
            "new_code": """def f():\n    return eval(\"1+1\")\n""",
            "operation": "replace",
            "new_name": None,
            "create_backup": False,
        },
        context=None,
        convert_result=False,
    )

    assert result["tool_id"] == "update_symbol"
    assert result["error"] is not None
    assert result["error"]["error_code"] == "forbidden"

    audit_path = policy_dir / "audit.jsonl"
    assert audit_path.exists()

    lines = [ln for ln in audit_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert lines

    events = [json.loads(ln) for ln in lines]
    assert any(
        e.get("tool_id") == "update_symbol"
        and e.get("tier") == "pro"
        and e.get("check") == "policy_evaluation"
        and e.get("decision") == "deny"
        for e in events
    )


@pytest.mark.skip(reason="[20250112_TEST] Test hangs - needs cross-file reference scanning mocks")
@pytest.mark.anyio
async def test_pro_warn_mode_allows_when_policy_yaml_missing_with_break_glass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    policy_dir = tmp_path / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)

    target_file = tmp_path / "app.py"
    target_file.write_text(
        """def f():
    return 1
""",
        encoding="utf-8",
    )

    monkeypatch.setenv("SCALPEL_GOVERNANCE_ENFORCEMENT", "warn")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_BREAK_GLASS", "1")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_FEATURES", "policy_evaluation")

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
            "new_code": """def f():\n    return 2\n""",
            "operation": "replace",
            "new_name": None,
            "create_backup": False,
        },
        context=None,
        convert_result=False,
    )

    assert result["tool_id"] == "update_symbol"
    assert result["error"] is None
    assert isinstance(result.get("warnings"), list)
    assert any("policy.yaml missing" in w for w in result["warnings"])

    # Ensure file was modified.
    assert "return 2" in target_file.read_text(encoding="utf-8")


@pytest.mark.skip(reason="[20260117_TEST] Governance policy_evaluation not yet integrated with update_symbol tool")
@pytest.mark.anyio
async def test_pro_block_mode_denies_when_policy_yaml_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    policy_dir = tmp_path / ".code-scalpel"
    policy_dir.mkdir(parents=True, exist_ok=True)

    target_file = tmp_path / "app.py"
    target_file.write_text(
        """def f():
    return 1
""",
        encoding="utf-8",
    )

    monkeypatch.setenv("SCALPEL_GOVERNANCE_ENFORCEMENT", "block")
    monkeypatch.setenv("SCALPEL_GOVERNANCE_FEATURES", "policy_evaluation")

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
            "new_code": """def f():\n    return 2\n""",
            "operation": "replace",
            "new_name": None,
            "create_backup": False,
        },
        context=None,
        convert_result=False,
    )

    assert result["tool_id"] == "update_symbol"
    assert result["error"] is not None
    assert result["error"]["error_code"] == "forbidden"

    # Ensure file was not modified.
    assert target_file.read_text(encoding="utf-8") == """def f():
    return 1
"""
