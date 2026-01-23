# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-17

### Initial Public Release

Code Scalpel is an MCP server toolkit that enables AI assistants to perform surgical code operations through AST parsing, taint analysis, and symbolic execution.

### Features

#### Code Analysis (6 tools)
- **`analyze_code`** - Parse code structure: functions, classes, imports, complexity metrics
- **`get_file_context`** - Quick file overview without reading full content
- **`crawl_project`** - Comprehensive project-wide analysis
- **`get_project_map`** - Multi-language project structure mapping
- **`scan_dependencies`** - Dependency analysis and version checking
- **`get_graph_neighborhood`** - Extract k-hop subgraphs around code symbols

#### Code Navigation (3 tools)
- **`get_call_graph`** - Function call relationships and dependencies
- **`get_cross_file_dependencies`** - Import resolution across files
- **`get_symbol_references`** - Find all usages of functions, classes, variables

#### Security Analysis (4 tools)
- **`security_scan`** - Taint-based vulnerability detection (SQL injection, XSS, etc.)
- **`cross_file_security_scan`** - Track taint flow across module boundaries
- **`unified_sink_detect`** - Polyglot dangerous function detection with CWE mapping
- **`type_evaporation_scan`** - Detect TypeScript/Python type boundary vulnerabilities

#### Code Extraction & Modification (3 tools)
- **`extract_code`** - Surgically extract functions/classes (99% token reduction)
- **`update_symbol`** - Safe, atomic symbol replacement with backup
- **`rename_symbol`** - Consistent renaming across definition and references

#### Testing & Verification (4 tools)
- **`generate_unit_tests`** - Symbolic execution generates tests for all paths
- **`symbolic_execute`** - Z3-based path exploration and constraint solving
- **`simulate_refactor`** - Verify code changes are safe before applying
- **`code_policy_check`** - Automated compliance and style checking

#### Utilities (2 tools)
- **`validate_paths`** - Security boundary enforcement for file access
- **`verify_policy_integrity`** - Cryptographic policy file verification

### Tier System

- **Community** - Free access to all 22 tools with baseline capabilities
- **Pro** - Unlimited findings, cross-file analysis, advanced features
- **Enterprise** - Compliance reporting, custom policies, audit trails

### Supported Languages

- Python (full AST + PDG + symbolic execution)
- JavaScript/TypeScript (AST + basic analysis)
- Java (AST parsing)
- Go, Rust, Ruby, PHP (AST parsing via tree-sitter)

### MCP Transports

- **stdio** - VS Code, GitHub Copilot, Claude Desktop
- **HTTP/SSE** - Remote servers, team deployments
- **Docker** - Isolated environments, CI/CD pipelines
