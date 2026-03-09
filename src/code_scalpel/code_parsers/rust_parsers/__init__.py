#!/usr/bin/env python3
"""Rust Parsers Module - Unified Interface and Registry

[20260305_FEATURE] Phase 2 tool parsers for Rust static analysis.
"""

__all__ = [
    "RustParserRegistry",
    "ClippyParser",
    "RustfmtParser",
    "CargoAuditParser",
    "CargoCheckParser",
    "RustAnalyzerParser",
]


class RustParserRegistry:
    """Registry for Rust static-analysis tool parsers.

    [20260305_FEATURE] Polyglot Phase 2: lazy-load factory pattern.
    """

    _TOOL_MAP: dict = {
        "clippy": ("rust_parsers_clippy", "ClippyParser"),
        "rustfmt": ("rust_parsers_rustfmt", "RustfmtParser"),
        "cargo_audit": ("rust_parsers_cargo_audit", "CargoAuditParser"),
        "cargo-audit": ("rust_parsers_cargo_audit", "CargoAuditParser"),
        "cargo_check": ("rust_parsers_cargo_check", "CargoCheckParser"),
        "cargo-check": ("rust_parsers_cargo_check", "CargoCheckParser"),
        "rust_analyzer": ("rust_parsers_rust_analyzer", "RustAnalyzerParser"),
        "rust-analyzer": ("rust_parsers_rust_analyzer", "RustAnalyzerParser"),
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
                f"Unknown Rust parser tool: {tool_name!r}. "
                f"Valid options: {sorted(set(self._TOOL_MAP.keys()))}"
            )
        module_name, class_name = self._TOOL_MAP[key]
        module = importlib.import_module(f".{module_name}", package=__package__)
        return getattr(module, class_name)()

    def analyze(self, path, tools=None):
        """Run all specified parsers on *path* and aggregate results."""
        from pathlib import Path

        _exec_map = {
            "clippy": "execute_clippy",
            "rustfmt": "execute_rustfmt",
            "cargo_audit": "execute_cargo_audit",
            "cargo_check": "execute_cargo_check",
            "rust_analyzer": "execute_rust_analyzer",
        }
        selected = [t.lower().replace("-", "_") for t in tools] if tools else list(
            k for k in self._TOOL_MAP if "-" not in k
        )
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
