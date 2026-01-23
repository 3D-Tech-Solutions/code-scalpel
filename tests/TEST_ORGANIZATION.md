# Test Organization Structure

[20260114_REFACTOR] Tests reorganized for better maintainability and targeted testing.

## Directory Structure

```
tests/
├── agents/                 # Agent framework integrations (302 tests)
│   ├── test_agents.py
│   ├── test_autogen_*.py
│   ├── test_crewai_*.py
│   └── test_base_agent_*.py
├── autonomy/               # Governance, policy, sandbox (394 tests)
│   ├── test_governance_*.py
│   ├── test_policy_engine*.py
│   ├── test_sandbox.py
│   ├── test_limits_merge.py
│   └── ...
├── cli/                    # CLI command tests (77 tests)
│   └── test_cli*.py
├── core/                   # Core analysis functionality (1,286 tests)
│   ├── ast/               # AST analysis (7 files)
│   ├── cache/             # Caching (2 files)
│   ├── parsers/           # Language parsers (28 files)
│   ├── pdg/               # PDG analysis (7 files)
│   └── test_*.py          # Core module tests
├── coverage/               # Coverage boost tests (625 tests)
│   └── test_coverage_*.py
├── evidence/               # Evidence files for validation
│   └── mcp-contract/
├── fixtures/               # Test fixtures and data
│   ├── data/
│   └── generate_fixture.py
├── integration/            # End-to-end integration tests (274 tests)
│   ├── test_integration*.py
│   ├── test_surgical_*.py
│   └── test_v151_integration.py
├── licenses/               # JWT test license files
│   └── *.jwt
├── licensing/              # License validation tests (58 tests)
│   ├── test_jwt_*.py
│   ├── test_crl_*.py
│   └── test_runtime_behavior_server.py
├── manual/                 # Manual test scripts (not auto-run)
│   └── manual_test_*.py
├── mcp/                    # MCP server/transport tests (531 tests)
│   ├── rename_symbol/
│   ├── scan_dependencies/
│   ├── test_mcp*.py
│   ├── test_tier_boundary_limits.py
│   └── test_type_evaporation_*.py
├── mcp_tool_verification/  # MCP contract verification (52 tests)
│   └── test_mcp_*.py
├── pdg_tools/              # PDG-specific tool tests (673 tests)
│   └── security/
├── scripts/                # Utility shell scripts
│   ├── create_init_files.sh
│   ├── organize_remaining.sh
│   └── organize_tests.sh
├── security/               # Security tests (re-exports from autonomy) (88 tests)
│   ├── test_crypto_verify.py
│   ├── test_sandbox.py
│   └── test_tamper_resistance.py
├── symbolic/               # Symbolic execution tests (295 tests)
│   ├── test_constraint_solver.py
│   ├── test_symbolic_*.py
│   └── test_test_generator*.py
├── tools/                  # MCP tool-specific tests (2,230 tests)
│   ├── analyze_code/
│   ├── code_policy_check/
│   ├── crawl_project/
│   ├── cross_file_security_scan/
│   ├── extract_code/
│   ├── generate_unit_tests/
│   ├── get_cross_file_dependencies/
│   ├── get_file_context/
│   ├── get_graph_neighborhood/
│   ├── get_project_map/
│   ├── get_symbol_references/
│   ├── individual/
│   ├── rename_symbol/
│   ├── security_scan/
│   ├── tiers/
│   ├── update_symbol/
│   ├── validate_paths/
│   └── verify_policy_integrity/
├── unit/                   # Unit tests (re-exports from core) (184 tests)
│   └── test_*.py
├── verification/           # Verification scripts (not auto-run)
│   └── verify_*.py
├── conftest.py             # Shared pytest fixtures
└── __init__.py
```

## Test Count Summary (January 14, 2026)

| Directory | Tests | Description |
|-----------|------:|-------------|
| **tools/** | 2,230 | Per-tool functionality and tier tests |
| **core/** | 1,286 | Core analysis (AST, PDG, parsers, cache) |
| **pdg_tools/** | 673 | PDG-specific tool tests |
| **coverage/** | 625 | Coverage improvement tests |
| **mcp/** | 531 | MCP server and transport tests |
| **autonomy/** | 394 | Governance, policy engine, sandbox |
| **agents/** | 302 | Agent framework integrations |
| **symbolic/** | 295 | Symbolic execution engine |
| **integration/** | 274 | End-to-end integration tests |
| **unit/** | 184 | Re-exports from core/ |
| **security/** | 88 | Re-exports from autonomy/ |
| **cli/** | 77 | CLI command tests |
| **licensing/** | 58 | License validation tests |
| **mcp_tool_verification/** | 52 | MCP contract verification |
| **TOTAL** | **7,069** | All tests |

## Running Tests

### Run all tests:
```bash
pytest tests/
```

### Run specific category:
```bash
pytest tests/core/              # Core functionality
pytest tests/mcp/               # MCP server tests
pytest tests/tools/             # Tool tests
pytest tests/autonomy/          # Governance tests
pytest tests/licensing/         # License tests
pytest tests/symbolic/          # Symbolic execution
```

### Run excluding slow tests:
```bash
pytest tests/ -m "not slow"
```

### Run with coverage:
```bash
pytest tests/ --cov=src/code_scalpel --cov-report=html
```

## Test Categories by Priority

### P0 - Critical (Must Pass for Release)
- `tests/core/` - Core analysis functionality
- `tests/licensing/` - License tier validation
- `tests/security/` - Security vulnerability detection
- `tests/mcp/` - MCP server integration

### P1 - High (Should Pass)
- `tests/tools/` - Tool functionality and tiers
- `tests/symbolic/` - Symbolic execution
- `tests/autonomy/` - Governance features

### P2 - Medium (Quality Assurance)
- `tests/integration/` - Integration tests
- `tests/agents/` - Agent integrations
- `tests/coverage/` - Coverage tracking

### P3 - Low (Convenience)
- `tests/cli/` - CLI functionality
- `tests/unit/` - Re-exported unit tests

## Directory Conventions

### Re-export Pattern
Some directories use re-exports for compatibility:
```python
# tests/unit/test_alias_resolver.py
from tests.core.test_alias_resolver import *  # noqa: F401, F403
```

This allows tests to be discovered in multiple locations without duplication.

### Tool-Specific Tests
Each tool in `tests/tools/` has its own subdirectory:
- `test_core_functionality.py` - Basic functionality
- `test_edge_cases.py` - Edge case handling
- `test_tier_enforcement.py` - Tier-based access control
- `test_*_tier.py` - Community/Pro/Enterprise tier tests

### Fixtures
Shared fixtures are in `tests/fixtures/data/`. Test-specific fixtures may be in subdirectories like `tests/tools/update_symbol/fixtures/`.

## Notes

- All test directories have `__init__.py` for proper package discovery
- Shell scripts moved to `tests/scripts/` (not auto-run)
- Manual tests in `tests/manual/` (not auto-run)
- Verification scripts in `tests/verification/` (not auto-run)
