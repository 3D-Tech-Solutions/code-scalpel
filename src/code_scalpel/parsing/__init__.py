"""
Unified parsing infrastructure with deterministic error handling.

All AST parsing flows through this module, ensuring consistent behavior
controlled by response_config.json.
"""

from .unified_parser import (
    ParsingError,
    SanitizationReport,
    parse_javascript_code,
    parse_python_code,
)

__all__ = [
    "parse_python_code",
    "parse_javascript_code",
    "ParsingError",
    "SanitizationReport",
]
