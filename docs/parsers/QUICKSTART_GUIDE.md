# Polyglot Parsers - Quick Reference for Developers

**Version:** Phase 1 Complete  
**Last Updated:** December 21, 2025  

---

## 🚀 Quick Start

### Using a Language Module

```python
# Example: Using Java Parsers
from code_scalpel.code_parser.java_parsers import JavaParserRegistry

registry = JavaParserRegistry()
result = registry.analyze(
    path=Path("/path/to/java/project"),
    tools=["checkstyle", "sonarqube", "pmd"]
)

# Get metrics
metrics = registry.get_aggregated_metrics()

# Generate report
report = registry.generate_unified_report(format="json")
```

---

## 📋 Module Reference

### Language Modules

| Language | Module | Tools | Status |
|----------|--------|-------|--------|
| **Java** | `java_parsers` | CheckStyle, SonarQube, PMD, SpotBugs | Phase 1 ✅ |
| **Kotlin** | `kotlin_parsers` | Detekt, KLint, Lint | Phase 1 ✅ |
| **JavaScript** | `javascript_parsers` | ESLint, JSHint, SonarQube | Phase 1 ✅ |
| **TypeScript** | `typescript_parsers` | ESLint, TSLint, Prettier | Phase 1 ✅ |
| **Ruby** | `ruby_parsers` | RuboCop, Reek, Brakeman | Phase 1 ✅ |
| **PHP** | `php_parsers` | PHPStan, Psalm, PHPMD | Phase 1 ✅ |
| **Swift** | `swift_parsers` | SwiftLint, Tailor, SourceKitten | Phase 1 ✅ |

---

## 📚 Documentation

### Module Documentation

Each module has comprehensive documentation:

```
docs/parsers/
├── JAVA_PARSERS_README.md              # 850+ lines
├── KOTLIN_PARSERS_README.md            # 850+ lines
├── JAVASCRIPT_PARSERS_README.md        # 850+ lines
├── TYPESCRIPT_PARSERS_README.md        # 850+ lines
├── RUBY_PARSERS_README.md              # 850+ lines
├── PHP_PARSERS_README.md               # 850+ lines
└── SWIFT_PARSERS_README.md             # 850+ lines
```

### Completion Documents

Each module has a completion summary:

```
docs/parsers/
├── JAVA_PARSERS_COMPLETION.md          # Methods, data classes
├── KOTLIN_PARSERS_COMPLETION.md        # Implementation details
├── JAVASCRIPT_PARSERS_COMPLETION.md    # Architecture summary
├── TYPESCRIPT_PARSERS_COMPLETION.md    # Phase 2 roadmap
├── RUBY_PARSERS_COMPLETION.md          # Quality metrics
├── PHP_PARSERS_COMPLETION.md           # Testing strategy
└── SWIFT_PARSERS_COMPLETION.md         # Integration points
```

### Summary Documentation

```
- POLYGLOT_PARSERS_SUMMARY.md      # 450+ lines, complete overview
- POLYGLOT_PARSERS_PHASE_1_COMPLETE.md  # 500+ lines, status report
- POLYGLOT_PARSERS_PHASE_1_MANIFEST.md  # File inventory
```

---

## 🏗️ Architecture

### Registry Pattern (All Modules)

```python
class LanguageParserRegistry:
    """Factory for language-specific parsers."""
    
    # Get a specific parser
    parser = registry.get_parser("eslint")
    
    # Analyze with multiple tools
    result = registry.analyze(path, tools=["eslint", "jshint"])
    
    # Get aggregated metrics
    metrics = registry.get_aggregated_metrics()
    
    # Generate report
    report = registry.generate_unified_report(format="json")
```

### Data Classes

All violations extend a common base:

