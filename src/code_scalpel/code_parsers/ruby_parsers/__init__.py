#!/usr/bin/env python3
"""
Ruby Parsers Module - Unified Interface and Registry.

[20260304_FEATURE] Full implementation of RubyParserRegistry.
Provides factory access to all 7 Ruby static-analysis tool parsers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .ruby_parsers_RuboCop import RuboCopParser
from .ruby_parsers_brakeman import BrakemanParser
from .ruby_parsers_Reek import ReekParser
from .ruby_parsers_bundler import BundlerParser
from .ruby_parsers_fasterer import FastererParser
from .ruby_parsers_simplecov import SimpleCovParser
from .ruby_parsers_ast import RubyASTParser

__all__ = [
    "RubyParserRegistry",
    "RuboCopParser",
    "BrakemanParser",
    "ReekParser",
    "BundlerParser",
    "FastererParser",
    "SimpleCovParser",
    "RubyASTParser",
]

# [20260304_FEATURE] Tool name → parser class mapping
_PARSER_MAP: Dict[str, Type] = {
    "rubocop": RuboCopParser,
    "brakeman": BrakemanParser,
    "reek": ReekParser,
    "bundler-audit": BundlerParser,
    "fasterer": FastererParser,
    "simplecov": SimpleCovParser,
    "ast": RubyASTParser,
}


class RubyParserRegistry:
    """
    Registry for Ruby parser implementations with factory pattern.

    [20260304_FEATURE] Provides unified access to all Ruby analysis tools.

    Supported tools:
        - rubocop      : Style/lint violations
        - brakeman     : Security vulnerability scanning
        - reek         : Code smell detection
        - bundler-audit: Dependency vulnerability scanning
        - fasterer     : Performance anti-pattern detection
        - simplecov    : Test coverage analysis
        - ast          : AST-based structure extraction
    """

    def __init__(self) -> None:
        """Initialize the Ruby parser registry."""
        self._parsers: Dict[str, object] = {}

    def get_parser(self, tool_name: str) -> object:
        """
        Get parser instance by tool name (cached).

        [20260304_FEATURE] Raises ValueError for unknown tool names.
        """
        if tool_name not in _PARSER_MAP:
            raise ValueError(
                f"Unknown Ruby parser: '{tool_name}'. "
                f"Available: {sorted(_PARSER_MAP.keys())}"
            )
        if tool_name not in self._parsers:
            self._parsers[tool_name] = _PARSER_MAP[tool_name]()
        return self._parsers[tool_name]

    def available_tools(self) -> List[str]:
        """Return list of all registered tool names."""
        return sorted(_PARSER_MAP.keys())

    def analyze(self, path: Path, tools: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run specified parsers on the given path.

        [20260304_FEATURE] Runs each tool and collects JSON reports.
        Returns dict mapping tool_name → JSON report string (or error message).

        If tools is None, runs all tools that have a CLI available.
        """
        import shutil

        tool_names = tools if tools is not None else self.available_tools()
        results: Dict[str, Any] = {}
        p = Path(path) if not isinstance(path, Path) else path

        for tool_name in tool_names:
            try:
                parser = self.get_parser(tool_name)
                if tool_name == "rubocop":
                    issues = parser.execute_rubocop([p])
                    results[tool_name] = parser.generate_report(issues)
                elif tool_name == "brakeman":
                    vulns = parser.execute_brakeman([p])
                    results[tool_name] = parser.generate_security_report(vulns)
                elif tool_name == "reek":
                    smells = parser.execute_reek([p])
                    results[tool_name] = parser.generate_report(smells)
                elif tool_name == "bundler-audit":
                    gems = parser.parse_gemfile(p / "Gemfile") if (p / "Gemfile").exists() else []
                    results[tool_name] = parser.generate_dependency_report(gems)
                elif tool_name == "fasterer":
                    issues = parser.execute_fasterer([p])
                    results[tool_name] = parser.generate_report(issues)
                elif tool_name == "simplecov":
                    rs = p / ".resultset.json"
                    if rs.exists():
                        metrics = parser.parse_resultset_json(rs)
                        results[tool_name] = parser.generate_report(metrics)
                    else:
                        results[tool_name] = '{"error": ".resultset.json not found"}'
                elif tool_name == "ast":
                    if p.is_file():
                        ir_module = parser.parse_file(p)
                        results[tool_name] = parser.generate_report(ir_module, str(p))
                    else:
                        results[tool_name] = '{"error": "path is not a file"}'
            except Exception as exc:  # noqa: BLE001
                results[tool_name] = f'{{"error": "{exc}"}}'

        return results
