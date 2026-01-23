"""Test suite for get_cross_file_dependencies MCP tool.

This test module validates:
- Tier enforcement (Community depth=1/50 files, Pro depth=5/500 files, Enterprise unlimited)
- Invalid license fallback behavior
- Feature gating for Pro/Enterprise features
- Circular dependency detection
- Mermaid diagram generation
- Deep chain resolution (2-10 levels)
- v3.4.0 MCP integration features (wildcard, alias, re-export)
- Multi-language support (Python, JS/TS, Java)

[20260103_TEST] Comprehensive tier-aware test suite for get_cross_file_dependencies
"""
