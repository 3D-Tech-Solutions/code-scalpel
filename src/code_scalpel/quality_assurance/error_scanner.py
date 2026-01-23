"""
ErrorScanner - Comprehensive project-wide error detection for code-scalpel.

# [20251224_REFACTOR] Moved from code_scalpel/error_scanner.py to
# code_scalpel/quality_assurance/error_scanner.py as part of Issue #1
# in PROJECT_REORG_REFACTOR.md Phase 1.

This module provides robust, recursive error scanning across entire projects,
addressing limitations in directory-level scanning by explicitly checking all files.

Key Features:
- Recursive Python file discovery
- Batch error checking with explicit file paths
- Error aggregation and categorization
- Filtering and sorting capabilities
- Multiple output formats (JSON, HTML, text)
- CLI integration
- Statistics and reporting

Usage:
    from code_scalpel.error_scanner import ErrorScanner

    scanner = ErrorScanner()
    results = scanner.scan_directory("src/")
    report = scanner.generate_report(results)
    print(report.summary())

Command-line:
    python -m code_scalpel.error_scanner --path src/ --format json

======================================

COMMUNITY (Current & Planned):

PRO (Enhanced Features):

ENTERPRISE (Advanced Capabilities):
"""

from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from subprocess import TimeoutExpired

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class CodeError:
    """Represents a single code error."""

    file_path: str
    line_number: int
    column: int
    message: str
    error_type: str
    severity: ErrorSeverity
    code: str = ""  # The problematic code snippet

    def __hash__(self):
        return hash((self.file_path, self.line_number, self.message))

    def __eq__(self, other):
        if not isinstance(other, CodeError):
            return False
        return (
            self.file_path == other.file_path
            and self.line_number == other.line_number
            and self.message == other.message
        )


@dataclass
class ScanResults:
    """Results from a comprehensive scan."""

    root_path: str
    files_checked: int = 0
    files_with_errors: int = 0
    total_errors: int = 0
    errors: list[CodeError] = field(default_factory=list)
    error_types: dict[str, int] = field(default_factory=dict)
    severity_counts: dict[ErrorSeverity, int] = field(default_factory=dict)
    scan_duration_seconds: float = 0.0

    def add_error(self, error: CodeError):
        """Add an error to results."""
        if error not in self.errors:
            self.errors.append(error)
            self.total_errors += 1

            # Track by type
            self.error_types[error.error_type] = self.error_types.get(error.error_type, 0) + 1

            # Track by severity
            self.severity_counts[error.severity] = self.severity_counts.get(error.severity, 0) + 1

    def get_errors_by_file(self, file_path: str) -> list[CodeError]:
        """Get all errors for a specific file."""
        return [e for e in self.errors if e.file_path == file_path]

    def get_errors_by_severity(self, severity: ErrorSeverity) -> list[CodeError]:
        """Get all errors of a specific severity."""
        return [e for e in self.errors if e.severity == severity]

    def get_errors_by_type(self, error_type: str) -> list[CodeError]:
        """Get all errors of a specific type."""
        return [e for e in self.errors if e.error_type == error_type]

    def sort_by_severity(self) -> list[CodeError]:
        """Get errors sorted by severity (errors first, then warnings, then info)."""
        severity_order = {
            ErrorSeverity.ERROR: 0,
            ErrorSeverity.WARNING: 1,
            ErrorSeverity.INFO: 2,
        }
        return sorted(
            self.errors,
            key=lambda e: (severity_order[e.severity], e.file_path, e.line_number),
        )

    def sort_by_file(self) -> list[CodeError]:
        """Get errors sorted by file path."""
        return sorted(self.errors, key=lambda e: (e.file_path, e.line_number))


