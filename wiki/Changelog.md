# Changelog

All notable changes to Code Scalpel are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-01-17

### Initial Public Release 🎉

Code Scalpel is an MCP server toolkit that enables AI assistants to perform surgical code operations through AST parsing, taint analysis, and symbolic execution.

### Features

#### Code Extraction & Modification (3 tools)

- **`extract_code`** - Surgically extract functions/classes (99% token reduction)
  - File path-based extraction (server reads file)
  - Support for Python, JavaScript/TypeScript, Java
  - Optional cross-file dependency resolution
  - Token count estimates
- **`update_symbol`** - Safe, atomic symbol replacement
  - Automatic backup creation
  - Syntax validation
  - Preserves surrounding code
- **`rename_symbol`** - Consistent renaming across references
  - Updates definition and all call sites
  - Multi-file support

#### Code Analysis (6 tools)

- **`analyze_code`** - Parse structure: functions, classes, imports, complexity
  - Multi-language support
  - Cyclomatic complexity calculation
  - Import analysis
- **`get_file_context`** - Quick overview without full read
  - Lists functions, classes, imports
  - Complexity score
  - Security warnings
- **`crawl_project`** - Comprehensive project-wide analysis
  - All files scan
  - Metrics aggregation
  - Complexity hotspot detection
- **`get_project_map`** - Multi-language project structure
  - Directory tree mapping
  - Entry point detection
  - Language distribution
- **`scan_dependencies`** - Dependency analysis and CVE checking
  - Python (pip), JavaScript (npm), Java (Maven/Gradle)
  - Known vulnerability detection
  - Version checking
- **`get_graph_neighborhood`** - Extract k-hop subgraphs
  - Prevents graph explosion on large codebases
  - Configurable hop distance
  - Mermaid diagram generation

#### Code Navigation (3 tools)

- **`get_call_graph`** - Function relationships and dependencies
  - Intra-file call tracking
  - Entry point detection
  - Circular import detection
  - Mermaid diagram visualization
- **`get_cross_file_dependencies`** - Import resolution across files
  - Direct and transitive dependencies
  - Dependency graph generation
  - Circular dependency detection
- **`get_symbol_references`** - Find all usages of symbols
  - Definition location
  - All reference sites with context
  - Line and column numbers

#### Security Analysis (4 tools)

- **`security_scan`** - Taint-based vulnerability detection
  - Detects 12+ CWE types:
    - CWE-89: SQL Injection
    - CWE-78: Command Injection
    - CWE-79: Cross-Site Scripting (XSS)
    - CWE-22: Path Traversal
    - CWE-94: Code Injection
    - CWE-90: LDAP Injection
    - CWE-611: XML External Entity (XXE)
    - CWE-918: SSRF
    - CWE-601: Open Redirect
    - CWE-502: Insecure Deserialization
    - CWE-798: Hardcoded Credentials
    - CWE-327: Weak Cryptography
  - Taint flow tracing
  - Confidence scoring
- **`cross_file_security_scan`** - Track taint across modules
  - Multi-file vulnerability detection
  - Cross-boundary taint tracking
  - Defense against split-code attacks
- **`unified_sink_detect`** - Polyglot dangerous function detection
  - Multi-language sink identification
  - CWE mapping
  - Confidence scoring
- **`type_evaporation_scan`** - TypeScript/Python type boundary issues
  - Detects type system evaporation at serialization
  - Frontend/backend correlation
  - JSON boundary analysis

#### Testing & Verification (4 tools)

- **`generate_unit_tests`** - Auto-generate tests from symbolic execution
  - pytest and unittest framework support
  - Path-based test generation
  - Edge case coverage
- **`symbolic_execute`** - Z3-based path exploration
  - All execution paths discovery
  - Constraint solving
  - Loop unrolling
- **`simulate_refactor`** - Verify changes before applying
  - Security impact analysis
  - Structural change detection
  - Behavior preservation check
- **`code_policy_check`** - Compliance and style checking
  - Basic anti-patterns (Community)
  - Security patterns (Pro)
  - Compliance standards: HIPAA, SOC2, GDPR, PCI-DSS (Enterprise)

#### Utilities (2 tools)

- **`validate_paths`** - Security boundary enforcement
  - Path traversal protection
  - Symbolic link restriction
  - Docker volume boundary enforcement
- **`verify_policy_integrity`** - Cryptographic verification
  - HMAC-SHA256 signatures
  - Tamper detection
  - Fail-closed security model

### Tier System

- **Community** (MIT License, Free)
  - All 22 tools available
  - Baseline limits (50 findings, 100 refs, 500 nodes)
  - Full AST + PDG + symbolic execution
  
- **Pro** (Commercial)
  - Unlimited findings
  - Cross-file security scanning
  - Advanced metrics
  - Custom rules
  
- **Enterprise** (Commercial)
  - All Pro features
  - Compliance reporting (HIPAA, SOC2, GDPR, PCI-DSS)
  - PDF certificates
  - Audit trails
  - SLA support

