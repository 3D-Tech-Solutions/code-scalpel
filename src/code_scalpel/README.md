# Code Scalpel - Source Code

**Version:** 3.0.5 "Ninja Consolidation"  
**Release Date:** December 23, 2025

<!-- TODO [COMMUNITY]: Maintain documentation alignment with latest release (current)
     TODO [PRO]: Add architecture diagrams for each module
     TODO [ENTERPRISE]: Add automated API documentation generation -->

## Overview

This is the main source directory for Code Scalpel, an MCP server toolkit for AI-driven surgical code analysis and modification.

<!-- TODO [COMMUNITY]: Core module status and dependencies (current)
     TODO [PRO]: Performance benchmarks for each module
     TODO [ENTERPRISE]: Distributed deployment topology diagrams -->

## Module Organization

<!-- TODO [COMMUNITY]: Organization by capability tier (current)
     TODO [PRO]: Cross-module dependency analysis and import tracking
     TODO [ENTERPRISE]: Microservices decomposition for independent deployment -->

### Core Analysis
- **ast_tools/** - AST parsing and analysis
- **pdg_tools/** - Program Dependence Graph construction and analysis
- **symbolic_execution_tools/** - Symbolic execution engine and security analysis (500K+ LOC)

### Language Support
- **polyglot/** - Modern multi-language parsing (tree-sitter based)
- **code_parser/** - Legacy language-specific parsers
- **ir/** - Unified Intermediate Representation for cross-language analysis
- **parsers/** - Lightweight parser factory

### Security & Governance
- **security/** - Security analysis tools and vulnerability detection
- **policy_engine/** - Policy enforcement and semantic analysis
- **policy/** - Change budget and modification limits
- **governance/** - Compliance reporting and audit logging

### Code Modification
- **generators/** - Test generation and refactoring simulation
- **surgical_extractor.py** - Precise code extraction
- **surgical_patcher.py** - Safe code modification
- **code_analyzer.py** - Single-file code analysis
- **project_crawler.py** - Project-wide analysis

### Infrastructure
- **cache/** - Unified caching layer (v3.0.5 consolidation)
- **utilities/** - Path resolution and shared utilities
- **config/** - Configuration management
- **graph_engine/** - Dependency graph construction

### Integrations
- **mcp/** - MCP server with 22 tools
- **integrations/** - REST API, AutoGen, CrewAI integrations
- **agents/** - AI agent implementations
- **autonomy/** - Error-to-diff autonomous fixing engine

## Quick Start

```python
# Import core functionality
from code_scalpel import (
    CodeAnalyzer,
    AnalysisResult,
    extract_function,
    update_function_in_file,
)

# Analyze code
analyzer = CodeAnalyzer()
result = analyzer.analyze("def foo(): return 1")
print(result.metrics.num_functions)

# Extract function
from code_scalpel import extract_function
func_code = extract_function(file_path, "function_name")

# Start MCP server
from code_scalpel import run_server
run_server(port=8080)
```

<!-- TODO [COMMUNITY]: Basic usage examples (current)
     TODO [PRO]: Advanced configuration and profiles
     TODO [ENTERPRISE]: Custom integration patterns and deployment scenarios -->

## Module Statistics (v3.0.5)

| Module | LOC | Status | Coverage |
|--------|-----|--------|----------|
| symbolic_execution_tools | 500K+ | Stable | 95%+ |
| ir | 180K+ | Stable | 95%+ |
| code_parser | 150K+ | Legacy | 90%+ |
| polyglot | 80K+ | Stable | 90%+ |
| pdg_tools | 120K+ | Stable | 100% |
| mcp | 4K+ | Stable | 100% |
| **Total** | **~1.2M LOC** | | **94.86%** |

<!-- TODO [COMMUNITY]: Baseline metrics and status tracking (current)
     TODO [PRO]: Performance regression detection across releases
     TODO [ENTERPRISE]: Automated metric collection and trending -->

## Key Features (v3.0.5)

✅ **Cache Consolidation** - Unified cache implementation (eliminated 277 LOC redundancy)  
✅ **22 MCP Tools** - Full toolkit for AI agents  
✅ **Multi-Language** - Python, Java, JavaScript, TypeScript support  
✅ **Security Analysis** - OWASP Top 10 vulnerability detection  
✅ **Symbolic Execution** - Path exploration with Z3 solver  
✅ **Cross-File Analysis** - Dependency tracking across modules  
✅ **Test Generation** - Automated unit test creation  
✅ **Autonomy Engine** - Error-to-diff automatic fixing  

## Documentation

- **Architecture:** `docs/architecture/`
- **Guides:** `docs/guides/`
- **API Reference:** `docs/modules/`
- **Release Notes:** `docs/release_notes/RELEASE_NOTES_v3.0.5.md`
- **Organizational Analysis:** `ORGANIZATIONAL_ANALYSIS.md`

## Testing

```bash
# Run all tests
pytest tests/

# Run specific module tests
pytest tests/test_cache/
pytest tests/test_symbolic_execution/

# Coverage report
pytest --cov=src/code_scalpel --cov-report=html
```

<!-- TODO [COMMUNITY]: Standard test execution (current)
     TODO [PRO]: Performance testing and benchmarks
     TODO [ENTERPRISE]: Distributed testing across agents -->

## Development

```bash
# Install in development mode
pip install -e .

# Format code
black src/code_scalpel
ruff check src/code_scalpel --fix

# Type checking
mypy src/code_scalpel
```

<!-- TODO [COMMUNITY]: Standard development workflow (current)
     TODO [PRO]: IDE integration setup and debugging
     TODO [ENTERPRISE]: Custom development environment provisioning -->

## Module READMEs

Every subdirectory contains a README.md with detailed module documentation:
- Purpose and overview
- Key components and APIs
- Usage examples
- Integration points
- Version status

<!-- TODO [COMMUNITY]: Documentation completeness checklist (current)
     TODO [PRO]: Auto-generated API docs from docstrings
     TODO [ENTERPRISE]: Multi-language documentation support -->

## v3.0.5 Changes

**Cache Consolidation:**
- Merged `cache/analysis_cache.py` + `utilities/cache.py` → `cache/unified_cache.py`
- Eliminated 277 lines of redundancy
- Preserved all features from both implementations
- Backward compatible imports

**Documentation:**
- Fixed MCP tool count (19 → 20)
- Created READMEs for all 33 directories
- Archived old cache implementations with explanation

<!-- TODO [COMMUNITY]: Release notes and change tracking (current)
     TODO [PRO]: Migration guides and breaking changes documentation
     TODO [ENTERPRISE]: Upgrade automation and compatibility matrices -->

## Contact

- **Author:** Timmothy Escolopio
- **Email:** time@3dtechsolutions.us
- **Organization:** 3D Tech Solutions LLC
- **License:** MIT
- **Repository:** [code-scalpel](https://github.com/3D-Tech-Solutions/code-scalpel)
