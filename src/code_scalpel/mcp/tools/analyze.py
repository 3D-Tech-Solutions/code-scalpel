"""Analyze MCP tool registrations."""

from __future__ import annotations

import asyncio
import difflib
import os
import time
from importlib import import_module
from pathlib import Path

from code_scalpel.mcp.helpers.analyze_helpers import _analyze_code_sync
from code_scalpel.mcp.contract import ToolResponseEnvelope, ToolError, make_envelope
from code_scalpel import __version__ as _pkg_version
from code_scalpel.mcp.protocol import _get_current_tier
from code_scalpel.mcp.v1_1_kernel_adapter import get_adapter

# Avoid static import resolution issues in some type checkers
mcp = import_module("code_scalpel.mcp.protocol").mcp


def _get_project_files(project_root: str | Path, max_files: int = 1000) -> list[str]:
    """Get list of all files in project for fuzzy matching suggestions.

    Args:
        project_root: Root directory of the project
        max_files: Maximum number of files to collect

    Returns:
        List of relative file paths from project root
    """
    project_root = Path(project_root).resolve()
    files = []

    def _collect_files(directory: Path, current_depth: int) -> None:
        """Recursive file collector with depth limit."""
        if current_depth > 5:  # Limit depth to avoid excessive scanning
            return

        try:
            for item in directory.iterdir():
                if item.name.startswith("."):
                    continue

                if item.is_dir():
                    # Skip common exclude directories
                    if item.name not in {
                        "node_modules",
                        "__pycache__",
                        ".git",
                        ".venv",
                        "venv",
                        ".pytest_cache",
                        ".mypy_cache",
                        ".ruff_cache",
                        "build",
                        "dist",
                    }:
                        _collect_files(item, current_depth + 1)
                elif item.is_file():
                    try:
                        relative_path = str(item.relative_to(project_root))
                        files.append(relative_path)
                        if len(files) >= max_files:
                            return
                    except ValueError:
                        # Skip files outside project root
                        continue

        except (PermissionError, OSError):
            # Skip directories we can't access
            pass

    _collect_files(project_root, 0)
    return files


def _find_similar_file_paths(
    invalid_path: str, project_files: list[str], max_suggestions: int = 3
) -> dict:
    """Find similar file paths using fuzzy string matching.

    Args:
        invalid_path: The invalid file path that was requested
        project_files: List of all valid file paths in the project
        max_suggestions: Maximum number of suggestions to return

    Returns:
        Dict with suggestion, confidence, message, and alternatives
    """
    if not project_files:
        return {}

    # Get filename from path for better matching
    invalid_filename = Path(invalid_path).name

    # Find closest matches using difflib
    matches = difflib.get_close_matches(
        invalid_path, project_files, n=max_suggestions * 2, cutoff=0.4
    )

    # Also try matching just the filename
    filename_matches = difflib.get_close_matches(
        invalid_filename,
        [Path(f).name for f in project_files],
        n=max_suggestions * 2,
        cutoff=0.6,
    )

    # Convert filename matches back to full paths
    filename_to_full = {Path(f).name: f for f in project_files}
    full_filename_matches = [
        filename_to_full[name] for name in filename_matches if name in filename_to_full
    ]

    # Combine and deduplicate matches
    all_matches = list(set(matches + full_filename_matches))

    if not all_matches:
        return {}

    # Calculate confidence scores (higher for better matches)
    scored_matches = []
    for match in all_matches[:max_suggestions]:
        # Use difflib ratio as confidence score
        confidence = difflib.SequenceMatcher(None, invalid_path, match).ratio()
        scored_matches.append((match, confidence))

    # Sort by confidence (highest first)
    scored_matches.sort(key=lambda x: x[1], reverse=True)

    best_match, best_confidence = scored_matches[0]
    alternatives = [match for match, _ in scored_matches[1:max_suggestions]]

    return {
        "suggestion": best_match,
        "confidence": round(best_confidence, 2),
        "message": f"Did you mean '{best_match}'?",
        "alternatives": alternatives,
    }


