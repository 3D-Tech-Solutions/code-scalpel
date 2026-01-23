#!/usr/bin/env python3
"""
Roslyn Analyzers C# Parser - .NET Compiler Platform analysis integration.

#
# Reference: https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/overview
# Command: dotnet build /p:RunAnalyzersDuringBuild=true
"""

# from . import base_parser


class RoslynAnalyzersParser:
    """Parser for .NET Roslyn Analyzers output."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.language = "csharp"

    def parse(self) -> None:
        """Parse Roslyn analyzer diagnostics from build output."""
        raise NotImplementedError("Roslyn Analyzers parser not yet implemented")

    def parse_sarif(self, sarif_path: str) -> list | None:
        """Parse SARIF format output from analyzers."""
        raise NotImplementedError("Roslyn Analyzers parser not yet implemented")
