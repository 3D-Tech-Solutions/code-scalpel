"""
Type Checker - Pro Tier Feature.

[20251226_FEATURE] v3.2.9 - Pro tier type-check integration.

This module runs type checkers on refactored code:
- Python: mypy for type checking
- TypeScript: tsc for type checking
- Java: javac with type checking enabled
"""

import logging
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict


class TypeCheckResultDict(TypedDict, total=False):
    """Type checking result dictionary."""

    success: bool
    language: str
    checker: str
    output: str
    errors: list[str]
    warnings: list[str]
    exit_code: int
    type_coverage: float
    inferred_types: dict[str, str]


logger = logging.getLogger(__name__)


@dataclass
class TypeCheckResult:
    """Result of type checking."""

    success: bool  # Whether type check passed
    language: str  # Language that was checked
    checker: str  # Type checker used
    output: str  # Type checker output
    errors: list[str]  # Type errors
    warnings: list[str]  # Type warnings
    exit_code: int  # Type checker exit code


class TypeChecker:
    """
    Runs type checkers on refactored code.

    Pro tier feature that catches type errors before deployment.
    """

    def __init__(self, timeout: int = 5):
        """
        Initialize the type checker.

        Args:
            timeout: Maximum seconds to wait for type checking (default: 5)
        """
        self.timeout = timeout

    def check_python_mypy(self, code: str) -> TypeCheckResult:
        """
        Type check Python code using mypy.

        Args:
            code: Python source code

        Returns:
            TypeCheckResult with type checking status
        """
        try:
            # Check if mypy is available
            result = subprocess.run(
                ["which", "mypy"],
                capture_output=True,
                timeout=1,
            )
            if result.returncode != 0:
                return TypeCheckResult(
                    success=False,
                    language="python",
                    checker="mypy",
                    output="mypy not found in PATH",
                    errors=["mypy not installed"],
                    warnings=["Install mypy: pip install mypy"],
                    exit_code=127,
                )

            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(code)
                temp_path = f.name

            try:
                # Run mypy
                result = subprocess.run(
                    ["mypy", "--no-error-summary", temp_path],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )

                errors = []
                warnings = []

                # mypy returns 0 for success, 1 for type errors
                if result.returncode != 0:
                    # Parse output for errors
                    for line in result.stdout.splitlines():
                        if "error:" in line.lower():
                            errors.append(line)
                        elif "note:" in line.lower() or "warning:" in line.lower():
                            warnings.append(line)

                return TypeCheckResult(
                    success=result.returncode == 0,
                    language="python",
                    checker="mypy",
                    output=result.stdout,
                    errors=(errors if errors else ([result.stdout] if result.returncode != 0 else [])),
                    warnings=warnings,
                    exit_code=result.returncode,
                )
            finally:
                Path(temp_path).unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            return TypeCheckResult(
                success=False,
                language="python",
                checker="mypy",
                output=f"Type check timed out after {self.timeout} seconds",
                errors=[f"Timeout after {self.timeout}s"],
                warnings=[],
                exit_code=124,
            )
        except Exception as e:
            return TypeCheckResult(
                success=False,
                language="python",
                checker="mypy",
                output=f"Type check failed: {str(e)}",
                errors=[str(e)],
                warnings=[],
                exit_code=1,
            )

    def check_typescript(self, code: str) -> TypeCheckResult:
        """
        Type check TypeScript code using tsc.

        Args:
            code: TypeScript source code

        Returns:
            TypeCheckResult with type checking status
        """
        try:
            # Check if tsc is available
            result = subprocess.run(
                ["which", "tsc"],
                capture_output=True,
                timeout=1,
            )
            if result.returncode != 0:
                return TypeCheckResult(
                    success=False,
                    language="typescript",
                    checker="tsc",
                    output="tsc not found in PATH",
                    errors=["tsc not installed"],
                    warnings=["Install TypeScript: npm install -g typescript"],
                    exit_code=127,
                )

            with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as f:
                f.write(code)
                temp_path = f.name

            try:
                # Run tsc with --noEmit to only check types
                result = subprocess.run(
                    ["tsc", "--noEmit", "--strict", temp_path],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )

                errors = []
                warnings = []

                if result.returncode != 0:
                    # Parse output for errors
                    for line in result.stdout.splitlines():
                        if "error TS" in line:
                            errors.append(line)

                return TypeCheckResult(
                    success=result.returncode == 0,
                    language="typescript",
                    checker="tsc",
                    output=result.stdout + result.stderr,
                    errors=(errors if errors else ([result.stdout] if result.returncode != 0 else [])),
                    warnings=warnings,
                    exit_code=result.returncode,
                )
            finally:
                Path(temp_path).unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            return TypeCheckResult(
                success=False,
                language="typescript",
                checker="tsc",
                output=f"Type check timed out after {self.timeout} seconds",
                errors=[f"Timeout after {self.timeout}s"],
                warnings=[],
                exit_code=124,
            )
        except Exception as e:
            return TypeCheckResult(
                success=False,
                language="typescript",
                checker="tsc",
                output=f"Type check failed: {str(e)}",
                errors=[str(e)],
                warnings=[],
                exit_code=1,
            )

    def check_code(self, code: str, language: str = "python") -> TypeCheckResult:
        """
        Type check code using appropriate checker.

        Args:
            code: Source code
            language: Programming language (python, typescript, java)

        Returns:
            TypeCheckResult with type checking status
        """
        language = language.lower()

        if language in ("python", "py"):
            return self.check_python_mypy(code)
        elif language in ("typescript", "ts"):
            return self.check_typescript(code)
        elif language == "java":
            # Java type checking is done by javac (handled by BuildVerifier)
            return TypeCheckResult(
                success=True,
                language="java",
                checker="javac",
                output="Java type checking handled by build verification",
                errors=[],
                warnings=[],
                exit_code=0,
            )
        else:
            return TypeCheckResult(
                success=False,
                language=language,
                checker="unknown",
                output=f"Unsupported language: {language}",
                errors=[f"Language '{language}' not supported"],
                warnings=[],
                exit_code=1,
            )

    def to_dict(self, result: TypeCheckResult) -> TypeCheckResultDict:
        """Convert TypeCheckResult to dict for JSON serialization."""
        return {
            "success": result.success,
            "language": result.language,
            "checker": result.checker,
            "output": result.output,
            "errors": result.errors,
            "warnings": result.warnings,
            "exit_code": result.exit_code,
        }
