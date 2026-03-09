# AGENTS.md - Code Scalpel Developer Guide

Quick reference for agent developers working on Code Scalpel. This guide covers build commands, code style, and critical development rules.

## Quick Start Commands

| Task | Command |
|------|---------|
| Full test suite | `pytest tests/` |
| Single test | `pytest tests/path/to/test_module.py::test_function_name` |
| Tests with coverage | `pytest --cov=src/code_scalpel tests/` |
| Coverage report | `pytest --cov=src/code_scalpel --cov-report=html tests/` |
| Lint code | `ruff check src/ tests/` |
| Check formatting | `black --check src/ tests/` |
| Auto-format code | `black src/ tests/` |
| Type checking | `pyright src/` |
| Security audit | `bandit -r src/` |
| Build package | `python -m build` |
| Install editable | `pip install -e .` |
| Install with dev tools | `pip install -e ".[dev]"` |

## Python Version & Dependencies

- **Required:** Python 3.10+ (3.13 also supported)
- **Project:** Uses hatchling as build backend
- **Core tools:** pytest, pytest-cov, black, ruff, pyright
- **Test timeout:** 600s (per pytest.ini for MCP/tool tests)
- **Type checking:** Pyright in basic mode on Python 3.10

## Code Style Guidelines

### Formatting & Linting
- **Line length:** 88 characters (Black default)
- **Formatter:** Black (auto-formats on save recommended)
- **Linter:** Ruff strict mode (ignores E501 for docstrings/comments)
- **Import style:** isort with Black profile

### Import Organization
```python
# 1. Standard library
import asyncio
import os
from typing import TYPE_CHECKING

# 2. Third-party
from pydantic import BaseModel
from mcp import Server

# 3. Local imports
from code_scalpel.mcp.tools import context
```

### Type Hints & Documentation
- Type hints required for all public function signatures
- Docstrings required for all public functions and classes
- Google-style docstrings for MCP tool documentation
- Include parameter types, return types, and examples where helpful

### Naming Conventions
- **Classes:** PascalCase (e.g., `ContextAnalyzer`)
- **Functions/variables:** snake_case (e.g., `extract_ast_nodes`)
- **Private members:** Leading underscore (e.g., `_internal_cache`)
- **Constants:** UPPER_CASE (e.g., `DEFAULT_TIMEOUT`)

### Error Handling
- No bare `except:` clauses - always specify exception type
- Use specific, descriptive exception messages
- Log errors using structlog (structured logging)
- Propagate tier-related errors with context

### Async Patterns
- Use `asyncio.to_thread()` for blocking I/O operations
- Mark async functions with `async def`
- Use type hints for awaitables: `Coroutine[Any, Any, T]`
- Test async code with pytest-asyncio (asyncio_mode = auto)

## MCP Tool Development

### Tool Structure
- All MCP tools are async functions decorated with `@mcp.tool()`
- Located in `src/code_scalpel/mcp/tools/` (context, extraction, analyze, security, graph, policy, symbolic, system, oracle)
- Return `ToolResponseEnvelope` with metadata: tier_applied, duration_ms, error

### Docstring Format (Required)
MCP tool docstrings follow a standardized format:
```python
async def tool_name(param1: str, param2: int) -> ToolResponseEnvelope:
    """
    Brief description of what the tool does.

    Community Tier: Basic capability (always available).
    Pro Tier: Enhanced capability with better performance.
    Enterprise Tier: Full capability including advanced features.

    Args:
        param1: Description of first parameter
        param2: Description of second parameter

    Returns:
        ToolResponseEnvelope with 'data' field containing results, or 'error' on failure
    """
```

### Change Tagging
- All changes must include a tag: `[YYYYMMDD_TYPE]` in docstrings and comments
- Types: SECURITY, BUGFIX, FEATURE, REFACTOR, PERF, TEST, DOCS, DEPRECATE
- Example: `# [20260129_FEATURE] New async context tool for faster analysis`

### Tier-Aware Development
- Tier limits defined in `src/code_scalpel/capabilities/limits.toml`
- Tools must enforce tier limits in their implementation
- Use `get_tool_capabilities()` to check tier at runtime
- Document tier differences explicitly in tool docstrings

## Testing Requirements

