#!/usr/bin/env python3
"""
Ruby AST Parser - Abstract Syntax Tree Analysis via RubyNormalizer.

[20260304_FEATURE] Full implementation using the RubyNormalizer IR layer.
Provides class/method/module extraction and complexity analysis for Ruby code.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class RubyClass:
    """Represents a Ruby class definition."""

    name: str
    file_path: str
    line_number: int
    parent_class: Optional[str] = None
    mixins: List[str] = field(default_factory=list)
    methods: List["RubyMethod"] = field(default_factory=list)


@dataclass
class RubyMethod:
    """Represents a Ruby method definition."""

    name: str
    file_path: str
    line_number: int
    class_name: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    visibility: str = "public"
    is_class_method: bool = False
    complexity: int = 1


@dataclass
class RubyModuleInfo:
    """Represents a Ruby module."""

    name: str
    file_path: str
    line_number: int
    methods: List[RubyMethod] = field(default_factory=list)
    nested_modules: List["RubyModuleInfo"] = field(default_factory=list)


class RubyASTParser:
    """
    Parser for Ruby AST analysis using the RubyNormalizer IR layer.

    [20260304_FEATURE] Wraps RubyNormalizer to extract structured information
    about classes, methods, and modules from Ruby source code.

    Provides class/method extraction, inheritance analysis, and
    meta-programming pattern detection without requiring external tools.
    """

    def __init__(self) -> None:
        """Initialize Ruby AST parser."""
        pass

    def _get_normalizer(self):
        """Lazy import to avoid hard dependency at module load time."""
        from code_scalpel.ir.normalizers.ruby_normalizer import RubyNormalizer  # type: ignore
        return RubyNormalizer()

    def parse_file(self, path: Path):
        """
        Parse a Ruby file and return an IRModule.

        [20260304_FEATURE] Delegates to RubyNormalizer.normalize().
        """
        code = path.read_text(encoding="utf-8")
        return self._get_normalizer().normalize(code)

    def parse_code(self, code: str):
        """
        Parse Ruby source code string and return an IRModule.

        [20260304_FEATURE] Delegates to RubyNormalizer.normalize().
        """
        return self._get_normalizer().normalize(code)

    # Alias for legacy stub compatibility
    def parse_ruby_file(self, file_path: Path):
        """Alias for parse_file()."""
        return self.parse_file(file_path)

    def extract_classes(self, ir_module, file_path: str = "") -> List[RubyClass]:
        """
        Extract RubyClass objects from an IRModule.

        [20260304_FEATURE] Iterates IRModule.body looking for IRClassDef nodes.
        Returns list of RubyClass with method lists populated.
        """
        from code_scalpel.ir.nodes import IRClassDef, IRFunctionDef  # type: ignore
        classes: List[RubyClass] = []
        body = getattr(ir_module, "body", []) or []
        for node in body:
            if not isinstance(node, IRClassDef):
                continue
            parent = getattr(node, "bases", [])
            parent_name = parent[0] if parent else None
            mixins = node._metadata.get("mixins", []) if hasattr(node, "_metadata") else []
            methods: List[RubyMethod] = []
            class_body = getattr(node, "body", []) or []
            for child in class_body:
                if isinstance(child, IRFunctionDef):
                    is_singleton = (
                        child._metadata.get("singleton", False)
                        if hasattr(child, "_metadata")
                        else False
                    )
                    params = [
                        getattr(p, "name", str(p))
                        for p in (getattr(child, "args", []) or [])
                    ]
                    methods.append(
                        RubyMethod(
                            name=child.name,
                            file_path=file_path,
                            line_number=getattr(child, "lineno", 0),
                            class_name=node.name,
                            parameters=params,
                            is_class_method=is_singleton,
                            complexity=self._estimate_complexity(child),
                        )
                    )
            classes.append(
                RubyClass(
                    name=node.name,
                    file_path=file_path,
                    line_number=getattr(node, "lineno", 0),
                    parent_class=parent_name,
                    mixins=mixins,
                    methods=methods,
                )
            )
        return classes

    def extract_methods(
        self, ir_module, class_context: Optional[str] = None, file_path: str = ""
    ) -> List[RubyMethod]:
        """
        Extract top-level (or all) RubyMethod objects from an IRModule.

        [20260304_FEATURE] If class_context given, only returns methods
        from that class; otherwise returns all top-level functions.
        """
        from code_scalpel.ir.nodes import IRClassDef, IRFunctionDef  # type: ignore
        methods: List[RubyMethod] = []
        body = getattr(ir_module, "body", []) or []
        if class_context:
            for node in body:
                if isinstance(node, IRClassDef) and node.name == class_context:
                    for child in (getattr(node, "body", []) or []):
                        if isinstance(child, IRFunctionDef):
                            methods.append(self._func_to_method(child, class_context, file_path))
        else:
            for node in body:
                if isinstance(node, IRFunctionDef):
                    methods.append(self._func_to_method(node, None, file_path))
                elif isinstance(node, IRClassDef):
                    for child in (getattr(node, "body", []) or []):
                        if isinstance(child, IRFunctionDef):
                            methods.append(self._func_to_method(child, node.name, file_path))
        return methods

    def _func_to_method(self, func, class_name: Optional[str], file_path: str) -> RubyMethod:
        """Convert an IRFunctionDef to a RubyMethod dataclass."""
        is_singleton = (
            func._metadata.get("singleton", False)
            if hasattr(func, "_metadata")
            else False
        )
        params = [
            getattr(p, "name", str(p))
            for p in (getattr(func, "args", []) or [])
        ]
        return RubyMethod(
            name=func.name,
            file_path=file_path,
            line_number=getattr(func, "lineno", 0),
            class_name=class_name,
            parameters=params,
            is_class_method=is_singleton,
            complexity=self._estimate_complexity(func),
        )

    def extract_modules(self, ir_module, file_path: str = "") -> List[RubyModuleInfo]:
        """
        Extract RubyModuleInfo objects from an IRModule.

        [20260304_FEATURE] Looks for IRClassDef nodes with kind==module metadata.
        """
        from code_scalpel.ir.nodes import IRClassDef, IRFunctionDef  # type: ignore
        modules: List[RubyModuleInfo] = []
        body = getattr(ir_module, "body", []) or []
        for node in body:
            if not isinstance(node, IRClassDef):
                continue
            meta = getattr(node, "_metadata", {}) or {}
            if meta.get("kind") != "module":
                continue
            methods: List[RubyMethod] = []
            for child in (getattr(node, "body", []) or []):
                if isinstance(child, IRFunctionDef):
                    methods.append(self._func_to_method(child, node.name, file_path))
            modules.append(
                RubyModuleInfo(
                    name=node.name,
                    file_path=file_path,
                    line_number=getattr(node, "lineno", 0),
                    methods=methods,
                )
            )
        return modules

    def _estimate_complexity(self, func) -> int:
        """
        Estimate cyclomatic complexity of an IRFunctionDef by counting branches.

        [20260304_FEATURE] Counts IRIf/IRWhile/IRFor nodes in function body.
        """
        from code_scalpel.ir.nodes import IRIf, IRWhile, IRFor  # type: ignore
        complexity = 1
        def _walk(nodes):
            nonlocal complexity
            for node in (nodes or []):
                if isinstance(node, (IRIf, IRWhile, IRFor)):
                    complexity += 1
                # Recurse into nested bodies
                for attr in ("body", "orelse", "handlers"):
                    _walk(getattr(node, attr, None) or [])
        _walk(getattr(func, "body", []))
        return complexity

    def find_class(self, ir_module, name: str, file_path: str = "") -> Optional[RubyClass]:
        """Return first class matching name, or None."""
        for cls in self.extract_classes(ir_module, file_path):
            if cls.name == name:
                return cls
        return None

    def find_method(self, ir_module, name: str, file_path: str = "") -> Optional[RubyMethod]:
        """Return first method matching name, or None."""
        for method in self.extract_methods(ir_module, file_path=file_path):
            if method.name == name:
                return method
        return None

    def analyze_inheritance(self, classes: List[RubyClass]) -> Dict[str, Any]:
        """
        Build an inheritance map from extracted classes.

        [20260304_FEATURE] Returns {child: parent} mapping.
        """
        return {c.name: c.parent_class for c in classes if c.parent_class}

    def detect_meta_programming(self, ir_module) -> List[Dict[str, Any]]:
        """
        Detect common Ruby meta-programming patterns in the IR.

        [20260304_FEATURE] Looks for attr_accessor, include, extend calls.
        """
        from code_scalpel.ir.nodes import IRCall  # type: ignore
        patterns: List[Dict[str, Any]] = []
        body = getattr(ir_module, "body", []) or []
        def _walk(nodes):
            for node in (nodes or []):
                if isinstance(node, IRCall):
                    fn = getattr(node, "func", None)
                    fname = getattr(fn, "name", None) or getattr(fn, "id", None) or str(fn)
                    if fname in ("attr_accessor", "attr_reader", "attr_writer",
                                 "include", "extend", "prepend",
                                 "define_method", "method_missing"):
                        patterns.append({
                            "pattern": fname,
                            "line": getattr(node, "lineno", 0),
                        })
                for attr in ("body", "orelse", "args"):
                    _walk(getattr(node, attr, None) or [])
        _walk(body)
        return patterns

    def generate_report(self, ir_module, file_path: str = "") -> str:
        """
        Generate a JSON report of extracted classes/methods/modules.

        [20260304_FEATURE] Returns JSON string.
        """
        classes = self.extract_classes(ir_module, file_path)
        methods = self.extract_methods(ir_module, file_path=file_path)
        modules = self.extract_modules(ir_module, file_path)
        report: Dict[str, Any] = {
            "tool": "ruby_ast",
            "file": file_path,
            "classes": [
                {
                    "name": c.name,
                    "line": c.line_number,
                    "parent": c.parent_class,
                    "mixins": c.mixins,
                    "method_count": len(c.methods),
                }
                for c in classes
            ],
            "top_level_methods": [
                {
                    "name": m.name,
                    "line": m.line_number,
                    "complexity": m.complexity,
                    "parameters": m.parameters,
                }
                for m in methods if m.class_name is None
            ],
            "modules": [
                {
                    "name": mod.name,
                    "line": mod.line_number,
                    "method_count": len(mod.methods),
                }
                for mod in modules
            ],
        }
        return json.dumps(report, indent=2)
