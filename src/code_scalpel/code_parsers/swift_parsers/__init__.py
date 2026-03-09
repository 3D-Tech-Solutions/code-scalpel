#!/usr/bin/env python3
"""Swift Parsers Module - Unified Interface and Registry

This module provides a comprehensive interface for Swift code analysis.
"""

__all__ = [
    "SwiftParserRegistry",
    "SwiftLintParser",
    "TailorParser",
    "SourceKittenParser",
    "SwiftFormatParser",
]


class SwiftParserRegistry:
    """Registry for Swift static-analysis tool parsers.

    [20260304_FEATURE] Polyglot Phase 2: lazy-load factory pattern.
    All execute_* methods accept List[Path]; use call_style='list_path'.
    Note: parser execute methods currently raise NotImplementedError (Phase 2
    stubs) — the dispatcher handles this gracefully and returns no findings.
    """

    _TOOL_MAP: dict = {
        "swiftlint": ("swift_parsers_SwiftLint", "SwiftLintParser"),
        "tailor": ("swift_parsers_Tailor", "TailorParser"),
        "sourcekitten": ("swift_parsers_sourcekitten", "SourceKittenParser"),
        "swiftformat": ("swift_parsers_swiftformat", "SwiftFormatParser"),
    }

    def get_parser(self, tool_name: str):
        """Return an instantiated parser for *tool_name*.

        Args:
            tool_name: One of the recognised tool identifiers (case-insensitive).

        Raises:
            ValueError: If *tool_name* is not a recognised tool.
        """
        import importlib

        key = tool_name.lower()
        if key not in self._TOOL_MAP:
            raise ValueError(
                f"Unknown Swift parser tool: {tool_name!r}. "
                f"Valid options: {sorted(set(self._TOOL_MAP.keys()))}"
            )
        module_name, class_name = self._TOOL_MAP[key]
        module = importlib.import_module(f".{module_name}", package=__package__)
        return getattr(module, class_name)()

    def analyze(self, path, tools=None):
        """Run all specified parsers on *path* and aggregate results."""
        from pathlib import Path

        _exec_map = {
            "swiftlint": "execute_swiftlint",
            "tailor": "execute_tailor",
            "sourcekitten": "execute_sourcekitten",
            "swiftformat": "execute_swiftformat",
        }
        selected = [t.lower() for t in tools] if tools else list(self._TOOL_MAP.keys())
        results: dict = {}
        for tool_key in selected:
            try:
                parser = self.get_parser(tool_key)
                method_name = _exec_map.get(tool_key, "")
                if method_name and hasattr(parser, method_name):
                    results[tool_key] = getattr(parser, method_name)([Path(str(path))]) or []
                else:
                    results[tool_key] = []
            except Exception:
                results[tool_key] = []
        return results
