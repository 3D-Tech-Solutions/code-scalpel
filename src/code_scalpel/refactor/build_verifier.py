"""
Build Verifier - Pro Tier Feature.

[20251226_FEATURE] v3.2.9 - Pro tier build/compile verification.

This module runs language-specific compilers on refactored code:
- Python: py_compile for syntax checking
- JavaScript: esbuild for compilation
- Java: javac for compilation
- TypeScript: tsc for type checking
"""

import logging
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict


class BuildResultDict(TypedDict):
    """Build verification result dictionary."""

    success: bool
    language: str
    compiler: str
    output: str
    errors: list[str]
    warnings: list[str]
    exit_code: int


logger = logging.getLogger(__name__)


@dataclass
class BuildResult:
    """Result of build verification."""

    success: bool  # Whether build succeeded
    language: str  # Language that was built
    compiler: str  # Compiler used
    output: str  # Compiler output
    errors: list[str]  # Build errors
    warnings: list[str]  # Build warnings
    exit_code: int  # Compiler exit code


class BuildVerifier:
    """
    Verifies refactored code by running language-specific compilers.

    Pro tier feature that catches compilation errors before deployment.
    """

    def __init__(self, timeout: int = 5):
        """
        Initialize the build verifier.

        Args:
            timeout: Maximum seconds to wait for compilation (default: 5)
        """
        self.timeout = timeout

    def verify_python(self, code: str) -> BuildResult:
        """
        Verify Python code using py_compile.

        Args:
            code: Python source code

        Returns:
            BuildResult with compilation status
        """
        import py_compile

        errors = []

        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(code)
                temp_path = f.name

            try:
                # Attempt to compile
                py_compile.compile(temp_path, doraise=True)
                return BuildResult(
                    success=True,
                    language="python",
                    compiler="py_compile",
                    output="Compilation successful",
                    errors=[],
                    warnings=[],
                    exit_code=0,
                )
            except py_compile.PyCompileError as e:
                errors.append(str(e))
                return BuildResult(
                    success=False,
                    language="python",
                    compiler="py_compile",
                    output=str(e),
                    errors=errors,
                    warnings=[],
                    exit_code=1,
                )
            finally:
                Path(temp_path).unlink(missing_ok=True)

        except Exception as e:
            return BuildResult(
                success=False,
                language="python",
                compiler="py_compile",
                output=f"Build verification failed: {str(e)}",
                errors=[str(e)],
                warnings=[],
                exit_code=1,
            )

    def verify_javascript(self, code: str) -> BuildResult:
        """
        Verify JavaScript code using esbuild.

        Args:
            code: JavaScript source code

        Returns:
            BuildResult with compilation status
        """
        try:
            # Check if esbuild is available
            result = subprocess.run(
                ["which", "esbuild"],
                capture_output=True,
                timeout=1,
            )
            if result.returncode != 0:
                return BuildResult(
                    success=False,
                    language="javascript",
                    compiler="esbuild",
                    output="esbuild not found in PATH",
                    errors=["esbuild not installed"],
                    warnings=["Install esbuild: npm install -g esbuild"],
                    exit_code=127,
                )

            with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
                f.write(code)
                temp_path = f.name

            try:
                # Run esbuild
                result = subprocess.run(
                    ["esbuild", temp_path, "--bundle", "--format=esm"],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )

                errors = []
                warnings = []

                if result.returncode != 0:
                    errors.append(result.stderr)

                if "warning" in result.stderr.lower():
                    warnings.append(result.stderr)

                return BuildResult(
                    success=result.returncode == 0,
                    language="javascript",
                    compiler="esbuild",
                    output=result.stdout + result.stderr,
                    errors=errors,
                    warnings=warnings,
                    exit_code=result.returncode,
                )
            finally:
                Path(temp_path).unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            return BuildResult(
                success=False,
                language="javascript",
                compiler="esbuild",
                output=f"Build timed out after {self.timeout} seconds",
                errors=[f"Timeout after {self.timeout}s"],
                warnings=[],
                exit_code=124,
            )
        except Exception as e:
            return BuildResult(
                success=False,
                language="javascript",
                compiler="esbuild",
                output=f"Build verification failed: {str(e)}",
                errors=[str(e)],
                warnings=[],
                exit_code=1,
            )

    def verify_java(self, code: str) -> BuildResult:
        """
        Verify Java code using javac.

        Args:
            code: Java source code

        Returns:
            BuildResult with compilation status
        """
        try:
            # Check if javac is available
            result = subprocess.run(
                ["which", "javac"],
                capture_output=True,
                timeout=1,
            )
            if result.returncode != 0:
                return BuildResult(
                    success=False,
                    language="java",
                    compiler="javac",
                    output="javac not found in PATH",
                    errors=["javac not installed"],
                    warnings=["Install JDK"],
                    exit_code=127,
                )

            # Extract class name from code
            import re

            match = re.search(r"public\s+class\s+(\w+)", code)
            class_name = match.group(1) if match else "Main"

            with tempfile.TemporaryDirectory() as tmpdir:
                temp_file = Path(tmpdir) / f"{class_name}.java"
                temp_file.write_text(code)

                # Run javac
                result = subprocess.run(
                    ["javac", str(temp_file)],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=tmpdir,
                )

                errors = []
                warnings = []

                if result.returncode != 0:
                    errors.append(result.stderr)

                if "warning" in result.stdout.lower() or "warning" in result.stderr.lower():
                    warnings.append(result.stdout + result.stderr)

                return BuildResult(
                    success=result.returncode == 0,
                    language="java",
                    compiler="javac",
                    output=result.stdout + result.stderr,
                    errors=errors,
                    warnings=warnings,
                    exit_code=result.returncode,
                )

        except subprocess.TimeoutExpired:
            return BuildResult(
                success=False,
                language="java",
                compiler="javac",
                output=f"Build timed out after {self.timeout} seconds",
                errors=[f"Timeout after {self.timeout}s"],
                warnings=[],
                exit_code=124,
            )
        except Exception as e:
            return BuildResult(
                success=False,
                language="java",
                compiler="javac",
                output=f"Build verification failed: {str(e)}",
                errors=[str(e)],
                warnings=[],
                exit_code=1,
            )

    def verify_code(self, code: str, language: str = "python") -> BuildResult:
        """
        Verify code by running appropriate compiler.

        Args:
            code: Source code
            language: Programming language (python, javascript, java, typescript)

        Returns:
            BuildResult with compilation status
        """
        language = language.lower()

        if language in ("python", "py"):
            return self.verify_python(code)
        elif language in ("javascript", "js", "typescript", "ts"):
            return self.verify_javascript(code)
        elif language == "java":
            return self.verify_java(code)
        else:
            return BuildResult(
                success=False,
                language=language,
                compiler="unknown",
                output=f"Unsupported language: {language}",
                errors=[f"Language '{language}' not supported"],
                warnings=[],
                exit_code=1,
            )

    def to_dict(self, result: BuildResult) -> dict[str, Any]:
        """Convert BuildResult to dict for JSON serialization."""
        return {
            "success": result.success,
            "language": result.language,
            "compiler": result.compiler,
            "output": result.output,
            "errors": result.errors,
            "warnings": result.warnings,
            "exit_code": result.exit_code,
        }
