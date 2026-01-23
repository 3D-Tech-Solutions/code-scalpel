"""Tests for MCP response configuration filtering."""

import json
from pathlib import Path

import pytest


def _reset_response_config_singleton() -> None:
    # ResponseConfig is cached as a module-level singleton.
    # Tests that rely on filesystem config must reset it.
    from code_scalpel.mcp import response_config as rc

    rc._response_config = None  # type: ignore[attr-defined]


def test_response_config_loaded_from_cwd_filters_fields(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Loads .code-scalpel/response_config.json from CWD and applies exclusions."""
    config_dir = tmp_path / ".code-scalpel"
    config_dir.mkdir(parents=True)

    config = {
        "global": {
            "profile": "minimal",
            "exclude_empty_arrays": True,
            "exclude_empty_objects": True,
            "exclude_null_values": True,
            "exclude_default_values": True,
        },
        "profiles": {
            "minimal": {
                "envelope": {"include": []},
                "common_exclusions": ["server_version", "function_count", "keep"],
            }
        },
        "tool_overrides": {},
    }

    (config_dir / "response_config.json").write_text(json.dumps(config), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    _reset_response_config_singleton()

    from code_scalpel.mcp.response_config import filter_tool_response

    payload = {
        "success": True,
        "server_version": "x",
        "function_count": 123,
        "keep": "nope",
        "ok": "yep",
        "empty_list": [],
        "empty_obj": {},
        "null": None,
    }

    filtered = filter_tool_response(payload, tool_name="analyze_code", tier="community")

    # Contract-critical fields must remain.
    assert filtered["success"] is True

    # Exclusions applied.
    assert "server_version" not in filtered
    assert "function_count" not in filtered
    assert "keep" not in filtered

    # Empty / null values excluded by default.
    assert "empty_list" not in filtered
    assert "empty_obj" not in filtered
    assert "null" not in filtered

    # Unexcluded field remains.
    assert filtered["ok"] == "yep"


def test_response_config_falls_back_to_defaults_on_invalid_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Invalid JSON should fall back to DEFAULT_CONFIG without throwing."""
    config_dir = tmp_path / ".code-scalpel"
    config_dir.mkdir(parents=True)
    (config_dir / "response_config.json").write_text("{not: json}", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    _reset_response_config_singleton()

    from code_scalpel.mcp.response_config import filter_tool_response

    payload = {"success": True, "server_version": "x", "ok": "yep"}
    filtered = filter_tool_response(payload, tool_name="analyze_code", tier="community")

    # Defaults should still preserve `success` and should apply some exclusions.
    assert filtered["success"] is True
    assert filtered.get("ok") == "yep"