### Supported Languages

- **Python** - Full support (AST + PDG + symbolic execution + taint analysis)
- **JavaScript/TypeScript** - Full AST + call graphs + extraction + type evaporation detection
- **Java** - AST parsing + method extraction + Maven/Gradle dependency parsing
- **Go** - AST parsing via tree-sitter
- **Rust** - AST parsing via tree-sitter
- **Ruby** - AST parsing via tree-sitter
- **PHP** - AST parsing via tree-sitter

### MCP Transports

- **stdio** - VS Code, GitHub Copilot, Claude Desktop, Cursor
- **HTTP** - Remote servers, team deployments
- **SSE** - Web-based AI assistants
- **Docker** - Containerized environments

### Infrastructure

- **FastMCP** - MCP protocol implementation
- **tree-sitter** - Multi-language parsing
- **esprima** - JavaScript/TypeScript parsing
- **Z3 theorem prover** - Symbolic execution
- **Sigstore/Cosign** - Release artifact signing

### Documentation

- Complete GitHub Wiki
- 22 tool reference pages
- Security policy
- Architecture documentation
- 20+ code examples
- Troubleshooting guide
- Contributing guide

### Testing

- **7,100+ tests** across:
  - Unit tests
  - Integration tests
  - Per-tool tests
  - Security tests
  - MCP protocol tests
- **≥90% code coverage**
- Mutation testing
- Fuzz testing

### Quality Gates

- ✅ Ruff linting (100% pass)
- ✅ Black formatting (88 char line length)
- ✅ Pyright type checking (strict mode)
- ✅ SBOM generation
- ✅ Dependency vulnerability scanning (OSV/pip-audit)
- ✅ Release artifact signing

---

## [0.3.0] - 2025-12-18 (Pre-Release)

### Added

- Policy integrity verification with HMAC-SHA256
- Cryptographic manifest signing
- Sandbox execution mode
- Tier-based limits enforcement
- JWT license validation
- Cross-file dependency resolver
- React component extraction (JSX/TSX)

### Changed

- Refactored security analyzers to new directory structure
- Improved taint analysis accuracy
- Enhanced error messages

### Fixed

- Circular import detection
- Memory leaks in AST caching
- Type checking errors with external libraries

---

## [0.2.0] - 2025-11-15 (Pre-Release)

### Added

- Symbolic execution engine with Z3
- Unit test generation from execution paths
- Type evaporation scanner for TypeScript/Python
- Call graph visualization with Mermaid
- Cross-file security scanning

### Changed

- Optimized AST parsing performance (60% faster)
- Improved token efficiency in extraction

### Fixed

- False positives in SQL injection detection
- Path traversal on Windows
- Unicode handling in code extraction

---

## [0.1.0] - 2025-10-01 (Pre-Release)

### Added

- Initial MCP server implementation
- Basic extraction tools (extract_code, update_symbol, rename_symbol)
- Security scanning with taint analysis
- Python AST parsing
- JavaScript/TypeScript support via esprima
- Basic tier system

---

## Future Roadmap

### v1.1.0 (Q2 2026)

- [ ] GraphQL API support
- [ ] Enhanced Java support (PDG + taint analysis)
- [ ] Go taint analysis
- [ ] Real-time collaboration features
- [ ] VS Code extension with UI
- [ ] Performance dashboard

### v1.2.0 (Q3 2026)

- [ ] Kotlin language support
- [ ] Swift language support
- [ ] C/C++ basic support
- [ ] Enhanced compliance reporting
- [ ] Custom sink/source definitions
- [ ] Machine learning-based vulnerability detection

### v2.0.0 (Q4 2026)

- [ ] Multi-repository analysis
- [ ] Distributed scanning
- [ ] Team collaboration features
- [ ] Advanced IDE integrations
- [ ] Cloud-native deployment options
- [ ] Enhanced visualization tools

---

## Version History

| Version | Date | Key Features |
|---------|------|--------------|
| **1.0.0** | 2026-01-17 | Initial public release, 22 tools, 7 languages |
| 0.3.0 | 2025-12-18 | Policy enforcement, tier system |
| 0.2.0 | 2025-11-15 | Symbolic execution, test generation |
| 0.1.0 | 2025-10-01 | Initial pre-release |

---

## Upgrade Guide

### From 0.3.0 to 1.0.0

**Breaking Changes:**
- None (backward compatible)

**New Features:**
- All 22 tools now publicly available
- Enhanced documentation (GitHub Wiki)
- Improved error messages

**Migration:**
```bash
pip install --upgrade code-scalpel
```

**Configuration Changes:**
No configuration changes required. Existing `.env` files compatible.

---

## Release Notes Archive

Detailed release notes and changelogs are available at:
- **GitHub Releases:** https://github.com/3D-Tech-Solutions/code-scalpel/releases
- **Release Artifacts:** `release_artifacts/vX.Y.Z/`

---

**For support:** time@3dtechsolutions.us  
**Security issues:** See [Security Policy](Security)

