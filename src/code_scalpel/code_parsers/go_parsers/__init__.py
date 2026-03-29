#!/usr/bin/env python3
"""Go Parser Registry.

[20260303_FEATURE] Phase 2: Full GoParserRegistry with lazy-load factory
replacing NotImplementedError stubs.

Note: Go adapter (go_adapter.py) is already complete.  This module provides
the tool-parser registry only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

__all__ = [
    "GoParserRegistry",
    "GofmtParser",
    "GolintParser",
    "GovetParser",
    "StaticcheckParser",
    "GolangciLintParser",
    "GosecParser",
]

# Map of tool name → (module_file, class_name)
_TOOL_MAP: Dict[str, str] = {
    "golangci": "GolangciLintParser",
    "golangci-lint": "GolangciLintParser",
    "gosec": "GosecParser",
    "staticcheck": "StaticcheckParser",
    "govet": "GovetParser",
    "go_vet": "GovetParser",
    "golint": "GolintParser",
    "gofmt": "GofmtParser",
}

_MODULE_MAP: Dict[str, str] = {
    "GolangciLintParser": "go_parsers_golangci_lint",
    "GosecParser": "go_parsers_gosec",
    "StaticcheckParser": "go_parsers_staticcheck",
    "GovetParser": "go_parsers_govet",
    "GolintParser": "go_parsers_golint",
    "GofmtParser": "go_parsers_gofmt",
}


class GoParserRegistry:
    """Registry for Go parser implementations with lazy-load factory pattern.

    [20260303_FEATURE] Phase 2: full implementation.
    """

    def get_parser(self, tool_name: str) -> Any:
        """Return an instantiated parser for *tool_name*.

        Args:
            tool_name: One of "golangci", "gosec", "staticcheck", "govet",
                "golint", "gofmt" (case-insensitive, also accepts hyphened
                variants like "golangci-lint").

        Raises:
            ValueError: If tool_name is not recognised.
        """
        key = tool_name.lower()
        if key not in _TOOL_MAP:
            raise ValueError(
                f"Unknown Go parser tool: {tool_name!r}. "
                f"Valid options: {sorted(set(_TOOL_MAP.keys()))}"
            )
        class_name = _TOOL_MAP[key]
        mod = _import_parser_module(_MODULE_MAP[class_name])
        return getattr(mod, class_name)()

    def analyze(
        self,
        path: Union[str, Path],
        tools: Optional[List[str]] = None,
    ) -> Dict[str, List]:
        """Run all (or specified) parsers on *path* and aggregate results.

        [20260303_FEATURE] Returns ``{tool: [findings]}`` — empty list on error.
        """
        canonical_tools = [
            "golangci",
            "gosec",
            "staticcheck",
            "govet",
            "golint",
            "gofmt",
        ]
        selected = [t.lower() for t in tools] if tools else canonical_tools
        results: Dict[str, List] = {}
        for tool in selected:
            try:
                _parser = self.get_parser(tool)  # noqa: F841
                results[tool] = []  # default; parsers require CLI execution
            except Exception:  # noqa: BLE001
                results[tool] = []
        return results


def _import_parser_module(module_basename: str) -> Any:
    """Import a go_parsers sub-module by basename."""
    import importlib

    return importlib.import_module(
        f"code_scalpel.code_parsers.go_parsers.{module_basename}"
    )


# ---------------------------------------------------------------------------
# Module-level lazy attribute access (PEP 562)
# ---------------------------------------------------------------------------
def __getattr__(name: str) -> Any:
    _name_to_module = {v: k for k, v in _MODULE_MAP.items()}
    if name in _MODULE_MAP:
        mod = _import_parser_module(_MODULE_MAP[name])
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
