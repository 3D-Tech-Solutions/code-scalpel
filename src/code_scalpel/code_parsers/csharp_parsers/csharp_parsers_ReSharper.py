#!/usr/bin/env python3
"""
ReSharper C# Parser - JetBrains code analysis integration.

#
# Reference: https://www.jetbrains.com/help/resharper/InspectCode.html
# Command: inspectcode.exe Solution.sln -o=results.xml
"""

# from . import base_parser


class ReSharperParser:
    """Parser for JetBrains ReSharper InspectCode output."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.language = "csharp"

    def parse(self) -> None:
        """Parse ReSharper InspectCode XML output."""
        raise NotImplementedError("ReSharper parser not yet implemented")

    def run_inspectcode(self, solution_path: str) -> str | None:
        """Run InspectCode on a solution and return XML output path."""
        raise NotImplementedError("ReSharper parser not yet implemented")