### Test Coverage Standard
- **Threshold:** ≥95% combined (statement + branch)
- **Current:** 94.86% (working to improve)
- **Run coverage:** `pytest --cov=src/code_scalpel --cov-report=term-missing tests/`

### TDD Workflow (Mandatory)
1. Write failing test first
2. Implement feature to make test pass
3. Run full test suite to verify no regressions
4. Check linting and formatting

### Tier Testing Guidelines
- Use fixtures from `tests/tools/tiers/conftest.py`
- License files stored in `tests/licenses/` (git-ignored, not monkeypatched)
- Test all three tiers: Community, Pro, Enterprise
- Never skip tier enforcement in tests

### Test Organization
- Test files follow pattern: `test_*.py`
- Test classes follow pattern: `Test*`
- Test functions follow pattern: `test_*`
- Use pytest markers: `@pytest.mark.asyncio`, `@pytest.mark.slow`, `@pytest.mark.docker`

### Example Test Pattern
```python
import pytest
from code_scalpel.mcp.tools import context

@pytest.mark.asyncio
async def test_context_analysis_basic():
    """Test basic context analysis functionality."""
    result = await context.analyze_context("sample code")
    assert result.tier_applied == "community"
    assert "data" in result
```

## Pre-Commit Verification Checklist

Before committing code, ensure:

1. **Linting passes:** `ruff check src/ tests/`
2. **Formatting passes:** `black --check src/ tests/`
3. **Type checking passes:** `pyright src/`
4. **Tests pass:** `pytest tests/` (at minimum affected tests)
5. **Coverage maintained:** ≥95% combined (statement + branch)
6. **Change tag added:** `[YYYYMMDD_TYPE]` in docstrings/comments
7. **No security issues:** `bandit -r src/` should pass

### Test Execution Tips
- Run single file: `pytest tests/tools/test_context.py`
- Run single test: `pytest tests/tools/test_context.py::test_analyze_context`
- Run with pattern: `pytest -k "context" tests/`
- Skip slow tests: `pytest -m "not slow" tests/`
- Verbose output: `pytest -vv tests/`

## Release Protocol

### Pre-Release Checklist
1. Verify all tests pass: `pytest tests/`
2. Verify coverage: `pytest --cov=src/code_scalpel tests/` ≥95%
3. Run security audit: `bandit -r src/`
4. Update version in `pyproject.toml`
5. Create release evidence files in `release_artifacts/v{VERSION}/`
6. Update documentation index in `docs/INDEX.md`
7. Build package: `python -m build`

### Release Gates (Gating System)
- **Security Gate:** Security audit must pass
- **Artifact Gate:** Build must succeed
- **TestPyPI Gate:** Publish to TestPyPI first
- **PyPI Gate:** Final production release

### Documentation Rules (Critical)
- Never create documentation without explicit user direction
- No automatic documentation, summaries, or change logs
- When documentation is needed:
  - Place in `docs/` subdirectory
  - Release notes in `docs/release_notes/RELEASE_NOTES_v{VERSION}.md`
  - Evidence files in `release_artifacts/v{VERSION}/`
  - Update `docs/INDEX.md` with new documentation link
- Never recommend releases unless explicitly asked

## Language Completion Standard

A language is only considered **complete** when both phases are finished. Do not start a new language until the previous language's Phase 2 is done.

### Phase 1 — IR Layer (prerequisite for extraction)
1. `pip install tree-sitter-{lang}` + add to `pyproject.toml` (main deps, `[all]`, `[polyglot]`)
2. `Language.LANG = "lang"` enum added to both `code_parsers/extractor.py` and `polyglot/extractor.py`
3. Extension map entries (`.ext → Language.LANG`)
4. `detect_language()` content-based heuristics
5. `_parse()` dispatch case + `_parse_lang()` method
6. `src/code_scalpel/ir/normalizers/lang_normalizer.py` — `LangVisitor` + `LangNormalizer`
7. `normalizers/__init__.py` — conditional import with try/except
8. `code_parsers/adapters/lang_adapter.py` — real implementation (not stub)
9. `capabilities/limits.toml` — `"lang"` in all 3 tier sections of `analyze_code` and `unified_sink_detect`
10. MCP docstrings updated in `extraction.py` and `oracle.py`
11. `tests/languages/test_lang_parser.py` — 14+ test cases
12. `tests/languages/test_polyglot_support.py` — extension + extraction matrix rows

