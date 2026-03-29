---
name: cs-security
description: |
  Full security audit: detect local vulnerabilities, cross-file taint flows,
  CVEs in dependencies, and polyglot sink patterns. Complete security scan pipeline.
allowed-tools:
  - mcp__codescalpel__security_scan
  - mcp__codescalpel__cross_file_security_scan
  - mcp__codescalpel__unified_sink_detect
  - mcp__codescalpel__scan_dependencies
preamble-tier: 1
---

# /cs-security — Full Security Audit

Run a complete security analysis: find SQL injection, XSS, command injection, path
traversal, tainted data flows, and vulnerable dependencies.

## Usage

```bash
/cs-security
/cs-security src/api/
```

## The Full Pipeline

1. **Local analysis** — Detect SQL injection, XSS, command injection, path traversal within files
   - Taint analysis traces user input → dangerous functions
   - Confidence threshold: 70% minimum

2. **Cross-file analysis** — Find vulnerabilities that span module boundaries
   - Taint flows across function calls
   - Identifies where untrusted data enters your system

3. **Dependency scan** — Check for known CVEs in your libraries
   - Uses OSV (Open Source Vulnerabilities) database
   - Shows version constraints to fix

4. **Polyglot detection** — Find sinks across Python, JavaScript, TypeScript, Java
   - Frontend-backend vulnerability patterns
   - TypeScript type-safety issues at system boundaries

## Vulnerability Types Detected

- **SQL Injection** — Raw SQL with user input
- **XSS** — Unescaped output to HTML/DOM
- **Command Injection** — User input to shell commands
- **Path Traversal** — User input to file paths without validation
- **Tainted Data Flows** — Untrusted data reaching sensitive functions
- **Type Erosion** — JavaScript/TypeScript type safety breakdowns

## Interpreting Results

- **HIGH confidence** — Almost certainly a real vulnerability, fix immediately
- **MEDIUM confidence** — Likely a vulnerability, investigate and validate
- **LOW confidence** — Possible false positive, review code context

## What Happens Next

1. Read the vulnerability report
2. Use `/cs-extract` to see the vulnerable code
3. Use `/cs-refactor` to fix it safely
4. Re-run `/cs-security` to confirm the fix

## Pro Tip

Run this on your whole project regularly:
```bash
/cs-security .
```

See `CLAUDE.md` for the complete security workflow.
