# Contributing to Code Scalpel

Thank you for your interest in contributing to Code Scalpel! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.10+
- Git

### Clone and Install

```bash
git clone https://github.com/3D-Tech-Solutions/code-scalpel.git
cd code-scalpel

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev]"
```

### Install Pre-commit Hooks

```bash
pre-commit install
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/mcp/test_mcp.py -v

# Run with coverage
pytest tests/ --cov=src/code_scalpel --cov-report=html
```

## Code Quality

### Linting

```bash
# Check for issues
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/
```

### Formatting

```bash
# Check formatting
black --check src/ tests/

# Apply formatting
black src/ tests/
```

### Type Checking

```bash
pyright src/
```

## Submitting Changes

### Pull Request Process

1. **Fork** the repository
2. **Create a branch** for your feature or fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** following our coding standards
4. **Run tests** to ensure nothing is broken:
   ```bash
   pytest tests/ -v
   ```
5. **Run linters** and fix any issues:
   ```bash
   ruff check src/ tests/
   black src/ tests/
   ```
6. **Commit** with a clear message:
   ```bash
   git commit -m "feat: add support for X"
   ```
7. **Push** and create a Pull Request

### Commit Message Format

We follow conventional commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test additions or fixes
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

### Pull Request Guidelines

- Keep PRs focused on a single change
- Include tests for new functionality
- Update documentation as needed
- Ensure CI passes before requesting review

## Code Standards

- Use type hints for all function signatures
- Include docstrings for public functions and classes
- Follow PEP 8 style guidelines (enforced by ruff/black)
- Write tests for new functionality

## Reporting Issues

When reporting bugs, please include:

- Python version (`python --version`)
- Code Scalpel version (`pip show code-scalpel`)
- Minimal reproduction steps
- Expected vs actual behavior
- Error messages/tracebacks

## Questions?

- Open a [GitHub Discussion](https://github.com/3D-Tech-Solutions/code-scalpel/discussions)
- Check existing [issues](https://github.com/3D-Tech-Solutions/code-scalpel/issues)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
