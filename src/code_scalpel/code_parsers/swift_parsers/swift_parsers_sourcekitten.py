#!/usr/bin/env python3
"""SourceKitten Parser - Swift AST and Semantic Analysis.

[20260304_FEATURE] Full implementation replacing Phase 2 stubs.

SourceKitten is a macOS/Linux tool that wraps Apple's SourceKit framework
for Swift AST introspection, documentation generation, and code structure.
Reference: https://github.com/jpsim/SourceKitten

Note: SourceKitten requires a macOS machine with Xcode or a Linux build of
Swift. The execute_sourcekitten() method raises NotImplementedError with
clear setup instructions (enterprise-tool pattern); all *parse* methods are
fully implemented.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SwiftSymbol:
    """Represents a Swift symbol (class, function, var, etc.)."""

    name: str
    kind: str
    file_path: str
    line_number: int
    column: int
    documentation: Optional[str] = None
    accessibility: str = "internal"
    children: List["SwiftSymbol"] = field(default_factory=list)


@dataclass
class SwiftComplexity:
    """Represents code complexity metrics."""

    symbol_name: str
    cyclomatic_complexity: int
    cognitive_complexity: int
    lines_of_code: int


# [20260304_FEATURE] SourceKit kind → human kind mapping
_KIND_MAP: Dict[str, str] = {
    "source.lang.swift.decl.class": "class",
    "source.lang.swift.decl.struct": "struct",
    "source.lang.swift.decl.enum": "enum",
    "source.lang.swift.decl.protocol": "protocol",
    "source.lang.swift.decl.function.free": "function",
    "source.lang.swift.decl.function.method.instance": "method",
    "source.lang.swift.decl.function.method.static": "static_method",
    "source.lang.swift.decl.function.method.class": "class_method",
    "source.lang.swift.decl.var.instance": "property",
    "source.lang.swift.decl.var.static": "static_property",
    "source.lang.swift.decl.var.global": "global_var",
    "source.lang.swift.decl.extension": "extension",
    "source.lang.swift.decl.typealias": "typealias",
    "source.lang.swift.decl.enumelement": "enum_case",
}


def _extract_symbols_recursive(
    substructure: List[Dict],
    file_path: str,
) -> List[SwiftSymbol]:
    """Recursively walk a SourceKit substructure list and build SwiftSymbols."""
    symbols: List[SwiftSymbol] = []
    for item in substructure:
        raw_kind = item.get("key.kind", "")
        kind = _KIND_MAP.get(raw_kind, raw_kind)
        name = item.get("key.name", "<anonymous>")
        doc = item.get(
            "key.doc.full_as_xml",
            item.get("key.parsed_scope.start", None),
        )
        symbol = SwiftSymbol(
            name=name,
            kind=kind,
            file_path=file_path,
            line_number=item.get("key.parsed_range.start.line", 0),
            column=item.get("key.parsed_range.start.column", 0),
            documentation=str(doc) if doc else None,
            accessibility=item.get("key.accessibility", "internal"),
            children=_extract_symbols_recursive(
                item.get("key.substructure", []), file_path
            ),
        )
        symbols.append(symbol)
    return symbols


class SourceKittenParser:
    """
    Parser for SourceKitten Swift AST and semantic analysis.

    [20260304_FEATURE] Full parse implementation; execute raises
    NotImplementedError with setup instructions (enterprise-tool pattern).
    """

    def __init__(self) -> None:
        """Initialise SourceKitten parser."""
        self.symbols: List[SwiftSymbol] = []
        self.complexity_metrics: List[SwiftComplexity] = []

    # ------------------------------------------------------------------
    # Execution (enterprise-tool pattern)
    # ------------------------------------------------------------------

    def execute_sourcekitten(self, paths: List[Path]) -> List[SwiftSymbol]:
        """
        Run SourceKitten and return structured symbols.

        [20260304_FEATURE] Enterprise-tool pattern: raises NotImplementedError
        so callers receive clear instructions instead of a silent failure.

        To use SourceKitten::

            # macOS with Homebrew:
            brew install sourcekitten

            # Linux:
            # Build from source — https://github.com/jpsim/SourceKitten

            # Run manually and pipe to parse_sourcekitten_output():
            sourcekitten structure --file MyFile.swift > ast.json
        """
        raise NotImplementedError(
            "SourceKitten must be invoked externally.\n"
            "macOS: brew install sourcekitten\n"
            "Usage: sourcekitten structure --file <file.swift>\n"
            "Then call: parser.parse_sourcekitten_output(output_path)"
        )

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse_sourcekitten_output(self, output_path: Path) -> List[SwiftSymbol]:
        """
        Parse a saved SourceKitten JSON output file.

        [20260304_FEATURE] SourceKitten structure output format::

            {"key.substructure": [{"key.kind": "source.lang.swift.decl.class",
                                   "key.name": "MyClass", ...}]}
        """
        try:
            text = output_path.read_text(encoding="utf-8")
        except OSError:
            return []
        return self._parse_json(text, file_path=str(output_path))

    def _parse_json(self, json_text: str, file_path: str = "") -> List[SwiftSymbol]:
        """Parse SourceKitten JSON text into SwiftSymbol list."""
        if not json_text or not json_text.strip():
            return []
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            return []
        substructure = data.get("key.substructure", [])
        return _extract_symbols_recursive(substructure, file_path)

    def extract_symbols(self, output: Dict[str, Any]) -> List[SwiftSymbol]:
        """
        Extract symbols from an already-parsed SourceKitten dict.

        [20260304_FEATURE] Accepts raw dict (e.g. json.loads result).
        """
        return _extract_symbols_recursive(
            output.get("key.substructure", []), ""
        )

    # ------------------------------------------------------------------
    # Analysis helpers
    # ------------------------------------------------------------------

    def analyze_complexity(
        self, symbols: List[SwiftSymbol]
    ) -> List[SwiftComplexity]:
        """
        Produce complexity estimates for function-like symbols.

        [20260304_FEATURE] Cyclomatic complexity approximated by child count.
        SourceKit does not expose cyclomatic complexity directly.
        """
        results: List[SwiftComplexity] = []
        function_kinds = {"function", "method", "static_method", "class_method"}
        for sym in symbols:
            if sym.kind not in function_kinds:
                continue
            approx_cc = 1 + len(sym.children)
            results.append(
                SwiftComplexity(
                    symbol_name=sym.name,
                    cyclomatic_complexity=approx_cc,
                    cognitive_complexity=approx_cc,  # approximation
                    lines_of_code=0,
                )
            )
        return results

    def extract_documentation(
        self, symbols: List[SwiftSymbol]
    ) -> Dict[str, str]:
        """
        Return a mapping of symbol name → documentation string.

        [20260304_FEATURE] Symbols without documentation are omitted.
        """
        return {
            sym.name: sym.documentation
            for sym in symbols
            if sym.documentation
        }

    def generate_ast_report(self, symbols: List[SwiftSymbol]) -> str:
        """
        Generate a compact JSON report of extracted symbols.

        [20260304_FEATURE] Returns a JSON array of symbol metadata.
        """
        def _sym_to_dict(s: SwiftSymbol) -> Dict[str, Any]:
            return {
                "name": s.name,
                "kind": s.kind,
                "file": s.file_path,
                "line": s.line_number,
                "accessibility": s.accessibility,
                "children": [_sym_to_dict(c) for c in s.children],
            }
        return json.dumps([_sym_to_dict(s) for s in symbols], indent=2)

