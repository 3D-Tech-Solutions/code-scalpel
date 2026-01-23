"""
Cross-File Security Scan Tool Test Suite.

[20260103_FEATURE] v3.1.0+ - Comprehensive test organization for cross_file_security_scan tool

Test Organization:
    - test_tiers.py: Tier system enforcement (community/pro/enterprise)
    - test_core_functionality.py: Core vulnerability detection and cross-file taint tracking
    - test_edge_cases.py: Edge cases, complex scenarios, error handling
    - test_mcp_interface.py: MCP protocol compliance and tool interface

Roadmap Reference:
    See docs/roadmap/cross_file_security_scan.md for feature roadmap
    See docs/testing/test_assessments/cross_file_security_scan_test_assessment.md for assessment

Test Coverage Summary:
    ✅ Tier enforcement: Community (depth=3, modules=10), Pro (depth=10, modules=100), Enterprise (unlimited)
    ✅ Vulnerability detection: SQL injection, command injection, path traversal
    ✅ Cross-file taint tracking: Module boundaries, multi-hop flows, call graphs
    ✅ Edge cases: Empty projects, syntax errors, circular imports, dynamic imports
    ✅ MCP interface: Tool availability, parameter validation, result serialization

Current Status: 60+ tests across 4 modules
"""
