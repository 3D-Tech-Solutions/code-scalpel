"""
Comprehensive tier-specific tests for get_file_context tool.

This test suite validates the get_file_context tool's tier-gating mechanism
by explicitly testing each tier's capabilities:

- Community tier: Basic extraction (functions, classes, imports, security issues)
- Pro tier: Code quality metrics (code smells, doc coverage, maintainability)
- Enterprise tier: Organizational metadata (compliance, owners, tech debt)

The investigation revealed that all advertised features ARE implemented,
but are tier-gated. These tests validate that tier-gating works correctly
by enabling/disabling capabilities per tier.
"""
