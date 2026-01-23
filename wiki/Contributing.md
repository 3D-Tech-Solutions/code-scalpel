# Contributing

Thank you for your interest in contributing to Code Scalpel! This guide will help you get started.

## Code of Conduct

By participating in this project, you agree to:
- Be respectful and inclusive
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards other contributors

## Getting Started

### Development Setup

1. **Fork and clone:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/code-scalpel.git
   cd code-scalpel
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

5. **Verify installation:**
   ```bash
   pytest tests/ -k "smoke" -v
   ```

### Development Workflow

1. **Create a branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes**

3. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

4. **Check code quality:**
   ```bash
   # Linting
   ruff check .
   
   # Formatting
   python -m black --check .
   
   # Type checking
   python -m pyright src/
   ```

5. **Commit changes:**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

6. **Push and create PR:**
   ```bash
   git push origin feature/your-feature-name
   ```

## Project Structure

```
code-scalpel/
├── src/code_scalpel/
│   ├── mcp/                 # MCP server and tools
│   │   ├── server.py        # MCP server implementation
│   │   ├── tools/           # Tool implementations
│   │   └── helpers/         # Tool helper functions
│   ├── ast_tools/           # AST parsing and analysis
│   ├── pdg/                 # Program Dependence Graph
│   ├── security/            # Security analysis
│   │   └── analyzers/       # Taint analysis, etc.
│   ├── symbolic/            # Symbolic execution
│   ├── licensing/           # Tier management
│   └── autonomy/            # Policy enforcement
├── tests/                   # Test suite (7,100+ tests)
│   ├── core/                # Core functionality tests
│   ├── mcp/                 # MCP server tests
│   ├── tools/               # Per-tool tests
│   └── security/            # Security tests
├── examples/                # Usage examples
├── docs/                    # Documentation
└── wiki/                    # GitHub Wiki content
```

## Testing

### Running Tests

```bash
# All tests
pytest

# Specific category
pytest tests/tools/

# Specific tool
pytest tests/tools/extract_code/

# With coverage
pytest --cov=code_scalpel --cov-report=html

# Verbose output
pytest -v -s
```

### Test Organization

Code Scalpel has **7,100+ tests** organized by:

- **Unit tests** (`tests/unit/`) - Individual function tests
- **Integration tests** (`tests/integration/`) - End-to-end workflows
- **Tool tests** (`tests/tools/`) - Per-tool functionality
- **Security tests** (`tests/security/`) - Security feature tests
- **MCP tests** (`tests/mcp/`) - Protocol tests

### Writing Tests

**Example test structure:**

```python
# tests/tools/extract_code/test_extract_function.py
import pytest
from code_scalpel.mcp.helpers.extraction_helpers import extract_code

def test_extract_simple_function():
    """Test extraction of a simple Python function."""
    code = """
def hello():
    return "world"
"""
    
    result = extract_code(
        code=code,
        target_type="function",
        target_name="hello"
    )
    
    assert result.success
    assert "def hello():" in result.target_code
    assert result.target_name == "hello"

def test_extract_nonexistent_function():
    """Test error handling for missing function."""
    code = "def foo(): pass"
    
    result = extract_code(
        code=code,
        target_type="function",
        target_name="bar"
    )
    
    assert not result.success
    assert "not found" in result.error.lower()
```

### Test Requirements

All PRs must:
- ✅ Pass all existing tests
- ✅ Include tests for new features
- ✅ Maintain ≥90% code coverage
- ✅ Pass linting (Ruff)
- ✅ Pass formatting (Black)
- ✅ Pass type checking (Pyright)

## Code Quality Standards

### Linting with Ruff

```bash
# Check code
ruff check .

# Auto-fix issues
ruff check --fix .
```

**Configuration:** `pyproject.toml`

### Formatting with Black

```bash
# Check formatting
python -m black --check .

# Apply formatting
python -m black .
```

**Line length:** 88 characters (Black default)

### Type Checking with Pyright

```bash
# Check types
python -m pyright src/

# Check specific file
python -m pyright src/code_scalpel/mcp/server.py
```

**Configuration:** `pyrightconfig.json`

### Pre-commit Hooks

Automatically run checks before commit:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.0
    hooks:
      - id: black

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.2.0
    hooks:
      - id: ruff
        args: [--fix]

  - repo: local
    hooks:
      - id: pytest-quick
        name: pytest-quick
        entry: pytest tests/ -x
        language: system
        pass_filenames: false
        always_run: true
```

## Contribution Types

### Bug Fixes

1. **Open an issue first** (if not already reported)
2. **Reference the issue** in your PR: `Fixes #123`
3. **Include test** demonstrating the bug
4. **Add test** verifying the fix

**Commit message:**
```
fix: resolve Pyright type errors in extraction helpers

- Added None check for cross_file_result.target (line 282)
- Prevents "Object of type None is not subscriptable" error
- Added defensive if statement in security_analyzer.py (line 480)

Fixes #123
```

### New Features

1. **Discuss in an issue first** (prevents duplicate work)
2. **Follow existing patterns** (see similar tools)
3. **Include comprehensive tests**
4. **Update documentation** (docstrings + wiki)

**Commit message:**
```
feat: add TypeScript JSX/TSX component extraction

- Support for React functional and class components
- Detect Server Components (async components)
- Detect Server Actions ('use server' directive)
- Added tests for 10+ React component patterns

Closes #456
```

### Documentation

1. **Update docstrings** for code changes
2. **Update wiki pages** for user-facing changes
3. **Add examples** for new features
4. **Keep README.md updated**

