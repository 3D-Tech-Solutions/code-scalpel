"""
Java import resolution for cross-file analysis.

[20260309_FEATURE] Provide Java package and import discovery with the same
minimal surface used by cross-file analysis: module_to_file, file_to_module,
imports, and edges.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, List, Set, Tuple, Union

from code_scalpel.ast_tools.import_resolver import (
    ImportGraphResult,
    ImportInfo,
    ImportResolver,
    ImportType,
)


class JavaImportResolver:
    """
    Build package and import relationships for Java projects.

    [20260309_FEATURE] This resolver intentionally exposes the same core
    fields consumed by cross-file analysis as the existing Python resolver,
    allowing the Java cross-file scan to be ported incrementally.
    """

    PACKAGE_RE = re.compile(r"^\s*package\s+([A-Za-z_][\w.]*)\s*;")
    IMPORT_RE = re.compile(r"^\s*import\s+(static\s+)?([A-Za-z_][\w.]*(?:\.\*)?)\s*;")
    SKIP_DIRS = ImportResolver.SKIP_DIRS

    def __init__(self, project_root: Union[str, Path]):
        self.project_root = Path(project_root).resolve()
        self.imports: DefaultDict[str, List[ImportInfo]] = defaultdict(list)
        self.edges: DefaultDict[str, Set[str]] = defaultdict(set)
        self.module_to_file: Dict[str, str] = {}
        self.file_to_module: Dict[str, str] = {}
        self.package_to_modules: DefaultDict[str, Set[str]] = defaultdict(set)

    def clear(self) -> None:
        """Reset resolver state."""
        self.imports.clear()
        self.edges.clear()
        self.module_to_file.clear()
        self.file_to_module.clear()
        self.package_to_modules.clear()

    def build(self) -> ImportGraphResult:
        """Build Java package and import metadata for the project root."""
        self.clear()

        if not self.project_root.exists():
            return ImportGraphResult(
                success=False, errors=["Project root does not exist"]
            )

        java_files = self._find_java_files()
        for file_path in java_files:
            module_name = self._get_module_name(file_path)
            self.module_to_file[module_name] = str(file_path)
            self.file_to_module[str(file_path)] = module_name
            package_name = module_name.rsplit(".", 1)[0] if "." in module_name else ""
            if package_name:
                self.package_to_modules[package_name].add(module_name)

        for file_path in java_files:
            module_name = self.file_to_module[str(file_path)]
            self._extract_imports(file_path, module_name)

        return ImportGraphResult(
            success=True,
            modules=len(self.module_to_file),
            imports=sum(len(imps) for imps in self.imports.values()),
        )

    def _find_java_files(self) -> List[Path]:
        """Collect Java source files under the project root."""
        java_files: List[Path] = []
        for path in self.project_root.rglob("*.java"):
            if any(part in self.SKIP_DIRS for part in path.parts):
                continue
            java_files.append(path)
        return sorted(java_files)

    def _get_module_name(self, file_path: Path) -> str:
        """Compute a Java module key as package plus file stem."""
        package_name = self._extract_package(file_path)
        class_name = file_path.stem
        if package_name:
            return f"{package_name}.{class_name}"
        return class_name

    def _extract_package(self, file_path: Path) -> str:
        """Extract the declared package name from a Java file."""
        source = file_path.read_text(encoding="utf-8")
        for line in source.splitlines():
            match = self.PACKAGE_RE.match(line)
            if match:
                return match.group(1)
        return ""

    def _extract_imports(self, file_path: Path, module_name: str) -> None:
        """Parse Java import declarations into ImportInfo entries."""
        source = file_path.read_text(encoding="utf-8")
        for lineno, line in enumerate(source.splitlines(), start=1):
            match = self.IMPORT_RE.match(line)
            if not match:
                continue

            is_static = bool(match.group(1))
            import_path = match.group(2)
            import_info, edge_targets = self._make_import_info(
                file_path=file_path,
                import_path=import_path,
                line=lineno,
                is_static=is_static,
            )
            self.imports[module_name].append(import_info)
            for edge_target in edge_targets:
                self.edges[module_name].add(edge_target)

    def _make_import_info(
        self,
        file_path: Path,
        import_path: str,
        line: int,
        is_static: bool,
    ) -> Tuple[ImportInfo, List[str]]:
        """Convert a Java import declaration into ImportInfo and edge target."""
        if import_path.endswith(".*"):
            module = import_path[:-2]
            import_info = ImportInfo(
                module=module,
                name="*",
                import_type=ImportType.WILDCARD,
                line=line,
                file=str(file_path),
            )
            if is_static:
                return (
                    import_info,
                    [module] if module in self.module_to_file else [],
                )

            # [20260315_FEATURE] Expand wildcard package imports to project-local
            # Java modules so cross-file graph/security slices can reuse resolver edges.
            return import_info, sorted(self.package_to_modules.get(module, set()))

        module, name = import_path.rsplit(".", 1)
        import_type = ImportType.FROM if is_static else ImportType.DIRECT
        import_info = ImportInfo(
            module=module,
            name=name,
            import_type=import_type,
            line=line,
            file=str(file_path),
        )

        if is_static:
            edge_targets = [module] if module in self.module_to_file else []
        else:
            edge_targets = [import_path] if import_path in self.module_to_file else []
        return import_info, edge_targets