```python
@dataclass
class Violation:
    rule_id: str
    message: str
    severity: Severity      # Notice, Warning, Error
    file_path: str
    line_number: int
    column: int
    correctable: bool

@dataclass
class AnalysisResult:
    violations: List[Violation]
    metrics: Dict[str, Any]
    issues: List[Issue]
    summary: SummaryMetrics
    timestamp: datetime
```

---

## 🔧 Configuration Files

### Standard Configuration Locations

```
Java:      .checkstyle.xml, pom.xml
Kotlin:    detekt.yml
JavaScript: .eslintrc.json, package.json
TypeScript: tsconfig.json, .eslintrc.json
Ruby:      .rubocop.yml, Gemfile
PHP:       phpstan.neon, psalm.xml
Swift:     .swiftlint.yml, .tailor.yml
```

### Example: JavaScript Config

```json
{
    "env": { "browser": true, "es2021": true },
    "extends": "eslint:recommended",
    "rules": {
        "indent": ["error", 2],
        "quotes": ["error", "single"],
        "semi": ["error", "always"]
    }
}
```

---

## 📖 Documentation Structure

### README (850+ lines per module)

1. **Overview** - Module capabilities
2. **Architecture** - Directory structure, component relationships
3. **Supported Tools** - Detailed tool documentation
4. **Implementation Status** - Phase 1/2 checklists
5. **API Reference** - All method signatures
6. **Phase 2 Roadmap** - Sprint breakdown
7. **Integration Guide** - Usage examples
8. **Configuration** - Tool config examples
9. **Performance** - Benchmarks and optimization
10. **Troubleshooting** - Common issues

### Completion Document (400+ lines)

1. **Summary** - Phase 1 deliverables
2. **Implemented Components** - Classes and methods
3. **Data Classes** - Type definitions
4. **Phase 2 Deliverables** - Roadmap
5. **Testing Strategy** - Coverage goals
6. **Quality Metrics** - Standards

---

## ⚙️ Implementation Status

### Phase 1: Complete ✅
- [x] Module structure
- [x] Data classes
- [x] Method signatures
- [x] Docstrings
- [x] Registry pattern
- [x] Configuration examples
- [x] Integration guide
- [x] Documentation

### Phase 2: Planned 🔄
- [ ] Tool execution
- [ ] Output parsing
- [ ] Configuration loading
- [ ] Result aggregation
- [ ] Report generation
- [ ] Unit tests (>90%)
- [ ] Integration tests (>80%)

### Phase 3: Future 🚀
- [ ] ML-based categorization
- [ ] Cross-language analysis
- [ ] IDE integration
- [ ] SaaS dashboard

---

## 🎯 Phase 2 Timeline

### Sprint 1: Foundation (Weeks 1-3)
- Java execution wrappers
- Basic output parsing
- Configuration loading

### Sprint 2: JVM Languages (Weeks 4-6)
- Kotlin Detekt & KLint
- JavaScript ESLint & JSHint
- Unit tests (>90%)

### Sprint 3: Dynamically Typed (Weeks 7-10)
- TypeScript ESLint & TSLint
- Ruby RuboCop & Reek
- Security scanning

### Sprint 4: Modern Languages (Weeks 11-14)
- PHP PHPStan & Psalm
- Swift SwiftLint & Tailor
- Registry factory

### Sprint 5: Integration (Weeks 15-19)
- End-to-end tests
- Performance tests
- Report generation
- Documentation

---

## 📊 Code Statistics

### Overall

| Metric | Value |
|--------|-------|
| Parser Classes | 25+ |
| Data Classes | 80+ |
| Methods | 240+ |
| Lines of Code | 7,650+ |
| Documentation | 10,150+ lines |
| Examples | 125+ |

### Per Module

| Module | Classes | Methods | Data Classes |
|--------|---------|---------|--------------|
| Java | 5 | 34 | 12 |
| Kotlin | 4 | 32 | 10 |
| JavaScript | 4 | 35 | 11 |
| TypeScript | 4 | 37 | 12 |
| Ruby | 4 | 39 | 13 |
| PHP | 4 | 37 | 12 |
| Swift | 5 | 30 | 10 |

