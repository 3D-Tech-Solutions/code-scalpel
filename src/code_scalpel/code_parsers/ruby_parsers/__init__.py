#!/usr/bin/env python3
"""
Ruby Parsers Module - Unified Interface and Registry


This module provides a comprehensive interface for Ruby code analysis.
"""

__all__ = [
    "RubyParserRegistry",
    "RuboCopParser",
    "ReekParser",
]


class RubyParserRegistry:
    """Registry for Ruby parser implementations with factory pattern."""

    def __init__(self):
        """Initialize the Ruby parser registry."""
        raise NotImplementedError("Phase 2: Registry initialization")

    def get_parser(self, tool_name: str):
        """Get parser instance by tool name."""
        raise NotImplementedError("Phase 2: Parser factory method")

    def analyze(self, path, tools=None):
        """Run all specified parsers on given path."""
        raise NotImplementedError("Phase 2: Aggregated analysis")