class ErrorScanner:
    """
    Comprehensive project error scanner.

    Recursively finds all Python files and checks them for errors,
    addressing the limitations of directory-level error scanning.
    """

    def __init__(self, batch_size: int = 30, verbose: bool = False, use_pylint: bool = False):
        """
        Initialize the ErrorScanner.

        Args:
            batch_size: Number of files to check in each batch (default: 30)
            verbose: Enable verbose logging (default: False)
            use_pylint: Enable slower pylint analysis (default: False)
        """
        self.batch_size = batch_size
        self.verbose = verbose
        self.use_pylint = use_pylint

        if verbose:
            logging.basicConfig(level=logging.DEBUG)
            logger.setLevel(logging.DEBUG)

    def scan_directory(self, root_path: str | Path) -> ScanResults:
        """
        Recursively scan a directory for all Python files and check for errors.

        Args:
            root_path: Root directory to scan

        Returns:
            ScanResults containing all errors found
        """

        root = Path(root_path)
        if not root.exists():
            raise FileNotFoundError(f"Path not found: {root_path}")

        if not root.is_dir():
            raise NotADirectoryError(f"Not a directory: {root_path}")

        start_time = time.time()

        # Find all Python files
        python_files = self._find_python_files(root)
        logger.info(f"Found {len(python_files)} Python files to scan")

        results = ScanResults(root_path=str(root))
        results.files_checked = len(python_files)

        if not python_files:
            logger.warning("No Python files found to scan")
            return results

        # Process in batches
        for i in range(0, len(python_files), self.batch_size):
            batch = python_files[i : i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(python_files) + self.batch_size - 1) // self.batch_size

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} files)")

            # Check this batch
            batch_errors = self._check_files_batch(batch)

            # Aggregate results
            for file_path, errors in batch_errors.items():
                if errors:
                    if file_path not in [e.file_path for e in results.errors]:
                        results.files_with_errors += 1

                    for error in errors:
                        results.add_error(error)

        results.scan_duration_seconds = time.time() - start_time

        return results

    def _find_python_files(self, root: Path) -> list[Path]:
        """
        Recursively find all Python files in a directory.

        Args:
            root: Root directory to search

        Returns:
            List of Python file paths
        """
        python_files = []

        # Skip common non-code directories
        skip_dirs = {
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
            ".pytest_cache",
            ".mypy_cache",
            "dist",
            "build",
            "*.egg-info",
        }

        for py_file in root.rglob("*.py"):
            # Check if any parent directory should be skipped
            if any(part in skip_dirs for part in py_file.parts):
                continue

            python_files.append(py_file)

        return sorted(python_files)

    def _check_files_batch(self, files: list[Path]) -> dict[str, list[CodeError]]:
        """
        Check a batch of files for errors using mypy, flake8, pylint, and ruff.

        Attempts to use multiple linters and type checkers:
        - mypy: type checking
        - flake8: PEP 8 style and logical errors
        - ruff: fast multi-rule linting
        - pylint: comprehensive code analysis

        Falls back to syntax checking if all are unavailable.

        Args:
            files: List of file paths to check

        Returns:
            Dict mapping file paths to lists of errors
        """
        batch_errors: dict[str, list[CodeError]] = {}

        # Ensure all files have an entry
        for file_path in files:
            batch_errors[str(file_path)] = []

        # Try mypy for type checking
        try:
            from mypy import api  # type: ignore[import]

            file_paths_str = [str(f) for f in files]

            # Run mypy
            result = api.run(file_paths_str)
            stdout, stderr, exit_code = result

            # Parse mypy output
            if stdout:
                for error in self._parse_mypy_output(stdout):
                    file_key = error.file_path
                    if file_key not in batch_errors:
                        batch_errors[file_key] = []
                    batch_errors[file_key].append(error)

            if self.verbose and stderr:
                logger.debug(f"mypy stderr: {stderr}")

        except ImportError:
            logger.debug("mypy not available, skipping type checking")

        # Try flake8 for linting
        try:
            for file_path in files:
                errors = self._parse_flake8_errors(str(file_path))
                if errors:
                    batch_errors[str(file_path)].extend(errors)

        except Exception as e:
            logger.debug(f"flake8 check failed: {e}")

        # Try ruff for fast linting
        try:
            for file_path in files:
                errors = self._parse_ruff_errors(str(file_path))
                if errors:
                    # Merge with existing errors, avoiding duplicates
                    for error in errors:
                        if error not in batch_errors[str(file_path)]:
                            batch_errors[str(file_path)].append(error)

        except Exception as e:
            logger.debug(f"ruff check failed: {e}")

        # Try pylint for comprehensive analysis
        if self.use_pylint:
            try:
                for file_path in files:
                    errors = self._parse_pylint_errors(str(file_path))
                    if errors:
                        # Merge with existing errors, avoiding duplicates
                        for error in errors:
                            if error not in batch_errors[str(file_path)]:
                                batch_errors[str(file_path)].append(error)

            except Exception as e:
                logger.debug(f"pylint check failed: {e}")

        # Final fallback: syntax checking for any unchecked files
        for file_path in files:
            if not batch_errors[str(file_path)]:
                syntax_errors = self._check_file_syntax(file_path)
                if syntax_errors:
                    batch_errors[str(file_path)] = syntax_errors

        # Log results if verbose
        if self.verbose:
            for file_path in files:
                error_count = len(batch_errors[str(file_path)])
                logger.debug(f"Checked {file_path}: {error_count} errors")

        return batch_errors

    def _parse_mypy_output(self, output: str) -> list[CodeError]:
        """
        Parse mypy error output into CodeError objects.

        Mypy output format: file.py:line:column: error: message

        Args:
            output: Raw mypy output

        Returns:
            List of CodeError objects
        """
        errors = []

        for line in output.strip().split("\n"):
            if not line.strip():
                continue

            # Parse: path/file.py:123:45: error: message
            parts = line.split(":", 3)
            if len(parts) < 4:
                continue

            file_path = parts[0].strip()
            try:
                line_num = int(parts[1].strip())
                col_num = int(parts[2].strip())
            except ValueError:
                continue

            message_part = parts[3].strip()

            # Determine severity from message
            if "error:" in message_part:
                severity = ErrorSeverity.ERROR
                message = message_part.replace("error:", "").strip()
                error_type = "type_error"
            elif "warning:" in message_part:
                severity = ErrorSeverity.WARNING
                message = message_part.replace("warning:", "").strip()
                error_type = "type_warning"
            else:
                severity = ErrorSeverity.INFO
                message = message_part
                error_type = "note"

            errors.append(
                CodeError(
                    file_path=file_path,
                    line_number=line_num,
                    column=col_num,
                    message=message,
                    error_type=error_type,
                    severity=severity,
                )
            )

        return errors

    def _parse_flake8_errors(self, file_path: str) -> list[CodeError]:
        """
        Parse flake8 errors for a file.

        Args:
            file_path: Path to the file to check

        Returns:
            List of CodeError objects
        """
        errors = []

        try:
            import subprocess

            result = subprocess.run(
                ["flake8", file_path, "--max-line-length=120"],
                capture_output=True,
                text=True,
            )

            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if not line.strip():
                        continue

                    # Parse: file.py:line:column: code message
                    parts = line.split(":", 3)
                    if len(parts) < 4:
                        continue

                    try:
                        line_num = int(parts[1].strip())
                        col_num = int(parts[2].strip())
                    except ValueError:
                        continue

                    message_part = parts[3].strip()

                    # Extract error code (e.g., F401, E302)
                    code_match = message_part.split(" ", 1)
                    error_code = code_match[0] if code_match else "unknown"
                    message = code_match[1] if len(code_match) > 1 else message_part

                    # Map flake8 codes to severity
                    if error_code.startswith("E") or error_code.startswith("F"):
                        severity = ErrorSeverity.ERROR
                    elif error_code.startswith("W"):
                        severity = ErrorSeverity.WARNING
                    else:
                        severity = ErrorSeverity.INFO

                    errors.append(
                        CodeError(
                            file_path=file_path,
                            line_number=line_num,
                            column=col_num,
                            message=message,
                            error_type=f"flake8_{error_code}",
                            severity=severity,
                        )
                    )

        except (ImportError, FileNotFoundError):
            logger.debug("flake8 command not available")
        except Exception as e:
            logger.debug(f"Error parsing flake8 output: {e}")

        return errors

    def _parse_ruff_errors(self, file_path: str) -> list[CodeError]:
        """
        Parse ruff linting errors for a file.

        Args:
            file_path: Path to the file to check

        Returns:
            List of CodeError objects
        """
        errors = []

        try:
            import subprocess

            result = subprocess.run(
                ["ruff", "check", file_path, "--output-format=text"],
                capture_output=True,
                text=True,
            )

            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if not line.strip() or line.startswith("All checks passed"):
                        continue

                    # Parse: file.py:line:column: code message
                    parts = line.split(":", 3)
                    if len(parts) < 4:
                        continue

                    try:
                        line_num = int(parts[1].strip())
                        col_num = int(parts[2].strip())
                    except ValueError:
                        continue

                    message_part = parts[3].strip()

                    # Extract error code (e.g., F401, E302)
                    code_match = message_part.split(" ", 1)
                    error_code = code_match[0] if code_match else "unknown"
                    message = code_match[1] if len(code_match) > 1 else message_part

                    # Map ruff codes to severity
                    if error_code.startswith("E") or error_code.startswith("F"):
                        severity = ErrorSeverity.ERROR
                    elif error_code.startswith("W"):
                        severity = ErrorSeverity.WARNING
                    else:
                        severity = ErrorSeverity.INFO

                    errors.append(
                        CodeError(
                            file_path=file_path,
                            line_number=line_num,
                            column=col_num,
                            message=message,
                            error_type=f"ruff_{error_code}",
                            severity=severity,
                        )
                    )

        except (ImportError, FileNotFoundError):
            logger.debug("ruff command not available")
        except Exception as e:
            logger.debug(f"Error parsing ruff output: {e}")

        return errors

    def _parse_pylint_errors(self, file_path: str) -> list[CodeError]:
        """
        Parse pylint errors for a file.

        Args:
            file_path: Path to the file to check

        Returns:
            List of CodeError objects
        """
        errors = []

        try:
            import json
            import subprocess

            result = subprocess.run(
                [
                    "pylint",
                    file_path,
                    "--output-format=json",
                    "--disable=all",
                    "--enable=E,W,C0101,C0103,W0611,W0612",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.stdout:
                try:
                    messages = json.loads(result.stdout)
                    for msg in messages:
                        error_code = msg.get("symbol", "unknown")
                        line_num = msg.get("line", 0)
                        col_num = msg.get("column", 0)
                        message = msg.get("message", "")

                        # Map pylint codes to severity
                        if error_code.startswith("E") or error_code in [
                            "unused-import",
                            "undefined-variable",
                        ]:
                            severity = ErrorSeverity.ERROR
                        elif error_code.startswith("W"):
                            severity = ErrorSeverity.WARNING
                        else:
                            severity = ErrorSeverity.INFO

                        errors.append(
                            CodeError(
                                file_path=file_path,
                                line_number=line_num,
                                column=col_num,
                                message=message,
                                error_type=f"pylint_{error_code}",
                                severity=severity,
                            )
                        )
                except json.JSONDecodeError:
                    logger.debug("Failed to parse pylint JSON output")

        except (ImportError, FileNotFoundError):
            logger.debug("pylint command not available")
        except TimeoutExpired:
            logger.debug("pylint check timed out")
        except Exception as e:
            logger.debug(f"Error parsing pylint output: {e}")

        return errors

    def _check_file_syntax(self, file_path: Path) -> list[CodeError]:
        """
        Check a single file for syntax errors (fallback method).

        Args:
            file_path: Path to the file

        Returns:
            List of CodeError objects for syntax errors
        """
        errors = []

        try:
            with open(file_path, encoding="utf-8") as f:
                code = f.read()

            import ast

            ast.parse(code)

        except SyntaxError as e:
            errors.append(
                CodeError(
                    file_path=str(file_path),
                    line_number=e.lineno or 0,
                    column=e.offset or 0,
                    message=e.msg or "Syntax error",
                    error_type="syntax_error",
                    severity=ErrorSeverity.ERROR,
                    code=e.text or "",
                )
            )
        except UnicodeDecodeError as e:
            errors.append(
                CodeError(
                    file_path=str(file_path),
                    line_number=0,
                    column=0,
                    message=f"Unicode decode error: {e.reason}",
                    error_type="encoding_error",
                    severity=ErrorSeverity.ERROR,
                )
            )
        except Exception as e:
            errors.append(
                CodeError(
                    file_path=str(file_path),
                    line_number=0,
                    column=0,
                    message=f"Error checking file: {str(e)}",
                    error_type="check_error",
                    severity=ErrorSeverity.WARNING,
                )
            )

        return errors

    def generate_report(self, results: ScanResults, format: str = "text") -> str:
        """
        Generate a formatted report of scan results.

        Args:
            results: ScanResults from scan_directory()
            format: Output format ('text', 'json', 'html')

        Returns:
            Formatted report string
        """
        if format == "json":
            return self._format_json(results)
        elif format == "html":
            return self._format_html(results)
        else:
            return self._format_text(results)

    def _format_text(self, results: ScanResults) -> str:
        """Format results as human-readable text."""
        lines = []

        lines.append("=" * 80)
        lines.append("ERROR SCAN REPORT")
        lines.append("=" * 80)
        lines.append("")

        # Summary
        lines.append("SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Root Path:          {results.root_path}")
        lines.append(f"Files Scanned:      {results.files_checked}")
        lines.append(f"Files with Errors:  {results.files_with_errors}")
        lines.append(f"Total Errors:       {results.total_errors}")
        lines.append(f"Scan Duration:      {results.scan_duration_seconds:.2f}s")
        lines.append("")

        # Error breakdown
        if results.error_types:
            lines.append("ERRORS BY TYPE")
            lines.append("-" * 40)
            for error_type, count in sorted(results.error_types.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  {error_type:30} {count:5d}")
            lines.append("")

        if results.severity_counts:
            lines.append("ERRORS BY SEVERITY")
            lines.append("-" * 40)
            for severity in [
                ErrorSeverity.ERROR,
                ErrorSeverity.WARNING,
                ErrorSeverity.INFO,
            ]:
                count = results.severity_counts.get(severity, 0)
                if count > 0:
                    lines.append(f"  {severity.value.upper():30} {count:5d}")
            lines.append("")

        # Detailed errors
        if results.errors:
            lines.append("DETAILED ERRORS")
            lines.append("-" * 40)

            sorted_errors = results.sort_by_severity()

            current_file = None
            for error in sorted_errors:
                if error.file_path != current_file:
                    current_file = error.file_path
                    lines.append("")
                    lines.append(f"📄 {error.file_path}")

                severity_emoji = {
                    ErrorSeverity.ERROR: "❌",
                    ErrorSeverity.WARNING: "⚠️ ",
                    ErrorSeverity.INFO: "ℹ️ ",
                }

                lines.append(f"  {severity_emoji[error.severity]} Line {error.line_number}: {error.error_type}")
                lines.append(f"     {error.message}")
                if error.code:
                    lines.append(f"     Code: {error.code}")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    def _format_json(self, results: ScanResults) -> str:
        """Format results as JSON."""
        data = {
            "summary": {
                "root_path": results.root_path,
                "files_checked": results.files_checked,
                "files_with_errors": results.files_with_errors,
                "total_errors": results.total_errors,
                "scan_duration_seconds": results.scan_duration_seconds,
            },
            "error_types": results.error_types,
            "severity_counts": {k.value: v for k, v in results.severity_counts.items()},
            "errors": [
                {
                    "file": e.file_path,
                    "line": e.line_number,
                    "column": e.column,
                    "type": e.error_type,
                    "severity": e.severity.value,
                    "message": e.message,
                    "code": e.code,
                }
                for e in results.sort_by_file()
            ],
        }

        return json.dumps(data, indent=2)

    def _format_html(self, results: ScanResults) -> str:
        """Format results as HTML."""
        html_lines = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "  <title>Code Error Scan Report</title>",
            "  <style>",
            "    body { font-family: monospace; margin: 20px; }",
            "    .summary { background: #f0f0f0; padding: 15px; border-radius: 5px; margin-bottom: 20px; }",
            "    .error { border-left: 4px solid #d32f2f; padding: 10px; margin-bottom: 10px; }",
            "    .error.warning { border-left-color: #fbc02d; }",
            "    .error.info { border-left-color: #1976d2; }",
            "    .file-name { font-weight: bold; margin-top: 15px; }",
            "    .line-number { color: #666; }",
            "    .message { margin-top: 5px; }",
            "    table { border-collapse: collapse; width: 100%; margin-top: 10px; }",
            "    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "    th { background: #f5f5f5; }",
            "  </style>",
            "</head>",
            "<body>",
            "  <h1>Code Error Scan Report</h1>",
            "  <div class='summary'>",
            f"    <p><strong>Root Path:</strong> {results.root_path}</p>",
            f"    <p><strong>Files Scanned:</strong> {results.files_checked}</p>",
            f"    <p><strong>Files with Errors:</strong> {results.files_with_errors}</p>",
            f"    <p><strong>Total Errors:</strong> {results.total_errors}</p>",
            f"    <p><strong>Scan Duration:</strong> {results.scan_duration_seconds:.2f}s</p>",
            "  </div>",
        ]

        # Error breakdown table
        if results.error_types:
            html_lines.extend(
                [
                    "  <h2>Errors by Type</h2>",
                    "  <table>",
                    "    <tr><th>Type</th><th>Count</th></tr>",
                ]
            )

            for error_type, count in sorted(results.error_types.items(), key=lambda x: x[1], reverse=True):
                html_lines.append(f"    <tr><td>{error_type}</td><td>{count}</td></tr>")

            html_lines.append("  </table>")

        # Detailed errors
        if results.errors:
            html_lines.append("  <h2>Detailed Errors</h2>")

            current_file = None
            for error in results.sort_by_file():
                if error.file_path != current_file:
                    current_file = error.file_path
                    html_lines.append(f"  <div class='file-name'>📄 {error.file_path}</div>")

                severity_class = error.severity.value
                html_lines.append(f"  <div class='error {severity_class}'>")
                html_lines.append(
                    f"    <span class='line-number'>Line {error.line_number}:</span> "
                    f"<strong>{error.error_type}</strong>"
                )
                html_lines.append(f"    <div class='message'>{error.message}</div>")
                if error.code:
                    html_lines.append(f"    <pre>{error.code}</pre>")
                html_lines.append("  </div>")

        html_lines.extend(["</body>", "</html>"])

        return "\n".join(html_lines)


# CLI Interface
def main():
    """Command-line interface for error scanning."""
    import argparse

    parser = argparse.ArgumentParser(description="Comprehensive project error scanner for code-scalpel")
    parser.add_argument(
        "--path",
        type=str,
        default="src/",
        help="Root directory to scan (default: src/)",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json", "html"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file (if not specified, prints to stdout)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=30,
        help="Batch size for processing files (default: 30)",
    )
    parser.add_argument(
        "--pylint",
        action="store_true",
        help="Enable slower pylint analysis (slower but more thorough)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Create scanner and run
    scanner = ErrorScanner(batch_size=args.batch_size, verbose=args.verbose, use_pylint=args.pylint)

    print(f"Scanning {args.path}...", file=sys.stderr)
    start = time.time()
    results = scanner.scan_directory(args.path)
    elapsed = time.time() - start

    # Generate report
    report = scanner.generate_report(results, format=args.format)

    # Output
    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Report written to {args.output} (took {elapsed:.2f}s)", file=sys.stderr)
    else:
        print(report)

    # Exit with error code if errors found
    if results.total_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
