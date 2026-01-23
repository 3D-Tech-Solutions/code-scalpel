"""Tier gating smoke tests for get_file_context async wrapper."""

import textwrap

import pytest

from code_scalpel.mcp.models.core import FileContextResult
from code_scalpel.mcp.tools.context import get_file_context

# [20251225_TEST] Ensure async wrapper respects tier capabilities


def _caps(max_lines, capabilities):
    return {"limits": {"max_context_lines": max_lines}, "capabilities": capabilities}


@pytest.mark.asyncio
async def test_async_get_file_context_pro(monkeypatch, tmp_path):
    helper = tmp_path / "helper.py"
    helper.write_text("CONST = 1\n")

    target = tmp_path / "target.py"
    target.write_text(textwrap.dedent("""
            import helper

            def calc(x):
                return helper.CONST + x
            """))

    pro_caps = _caps(
        2000,
        {
            "raw_source_retrieval",
            "ast_based_outlining",
            "semantic_summarization",
            "intent_extraction",
            "related_imports_inclusion",
            "smart_context_expansion",
        },
    )

    import code_scalpel.mcp.server as server

    monkeypatch.setattr(server, "get_current_tier_from_license", lambda: "pro")
    monkeypatch.setattr(server, "get_tool_capabilities", lambda tool, tier: pro_caps)

    result = await get_file_context(str(target))

    assert isinstance(result, FileContextResult)
    assert result.semantic_summary
    assert result.related_imports
    assert result.expanded_context


@pytest.mark.asyncio
async def test_async_get_file_context_enterprise_redaction(monkeypatch, tmp_path):
    secret = tmp_path / "secret.py"
    secret.write_text("token='AKIA1234567890123456'\nemail='x@y.com'\n")

    enterprise_caps = _caps(
        None,
        {
            "raw_source_retrieval",
            "ast_based_outlining",
            "semantic_summarization",
            "intent_extraction",
            "related_imports_inclusion",
            "smart_context_expansion",
            "pii_redaction",
            "secret_masking",
            "api_key_detection",
            "rbac_aware_retrieval",
            "file_access_control",
        },
    )

    import code_scalpel.mcp.server as server

    monkeypatch.setattr(server, "get_current_tier_from_license", lambda: "enterprise")
    monkeypatch.setattr(server, "get_tool_capabilities", lambda tool, tier: enterprise_caps)

    result = await get_file_context(str(secret))

    assert isinstance(result, FileContextResult)
    assert result.pii_redacted is True
    assert result.secrets_masked is True
    assert result.access_controlled is True
    assert result.redaction_summary
