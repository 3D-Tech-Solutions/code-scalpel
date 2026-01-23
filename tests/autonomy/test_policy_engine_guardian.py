import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from code_scalpel.policy_engine.policy_engine import (
    Operation,
    PolicyDecision,
    PolicyEngine,
)

# [20251216_TEST] Cover PolicyEngine happy-path and failure-path behavior


def _write_policy_file(tmp_path: Path, action: str = "WARN") -> Path:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(f"""
policies:
  - name: safe-edit
    description: Test policy
    rule: |
      package scalpel.security
      deny = []
    severity: MEDIUM
    action: {action}
""")
    return policy_path


def _make_run(side_effects):
    def _runner(args, **kwargs):
        key = tuple(args)
        if key in side_effects:
            return side_effects[key]
        # default success
        return SimpleNamespace(returncode=0, stdout="{}", stderr=b"")

    return _runner


def test_policy_engine_allows_with_warning(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    policy_path = _write_policy_file(tmp_path, action="WARN")

    eval_output = json.dumps({"result": [{"expressions": [{"value": ["warn"]}]}]})
    side_effects = {
        ("opa", "version"): SimpleNamespace(returncode=0, stdout="v", stderr=b""),
        ("opa", "check", "-"): SimpleNamespace(returncode=0, stdout="", stderr=b""),
        (
            "opa",
            "eval",
            "-d",
            "PLACEHOLDER",
            "-i",
            "PLACEHOLDER",
            "--format",
            "json",
            "data.code-scalpel.security.deny",
        ): SimpleNamespace(returncode=0, stdout=eval_output, stderr=""),
    }

    def fake_run(args, **kwargs):
        # Align temp file keys to the placeholder tuple above
        key = tuple(args)
        if key[0] == "opa" and key[1] == "eval":
            return side_effects[
                (
                    "opa",
                    "eval",
                    "-d",
                    "PLACEHOLDER",
                    "-i",
                    "PLACEHOLDER",
                    "--format",
                    "json",
                    "data.code-scalpel.security.deny",
                )
            ]
        return side_effects.get(key, SimpleNamespace(returncode=0, stdout="{}", stderr=b""))

    monkeypatch.setattr("code_scalpel.policy_engine.policy_engine.subprocess.run", fake_run)

    engine = PolicyEngine(policy_path=str(policy_path))
    op = Operation(type="code_edit", code="print('hi')", language="python", file_path="file.py")
    decision = engine.evaluate(op)

    assert decision.allowed is True
    assert "warning" in decision.reason
    assert decision.requires_override is False
    assert decision.violations and decision.violations[0].action == "WARN"


def test_policy_engine_denies_on_eval_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    policy_path = _write_policy_file(tmp_path, action="DENY")

    side_effects = {
        ("opa", "version"): SimpleNamespace(returncode=0, stdout="v", stderr=b""),
        ("opa", "check", "-"): SimpleNamespace(returncode=0, stdout="", stderr=b""),
        (
            "opa",
            "eval",
            "-d",
            "PLACEHOLDER",
            "-i",
            "PLACEHOLDER",
            "--format",
            "json",
            "data.code-scalpel.security.deny",
        ): SimpleNamespace(returncode=1, stdout="{}", stderr=b"boom"),
    }

    def fake_run(args, **kwargs):
        key = tuple(args)
        if key[0] == "opa" and key[1] == "eval":
            return side_effects[
                (
                    "opa",
                    "eval",
                    "-d",
                    "PLACEHOLDER",
                    "-i",
                    "PLACEHOLDER",
                    "--format",
                    "json",
                    "data.code-scalpel.security.deny",
                )
            ]
        return side_effects.get(key, SimpleNamespace(returncode=0, stdout="{}", stderr=b""))

    monkeypatch.setattr("code_scalpel.policy_engine.policy_engine.subprocess.run", fake_run)

    engine = PolicyEngine(policy_path=str(policy_path))
    op = Operation(type="file_access", file_path="secret.txt")
    decision = engine.evaluate(op)

    assert decision.allowed is False
    assert "failing CLOSED" in decision.reason
    assert decision.requires_override is False


def test_request_override_single_use(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    policy_path = _write_policy_file(tmp_path, action="WARN")

    # Simplify init by mocking subprocess calls
    monkeypatch.setattr(
        "code_scalpel.policy_engine.policy_engine.subprocess.run",
        lambda *_, **__: SimpleNamespace(returncode=0, stdout="{}", stderr=b""),
    )

    engine = PolicyEngine(policy_path=str(policy_path))
    monkeypatch.setattr(engine, "_log_override_request", lambda **kwargs: None)
    monkeypatch.setattr(engine, "_verify_human_code", lambda code: True)

    decision = PolicyDecision(allowed=False, reason="deny", violated_policies=["p1"])
    op = Operation(type="code_edit", file_path="danger.py")

    approved = engine.request_override(op, decision, justification="needed", human_code="123456")
    assert approved.approved is True

    reused = engine.request_override(op, decision, justification="again", human_code="123456")
    assert reused.approved is False
    assert "already used" in reused.reason
