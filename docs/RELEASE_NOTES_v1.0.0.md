# Code Scalpel v1.0.0 Release Notes

**Release Date:** January 18, 2026

## Overview

Code Scalpel v1.0.0 is the public release of the AI-powered code analysis and refactoring toolkit. This release provides stable, production-ready code analysis, extraction, and modification tools with comprehensive testing and security hardening.

## Key Features

### Core Analysis Tools
- **`analyze_code`** - Static code structure analysis (Python, JavaScript/TypeScript, Java)
- **`extract_code`** - Surgical extraction of functions, classes, and methods with dependency resolution
- **`get_project_map`** - High-level project structure analysis with complexity hotspots
- **`get_symbol_references`** - Find all usages of symbols across the codebase
- **`security_scan`** - Taint-flow analysis for detecting vulnerabilities (SQL injection, XSS, code injection, etc.)

### Code Modification Tools
- **`rename_symbol`** - Safe refactoring with atomic updates and rollback support
- **`update_symbol`** - Surgical replacement of functions/classes with backup management
- **`simulate_refactor`** - Verify code changes are safe before applying them

### Advanced Analysis
- **`get_graph_neighborhood`** - Extract k-hop subgraphs around code elements
- **`get_cross_file_dependencies`** - Analyze module and service dependencies
- **`symbolic_execute`** - Explore all execution paths in functions
- **`generate_unit_tests`** - Auto-generate tests from symbolic execution paths

### Security & Compliance
- **`verify_policy_integrity`** - Validate policy files haven't been tampered with
- **`code_policy_check`** - Enforce coding standards and compliance rules
- **`unified_sink_detect`** - Detect dangerous functions across multiple languages
- **`type_evaporation_scan`** - Identify type system vulnerabilities in TypeScript/Python boundaries

### Project Management
- **`scan_dependencies`** - Identify and audit project dependencies with vulnerability checking
- **`crawl_project`** - Analyze entire project for structure and metrics

## Technical Specifications

### Supported Languages
- Python 3.8+
- JavaScript/TypeScript (ES6+)
- Java (8+)

### Platform Support
- Linux (x86_64, ARM64)
- macOS (Intel, Apple Silicon)
- Windows (WSL2 compatible)

### Build & Quality Metrics
- **Test Coverage:** 97.93% (3,018 tests passing)
- **Code Scanning:** Bandit SAST (10 medium severity findings, 0 high)
- **Dependencies:** All current (pip-audit clean, no CVEs in v1.0.0 release)
- **Build Artifacts:** Wheel + sdist validated via twine

## Installation

### From PyPI (Recommended)
```bash
pip install code-scalpel>=1.0.0
```

### From Source
```bash
git clone https://github.com/tescolopio/code_scalpel_community.git
cd code_scalpel_community
pip install -e .
```

## Getting Started

### Basic Usage
```python
from code_scalpel import analyze_code, extract_code

# Analyze a Python file
analysis = analyze_code("path/to/file.py")
print(f"Found {len(analysis.functions)} functions")

# Extract a function
code = extract_code(
    file_path="path/to/file.py",
    target_type="function",
    target_name="my_function"
)
```

### MCP Server Usage
Code Scalpel integrates with the Model Context Protocol (MCP):

```bash
python -m code_scalpel.mcp.server --transport stdio --root /path/to/project
```

## Tier Structure

This v1.0.0 release includes **Community tier** features. Pro and Enterprise tiers with advanced capabilities are available under separate licensing.

### Community Tier (v1.0.0)
- ✅ All core analysis tools
- ✅ Basic security scanning
- ✅ Code extraction and modification
- ✅ Policy checking (basic)
- ✅ 50 dependency limit in scan_dependencies
- ✅ 1,000 file limit in crawl_project

## Known Limitations

1. **Enterprise Test Failures** - Some edge-case envelope validation tests fail in enterprise tier (does not affect community tier functionality)
2. **JavaScript/TypeScript** - Some advanced TypeScript patterns (super, spread operators) not fully supported in normalization
3. **Java Analysis** - Limited to source-level analysis; bytecode analysis planned for future releases
4. **Performance** - Large projects (>10K files) may require memory tuning; see docs/guides/ for optimization tips

## Breaking Changes from Pre-release

- **Removed** deprecated modules: `code_scalpel.polyglot`, `code_scalpel.project_crawler`, `code_scalpel.surgical_extractor`
- **Use Instead:** `code_scalpel.analysis`, `code_scalpel.code_parsers`, `code_scalpel.surgery`
- **Response Envelope** - Responses now use minimal profile by default (reduced token usage)

## Bug Fixes & Improvements

### Security
- Fixed potential URL scheme injection in dependency scanning
- Improved temp directory handling (now uses system temp with isolation)
- Enhanced cryptographic signature verification for policy files

### Performance
- Optimized AST traversal for large codebases
- Reduced memory footprint in project crawling
- Improved parallelization in multi-file operations

### Reliability
- Fixed race conditions in concurrent tool execution
- Enhanced error handling and reporting
- Improved timeout management for long-running operations

## Documentation

- [Getting Started Guide](docs/getting_started/README.md)
- [API Reference](docs/guides/API_REFERENCE.md)
- [Security Scanning Guide](docs/guides/SECURITY_SCANNING.md)
- [Best Practices](docs/guides/BEST_PRACTICES.md)

## Support & Feedback

- **Issues:** Report bugs via [GitHub Issues](https://github.com/tescolopio/code_scalpel_community/issues)
- **Discussions:** Join community discussions on [GitHub Discussions](https://github.com/tescolopio/code_scalpel_community/discussions)
- **Security:** Report security issues to [SECURITY.md](SECURITY.md)

## License

Code Scalpel v1.0.0 is released under the [License](LICENSE) terms. See [LICENSE](LICENSE) for details.

## Acknowledgments

- Community contributors and testers
- Open source projects: tree-sitter, z3-solver, networkx, Pydantic, MCP

---

**Version:** 1.0.0  
**Release Date:** January 18, 2026  
**Status:** Production Ready
