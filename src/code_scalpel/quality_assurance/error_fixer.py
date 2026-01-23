"""
ErrorFixer - Automatic code quality fixes for code-scalpel.

# [20251224_REFACTOR] Moved from code_scalpel/error_fixer.py to
# code_scalpel/quality_assurance/error_fixer.py as part of Issue #1
# in PROJECT_REORG_REFACTOR.md Phase 1.

Provides automated fixes for whitespace issues found by the ErrorScanner.

Key Features:
- Automatic whitespace cleanup (trailing spaces, blank line spaces)
- Dry-run mode to preview changes
- Batch processing
- Statistics on fixed errors

Usage (command-line):
    python error_fixer.py --path src/ --dry-run
    python error_fixer.py --path src/ --fix


"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class FixResult:
    """Result of a single fix operation."""

    file_path: str
    error_type: str
    line_number: int
    fixed: bool = False
    message: str = ""


@dataclass
class FixResults:
    """Results from fixing a batch of files."""

    root_path: str
    files_scanned: int = 0
    files_modified: int = 0
    total_fixed: int = 0
    fixes_by_type: dict[str, int] = field(default_factory=dict)
    results: list[FixResult] = field(default_factory=list)

    def add_result(self, result: FixResult):
        """Add a fix result."""
        self.results.append(result)
        if result.fixed:
            self.total_fixed += 1
            self.fixes_by_type[result.error_type] = self.fixes_by_type.get(result.error_type, 0) + 1


class ErrorFixer:
    """
    Automatic whitespace error fixer.

    Fixes whitespace issues identified by ErrorScanner:
    - W293: Blank line with whitespace
    - W291: Trailing whitespace
    """

    def __init__(self, verbose: bool = False):
        """Initialize the ErrorFixer."""
        self.verbose = verbose
        if verbose:
            logging.basicConfig(level=logging.DEBUG)
            logger.setLevel(logging.DEBUG)

    def fix_directory(self, root_path: str | Path, dry_run: bool = True) -> FixResults:
        """Fix errors in all Python files in a directory."""
        root = Path(root_path)
        if not root.exists():
            raise FileNotFoundError(f"Path not found: {root_path}")

        if not root.is_dir():
            raise NotADirectoryError(f"Not a directory: {root_path}")

        python_files = sorted(root.rglob("*.py"))

        skip_dirs = {
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
            ".pytest_cache",
        }

        python_files = [f for f in python_files if not any(part in skip_dirs for part in f.parts)]

        logger.info(f"Found {len(python_files)} Python files to fix")

        results = FixResults(root_path=str(root))
        results.files_scanned = len(python_files)

        for file_path in python_files:
            file_results = self.fix_file(file_path, dry_run=dry_run)
            if file_results:
                results.files_modified += 1
                for result in file_results:
                    results.add_result(result)

        return results

    def fix_file(self, file_path: Path | str, dry_run: bool = True) -> list[FixResult]:
        """Fix whitespace errors in a single file."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return []

        fix_results = []
        modified_lines = []

        for i, line in enumerate(lines):
            has_newline = line.endswith("\n")
            line_content = line.rstrip("\n")

            # W293: blank line with whitespace
            if line_content.strip() == "" and line_content != "":
                fix_results.append(
                    FixResult(
                        file_path=str(file_path),
                        error_type="W293",
                        line_number=i + 1,
                        fixed=True,
                        message="Removed whitespace from blank line",
                    )
                )
                modified_lines.append("\n" if has_newline else "")
                continue

            # W291: trailing whitespace
            if line_content != line_content.rstrip():
                fix_results.append(
                    FixResult(
                        file_path=str(file_path),
                        error_type="W291",
                        line_number=i + 1,
                        fixed=True,
                        message="Removed trailing whitespace",
                    )
                )
                line_content = line_content.rstrip()

            modified_lines.append(line_content + ("\n" if has_newline else ""))

        if fix_results and not dry_run:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(modified_lines)
                logger.info(f"Fixed {len(fix_results)} issues in {file_path}")
            except Exception as e:
                logger.error(f"Error writing {file_path}: {e}")
                return []

        return fix_results

    def generate_report(self, results: FixResults) -> str:
        """Generate a report of fixes."""
        lines = []

        lines.append("=" * 80)
        lines.append("WHITESPACE FIX REPORT")
        lines.append("=" * 80)
        lines.append("")

        lines.append("SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Root Path:          {results.root_path}")
        lines.append(f"Files Scanned:      {results.files_scanned}")
        lines.append(f"Files Modified:     {results.files_modified}")
        lines.append(f"Total Fixes:        {results.total_fixed}")
        lines.append("")

        if results.fixes_by_type:
            lines.append("FIXES BY TYPE")
            lines.append("-" * 40)
            for error_type, count in sorted(results.fixes_by_type.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  {error_type:20} {count:5d}")
            lines.append("")

        if results.results:
            file_counts = {}
            for result in results.results:
                if result.file_path not in file_counts:
                    file_counts[result.file_path] = 0
                file_counts[result.file_path] += 1

            lines.append("TOP FILES BY FIX COUNT")
            lines.append("-" * 40)
            for file_path, count in sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:15]:
                lines.append(f"  {count:3d}  {file_path}")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)


def main():
    """Command-line interface."""
    import argparse

    parser = argparse.ArgumentParser(description="Fix whitespace errors")
    parser.add_argument("--path", type=str, default="src/", help="Directory to fix")
    parser.add_argument("--fix", action="store_true", help="Apply fixes (default: dry-run only)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()
    dry_run = not args.fix

    fixer = ErrorFixer(verbose=args.verbose)
    mode = "DRY RUN (preview)" if dry_run else "FIX MODE (writing)"
    print(f"Running in {mode}...", file=sys.stderr)

    results = fixer.fix_directory(args.path, dry_run=dry_run)
    print(fixer.generate_report(results))

    if dry_run:
        print("This was a DRY RUN. Run with --fix to apply changes.", file=sys.stderr)


if __name__ == "__main__":
    main()
