"""
Unit tests module.

This module re-exports tests from tests/core/ for compatibility with
standard test directory layouts. The actual unit tests are located in:
- tests/core/ - Core library unit tests
- tests/core/ast/ - AST processing tests
- tests/core/cache/ - Caching tests
- tests/core/parsers/ - Parser tests
- tests/core/pdg/ - PDG (Program Dependency Graph) tests

Usage:
    pytest tests/unit/  # Runs all unit tests via re-export
    pytest tests/core/  # Direct access to unit tests
"""
