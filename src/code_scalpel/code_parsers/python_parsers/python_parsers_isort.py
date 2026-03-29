#!/usr/bin/env python3
"""
isort Parser - Import Sorting and Organization Analysis.
=========================================================

isort is a Python utility to sort imports alphabetically and automatically
separate them into sections. This module provides structured parsing of
isort output and configuration.

Implementation Status: NOT IMPLEMENTED
Priority: P2 - HIGH

    - [ ] P2-ISORT-001: Parse isort output format
    - [ ] P2-ISORT-002: Configuration parsing (setup.cfg, pyproject.toml)
    - [ ] P2-ISORT-003: Import grouping analysis
    - [ ] P2-ISORT-004: Sorting correctness checking
    - [ ] P2-ISORT-005: Multi-line import handling

==============================================================================
PLANNED [P2-ISORT-001]: isortParser for import organization
==============================================================================
Priority: HIGH
Status: ⏳ NOT IMPLEMENTED

Planned Features:
    - [ ] Parse isort --check-only --diff output
    - [ ] Identify unsorted import sections
    - [ ] Track import categories (stdlib, third-party, local, future)
    - [ ] Analyze import line length violations
    - [ ] Support --profile configurations (black, django, flask, etc.)
    - [ ] Handle from imports vs regular imports
    - [ ] Track circular import detection

    isort --check-only --diff will produce:
    ```
    import os
    import sys

    from third_party import something
    from . import local_module
    ```

Data Structures (Planned):
    ```python
    @dataclass
    class ImportGroup:
        category: str  # "future", "stdlib", "third-party", "local"
        imports: list[str]
        line_range: tuple[int, int]

    @dataclass
    class ImportIssue:
        issue_type: str  # "unsorted", "wrong-category", "line-too-long"
        location: SourceLocation
        current_order: list[str]
        expected_order: list[str]
        message: str

    @dataclass
    class IsortReport:
        file_path: str
        issues: list[ImportIssue]
        groups: list[ImportGroup]
        is_properly_sorted: bool
        diff: str | None  # Unified diff if --diff used
    ```

Test Cases (Planned):
    - Parse unsorted imports
    - Verify section separation (future, stdlib, third-party, local)
    - Handle multi-line imports
    - Verify import grouping
    - Test different profiles (black, django, flask)

    - [ ] Load from setup.cfg [isort] section
    - [ ] Load from pyproject.toml [tool.isort] section
    - [ ] Load from .isort.cfg file
    - [ ] Support --profile parameter

Related Features:
    - Integrates with AST parser for import analysis
    - Complements Pylint's import-related checks
    - Works with autopep8 and Black for formatting

Notes for Implementation:
    - isort can be run as a library via isort.api or subprocess
    - Primary use case: ensure consistent import ordering
    - Useful for identifying import organization patterns
    - Can be used as both validator and auto-fixer
    - Important for code consistency in teams

API Design (Planned):
    ```python
    class IsortParser:
        def __init__(self, profile: str = "black"):
            self.profile = profile

        def analyze_file(self, path: str) -> IsortReport:
            '''Check if file has properly sorted imports.'''
            pass

        def analyze_code(self, code: str, filename: str = "<string>") -> IsortReport:
            '''Analyze import order in code string.'''
            pass

        def get_fixed_code(self, code: str) -> str:
            '''Return code with sorted imports.'''
            pass

        def load_config(self, config_file: str) -> None:
            '''Load configuration from isort config file.'''
            pass
    ```
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SourceLocation:
    """Location in source code."""

    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None


@dataclass
class ImportGroup:
    """Represents a group of imports (future, stdlib, third-party, local)."""

    category: str  # "future", "stdlib", "third-party", "local"
    imports: list[str] = field(default_factory=list)
    line_range: tuple[int, int] | None = None
    properly_sorted: bool = True


@dataclass
class ImportIssue:
    """Represents an import sorting issue."""

    issue_type: str  # "unsorted", "wrong-category", "line-too-long", "circular"
    location: SourceLocation
    current_order: list[str] = field(default_factory=list)
    expected_order: list[str] = field(default_factory=list)
    message: str = ""


@dataclass
class IsortConfig:
    """Configuration for isort parser."""

    profile: str = "black"
    line_length: int = 88
    multi_line_mode: int = 3  # 0-10, mode for multi-line imports
    include_trailing_comma: bool = True
    force_single_line: bool = False
    use_parentheses: bool = True
    ensure_newline_before_comments: bool = False
    skip_glob: list[str] = field(default_factory=list)
    known_first_party: list[str] = field(default_factory=list)
    known_third_party: list[str] = field(default_factory=list)

    @classmethod
    def from_pyproject(cls, pyproject_path: str | Path) -> "IsortConfig":
        """Load configuration from pyproject.toml."""
        return cls()

    @classmethod
    def from_file(cls, config_path: str | Path) -> "IsortConfig":
        """Load configuration from .isort.cfg or setup.cfg."""
        return cls()


@dataclass
class IsortReport:
    """Results from isort analysis."""

    file_path: str
    is_properly_sorted: bool = True
    issues: list[ImportIssue] = field(default_factory=list)
    groups: list[ImportGroup] = field(default_factory=list)
    diff: str | None = None
    error: str | None = None


class IsortParser:
    """
    Parser for import organization using isort.

    STATUS: NOT IMPLEMENTED
    PRIORITY: P2 - HIGH

    Features (Planned):
        - Check import sorting against isort rules
        - Support multiple profiles (black, django, flask, etc.)
        - Identify import categories and grouping
        - Detect unsorted imports
        - Multi-line import handling
        - Configuration parsing

        - Implement analyze_file() method
        - Implement analyze_code() method
        - Add configuration support
        - Add profile support
        - Implement diff generation
    """

    def __init__(self, config: IsortConfig | None = None):
        """
        Initialize isort parser.

        Args:
            config: IsortConfig instance or None to use defaults
        """
        self.config = config or IsortConfig()

    def analyze_file(self, file_path: str | Path) -> IsortReport:
        """
        Analyze import sorting in a Python file.

        Args:
            file_path: Path to Python file

        Returns:
            IsortReport with sorting analysis results

        """
        # [20260303_FEATURE] run isort --check-only --diff on file
        path = Path(file_path)
        if not shutil.which("isort"):
            return IsortReport(
                file_path=str(path), is_properly_sorted=True, error="isort not found"
            )
        result = subprocess.run(
            ["isort", "--check-only", "--diff", str(path)],
            capture_output=True,
            text=True,
        )
        is_sorted = result.returncode == 0
        return IsortReport(
            file_path=str(path),
            is_properly_sorted=is_sorted,
            diff=result.stdout if not is_sorted else None,
        )

    def analyze_code(self, code: str, filename: str = "<string>") -> IsortReport:
        """
        Analyze import sorting in Python code string.

        Args:
            code: Python source code
            filename: Filename for error reporting

        Returns:
            IsortReport with sorting analysis results

        """
        # [20260303_FEATURE] write to temp file then run isort --check-only --diff
        if not shutil.which("isort"):
            return IsortReport(
                file_path=filename, is_properly_sorted=True, error="isort not found"
            )
        fd, tmp = tempfile.mkstemp(suffix=".py")
        try:
            os.write(fd, code.encode())
            os.close(fd)
            result = subprocess.run(
                ["isort", "--check-only", "--diff", tmp],
                capture_output=True,
                text=True,
            )
            is_sorted = result.returncode == 0
            return IsortReport(
                file_path=filename,
                is_properly_sorted=is_sorted,
                diff=result.stdout if not is_sorted else None,
            )
        finally:
            os.unlink(tmp)

    def get_fixed_code(self, code: str) -> str:
        """
        Get code with properly sorted imports.

        Args:
            code: Python source code

        Returns:
            Code with sorted imports

        """
        # [20260303_FEATURE] prefer isort library; fall back to subprocess
        try:
            import isort as _isort  # type: ignore[import]

            return _isort.code(code)  # type: ignore[no-any-return]
        except ImportError:
            pass
        if not shutil.which("isort"):
            return code
        fd, tmp = tempfile.mkstemp(suffix=".py")
        try:
            os.write(fd, code.encode())
            os.close(fd)
            subprocess.run(["isort", tmp], capture_output=True)
            with open(tmp) as fh:
                return fh.read()
        finally:
            os.unlink(tmp)

    def load_config(self, config_path: str | Path) -> None:
        """
        Load configuration from isort config file.

        Args:
            config_path: Path to .isort.cfg or setup.cfg

        """
        # [20260303_FEATURE] read profile setting from config file
        path = Path(config_path)
        if not path.exists():
            return
        content = path.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("profile"):
                parts = stripped.split("=", 1)
                if len(parts) == 2:
                    self.config.profile = parts[1].strip().strip('"').strip("'")
                break

    # -------------------------------------------------------------------------
    # [20260303_FEATURE] New methods added per Stage 4a spec
    # -------------------------------------------------------------------------

    def execute_isort(self, path: str = ".") -> list[dict]:
        """Run isort --check-only --diff on path; return [] if not available."""
        if not shutil.which("isort"):
            return []
        result = subprocess.run(
            ["isort", "--check-only", "--diff", path],
            capture_output=True,
            text=True,
        )
        unsorted = self.parse_diff_output(result.stdout)
        return [{"file": f, "is_sorted": False} for f in unsorted]

    def parse_diff_output(self, diff_text: str) -> list[str]:
        """Parse unified diff text and return list of unsorted file paths."""
        files: list[str] = []
        for line in diff_text.splitlines():
            if line.startswith("--- "):
                fname = line[4:].split("\t")[0].strip()
                if fname and fname != "/dev/null" and fname not in files:
                    files.append(fname)
        return files

    def check_files(self, paths: list) -> dict[str, bool]:
        """Return {str(path): is_sorted} dict for each path."""
        result_map: dict[str, bool] = {}
        no_isort = not shutil.which("isort")
        for p in paths:
            key = str(p)
            if no_isort:
                result_map[key] = True
                continue
            res = subprocess.run(
                ["isort", "--check-only", key],
                capture_output=True,
                text=True,
            )
            result_map[key] = res.returncode == 0
        return result_map

    def generate_report(self, findings: list, format: str = "json") -> str:
        """Return JSON report of unsorted files."""
        unsorted = [f["file"] if isinstance(f, dict) else str(f) for f in findings]
        return json.dumps(
            {"tool": "isort", "total_unsorted": len(unsorted), "files": unsorted},
            indent=2,
        )