@mcp.tool(
    description="Parse and extract code structure (functions, classes, imports) from source text or a file."
)
async def analyze_code(
    code: str | None = None, language: str = "auto", file_path: str | None = None
) -> ToolResponseEnvelope:
    """Analyze source code structure with AST parsing and metrics.

    Provide either 'code' (string) or 'file_path' (to read from file). Language is
    auto-detected if set to 'auto' (default). Use this tool to understand high-level
    architecture before attempting to edit, preventing hallucinated methods or classes.

    **Tier Behavior:**
    - Community: Basic AST parsing, functions/classes, complexity metrics, imports
    - Pro: All Community + cognitive complexity, code smells, Halstead metrics, duplicate detection
    - Enterprise: All Pro + custom rules, compliance checks, organization patterns, technical debt

    **Tier Capabilities:**
    - Community: Basic metrics only (max_file_size_mb=1)
    - Pro: All Community + advanced metrics and smells (max_file_size_mb=10)
    - Enterprise: All Pro + custom rules, compliance checks (max_file_size_mb=100)

    **Args:**
        code (str, optional): Source code to analyze. Either code or file_path required.
        language (str): Programming language for analysis. Default: "auto" (auto-detect).
                       Supported: python, javascript, typescript, java, c, cpp, csharp, go
        file_path (str, optional): Path to file to analyze. Either code or file_path required.

    **Returns:**
        ToolResponseEnvelope with AnalysisResult containing:
        - success (bool): True if analysis completed successfully
        - functions (list[str]): Function names found
        - classes (list[str]): Class names found
        - imports (list[str]): Import statements
        - complexity (int): Cyclomatic complexity estimate
        - lines_of_code (int): Total lines of code
        - function_details (list[dict]): Function info with line numbers, async status
        - class_details (list[dict]): Class info with line numbers, methods
        - issues (list[dict]): Issues found during analysis
        - cognitive_complexity (int): Cognitive complexity score (Pro/Enterprise, 0 if Community)
        - code_smells (list[dict]): Detected code smells (Pro/Enterprise, empty if Community)
        - halstead_metrics (dict, optional): Halstead complexity metrics (Pro/Enterprise, None if not computed)
        - duplicate_code_blocks (list[dict]): Detected duplicate code blocks (Pro/Enterprise)
        - dependency_graph (dict): Function call adjacency map (Pro/Enterprise)
        - naming_issues (list[dict]): Naming convention issues (Enterprise)
        - compliance_issues (list[dict]): Compliance findings (Enterprise)
        - custom_rule_violations (list[dict]): Custom rule matches (Enterprise)
        - organization_patterns (list[dict]): Detected architectural patterns (Enterprise)
        - frameworks (list[str]): Detected frameworks (Pro/Enterprise)
        - dead_code_hints (list[dict]): Dead code candidates (Pro/Enterprise)
        - decorator_summary (dict): Decorator/annotation summary (Pro/Enterprise)
        - type_summary (dict): Type annotation summary (Pro/Enterprise)
        - architecture_patterns (list[str]): Architecture/service-pattern hints (Enterprise)
        - technical_debt (dict): Technical debt scoring summary (Enterprise)
        - api_surface (dict): API surface summary (Enterprise)
        - prioritized (bool): Whether outputs were priority-ordered (Enterprise)
        - complexity_trends (dict): Historical complexity trend summary (Enterprise)
        - language_detected (str): Language that was actually analyzed
        - tier_applied (str): Tier applied for feature gating
        - error_location (dict, optional): Line/column of syntax error if applicable
        - suggested_fix (str, optional): Suggested fix for syntax error when applicable
        - sanitization_report (dict, optional): Parsing sanitization details
        - parser_warnings (list[str]): Parser warnings (e.g., sanitization notices)
        - error (str): Error message if analysis failed (invalid code, file not found, etc.)
        - tier_applied (str): Tier used for analysis
        - duration_ms (int): Analysis duration in milliseconds
    """
    started = time.perf_counter()
    try:
        adapter = get_adapter()

        # 1. Validate input: either code or file_path must be provided
        if code is None and file_path is None:
            raise ValueError("Either 'code' or 'file_path' must be provided")

        # If code is not provided, read from file_path
        if code is None and file_path is not None:
            # Get tier for limits
            tier = _get_current_tier()
            from code_scalpel.mcp.helpers.analyze_helpers import get_tool_capabilities

            capabilities = get_tool_capabilities("analyze_code", tier)
            limit_mb = capabilities.get("limits", {}).get("max_file_size_mb")

            # Check file exists
            if not os.path.isfile(file_path):
                from code_scalpel.mcp.helpers.session import _get_project_root

                project_root = _get_project_root()
                if project_root:
                    try:
                        project_files = _get_project_files(project_root, max_files=500)
                        oracle_suggestion = _find_similar_file_paths(
                            file_path, project_files
                        )
                        if oracle_suggestion:
                            error_msg = f"File not found: {file_path}"
                            error_obj = ToolError(
                                error=error_msg,
                                error_code="not_found",
                                error_details={"oracle_suggestion": oracle_suggestion},
                            )
                            duration_ms = int((time.perf_counter() - started) * 1000)
                            tier = _get_current_tier()
                            return make_envelope(
                                data=None,
                                tool_id="analyze_code",
                                tool_version=_pkg_version,
                                tier=tier,
                                duration_ms=duration_ms,
                                error=error_obj,
                            )
                    except Exception:
                        # If Oracle pipeline fails, fall back to simple error
                        pass

                # Fallback to simple error if Oracle pipeline unavailable
                raise ValueError(f"File not found: {file_path}")

            # Check file size before reading
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if limit_mb is not None and file_size_mb > limit_mb:
                raise ValueError(
                    f"File size {file_size_mb:.2f} MB exceeds limit of {limit_mb} MB for {tier} tier"
                )

            # Read the file
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()

        try:
            ctx = adapter.create_source_context(
                code=code, file_path=file_path, language=language
            )
            is_valid, error_obj, suggestions = adapter.validate_input(ctx)

            if not is_valid and error_obj:
                # Return error response with self-correction suggestions
                duration_ms = int((time.perf_counter() - started) * 1000)
                tier = _get_current_tier()
                # Enhance error with suggestions
                error_obj.error_details = error_obj.error_details or {}
                error_obj.error_details["suggestions"] = suggestions
                return make_envelope(
                    data=None,
                    tool_id="analyze_code",
                    tool_version=_pkg_version,
                    tier=tier,
                    duration_ms=duration_ms,
                    error=error_obj,
                )
        except ValueError:
            # Validation setup error
            pass  # Continue with legacy code path

        result = await asyncio.to_thread(
            _analyze_code_sync, code or "", language, file_path
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        return make_envelope(
            data=result,
            tool_id="analyze_code",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
        )
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        tier = _get_current_tier()
        error_obj = ToolError(error=str(exc), error_code="internal_error")
        return make_envelope(
            data=None,
            tool_id="analyze_code",
            tool_version=_pkg_version,
            tier=tier,
            duration_ms=duration_ms,
            error=error_obj,
        )


__all__ = ["analyze_code"]
