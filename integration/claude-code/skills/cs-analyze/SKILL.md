---
name: cs-analyze
description: |
  Analyze code structure: parse functions, classes, imports, and complexity metrics.
  Use to understand a file or project without reading the source code directly.
allowed-tools:
  - mcp__codescalpel__analyze_code
  - mcp__codescalpel__get_file_context
  - mcp__codescalpel__crawl_project
preamble-tier: 1
---

# /cs-analyze — Understand Code Structure

Parse and analyze the structure of a file or entire project. Extract all functions,
classes, imports, and complexity metrics without reading raw source code.

## Usage

```bash
/cs-analyze src/utils.py
/cs-analyze src/components/
/cs-analyze .
```

## What You Get

For a single file:
- All functions and their signatures
- All classes and methods
- All imports (standard library, third-party, local)
- Cyclomatic complexity (code complexity score)
- Lines of code (LOC)

For a directory or project:
- Module structure and hierarchy
- Top-level exports
- Import dependencies between modules
- Files sorted by complexity (hotspots first)

## When to Use This

✅ Understanding a codebase you're new to
✅ Finding where to add new features
✅ Identifying over-complex modules
✅ Tracing how modules depend on each other

## Next Steps

- Use `/cs-extract` to dive into specific functions
- Use `/cs-security` if you suspect vulnerabilities
- Use `/cs-map` to see the full architecture

See `CLAUDE.md` for the architecture mapping workflow.