### Phase 2 — Static Analysis Tool Parsers (required for completeness)
All tool parser files in `code_parsers/{lang}_parsers/` must be fully implemented:

| Tool type | Implementation pattern |
|-----------|----------------------|
| Free tool (CLI) | `execute_tool()` via subprocess + `parse_output()` + categorize + CWE mapping + report |
| Enterprise tool | `parse_output()` only; `execute_tool()` raises `NotImplementedError` with instructions |
| Graceful degradation | `shutil.which("tool") is None → return []` |

Each `{lang}_parsers/` directory requires:
- One file per static analysis tool
- `__init__.py` implementing `{Lang}ParserRegistry` with `get_parser(tool_name)` factory
- `tests/languages/test_{lang}_tool_parsers.py` with fixture-based tests (no tools need to be installed)

### Language Completion Status
See `wiki/Language-Completion-Roadmap.md` for full gap analysis, implementation specs, and sequenced work queue.

**Current roadmap focus:**
1. **Stage 10 graph-runtime parity**: keep graph/context discovery honest and expand support as narrow vertical slices rather than broad language claims.
2. **JavaScript/TypeScript runtime consistency**: complete the active JS/TS slice across `get_call_graph`, `get_graph_neighborhood`, `get_cross_file_dependencies`, `get_symbol_references`, and graph-derived `get_project_map` views.
3. **Stage 10.1 validation hardening**: completed for the current JS/TS runtime slice, including tier/metadata regressions and graph-surface doc audits.
4. **Java call-graph slice**: Java now enters the shared call-graph runtime, emits canonical `Class.method` nodes, and supports a narrow `get_call_graph` slice.
5. **Java scope boundary**: Pro/Enterprise resolve cross-file Java type/static imports, typed imported instance calls, superclass methods, and field-backed instance calls in `get_call_graph`; broader Java parity for neighborhood/dependency/reference surfaces is still separate work.

**Current incorporation status:**
- Phase 1 IR wiring and Phase 2 tool-parser work are broadly complete for the currently tracked languages in the roadmap.
- The remaining cross-language gap is not parser coverage; it is runtime parity in graph/context MCP surfaces, which remain Python-first overall.
- Treat `wiki/Language-Completion-Roadmap.md` as the source of truth for active parity work and checklist status.

---

## Key Development Principles

### Governance
- **Server-side governance:** Tier enforcement happens on server, not in agent
- **Agent simplicity:** Agents receive pass/fail responses (~50 tokens)
- **Tool authority:** If a tool says something is wrong, trust it

### Tier-Aware Capabilities
- 24 total MCP tools across 9 modules
- Each tool supports 3 tiers: Community (free), Pro, Enterprise
- Limits enforced per `src/code_scalpel/capabilities/limits.toml`
- Tools return metadata: `tier_applied`, `duration_ms`

### Performance & Efficiency
- Token efficiency is the top priority
- Minimize response sizes in ToolResponseEnvelope
- Use async/await for non-blocking I/O
- Implement timeouts appropriately (600s is generous for complex analyses)

## Configuration Files Reference

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project metadata, dependencies, build config, tool configs |
| `pytest.ini` | Pytest configuration, test paths, markers, timeout |
| `src/code_scalpel/capabilities/limits.toml` | Tier-specific limits for each MCP tool |
| `.github/copilot-instructions.md` | Comprehensive agent development guidelines |
| `docs/INDEX.md` | Master documentation index |

## Helpful Resources

- **Tool Specifications:** `docs/reference/DOCSTRING_SPECIFICATIONS.md` (all 23 tools)
- **Comprehensive Guidelines:** `.github/copilot-instructions.md` (836 lines, detailed rules)
- **Oracle Middleware:** `docs/oracle/ORACLE_INTEGRATION_GUIDE.md` (error recovery)
- **Architecture:** `docs/architecture/CODEBASE_EXPLORATION_REPORT.md` (system overview)
- **Audit Report:** `docs/reference/AUDIT_REPORT.md` (tool inventory and status)

---

**Last Updated:** March 3, 2026
**Project Version:** 2.1.0
**Python Support:** 3.10, 3.11, 3.12, 3.13
