"""
Tests for code_policy_check MCP tool.

This test suite validates:
1. Configuration loading from .code-scalpel/limits.toml
2. Rule detection across all categories (PY, SEC, ASYNC, BP)
3. Tier enforcement (Community/Pro/Enterprise)
4. License validation and fallback
5. MCP protocol compliance
"""
