<!-- [20251214_DOCS] DX and interop playbook for v1.5.4 -->

# Interop and DX Playbook (v1.5.4)

## One-Command Bootstrap
- Install deps and sanity-check: `python -m pip install -e .[dev] && python -m pip install pip-audit cyclonedx-bom && python -m pytest tests/test_symbolic_smoke.py -k cache_returns_dict`
- Minimal smoke: `python -m pytest tests/test_path_resolver.py::TestPathResolverInit::test_default_initialization`

## Quick Smoke Script (suggested)
- Add a script `scripts/smoke.sh` (or `.ps1` on Windows) to run: lint (ruff), format check (black --check), two fast pytest targets above, and `pip-audit --dry-run`.

## Integration Recipes

### LangChain (Python)
- Use `mcp_server_url` pointing to Code Scalpel MCP server.
- Wrap calls with `get_file_context`, `get_symbol_references`, and `update_symbol` for surgical edits; avoid whole-file rewrites.

### LlamaIndex
- Register a tool for `extract_code` and `simulate_refactor`; keep context windows small by requesting only target symbols.
- Cache analyzer outputs between runs to avoid repeated AST walks.

### Autogen
- Add a safety step invoking `simulate_refactor` before applying patches; gate on `result.safe is True`.
- Use `scan_dependencies` to block runs when high-severity vulnerabilities are detected.

### Claude Tools / OpenAI Function Calling
- Expose MCP tools (`analyze_code`, `extract_code`, `update_symbol`, `simulate_refactor`) as functions; keep schemas minimal.
- For large files, prefer `get_file_context` + `extract_code` instead of raw file reads.

### VS Code / CI Hooks
- VS Code: add tasks for `ruff`, `black --check`, and `pytest -q tests/test_path_resolver.py::TestEdgeCases::test_symlink_resolution` as a fast guard.
- CI: run full pytest, coverage, ruff, black, plus `pip-audit` and `cyclonedx-bom` to emit SBOM; publish artifacts to `release_artifacts/v1.5.4/`.

## Error Handling Patterns
- Prefer returning structured errors with remediation hints; surface workspace roots and attempted paths from `PathResolver` failures.
- Treat dynamic import analysis gaps as LAZY and fall back to explicit allowlists per project.

## Evidence Hooks
- When running CI, upload: coverage XML, mutation/fuzz summaries, `performance_benchmark_log.json`, SBOM, vuln scan output, and signing verification results.