---

## 🔍 Finding Things

### By Use Case

**I want to...**

- **Analyze Java code** → See `java_parsers/README.md`
- **Analyze JavaScript** → See `javascript_parsers/README.md`
- **Understand architecture** → See `POLYGLOT_PARSERS_SUMMARY.md`
- **Implement Phase 2** → See each module's completion document
- **Configure a tool** → See configuration examples in README
- **See an example** → Check integration guide in README
- **Find a method** → Check API reference in README
- **Understand data classes** → Check completion document

---

## 🏃 Getting Started

### Step 1: Choose Your Language

Find your language in the table above and note the module name.

### Step 2: Read the README

Go to `docs/parsers/{LANGUAGE}_PARSERS_README.md` and read the first 200 lines.

### Step 3: Copy an Example

Find an example that matches your use case in the integration guide.

### Step 4: Adapt to Your Project

Modify the example to work with your specific project path and tools.

---

## 🚨 Common Issues

### "Module not found"
Check that the module is installed: `pip install code-scalpel>=3.0.0`

### "Tool not found"
Install the tool separately (Phase 2 will handle this):
```bash
# Java
brew install checkstyle

# JavaScript
npm install -g eslint

# Ruby
gem install rubocop
```

### "Parser not implemented"
Phase 2 TODO - All methods raise `NotImplementedError` in Phase 1.

### "Configuration file not found"
Ensure `.eslintrc.json`, `.swiftlint.yml`, etc. are in project root.

---

## 📝 Phase 2 TODO Items

All Phase 2 work is marked with `[20251221_TODO]`:

```python
# Example
def execute_eslint(self, paths: List[Path]):
    """Execute ESLint analysis - Phase 2 TODO [20251221_TODO]"""
    raise NotImplementedError("Phase 2: ESLint execution")
```

Search for `[20251221_TODO]` to find all planned work.

---

## 🤝 Contributing

See [CONTRIBUTING_TO_MCP_REGISTRY.md](../../CONTRIBUTING_TO_MCP_REGISTRY.md)

### To Implement Phase 2:
1. Choose a module
2. Find a `[20251221_TODO]` item
3. Implement the method
4. Add unit tests (>90% coverage)
5. Update documentation
6. Submit pull request

---

## 📞 Support

### Documentation
- Module READMEs: 850+ lines each
- Completion documents: 400+ lines each
- Summary documentation: 1,350+ lines
- 125+ code examples

### GitHub
- Issues: Bug reports, feature requests
- Discussions: Questions, community support

### Contact
- Project: [Code Scalpel](https://github.com/3D-Tech-Solutions/code-scalpel)
- PyPI: [code-scalpel](https://pypi.org/project/code-scalpel/)

---

## 📚 Quick Links

| Resource | Link |
|----------|------|
| Module Overview | [POLYGLOT_PARSERS_SUMMARY.md](docs/parsers/POLYGLOT_PARSERS_SUMMARY.md) |
| Java Docs | [JAVA_PARSERS_README.md](docs/parsers/JAVA_PARSERS_README.md) |
| JavaScript Docs | [JAVASCRIPT_PARSERS_README.md](docs/parsers/JAVASCRIPT_PARSERS_README.md) |
| Ruby Docs | [RUBY_PARSERS_README.md](docs/parsers/RUBY_PARSERS_README.md) |
| Swift Docs | [SWIFT_PARSERS_README.md](docs/parsers/SWIFT_PARSERS_README.md) |
| Main Docs | [docs/INDEX.md](docs/INDEX.md) |
| Contributing | [CONTRIBUTING_TO_MCP_REGISTRY.md](CONTRIBUTING_TO_MCP_REGISTRY.md) |

---

**Code Scalpel v3.0.0 - Polyglot Static Analysis for AI Agents** 🚀

*Quick Reference v1.0 - December 21, 2025*