**Commit message:**
```
docs: add cross-file security scanning examples

- Added example to Examples.md
- Updated Security.md with taint tracking flow
- Added troubleshooting section for false positives
```

### Performance Improvements

1. **Benchmark before and after**
2. **Include benchmark results** in PR
3. **Verify no functionality regressions**

**Commit message:**
```
perf: optimize AST caching for repeated extractions

- Reduced extraction time by 60% for cached files
- Benchmark: 100ms → 40ms for 5000-line file
- No functionality changes

Before: avg 98.3ms, p95 145ms
After: avg 41.2ms, p95 58ms
```

## Pull Request Guidelines

### PR Title Format

Use conventional commits:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `perf:` - Performance
- `refactor:` - Code refactoring
- `test:` - Test changes
- `chore:` - Build/tooling

**Examples:**
- `feat: add symbolic execution for Java`
- `fix: resolve path traversal in validate_paths`
- `docs: update MCP tools reference`

### PR Description Template

```markdown
## Description
Brief description of the change.

## Motivation and Context
Why is this change needed? What problem does it solve?

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update

## Testing
- [ ] All existing tests pass
- [ ] New tests added for this change
- [ ] Tested manually in [environment]

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-reviewed code
- [ ] Commented complex sections
- [ ] Updated documentation
- [ ] No new warnings from linters
- [ ] Added/updated tests
- [ ] All tests passing locally

## Related Issues
Fixes #123
Closes #456
```

### Review Process

1. **Automated checks** must pass:
   - ✅ Tests (pytest)
   - ✅ Linting (Ruff)
   - ✅ Formatting (Black)
   - ✅ Type checking (Pyright)

2. **Code review** by maintainer

3. **Address feedback**

4. **Merge** when approved

## Security Contributions

### Reporting Vulnerabilities

**DO NOT** open public issues for security vulnerabilities.

**Contact:**
- Primary: time@3dtechsolutions.us
- Secondary: aescolopio@3dtechsolutions.us

See [Security Policy](Security) for details.

### Security Testing

```bash
# Run security-focused tests
pytest tests/security/ -v

# Test policy enforcement
pytest tests/autonomy/ -v

# Verify integrity mechanisms
pytest tests/mcp/test_policy_crypto.py -v
```

## Adding New Languages

To add support for a new programming language:

1. **Add tree-sitter grammar:**
   ```bash
   pip install tree-sitter-[language]
   ```

2. **Create parser:**
   ```python
   # src/code_scalpel/ast_tools/parsers/[language]_parser.py
   from code_scalpel.ast_tools.parser import BaseParser
   
   class KotlinParser(BaseParser):
       def parse(self, code: str) -> AST:
           # Implementation
   ```

3. **Register parser:**
   ```python
   # src/code_scalpel/ast_tools/parser.py
   PARSERS = {
       "python": PythonParser,
       "kotlin": KotlinParser,  # Add here
   }
   ```

4. **Add tests:**
   ```python
   # tests/core/parsers/test_kotlin_parser.py
   def test_parse_kotlin_function():
       # Tests
   ```

## Adding New MCP Tools

To create a new MCP tool:

1. **Create helper function:**
   ```python
   # src/code_scalpel/mcp/helpers/my_helpers.py
   async def my_new_tool(param: str) -> Result:
       """Tool implementation."""
       # Implementation
       return Result(...)
   ```

2. **Register tool:**
   ```python
   # src/code_scalpel/mcp/tools/my_tools.py
   from code_scalpel.mcp.protocol import mcp
   from code_scalpel.mcp.helpers import my_helpers
   
   @mcp.tool()
   async def my_new_tool(param: str) -> Result:
       """Public MCP tool wrapper."""
       return await my_helpers.my_new_tool(param)
   ```

3. **Add tests:**
   ```python
   # tests/tools/my_new_tool/test_my_new_tool.py
   def test_my_new_tool_basic():
       result = my_new_tool(param="test")
       assert result.success
   ```

4. **Update documentation:**
   - Add to `wiki/MCP-Tools-Reference.md`
   - Add example to `wiki/Examples.md`
   - Update tool count in `README.md`

## Release Process

(For maintainers)

### Release Checklist

- [ ] All tests passing (`pytest`)
- [ ] Coverage ≥90% (`pytest --cov`)
- [ ] Linting clean (`ruff check .`)
- [ ] Formatting clean (`black --check .`)
- [ ] Type checking clean (`pyright src/`)
- [ ] CHANGELOG.md updated
- [ ] Version bumped in `pyproject.toml`
- [ ] SBOM generated
- [ ] Dependency scan (OSV/pip-audit)
- [ ] Release artifacts signed (Sigstore/Cosign)
- [ ] Evidence bundle created
- [ ] Maintainer + Security Lead + Reviewer approval

### Versioning

Code Scalpel follows [Semantic Versioning](https://semver.org/):

- **MAJOR** - Breaking changes
- **MINOR** - New features (backward compatible)
- **PATCH** - Bug fixes (backward compatible)

## Communication

- **GitHub Issues** - Bug reports, feature requests
- **GitHub Discussions** - Questions, ideas, support
- **Pull Requests** - Code contributions
- **Email** - Security issues, private matters

## Recognition

Contributors are recognized in:
- `CONTRIBUTORS.md` file
- Release notes
- GitHub contributors page

Thank you for contributing to Code Scalpel! 🎉

---

**Related Pages:**
- [Architecture](Architecture) - System design
- [Security](Security) - Security policy
- [Troubleshooting](Troubleshooting) - Common issues
