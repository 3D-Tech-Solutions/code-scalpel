"""Helper implementations for context and discovery tools."""

from __future__ import annotations

import ast
import asyncio
import logging
import os
import re
from importlib import import_module
from pathlib import Path
from typing import Any, cast

from mcp.server.fastmcp import Context

from code_scalpel.licensing import get_current_tier
from code_scalpel.licensing.features import get_tool_capabilities, has_capability
from code_scalpel.parsing.unified_parser import (
    ParsingConfig,
    ParsingError,
    parse_python_code,
)
from code_scalpel.utilities.source_sanitizer import sanitize_python_source

_analyze_code_sync = import_module("code_scalpel.mcp.helpers.analyze_helpers")._analyze_code_sync
parse_file_cached = import_module("code_scalpel.mcp.helpers.ast_helpers").parse_file_cached
_core_models = import_module("code_scalpel.mcp.models.core")

ClassInfo = _core_models.ClassInfo
CrawlClassInfo = _core_models.CrawlClassInfo
CrawlFileResult = _core_models.CrawlFileResult
CrawlFunctionInfo = _core_models.CrawlFunctionInfo
CrawlSummary = _core_models.CrawlSummary
FileContextResult = _core_models.FileContextResult
FunctionInfo = _core_models.FunctionInfo
ProjectCrawlResult = _core_models.ProjectCrawlResult
SymbolReference = _core_models.SymbolReference
SymbolReferencesResult = _core_models.SymbolReferencesResult

resolve_path = import_module("code_scalpel.mcp.path_resolver").resolve_path

logger = logging.getLogger("code_scalpel.mcp.context")

__all__ = [
    "_crawl_project_discovery",
    "_crawl_project_sync",
    "crawl_project",
    "_get_file_context_sync",
    "get_file_context",
    "_get_symbol_references_sync",
    "get_symbol_references",
]


# [20260116_SECURITY] Redact secrets/PII before any analysis.
_ENV_VALUE_PATTERN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*\s*=\s*)(.+)\s*$")
_EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_AWS_KEY_PATTERN = re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")
_SECRET_QUOTED_PATTERN = re.compile(
    r"(?i)(\b(?:api[_-]?key|secret|token|password|passwd|access[_-]?key)\b)(\s*[:=]\s*)(['\"])(.*?)\3"
)
_SECRET_UNQUOTED_PATTERN = re.compile(
    r"(?i)(\b(?:api[_-]?key|secret|token|password|passwd|access[_-]?key)\b)(\s*[:=]\s*)([^\s#]+)"
)


def _is_env_file(path: Path) -> bool:
    """Check whether a file is an environment file that should be redacted."""
    name = path.name.lower()
    return name == ".env" or name.startswith(".env.")


def _redact_sensitive_content(path: Path, content: str) -> tuple[str, bool, bool, list[str]]:
    """Redact secrets/PII before analysis.

    Returns:
        Tuple of (redacted_content, pii_redacted, secrets_masked, summary)
    """
    redacted = content
    pii_redacted = False
    secrets_masked = False
    summary: list[str] = []

    if _is_env_file(path):
        masked_lines: list[str] = []
        for line in redacted.splitlines():
            match = _ENV_VALUE_PATTERN.match(line)
            if match:
                masked_lines.append(f"{match.group(1)}***REDACTED***")
                secrets_masked = True
            else:
                masked_lines.append(line)
        redacted = "\n".join(masked_lines)
        if secrets_masked:
            summary.append("Masked env values")

    redacted, aws_count = _AWS_KEY_PATTERN.subn("AKIA****************", redacted)
    if aws_count:
        secrets_masked = True
        summary.append("Masked AWS access key")

    def _mask_quoted(match: re.Match[str]) -> str:
        return f"{match.group(1)}{match.group(2)}{match.group(3)}***REDACTED***{match.group(3)}"

    redacted, quoted_count = _SECRET_QUOTED_PATTERN.subn(_mask_quoted, redacted)
    if quoted_count:
        secrets_masked = True
        summary.append("Masked secret assignment")

    redacted, unquoted_count = _SECRET_UNQUOTED_PATTERN.subn(
        lambda m: f"{m.group(1)}{m.group(2)}***REDACTED***", redacted
    )
    if unquoted_count:
        secrets_masked = True
        summary.append("Masked secret assignment")

    redacted, email_count = _EMAIL_PATTERN.subn("[REDACTED_EMAIL]", redacted)
    if email_count:
        pii_redacted = True
        summary.append("Redacted email")

    return redacted, pii_redacted, secrets_masked, summary


def _crawl_project_discovery(
    root_path: str,
    exclude_dirs: list[str] | None = None,
    *,
    max_files: int | None = None,
    max_depth: int | None = None,
    respect_gitignore: bool = True,
) -> ProjectCrawlResult:
    """
    Discovery-only crawl for Community tier.

    Provides file inventory and structure without deep analysis:
    - Lists Python files and their paths
    - Identifies entrypoint patterns (main blocks, CLI commands)
    - Basic statistics (file count, directory structure)
    - NO complexity analysis
    - NO function/class details
    - NO file contents

    [20251223_FEATURE] v3.2.8 - Community tier discovery crawl.
    """
    import os
    import re
    from datetime import datetime
    from fnmatch import fnmatch

    try:
        root = Path(root_path)
        if not root.exists():
            raise FileNotFoundError(f"Project root not found: {root_path}")

        # Default excludes
        default_excludes = {
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
            ".pytest_cache",
            ".mypy_cache",
            "dist",
            "build",
            ".tox",
            "htmlcov",
            ".eggs",
            "*.egg-info",
        }
        if exclude_dirs:
            default_excludes.update(exclude_dirs)

        gitignore_patterns: list[str] = []
        if respect_gitignore:
            gitignore_file = root / ".gitignore"
            if gitignore_file.exists() and gitignore_file.is_file():
                for raw in gitignore_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.startswith("!"):
                        # Negation patterns are intentionally ignored in this minimal implementation.
                        continue
                    gitignore_patterns.append(line)

        def _gitignore_match(rel_posix_path: str, pattern: str, *, is_dir: bool) -> bool:
            if pattern.endswith("/"):
                if not is_dir:
                    return False
                pattern = pattern[:-1]
            if "/" in pattern:
                return fnmatch(rel_posix_path, pattern)
            return fnmatch(Path(rel_posix_path).name, pattern)

        def _is_gitignored(rel_path: Path, *, is_dir: bool) -> bool:
            if not gitignore_patterns:
                return False
            rel_posix = rel_path.as_posix().lstrip("./")
            return any(_gitignore_match(rel_posix, pat, is_dir=is_dir) for pat in gitignore_patterns)

        python_files: list[CrawlFileResult] = []
        entrypoints: list[str] = []
        python_file_count = 0
        ext_counts: dict[str, int] = {}
        framework_hints: set[str] = set()
        reached_limit = False

        # Walk the directory tree
        for dirpath, dirnames, filenames in os.walk(root):
            rel_dir = Path(dirpath).relative_to(root)
            depth = len(rel_dir.parts)
            if max_depth is not None and depth >= max_depth:
                dirnames[:] = []
            else:
                filtered_dirnames: list[str] = []
                for d in dirnames:
                    if d in default_excludes:
                        continue
                    rel_child = rel_dir / d
                    if _is_gitignored(rel_child, is_dir=True):
                        continue
                    filtered_dirnames.append(d)
                dirnames[:] = filtered_dirnames

            for filename in filenames:
                suffix = Path(filename).suffix.lower() or "(no_ext)"
                ext_counts[suffix] = ext_counts.get(suffix, 0) + 1
                rel_file = rel_dir / filename
                if _is_gitignored(rel_file, is_dir=False):
                    continue

                if filename.endswith(".py"):
                    if max_files is not None and python_file_count >= max_files:
                        reached_limit = True
                        dirnames[:] = []
                        break
                    python_file_count += 1
                    file_path = Path(dirpath) / filename
                    rel_path = str(file_path.relative_to(root))

                    # Check for entrypoint patterns without parsing
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        # [20251230_FIX][crawl] Detect common web/CLI entrypoints in discovery mode.
                        # Previously we only matched Flask '@app.route', missing patterns like '@app.get'.
                        route_decorator = re.search(
                            r"@\w+\.(route|get|post|put|delete|patch)\s*\(",
                            content,
                        )
                        is_entrypoint = (
                            'if __name__ == "__main__"' in content
                            or "if __name__ == '__main__'" in content
                            or "@click.command" in content
                            or bool(route_decorator)
                            or "def main(" in content
                        )

                        if "flask" in content or "@app.route" in content:
                            framework_hints.add("flask")
                        if "django" in content:
                            framework_hints.add("django")
                        if "fastapi" in content:
                            framework_hints.add("fastapi")

                        if is_entrypoint:
                            entrypoints.append(rel_path)

                        # Create minimal file result (discovery mode)
                        python_files.append(
                            CrawlFileResult(
                                path=rel_path,
                                status="success",
                                lines_of_code=len(content.splitlines()),
                                functions=[],
                                classes=[],
                                imports=[],
                                complexity_warnings=[],
                                error=None,
                            )
                        )
                    except Exception as e:
                        python_files.append(
                            CrawlFileResult(
                                path=rel_path,
                                status="error",
                                lines_of_code=0,
                                error=f"Could not read file: {str(e)}",
                            )
                        )

            if reached_limit:
                break

        # Build discovery report
        languages = ", ".join(
            f"{ext}={count}" for ext, count in sorted(ext_counts.items(), key=lambda kv: (-kv[1], kv[0]))
        )
        limit_note = "" if not reached_limit else "(limit reached)"
        report = f"""# Project Discovery Report

    ## Summary
    - Python files discovered: {python_file_count} {limit_note}
    - Entrypoints detected: {len(entrypoints)}
    - File extensions observed: {languages if languages else '(none)'}

    ## Entrypoints
    {chr(10).join(f'- {ep}' for ep in entrypoints) if entrypoints else '(none detected)'}

    ## Files
    {chr(10).join(f'- {f.path}' for f in python_files[:50])}
    {'...' if len(python_files) > 50 else ''}
    """

        summary = CrawlSummary(
            total_files=python_file_count,
            successful_files=len([f for f in python_files if f.status == "success"]),
            failed_files=len([f for f in python_files if f.status == "error"]),
            total_lines_of_code=sum(f.lines_of_code for f in python_files),
            total_functions=0,  # Not analyzed in discovery mode
            total_classes=0,  # Not analyzed in discovery mode
            complexity_warnings=0,  # Not analyzed in discovery mode
        )

        # Map extensions to language names for breakdown (best-effort)
        ext_lang_map = {
            ".py": "python",
            ".pyw": "python",
            ".js": "javascript",
            ".mjs": "javascript",
            ".cjs": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
        }
        language_breakdown: dict[str, int] = {}
        for ext, count in ext_counts.items():
            lang = ext_lang_map.get(ext, ext.lstrip("."))
            language_breakdown[lang] = language_breakdown.get(lang, 0) + count

        return ProjectCrawlResult(
            success=True,
            root_path=str(root),
            timestamp=datetime.now().isoformat(),
            summary=summary,
            files=python_files,
            errors=[],
            markdown_report=report,
            language_breakdown=language_breakdown or None,
            cache_hits=None,
            compliance_summary=None,
            framework_hints=sorted(framework_hints) if framework_hints else None,
            entrypoints=entrypoints or None,
        )

    except Exception as e:
        return ProjectCrawlResult(
            success=False,
            root_path=root_path,
            timestamp=datetime.now().isoformat(),
            summary=CrawlSummary(
                total_files=0,
                successful_files=0,
                failed_files=0,
                total_lines_of_code=0,
                total_functions=0,
                total_classes=0,
                complexity_warnings=0,
            ),
            error=f"Discovery crawl failed: {str(e)}",
        )


def _crawl_project_sync(
    root_path: str,
    exclude_dirs: list[str] | None = None,
    complexity_threshold: int = 10,
    include_report: bool = True,
    capabilities: set[str] | None = None,
    max_files: int | None = None,
    max_depth: int | None = None,
    respect_gitignore: bool = True,
    ctx: Context | None = None,
) -> ProjectCrawlResult:
    """Synchronous implementation of crawl_project."""
    try:
        import json

        from code_scalpel.analysis.project_crawler import ProjectCrawler

        # [20251229_FEATURE] Enterprise: Incremental indexing with cache
        cache_file: Path | None = None
        cached_results = {}
        cache_hits = 0
        incremental_mode = capabilities and "incremental_indexing" in capabilities

        if incremental_mode:
            cache_dir = Path(root_path) / ".scalpel_cache"
            cache_dir.mkdir(exist_ok=True)
            cache_file = cache_dir / "crawl_cache.json"

            # Ensure cache file exists even on first run
            if cache_file is not None and not cache_file.exists():
                try:
                    cache_file.touch()
                except Exception:
                    cache_file = None

            if cache_file is not None and cache_file.exists():
                try:
                    with open(cache_file, encoding="utf-8") as f:
                        cached_results = json.load(f)
                except Exception:
                    cached_results = {}

        # [20260101_BUGFIX] Enterprise: Load custom crawl rules from config file
        # Fixes test_crawl_project_enterprise_custom_rules_config
        include_extensions: tuple[str, ...] | None = None
        custom_exclude_dirs: list[str] = list(exclude_dirs) if exclude_dirs else []

        if capabilities and "custom_crawl_rules" in capabilities:
            config_file = Path(root_path) / ".code-scalpel" / "crawl_project.json"
            if config_file.exists() and config_file.is_file():
                try:
                    with open(config_file, encoding="utf-8") as f:
                        custom_config = json.load(f)
                    # Load include_extensions from config
                    if "include_extensions" in custom_config:
                        include_extensions = tuple(custom_config["include_extensions"])
                        # [20260102_DEBUG] Log config loading for debugging
                        logger.info(f"Loaded include_extensions from config: {include_extensions}")
                    # Merge exclude_dirs from config
                    if "exclude_dirs" in custom_config:
                        custom_exclude_dirs.extend(custom_config["exclude_dirs"])
                except Exception as e:
                    # [20260102_BUGFIX] Don't silently ignore errors - log them for debugging
                    logger.warning(f"Failed to load custom crawl config from {config_file}: {e}")

        crawler = ProjectCrawler(
            root_path,
            exclude_dirs=(frozenset(custom_exclude_dirs) if custom_exclude_dirs else None),
            complexity_threshold=complexity_threshold,
            max_files=max_files,
            max_depth=max_depth,
            respect_gitignore=respect_gitignore,
            include_extensions=include_extensions,
        )

        # [20251229_FEATURE] Enterprise: Optimization for 100k+ files
        use_optimization = capabilities and "100k_plus_files_support" in capabilities
        if use_optimization:
            logger.info(f"Enterprise mode: Optimizing for large-scale crawl in {root_path}")

        result = crawler.crawl()

        # [20251229_FEATURE] Enterprise: Filter unchanged files if incremental
        if incremental_mode:
            filtered_files = []
            for file_result in result.files_analyzed:
                # [20260116_BUGFIX] Cooperative cancellation for long-running crawls.
                if ctx:
                    if hasattr(ctx, "should_cancel") and ctx.should_cancel():  # type: ignore[attr-defined]
                        raise asyncio.CancelledError("Crawl cancelled by user")
                    if (
                        hasattr(ctx, "request_context")
                        and hasattr(ctx.request_context, "lifecycle_context")
                        and ctx.request_context.lifecycle_context.is_cancelled  # type: ignore[attr-defined]
                    ):
                        raise asyncio.CancelledError("Crawl cancelled by user")
                file_path = str(file_result.path)
                try:
                    mtime = Path(file_result.path).stat().st_mtime
                    cached_mtime = cached_results.get(file_path, {}).get("mtime")
                    if cached_mtime and mtime == cached_mtime:
                        # Use cached result
                        cache_hits += 1
                        continue
                    else:
                        # File changed or new
                        filtered_files.append(file_result)
                        cached_results[file_path] = {"mtime": mtime}
                except Exception:
                    filtered_files.append(file_result)

            # Update result with filtered files
            result.files_analyzed = filtered_files if filtered_files else result.files_analyzed

            # Save cache (always write when incremental is enabled)
            if cache_file:
                try:
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(cached_results, f)
                except Exception:
                    pass

        # Convert to Pydantic models
        def to_func_info(f) -> CrawlFunctionInfo:
            return CrawlFunctionInfo(
                name=f.qualified_name,
                lineno=f.lineno,
                complexity=f.complexity,
            )

        def to_class_info(c) -> CrawlClassInfo:
            return CrawlClassInfo(
                name=c.name,
                lineno=c.lineno,
                methods=[to_func_info(m) for m in c.methods],
                bases=c.bases,
            )

        def to_file_result(fr, root: str) -> CrawlFileResult:
            import os

            return CrawlFileResult(
                path=os.path.relpath(fr.path, root),
                status=fr.status,
                lines_of_code=fr.lines_of_code,
                functions=[to_func_info(f) for f in fr.functions],
                classes=[to_class_info(c) for c in fr.classes],
                imports=fr.imports,
                complexity_warnings=[to_func_info(f) for f in fr.complexity_warnings],
                error=fr.error,
            )

        summary = CrawlSummary(
            total_files=result.total_files,
            successful_files=len(result.files_analyzed),
            failed_files=len(result.files_with_errors),
            total_lines_of_code=result.total_lines_of_code,
            total_functions=result.total_functions,
            total_classes=result.total_classes,
            complexity_warnings=len(result.all_complexity_warnings),
        )

        files = []
        for f in result.files_analyzed:
            # [20260116_BUGFIX] Cooperative cancellation during result materialization.
            if ctx:
                if hasattr(ctx, "should_cancel") and ctx.should_cancel():  # type: ignore[attr-defined]
                    raise asyncio.CancelledError("Crawl cancelled by user")
                if (
                    hasattr(ctx, "request_context")
                    and hasattr(ctx.request_context, "lifecycle_context")
                    and ctx.request_context.lifecycle_context.is_cancelled  # type: ignore[attr-defined]
                ):
                    raise asyncio.CancelledError("Crawl cancelled by user")
            files.append(to_file_result(f, result.root_path))

        errors = []
        for f in result.files_with_errors:
            if ctx:
                if hasattr(ctx, "should_cancel") and ctx.should_cancel():  # type: ignore[attr-defined]
                    raise asyncio.CancelledError("Crawl cancelled by user")
                if (
                    hasattr(ctx, "request_context")
                    and hasattr(ctx.request_context, "lifecycle_context")
                    and ctx.request_context.lifecycle_context.is_cancelled  # type: ignore[attr-defined]
                ):
                    raise asyncio.CancelledError("Crawl cancelled by user")
            errors.append(to_file_result(f, result.root_path))

        # Language breakdown (best-effort by file extension)
        lang_counts: dict[str, int] = {}
        ext_lang_map = {
            ".py": "python",
            ".pyw": "python",
            ".js": "javascript",
            ".mjs": "javascript",
            ".cjs": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
        }
        for f in files:
            suffix = Path(f.path).suffix.lower()
            lang = ext_lang_map.get(suffix, suffix.lstrip("."))
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

        compliance_summary: dict[str, Any] | None = None
        if capabilities and "compliance_scanning" in capabilities:
            # Placeholder best-effort hook; actual compliance analysis is tool-side
            compliance_summary = {
                "status": "not_implemented",
                "files_checked": 0,
                "violations": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
            }

        report = ""
        if include_report:
            report = crawler.generate_report(result)

            # [20251225_FEATURE] Pro/Enterprise: framework and ecosystem signals.
            if capabilities and "framework_entrypoint_detection" in capabilities:
                framework_signals: set[str] = set()
                nextjs_routes: list[dict] = []
                django_routes: list[dict] = []
                flask_routes: list[dict] = []

                root = Path(root_path)

                # Next.js pages detection
                if capabilities and "nextjs_pages_detection" in capabilities:
                    # Check pages/ directory (Pages Router)
                    pages_dir = root / "pages"
                    if pages_dir.exists():
                        framework_signals.add("Next.js (Pages Router)")
                        for page_file in pages_dir.rglob("*.{js,jsx,ts,tsx}"):
                            rel_path = page_file.relative_to(pages_dir)
                            route = "/" + str(rel_path.with_suffix("")).replace("\\", "/")
                            if route.endswith("/index"):
                                route = route[:-6] or "/"
                            # Detect dynamic routes
                            if "[" in route:
                                route_type = "dynamic"
                            elif route.startswith("/api/"):
                                route_type = "api"
                            else:
                                route_type = "page"
                            nextjs_routes.append(
                                {
                                    "path": str(page_file.relative_to(root)),
                                    "route": route,
                                    "type": route_type,
                                }
                            )

                    # Check app/ directory (App Router)
                    app_dir = root / "app"
                    if app_dir.exists():
                        framework_signals.add("Next.js (App Router)")
                        for layout_or_page in app_dir.rglob("*.{js,jsx,ts,tsx}"):
                            filename = layout_or_page.name
                            if filename in (
                                "page.tsx",
                                "page.jsx",
                                "page.js",
                                "page.ts",
                                "layout.tsx",
                                "layout.jsx",
                                "layout.js",
                                "layout.ts",
                                "route.tsx",
                                "route.jsx",
                                "route.js",
                                "route.ts",
                            ):
                                rel_path = layout_or_page.parent.relative_to(app_dir)
                                route = "/" + str(rel_path).replace("\\", "/")
                                if route == "/.":
                                    route = "/"
                                route_type = "app-" + filename.split(".")[0]
                                nextjs_routes.append(
                                    {
                                        "path": str(layout_or_page.relative_to(root)),
                                        "route": route,
                                        "type": route_type,
                                    }
                                )

                # Django views detection
                if capabilities and "django_views_detection" in capabilities:
                    for fr in result.files_analyzed:
                        # Check for Django imports
                        has_django = any(imp.startswith("django") for imp in fr.imports)
                        if has_django:
                            framework_signals.add("Django")
                            # Parse urls.py files
                            if "urls.py" in fr.path:
                                try:
                                    with open(fr.path, encoding="utf-8") as f:
                                        content = f.read()
                                        # Simple regex to find path() calls
                                        patterns = re.findall(
                                            r'path\(["\']([^"\']+)["\'],\s*(\w+)',
                                            content,
                                        )
                                        for route, view in patterns:
                                            django_routes.append(
                                                {
                                                    "route": route,
                                                    "view": view,
                                                    "file": fr.path,
                                                }
                                            )
                                except Exception:
                                    pass

                # Flask routes detection
                if capabilities and "flask_routes_detection" in capabilities:
                    for fr in result.files_analyzed:
                        has_flask = any(imp.startswith("flask") for imp in fr.imports)
                        if has_flask:
                            framework_signals.add("Flask")
                            try:
                                with open(fr.path, encoding="utf-8") as f:
                                    content = f.read()
                                    # Parse @app.route decorators
                                    patterns = re.findall(
                                        r'@(?:app|blueprint)\.route\(["\']([^"\']+)["\'](?:,\s*methods=\[([^\]]+)\])?\)',
                                        content,
                                    )
                                    for route, methods in patterns:
                                        flask_routes.append(
                                            {
                                                "route": route,
                                                "methods": (
                                                    methods.replace('"', "").replace("'", "") if methods else "GET"
                                                ),
                                                "file": fr.path,
                                            }
                                        )
                            except Exception:
                                pass

                # Basic framework detection via imports (fallback)
                for fr in result.files_analyzed:
                    for imp in fr.imports:
                        if imp.startswith("fastapi"):
                            framework_signals.add("FastAPI")
                        if imp.startswith("click"):
                            framework_signals.add("Click")
                        if imp.startswith("typer"):
                            framework_signals.add("Typer")

                # Generate framework report sections
                if framework_signals:
                    report += "\n\n## Framework Signals\n" + "\n".join(
                        f"- {name}" for name in sorted(framework_signals)
                    )

                if nextjs_routes:
                    report += "\n\n### Next.js Routes\n"
                    for route_info in sorted(nextjs_routes, key=lambda x: x["route"]):
                        report += f"- `{route_info['route']}` ({route_info['type']}) - {route_info['path']}\n"

                if django_routes:
                    report += "\n\n### Django URL Patterns\n"
                    for route_info in sorted(django_routes, key=lambda x: x["route"]):
                        report += f"- `{route_info['route']}` -> {route_info['view']}\n"

                if flask_routes:
                    report += "\n\n### Flask Routes\n"
                    for route_info in sorted(flask_routes, key=lambda x: x["route"]):
                        report += f"- `{route_info['route']}` [{route_info['methods']}] - {route_info['file']}\n"

            if capabilities and "generated_code_detection" in capabilities:
                root = Path(root_path)
                known_generated = [
                    "migrations",
                    "alembic",
                    "dist",
                    "build",
                    "node_modules",
                    "__pycache__",
                    ".venv",
                    "venv",
                ]
                present = [d for d in known_generated if (root / d).exists()]

                # Content-based detection for generated code
                generated_files: list[str] = []
                generation_markers = [
                    "<auto-generated",
                    "@generated",
                    "autogenerated",
                    "do not edit",
                    "generated by",
                    "this file is automatically",
                    "code generator",
                ]

                for fr in result.files_analyzed:
                    try:
                        with open(fr.path, encoding="utf-8", errors="ignore") as f:
                            # Check first 20 lines for generation markers
                            header = "".join(f.readline().lower() for _ in range(20))
                            if any(marker in header for marker in generation_markers):
                                generated_files.append(str(Path(fr.path).relative_to(root)))
                    except Exception:
                        pass

                if present or generated_files:
                    report += "\n\n## Generated/Third-Party Code\n"
                    if present:
                        report += "### Folders (Heuristics)\n" + "\n".join(f"- {d}" for d in present) + "\n"
                    if generated_files:
                        report += "\n### Files (Content Analysis)\n" + "\n".join(
                            f"- {f}" for f in generated_files[:20]
                        )  # Limit to 20
                        if len(generated_files) > 20:
                            report += f"\n- ... and {len(generated_files) - 20} more"

            # [20251229_FEATURE] Enterprise: Monorepo detection and support
            if capabilities and "monorepo_support" in capabilities:
                root = Path(root_path)
                workspaces: list[dict] = []

                # Detect Yarn/npm workspaces
                package_json = root / "package.json"
                if package_json.exists():
                    try:
                        import json as json_lib

                        with open(package_json, encoding="utf-8") as f:
                            pkg_data = json_lib.load(f)
                            if "workspaces" in pkg_data:
                                workspace_patterns = pkg_data["workspaces"]
                                if isinstance(workspace_patterns, dict):
                                    workspace_patterns = workspace_patterns.get("packages", [])

                                for pattern in workspace_patterns:
                                    for workspace_dir in root.glob(pattern):
                                        if workspace_dir.is_dir():
                                            workspace_pkg = workspace_dir / "package.json"
                                            if workspace_pkg.exists():
                                                try:
                                                    with open(
                                                        workspace_pkg,
                                                        encoding="utf-8",
                                                    ) as wf:
                                                        wp_data = json_lib.load(wf)
                                                        workspaces.append(
                                                            {
                                                                "name": wp_data.get(
                                                                    "name",
                                                                    workspace_dir.name,
                                                                ),
                                                                "path": str(workspace_dir.relative_to(root)),
                                                                "type": "npm-workspace",
                                                            }
                                                        )
                                                except Exception:
                                                    pass
                    except Exception:
                        pass

                # Detect Lerna monorepo
                lerna_json = root / "lerna.json"
                if lerna_json.exists():
                    try:
                        import json as json_lib

                        with open(lerna_json, encoding="utf-8") as f:
                            lerna_data = json_lib.load(f)
                            packages = lerna_data.get("packages", ["packages/*"])
                            for pattern in packages:
                                for pkg_dir in root.glob(pattern):
                                    if pkg_dir.is_dir() and (pkg_dir / "package.json").exists():
                                        workspaces.append(
                                            {
                                                "name": pkg_dir.name,
                                                "path": str(pkg_dir.relative_to(root)),
                                                "type": "lerna-package",
                                            }
                                        )
                    except Exception:
                        pass

                # Detect Python monorepos (multiple pyproject.toml or setup.py)
                python_projects = []
                for pyproject in root.rglob("pyproject.toml"):
                    if pyproject.parent != root:  # Sub-projects only
                        try:
                            import toml

                            with open(pyproject, encoding="utf-8") as f:
                                proj_data = toml.load(f)
                                name = proj_data.get("project", {}).get("name", pyproject.parent.name)
                                python_projects.append(
                                    {
                                        "name": name,
                                        "path": str(pyproject.parent.relative_to(root)),
                                        "type": "python-package",
                                    }
                                )
                        except Exception:
                            pass

                if workspaces or python_projects:
                    report += "\n\n## Monorepo Structure\n"
                    all_packages = workspaces + python_projects
                    for pkg in sorted(all_packages, key=lambda x: x["path"]):
                        report += f"- **{pkg['name']}** (`{pkg['path']}`) - {pkg['type']}\n"

            # [20251229_FEATURE] Enterprise: Cross-repository dependency linking
            if capabilities and "cross_repo_dependency_linking" in capabilities:
                root = Path(root_path)
                external_deps: list[dict] = []

                # Check for git submodules
                gitmodules = root / ".gitmodules"
                if gitmodules.exists():
                    try:
                        content = gitmodules.read_text(encoding="utf-8")

                        submodule_pattern = re.compile(
                            r'\[submodule "([^"]+)"\]\s+path\s*=\s*([^\s]+)\s+url\s*=\s*([^\s]+)'
                        )
                        for match in submodule_pattern.finditer(content):
                            name, path, url = match.groups()
                            external_deps.append(
                                {
                                    "name": name,
                                    "path": path,
                                    "url": url,
                                    "type": "git-submodule",
                                }
                            )
                    except Exception:
                        pass

                # Check for workspace dependencies in monorepo
                for pkg_json in root.rglob("package.json"):
                    try:
                        import json as json_lib

                        with open(pkg_json, encoding="utf-8") as f:
                            pkg_data = json_lib.load(f)
                            deps = pkg_data.get("dependencies", {})
                            for dep_name, dep_version in deps.items():
                                # Detect workspace/monorepo references
                                if dep_version.startswith("workspace:") or dep_version.startswith("link:"):
                                    external_deps.append(
                                        {
                                            "name": dep_name,
                                            "source": str(pkg_json.parent.relative_to(root)),
                                            "version": dep_version,
                                            "type": "workspace-link",
                                        }
                                    )
                    except Exception:
                        pass

                if external_deps:
                    report += "\n\n## Cross-Repository Dependencies\n"
                    for dep in sorted(external_deps, key=lambda x: x.get("name", "")):
                        if dep["type"] == "git-submodule":
                            report += f"- **{dep['name']}** (submodule) - `{dep['path']}` from {dep['url']}\n"
                        elif dep["type"] == "workspace-link":
                            report += (
                                f"- **{dep['name']}** (workspace) - {dep['version']} referenced by `{dep['source']}`\n"
                            )

        return ProjectCrawlResult(
            success=True,
            root_path=result.root_path,
            timestamp=result.timestamp,
            summary=summary,
            files=files,
            errors=errors,
            markdown_report=report,
            language_breakdown=lang_counts or None,
            cache_hits=cache_hits if incremental_mode else None,
            compliance_summary=compliance_summary,
            framework_hints=None,
            entrypoints=None,
        )

    except Exception as e:
        return ProjectCrawlResult(
            success=False,
            root_path=root_path,
            timestamp="",
            summary=CrawlSummary(
                total_files=0,
                successful_files=0,
                failed_files=0,
                total_lines_of_code=0,
                total_functions=0,
                total_classes=0,
                complexity_warnings=0,
            ),
            error=f"Crawl failed: {str(e)}",
        )


async def crawl_project(
    root_path: str | None = None,
    exclude_dirs: list[str] | None = None,
    complexity_threshold: int = 10,
    include_report: bool = True,
    pattern: str | None = None,
    pattern_type: str = "regex",
    include_related: list[str] | None = None,
    ctx: Any | None = None,
) -> ProjectCrawlResult:
    """
    Crawl an entire project directory and analyze all Python files.

    **Tier Behavior:**
    - Community: Discovery crawl (file inventory, structure, entrypoints)
    - Pro/Enterprise: Deep crawl (full analysis with complexity, dependencies, cross-file)

    Use this tool to get a comprehensive overview of a project's structure,
    complexity hotspots, and code metrics before diving into specific files.

    [20251215_FEATURE] v2.0.0 - Progress reporting for long-running operations.
    Reports progress as files are discovered and analyzed.

    [20251223_FEATURE] v3.2.8 - Tier-based behavior splitting.
    Community tier provides discovery-only crawl for inventory and entrypoints.

    Example::

        result = await crawl_project(
            root_path="/home/user/myproject",
            complexity_threshold=8,
            include_report=True
        )

        # Returns ProjectCrawlResult:
        # - summary: ProjectSummary(
        #     total_files=42,
        #     total_lines=5680,
        #     total_functions=187,
        #     total_classes=23,
        #     average_complexity=4.2
        # )
        # - files: [CrawlFileResult(path="src/main.py", ...), ...]
        # - complexity_hotspots: [
        #     CrawlFunctionInfo(name="parse_config", complexity=15, lineno=42),
        #     CrawlFunctionInfo(name="process_batch", complexity=12, lineno=156)
        # ]
        # - markdown_report: "# Project Analysis Report\n\n## Summary\n..."

        # Find files exceeding complexity threshold
        for hotspot in result.complexity_hotspots:
            print(f"{hotspot.name}: complexity {hotspot.complexity}")

    Args:
        root_path: Path to project root (defaults to current working directory)
        exclude_dirs: Additional directories to exclude (common ones already excluded)
        complexity_threshold: Complexity score that triggers a warning (default: 10)
        include_report: Include a markdown report in the response (default: True)

    Returns:
        ProjectCrawlResult with files, summary stats, complexity_hotspots, and markdown_report
    """
    if root_path is None:
        root_path = str(Path.cwd())

    # [20251215_FEATURE] v2.0.0 - Progress token support
    # Report initial progress
    if ctx:
        await ctx.report_progress(progress=0, total=100)

    # [20251225_FEATURE] Tier-based behavior via capability matrix (no upgrade hints).
    tier = get_current_tier()
    # [20260119_BUGFIX] Honor explicit tier override for tests without upconverting community
    if os.environ.get("CODE_SCALPEL_TEST_FORCE_TIER") == "1":
        forced_tier = os.environ.get("CODE_SCALPEL_TIER")
        if forced_tier in {"community", "pro", "enterprise"}:
            tier = forced_tier

    caps = get_tool_capabilities("crawl_project", tier)
    capabilities = set(caps.get("capabilities", set()))
    limits = caps.get("limits", {})
    max_files = limits.get("max_files")
    max_depth = limits.get("max_depth")
    respect_gitignore = "gitignore_respect" in capabilities

    # [20260106_FEATURE] v1.0 pre-release - Determine crawl mode for output metadata
    crawl_mode = "discovery" if tier == "community" else "deep"

    if tier == "community":
        # [20260119_BUGFIX] Enforce community default limit when not provided
        if not max_files:
            max_files = 100
        # Community: Discovery crawl (inventory + entrypoints)
        result = await asyncio.to_thread(
            _crawl_project_discovery,
            root_path,
            exclude_dirs,
            max_files=max_files,
            max_depth=max_depth,
            respect_gitignore=respect_gitignore,
        )
    else:
        # Pro/Enterprise: Deep crawl with optional feature sections
        result = await asyncio.to_thread(
            _crawl_project_sync,
            root_path,
            exclude_dirs,
            complexity_threshold,
            include_report,
            capabilities,
            max_files,
            max_depth,
            respect_gitignore,
            ctx,
        )

    # [20260106_FEATURE] v1.0 pre-release - Add output transparency metadata
    try:
        result = result.model_copy(
            update={
                "tier_applied": tier,
                "crawl_mode": crawl_mode,
                "files_limit_applied": max_files,
            }
        )
    except Exception:
        # Fallback for older Pydantic or if model_copy fails
        result.tier_applied = tier
        result.crawl_mode = crawl_mode
        result.files_limit_applied = max_files

    # Enterprise feature: project-wide custom pattern extraction (not a standalone MCP tool).
    if pattern:
        if not has_capability("extract_code", "custom_extraction_patterns", tier):
            try:
                result = result.model_copy(
                    update={
                        "pattern_success": False,
                        "pattern_error": "Custom pattern extraction requires ENTERPRISE tier",
                    }
                )
            except Exception:
                pass
        else:
            try:
                from code_scalpel.surgery.surgical_extractor import (
                    extract_with_custom_pattern as _extract_pattern,
                )

                pattern_result = await asyncio.to_thread(
                    _extract_pattern,
                    pattern=pattern,
                    pattern_type=pattern_type,
                    project_root=root_path,
                    include_related=include_related,
                )

                if getattr(pattern_result, "success", False):
                    payload: dict[str, Any] = {
                        "pattern_success": True,
                        "pattern_name": getattr(pattern_result, "pattern_name", None),
                        "pattern_matches": [
                            {
                                "symbol_name": match.symbol_name,
                                "symbol_type": match.symbol_type,
                                "file_path": match.file_path,
                                "line_number": match.line_number,
                                "code": match.code,
                                "match_reason": match.match_reason,
                            }
                            for match in pattern_result.matches
                        ],
                        "pattern_total_matches": getattr(pattern_result, "total_matches", None),
                        "pattern_files_scanned": getattr(pattern_result, "files_scanned", None),
                        "pattern_explanation": getattr(pattern_result, "explanation", None),
                    }
                else:
                    payload = {
                        "pattern_success": False,
                        "pattern_error": getattr(pattern_result, "error", None) or "Pattern extraction failed",
                    }

                try:
                    result = result.model_copy(update=payload)
                except Exception:
                    for key, value in payload.items():
                        setattr(result, key, value)

            except Exception as e:
                try:
                    result = result.model_copy(
                        update={
                            "pattern_success": False,
                            "pattern_error": f"Pattern extraction failed: {e}",
                        }
                    )
                except Exception:
                    pass

    return result


def _get_file_context_sync(
    file_path: str, tier: str | None = None, capabilities: dict | None = None
) -> FileContextResult:
    """
    Synchronous implementation of get_file_context.

    [20251214_FEATURE] v1.5.3 - Integrated PathResolver for intelligent path resolution
    [20251220_FEATURE] v3.0.5 - Multi-language support via file extension detection
    [20251225_FEATURE] v3.3.0 - Tier-gated limits, enrichments, and redaction
    """
    # Language detection by file extension
    LANG_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
    }

    # Tier + capability detection
    tier = tier or get_current_tier()

    # [20260104_BUGFIX] Accept capabilities as list overrides for test call sites.
    if isinstance(capabilities, list):
        caps_override: dict[str, Any] | None = {"capabilities": capabilities}
    elif isinstance(capabilities, dict):
        caps_override = capabilities
    else:
        caps_override = None

    caps = caps_override or get_tool_capabilities("get_file_context", tier) or {}
    caps_capabilities = []
    if isinstance(caps, dict):
        caps_capabilities = caps.get("capabilities", []) or []
    cap_set: set[str] = set(caps_capabilities)
    limits = caps.get("limits", {}) if isinstance(caps, dict) else {}
    limits = limits or {}
    max_context_lines = limits.get("max_context_lines", limits.get("context_lines"))

    # [20260111_FEATURE] v1.0 - Calculate output metadata flags for transparency
    PRO_CAPABILITIES = {
        "code_smell_detection",
        "documentation_coverage",
        "maintainability_index",
        "semantic_summarization",
        "intent_extraction",
        "related_imports_inclusion",
        "smart_context_expansion",
    }
    ENTERPRISE_CAPABILITIES = {
        "pii_redaction",
        "secret_masking",
        "api_key_detection",
        "rbac_aware_retrieval",
        "file_access_control",
        "custom_metadata_extraction",
        "compliance_flags",
        "technical_debt_scoring",
        "owner_team_mapping",
        "historical_metrics",
    }
    pro_features_enabled = bool(cap_set & PRO_CAPABILITIES)
    enterprise_features_enabled = bool(cap_set & ENTERPRISE_CAPABILITIES)

    try:
        # [20251214_FEATURE] Use PathResolver for intelligent path resolution
        try:
            resolved_path = resolve_path(file_path, str(Path.cwd()))
            path = Path(resolved_path)
        except FileNotFoundError as e:
            # PathResolver provides helpful error messages
            return FileContextResult(
                success=False,
                file_path=file_path,
                line_count=0,
                tier_applied=tier,
                max_context_lines_applied=max_context_lines,
                pro_features_enabled=pro_features_enabled,
                enterprise_features_enabled=enterprise_features_enabled,
                error=str(e),
            )

        code = path.read_text(encoding="utf-8")
        code, pii_redacted, secrets_masked, redaction_summary = _redact_sensitive_content(path, code)
        lines = code.splitlines()
        line_count = len(lines)

        # [20251225_BUGFIX] Enforce tier line limits before heavy work
        if max_context_lines is not None and line_count > int(max_context_lines):
            return FileContextResult(
                success=False,
                file_path=str(path),
                line_count=line_count,
                tier_applied=tier,
                max_context_lines_applied=max_context_lines,
                pro_features_enabled=pro_features_enabled,
                enterprise_features_enabled=enterprise_features_enabled,
                summary="",
                imports_truncated=False,
                total_imports=0,
                error=(
                    f"File has {line_count} lines which exceeds the {max_context_lines} line limit for {tier.title()} tier."
                ),
            )

        # [20251220_FEATURE] Detect language from file extension
        detected_lang = LANG_EXTENSIONS.get(path.suffix.lower(), "unknown")

        # For non-Python files, use analyze_code which handles multi-language
        if detected_lang != "python":
            analysis = _analyze_code_sync(code, detected_lang)
            total_imports = len(analysis.imports)

            semantic_summary = None
            if "semantic_summarization" in cap_set:
                function_count = len(analysis.functions)
                class_count = len(analysis.classes)
                semantic_summary = (
                    f"{detected_lang.title()} module with {function_count} function(s) and {class_count} class(es)."
                )

            expanded_context = None
            if "smart_context_expansion" in cap_set:
                preview_len = min(line_count, max_context_lines or 50, 50)
                expanded_context = "\n".join(lines[:preview_len])

            return FileContextResult(
                success=analysis.success if analysis.success is not None else True,
                file_path=str(path),
                tier_applied=tier,
                max_context_lines_applied=max_context_lines,
                pro_features_enabled=pro_features_enabled,
                enterprise_features_enabled=enterprise_features_enabled,
                language=detected_lang,
                line_count=line_count,
                functions=cast(list[FunctionInfo | str], analysis.functions),
                classes=cast(list[ClassInfo | str], analysis.classes),
                imports=analysis.imports[:20],
                exports=[],
                complexity_score=analysis.complexity,
                has_security_issues=False,
                summary=f"{detected_lang.title()} module with {len(analysis.functions)} function(s), {len(analysis.classes)} class(es)",
                imports_truncated=total_imports > 20,
                total_imports=total_imports,
                semantic_summary=semantic_summary,
                expanded_context=expanded_context,
                pii_redacted=pii_redacted,
                secrets_masked=secrets_masked,
                redaction_summary=redaction_summary,
                access_controlled="rbac_aware_retrieval" in cap_set or "file_access_control" in cap_set,
                error=analysis.error,
            )

        # Python-specific parsing (unified parser)
        try:
            tree, report = parse_python_code(code, filename=str(path))
            if getattr(report, "was_sanitized", False):
                code = report.sanitized_code or code
        except ParsingError:
            # [20260119_BUGFIX] Fallback sanitize for enterprise redaction flow.
            sanitized, changed = sanitize_python_source(code)
            if not changed:
                # Return error result but preserve redaction metadata
                return FileContextResult(
                    success=False,
                    file_path=str(path),
                    tier_applied=tier,
                    max_context_lines_applied=max_context_lines,
                    pro_features_enabled=pro_features_enabled,
                    enterprise_features_enabled=enterprise_features_enabled,
                    language=detected_lang,
                    line_count=line_count,
                    functions=[],
                    classes=[],
                    imports=[],
                    exports=[],
                    complexity_score=0,
                    has_security_issues=False,
                    summary="",
                    imports_truncated=False,
                    total_imports=0,
                    semantic_summary=None,
                    expanded_context=None,
                    pii_redacted=pii_redacted,
                    secrets_masked=secrets_masked,
                    redaction_summary=redaction_summary,
                    access_controlled="rbac_aware_retrieval" in cap_set or "file_access_control" in cap_set,
                    error="Invalid Python syntax and sanitization failed.",
                )
            code = sanitized
            tree, report = parse_python_code(
                code,
                filename=str(path),
                config=ParsingConfig(
                    mode="permissive",
                    allow_merge_conflicts=True,
                    allow_templates=True,
                    report_modifications=False,
                ),
            )

        # [20260104_BUGFIX] Return structured symbol info for tiered file context tests.
        functions: list[FunctionInfo] = []
        classes: list[ClassInfo] = []
        function_names: list[str] = []
        class_names: list[str] = []
        imports: list[str] = []
        exports: list[str] = []
        complexity = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                # Only top-level functions
                if hasattr(node, "col_offset") and node.col_offset == 0:
                    functions.append(
                        FunctionInfo(
                            name=node.name,
                            lineno=getattr(node, "lineno", 0) or 0,
                            end_lineno=getattr(node, "end_lineno", None),
                            is_async=isinstance(node, ast.AsyncFunctionDef),
                        )
                    )
                    function_names.append(node.name)
                    complexity += _count_complexity_node(node)
            elif isinstance(node, ast.ClassDef):
                if hasattr(node, "col_offset") and node.col_offset == 0:
                    methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]
                    classes.append(
                        ClassInfo(
                            name=node.name,
                            lineno=getattr(node, "lineno", 0) or 0,
                            end_lineno=getattr(node, "end_lineno", None),
                            methods=methods,
                        )
                    )
                    class_names.append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
            elif isinstance(node, ast.Assign):
                # Check for __all__ exports
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, ast.List | ast.Tuple):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    exports.append(elt.value)

        # Quick security check
        has_security_issues = False
        # [20260104_BUGFIX] Treat bare except handlers as security findings for Community tier.
        bare_except = any(isinstance(node, ast.ExceptHandler) and node.type is None for node in ast.walk(tree))
        security_patterns = [
            "eval(",
            "exec(",
            "cursor.execute",
            "os.system(",
            "subprocess.call(",
        ]
        for pattern in security_patterns:
            if pattern in code:
                has_security_issues = True
                break
        if bare_except:
            has_security_issues = True

        # Generate summary based on content
        summary_parts = []
        if classes:
            summary_parts.append(f"{len(classes)} class(es)")
        if functions:
            summary_parts.append(f"{len(functions)} function(s)")
        if "flask" in code.lower() or "app.route" in code:
            summary_parts.append("Flask web application")
        elif "django" in code.lower():
            summary_parts.append("Django module")
        elif "test_" in path.name or "pytest" in code:
            summary_parts.append("Test module")

        summary = ", ".join(summary_parts) if summary_parts else "Python module"

        # [20251220_FEATURE] v3.0.5 - Communicate truncation
        total_imports = len(imports)
        imports_truncated = total_imports > 20

        semantic_summary = None
        # [20260128_BUGFIX] Cast parse tree to Module for docstring-dependent enrichments.
        if "semantic_summarization" in cap_set:
            module_tree = cast(ast.Module, tree)
            doc = ast.get_docstring(module_tree) or ""
            semantic_summary = summary
            if doc:
                semantic_summary = f"{summary}. Docstring: {doc.strip()}"

        intent_tags: list[str] = []
        if "intent_extraction" in cap_set:
            module_tree = cast(ast.Module, tree)
            tag_source = " ".join([path.stem] + function_names + class_names + [ast.get_docstring(module_tree) or ""])
            for token in re.findall(r"[A-Za-z]{3,}", tag_source):
                lowered = token.lower()
                if lowered not in intent_tags:
                    intent_tags.append(lowered)
            if "flask" in code.lower():
                intent_tags.append("flask")
            if "django" in code.lower():
                intent_tags.append("django")

        related_imports: list[str] = []
        if "related_imports_inclusion" in cap_set:
            for imp in imports:
                candidate = path.parent / (imp.replace(".", "/") + ".py")
                if candidate.exists():
                    related_imports.append(str(candidate))

        expanded_context = None
        if "smart_context_expansion" in cap_set:
            preview_len = min(line_count, max_context_lines or 2000, 2000)
            expanded_context = "\n".join(lines[:preview_len])
            if not expanded_context:
                expanded_context = None

        if not redaction_summary and {"pii_redaction", "secret_masking", "api_key_detection"} & cap_set:
            redaction_summary = []

        access_controlled = "rbac_aware_retrieval" in cap_set or "file_access_control" in cap_set

        # [20251231_FEATURE] v3.3.1 - Pro tier: Code quality metrics
        code_smells: list[dict[str, Any]] = []
        doc_coverage: float | None = None
        maintainability_index: float | None = None

        # [20260128_BUGFIX] Normalize tree type before quality metric helpers.
        if "code_smell_detection" in cap_set:
            module_tree = cast(ast.Module, tree)
            code_smells = _detect_code_smells(module_tree, code, lines)

        if "documentation_coverage" in cap_set:
            module_tree = cast(ast.Module, tree)
            doc_coverage = _calculate_doc_coverage(module_tree, function_names, class_names)

        if {"maintainability_index", "maintainability_metrics"} & cap_set:
            maintainability_index = _calculate_maintainability_index(
                line_count, complexity, len(functions) + len(classes)
            )

        # [20251231_FEATURE] v3.3.1 - Enterprise tier: Organizational metadata
        custom_metadata: dict[str, Any] = {}
        compliance_flags: list[str] = []
        technical_debt_score: float | None = None
        owners: list[str] = []
        historical_metrics: dict[str, Any] | None = None

        if "custom_metadata_extraction" in cap_set:
            custom_metadata = _load_custom_metadata(path)

        if "compliance_flags" in cap_set:
            compliance_flags = _detect_compliance_flags(code, path)

        if "technical_debt_scoring" in cap_set:
            technical_debt_score = _calculate_technical_debt(code_smells, complexity, doc_coverage, line_count)

        if "owner_team_mapping" in cap_set:
            owners = _get_code_owners(path)

        if "historical_metrics" in cap_set:
            historical_metrics = _get_historical_metrics(path)

        return FileContextResult(
            success=True,
            file_path=str(path),
            tier_applied=tier,
            max_context_lines_applied=max_context_lines,
            pro_features_enabled=pro_features_enabled,
            enterprise_features_enabled=enterprise_features_enabled,
            language="python",
            line_count=line_count,
            functions=cast(list[FunctionInfo | str], functions),
            classes=cast(list[ClassInfo | str], classes),
            imports=imports[:20],
            exports=exports,
            complexity_score=complexity,
            has_security_issues=has_security_issues,
            summary=summary,
            imports_truncated=imports_truncated,
            total_imports=total_imports,
            semantic_summary=semantic_summary,
            intent_tags=intent_tags,
            related_imports=related_imports,
            expanded_context=expanded_context,
            pii_redacted=pii_redacted,
            secrets_masked=secrets_masked,
            redaction_summary=redaction_summary,
            access_controlled=access_controlled,
            code_smells=code_smells,
            doc_coverage=doc_coverage,
            maintainability_index=maintainability_index,
            custom_metadata=custom_metadata,
            compliance_flags=compliance_flags,
            technical_debt_score=technical_debt_score,
            owners=owners,
            historical_metrics=historical_metrics,
        )

    except Exception as e:
        return FileContextResult(
            success=False,
            file_path=str(file_path),
            line_count=0,
            tier_applied=tier if "tier" in dir() else "community",
            error=f"Analysis failed: {str(e)}",
        )


def _count_complexity_node(node: ast.AST) -> int:
    """Count cyclomatic complexity for a single node."""
    complexity = 1  # Base complexity
    for child in ast.walk(node):
        if isinstance(child, ast.If | ast.While | ast.For | ast.ExceptHandler):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
    return complexity


# [20251231_FEATURE] v3.3.1 - Pro tier helper functions for code quality metrics


def _detect_code_smells(tree: ast.Module, code: str, lines: list[str]) -> list[dict[str, Any]]:
    """
    Detect common code smells in Python code.

    Returns list of: [{type, line, message, severity}]
    Severity: low, medium, high
    """
    smells: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        # Long function (>50 lines)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if node.end_lineno and node.lineno:
                func_lines = node.end_lineno - node.lineno
                if func_lines > 50:
                    smells.append(
                        {
                            "type": "long_function",
                            "line": node.lineno,
                            "message": f"Function '{node.name}' has {func_lines} lines (>50)",
                            "severity": "medium" if func_lines < 100 else "high",
                        }
                    )

            # Too many parameters (>5)
            param_count = len(node.args.args) + len(node.args.kwonlyargs)
            if param_count > 5:
                smells.append(
                    {
                        "type": "too_many_parameters",
                        "line": node.lineno,
                        "message": f"Function '{node.name}' has {param_count} parameters (>5)",
                        "severity": "low" if param_count <= 7 else "medium",
                    }
                )

        # Deeply nested code (>4 levels)
        if isinstance(node, ast.If | ast.For | ast.While | ast.With | ast.Try):
            depth = _get_nesting_depth(node)
            if depth > 4:
                smells.append(
                    {
                        "type": "deep_nesting",
                        "line": node.lineno,
                        "message": f"Code block at line {node.lineno} has nesting depth {depth} (>4)",
                        "severity": "medium" if depth <= 6 else "high",
                    }
                )

        # God class (>20 methods)
        if isinstance(node, ast.ClassDef):
            method_count = sum(1 for n in node.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef))
            if method_count > 20:
                smells.append(
                    {
                        "type": "god_class",
                        "line": node.lineno,
                        "message": f"Class '{node.name}' has {method_count} methods (>20)",
                        "severity": "high",
                    }
                )

    # Check for magic numbers (numeric literals not 0, 1, -1)
    magic_numbers_found: set[tuple[int, float | int]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            if node.value not in (0, 1, -1, 0.0, 1.0, -1.0, 2, 10, 100):
                if hasattr(node, "lineno"):
                    key = (node.lineno, node.value)
                    if key not in magic_numbers_found:
                        magic_numbers_found.add(key)

    if len(magic_numbers_found) > 5:
        smells.append(
            {
                "type": "magic_numbers",
                "line": 0,
                "message": f"File contains {len(magic_numbers_found)} magic numbers",
                "severity": "low",
            }
        )

    # Check for bare except
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            smells.append(
                {
                    "type": "bare_except",
                    "line": node.lineno,
                    "message": "Bare 'except:' clause catches all exceptions",
                    "severity": "medium",
                }
            )

    return smells


def _get_nesting_depth(node: ast.AST, current_depth: int = 1) -> int:
    """Calculate maximum nesting depth of a code block."""
    max_depth = current_depth
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.If | ast.For | ast.While | ast.With | ast.Try):
            child_depth = _get_nesting_depth(child, current_depth + 1)
            max_depth = max(max_depth, child_depth)
    return max_depth


def _calculate_doc_coverage(tree: ast.Module, functions: list[str], classes: list[str]) -> float:
    """
    Calculate documentation coverage percentage.

    Returns: 0.0 to 100.0 (percentage of functions/classes with docstrings)
    """
    total_items = 0
    documented_items = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if hasattr(node, "col_offset") and node.col_offset == 0:
                total_items += 1
                if ast.get_docstring(node):
                    documented_items += 1
        elif isinstance(node, ast.ClassDef):
            if hasattr(node, "col_offset") and node.col_offset == 0:
                total_items += 1
                if ast.get_docstring(node):
                    documented_items += 1

    # Include module docstring
    if ast.get_docstring(tree):
        documented_items += 1
    total_items += 1  # Count module itself

    if total_items == 0:
        return 100.0

    return round((documented_items / total_items) * 100, 1)


def _calculate_maintainability_index(line_count: int, complexity: int, symbol_count: int) -> float:
    """
    Calculate Maintainability Index (0-100 scale, higher is better).

    Based on simplified Halstead/McCabe formula:
    MI = max(0, (171 - 5.2 * ln(V) - 0.23 * CC - 16.2 * ln(LOC)) * 100 / 171)

    Simplified version for quick calculation:
    MI = 100 - (complexity * 2) - (line_count / 50) - (symbol_count / 10)

    Clamped to 0-100 range.
    """
    import math

    # Simplified maintainability calculation
    if line_count == 0:
        return 100.0

    # Volume approximation (Halstead)
    volume = max(1, line_count * math.log2(max(1, symbol_count + 1)))

    # Simplified MI formula
    mi = 171 - 5.2 * math.log(max(1, volume)) - 0.23 * complexity - 16.2 * math.log(max(1, line_count))
    mi = (mi * 100) / 171

    return round(max(0.0, min(100.0, mi)), 1)


# [20251231_FEATURE] v3.3.1 - Enterprise tier helper functions


def _load_custom_metadata(file_path: Path) -> dict[str, Any]:
    """
    Load custom metadata from .code-scalpel/metadata.yaml if exists.

    Returns empty dict if not found or invalid.
    """
    try:
        # Search for .code-scalpel directory
        search_path = file_path.parent
        for _ in range(10):  # Max 10 levels up
            metadata_file = search_path / ".code-scalpel" / "metadata.yaml"
            if metadata_file.exists():
                import yaml

                with open(metadata_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}

                # Check for file-specific metadata
                rel_path = str(file_path.relative_to(search_path))
                file_metadata = data.get("files", {}).get(rel_path, {})
                global_metadata = {k: v for k, v in data.items() if k != "files"}
                return {**global_metadata, **file_metadata}

            if search_path.parent == search_path:
                break
            search_path = search_path.parent
    except Exception:
        pass
    return {}


def _detect_compliance_flags(code: str, file_path: Path) -> list[str]:
    """
    Detect compliance-relevant patterns in code.

    Returns list of compliance flags: HIPAA, PCI, SOC2, GDPR, etc.
    """
    flags: list[str] = []
    code_lower = code.lower()

    # HIPAA - Health data patterns
    hipaa_patterns = [
        "patient",
        "health",
        "medical",
        "diagnosis",
        "phi",
        "protected_health",
    ]
    if any(p in code_lower for p in hipaa_patterns):
        flags.append("HIPAA")

    # PCI-DSS - Payment card patterns
    pci_patterns = ["credit_card", "card_number", "cvv", "pan", "cardholder", "payment"]
    if any(p in code_lower for p in pci_patterns):
        flags.append("PCI-DSS")

    # SOC2 - Security/audit patterns
    soc2_patterns = ["audit_log", "access_control", "encryption", "authenticate"]
    if any(p in code_lower for p in soc2_patterns):
        flags.append("SOC2")

    # GDPR - Personal data patterns
    gdpr_patterns = [
        "personal_data",
        "gdpr",
        "consent",
        "data_subject",
        "right_to_erasure",
    ]
    if any(p in code_lower for p in gdpr_patterns):
        flags.append("GDPR")

    return flags


def _calculate_technical_debt(
    code_smells: list[dict[str, Any]],
    complexity: int,
    doc_coverage: float | None,
    line_count: int,
) -> float:
    """
    Calculate technical debt score in estimated hours to fix.

    Based on:
    - Code smells (weighted by severity)
    - Missing documentation
    - High complexity
    """
    debt_hours = 0.0

    # Code smell debt
    severity_weights = {"low": 0.25, "medium": 0.5, "high": 1.0}
    for smell in code_smells:
        debt_hours += severity_weights.get(smell.get("severity", "low"), 0.25)

    # Documentation debt (rough estimate: 0.1 hours per undocumented item per 100 lines)
    if doc_coverage is not None and doc_coverage < 80:
        missing_doc_pct = (80 - doc_coverage) / 100
        debt_hours += (line_count / 100) * missing_doc_pct * 0.5

    # Complexity debt
    if complexity > 20:
        debt_hours += (complexity - 20) * 0.1

    return round(debt_hours, 1)


def _get_code_owners(file_path: Path) -> list[str]:
    """
    Parse CODEOWNERS file to find owners for the given file.

    Returns list of owner identifiers (GitHub usernames, team names, or emails).
    """
    try:
        # Search for CODEOWNERS file
        search_path = file_path.parent
        codeowners_locations = [
            ".github/CODEOWNERS",
            "CODEOWNERS",
            "docs/CODEOWNERS",
        ]

        for _ in range(10):  # Max 10 levels up
            for loc in codeowners_locations:
                codeowners_file = search_path / loc
                if codeowners_file.exists():
                    return _parse_codeowners(codeowners_file, file_path, search_path)

            if search_path.parent == search_path:
                break
            search_path = search_path.parent
    except Exception:
        pass
    return []


def _parse_codeowners(codeowners_file: Path, target_file: Path, repo_root: Path) -> list[str]:
    """Parse CODEOWNERS and return owners matching the target file."""
    try:
        rel_path = str(target_file.relative_to(repo_root))
        owners: list[str] = []

        with open(codeowners_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split()
                if len(parts) < 2:
                    continue

                pattern = parts[0]
                line_owners = parts[1:]

                # Simple pattern matching (supports * and **)
                if _codeowners_pattern_matches(pattern, rel_path):
                    owners = line_owners  # Last matching pattern wins

        return owners
    except Exception:
        return []


def _codeowners_pattern_matches(pattern: str, file_path: str) -> bool:
    """Check if a CODEOWNERS pattern matches a file path."""
    import fnmatch

    # Normalize paths
    pattern = pattern.lstrip("/")
    file_path = file_path.replace("\\", "/")

    # Handle directory patterns
    if pattern.endswith("/"):
        return file_path.startswith(pattern) or fnmatch.fnmatch(file_path, pattern + "*")

    # Handle glob patterns
    if "*" in pattern:
        # Convert ** to match any path depth
        glob_pattern = pattern.replace("**", "*")
        return fnmatch.fnmatch(file_path, glob_pattern)

    # Exact match or prefix match for directories
    return file_path == pattern or file_path.startswith(pattern + "/")


def _get_historical_metrics(file_path: Path) -> dict[str, Any] | None:
    """
    Get historical metrics from git for the file.

    Returns: {churn, age_days, contributors, last_modified}
    or None if git is not available.
    """
    import subprocess
    import time

    try:
        # Find git root
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=file_path.parent,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None

        git_root = Path(result.stdout.strip())
        rel_path = str(file_path.relative_to(git_root))

        # Get commit count (churn indicator)
        result = subprocess.run(
            ["git", "log", "--oneline", "--follow", "--", rel_path],
            cwd=git_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        commit_count = len(result.stdout.strip().splitlines()) if result.returncode == 0 else 0

        # Get unique contributors
        result = subprocess.run(
            ["git", "log", "--format=%ae", "--follow", "--", rel_path],
            cwd=git_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        contributors = list(set(result.stdout.strip().splitlines())) if result.returncode == 0 else []

        # Get file age (first commit date)
        result = subprocess.run(
            [
                "git",
                "log",
                "--follow",
                "--format=%at",
                "--diff-filter=A",
                "--",
                rel_path,
            ],
            cwd=git_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        first_commit_ts = None
        if result.returncode == 0 and result.stdout.strip():
            try:
                first_commit_ts = int(result.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError):
                pass

        # Get last modified date
        result = subprocess.run(
            ["git", "log", "-1", "--format=%at", "--", rel_path],
            cwd=git_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        last_modified_ts = None
        if result.returncode == 0 and result.stdout.strip():
            try:
                last_modified_ts = int(result.stdout.strip())
            except ValueError:
                pass

        now = time.time()

        return {
            "churn": commit_count,
            "age_days": (int((now - first_commit_ts) / 86400) if first_commit_ts else None),
            "contributors": contributors[:10],  # Limit to 10
            "contributor_count": len(contributors),
            "last_modified_days_ago": (int((now - last_modified_ts) / 86400) if last_modified_ts else None),
        }

    except Exception:
        return None


async def get_file_context(file_path: str) -> FileContextResult:
    """
    Get a file overview without reading full content.

    [v1.4.0] Use this tool to quickly assess if a file is relevant to your task
    without consuming tokens on full content. Returns functions, classes, imports,
    complexity score, and security warnings.

    Why AI agents need this:
    - Quickly assess file relevance before extracting code
    - Understand file structure without token overhead
    - Make informed decisions about which functions to modify

    Example::

        result = await get_file_context("src/services/payment.py")

        # Returns FileContextResult:
        # - file_path: "src/services/payment.py"
        # - functions: ["process_payment", "validate_card", "refund_transaction"]
        # - classes: ["PaymentProcessor", "PaymentError"]
        # - imports: ["stripe", "decimal.Decimal", "datetime"]
        # - complexity_score: 8
        # - line_count: 245
        # - has_security_issues: True
        # - security_warnings: ["Potential SQL injection at line 87"]
        # - docstring: "Payment processing service for Stripe integration."

        # Use to decide if file is relevant
        if "payment" in result.functions or result.has_security_issues:
            # Now extract specific functions
            code = await extract_code(file_path, symbol_name="process_payment")

    Args:
        file_path: Path to the file (absolute or relative to project root)
                   Supports: .py, .js, .ts, .java, .go, .rs, .rb, .php

    Returns:
        FileContextResult with functions, classes, imports, complexity, and security warnings
    """
    try:
        return await asyncio.to_thread(_get_file_context_sync, file_path)
    except Exception as e:
        with open("mcp_error.log", "a") as f:
            f.write(f"Error in get_file_context: {e}\n")
            import traceback

            traceback.print_exc(file=f)
        raise


def _get_symbol_references_sync(
    symbol_name: str,
    project_root: str | None = None,
    max_files: int | None = None,
    max_references: int | None = 100,
    scope_prefix: str | None = None,
    include_tests: bool = True,
    enable_categorization: bool = False,
    enable_codeowners: bool = False,
    enable_impact_analysis: bool = False,
    *,
    tier: str | None = None,
    capabilities: list[str] | None = None,
) -> SymbolReferencesResult:
    """
    Synchronous implementation of get_symbol_references.

    [20251220_FEATURE] v3.0.5 - Optimized single-pass AST walking with deduplication
    [20251220_PERF] v3.0.5 - Uses AST cache to avoid re-parsing unchanged files
    [20251226_FEATURE] Enterprise impact analysis with risk scoring
    [20250112_FEATURE] v3.3.0 - Output metadata fields for tier transparency
    """
    # Resolve tier early for metadata
    tier = tier or get_current_tier()
    capabilities = capabilities or []

    # Determine Pro and Enterprise feature lists
    pro_features = [
        "usage_categorization",
        "read_write_classification",
        "import_classification",
        "scope_filtering",
        "test_file_filtering",
    ]
    enterprise_features = [
        "codeowners_integration",
        "ownership_attribution",
        "impact_analysis",
        "change_risk_assessment",
    ]

    enabled_pro = [f for f in capabilities if f in pro_features] or None
    enabled_enterprise = [f for f in capabilities if f in enterprise_features] or None

    try:
        root = Path(project_root) if project_root else Path.cwd()

        if not root.exists():
            return SymbolReferencesResult(
                success=False,
                symbol_name=symbol_name,
                error=f"Project root not found: {root}.",
                tier_applied=tier,
                pro_features_enabled=enabled_pro,
                enterprise_features_enabled=enabled_enterprise,
            )

        references: list[SymbolReference] = []
        definition_file = None
        definition_line = None
        # Track seen (file, line, col) triples to avoid duplicates in single pass
        seen: set[tuple[str, int, int]] = set()

        def _is_test_path(rel_path: str) -> bool:
            p = rel_path.replace("\\", "/")
            name = p.rsplit("/", 1)[-1]
            return "/tests/" in f"/{p}/" or name.startswith("test_") or name.endswith("_test.py")

        # [20251226_FEATURE] Enterprise: Enhanced CODEOWNERS support with validation
        def _find_codeowners_file(search_root: Path) -> Path | None:
            candidates = [
                search_root / "CODEOWNERS",
                search_root / ".github" / "CODEOWNERS",
                search_root / "docs" / "CODEOWNERS",
            ]
            for c in candidates:
                if c.exists() and c.is_file():
                    return c
            return None

        def _parse_codeowners_inner(
            path: Path,
        ) -> tuple[list[tuple[str, list[str], int]], list[str] | None]:
            """Parse CODEOWNERS with validation. Returns (rules, default_owners)."""
            rules: list[tuple[str, list[str], int]] = []  # (pattern, owners, specificity)
            default_owners: list[str] | None = None
            try:
                for raw in path.read_text(encoding="utf-8").splitlines():
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split()
                    if len(parts) < 2:
                        continue
                    pattern = parts[0].lstrip("/")
                    owners = [p for p in parts[1:] if p.startswith("@")] or parts[1:]
                    # [20251226_FEATURE] Calculate pattern specificity (more specific wins)
                    specificity = len(pattern.split("/")) + (0 if "*" in pattern else 10)
                    if pattern == "*":
                        default_owners = owners
                    else:
                        rules.append((pattern, owners, specificity))
            except Exception:
                return [], None
            # Sort by specificity descending (most specific first)
            rules.sort(key=lambda x: x[2], reverse=True)
            return rules, default_owners

        def _match_owners(
            rules: list[tuple[str, list[str], int]],
            rel_path: str,
            default_owners: list[str] | None = None,
        ) -> tuple[list[str] | None, float]:
            """Match owners with confidence score based on pattern specificity."""
            if not rules and not default_owners:
                return None, 0.0
            import fnmatch

            normalized = rel_path.replace("\\", "/")
            # [20251226_FEATURE] Enhanced pattern matching with recursive support
            for pattern, owners, specificity in rules:
                # Handle recursive patterns (**)
                if "**" in pattern:
                    base = pattern.replace("**", "*")
                    if fnmatch.fnmatch(normalized, base):
                        confidence = min(1.0, specificity / 20.0)
                        return owners, confidence
                # Standard glob matching
                if fnmatch.fnmatch(normalized, pattern):
                    confidence = min(1.0, specificity / 20.0)
                    return owners, confidence
                # Directory match (pattern applies to all files in directory)
                if fnmatch.fnmatch(normalized, f"{pattern}/*"):
                    confidence = min(1.0, (specificity - 1) / 20.0)
                    return owners, confidence
                # Exact directory match
                if normalized.startswith(pattern + "/"):
                    confidence = min(1.0, specificity / 20.0)
                    return owners, confidence
            # Fall back to default owners
            if default_owners:
                return default_owners, 0.3
            return None, 0.0

        codeowners_rules: list[tuple[str, list[str], int]] = []
        default_owners: list[str] | None = None
        if enable_codeowners or enable_impact_analysis:
            codeowners_file = _find_codeowners_file(root)
            if codeowners_file is not None:
                codeowners_rules, default_owners = _parse_codeowners_inner(codeowners_file)

        # [20251226_FEATURE] Enterprise: Track complexity per file for impact analysis
        file_complexity: dict[str, int] = {}

        # Collect candidate python files first to allow file-level limits.
        candidate_files: list[Path] = []
        scope_norm = (scope_prefix or "").strip().lstrip("/")

        # Walk through all Python files
        for py_file in root.rglob("*.py"):
            # Skip common non-source directories
            if any(
                part.startswith(".") or part in ("__pycache__", "node_modules", "venv", ".venv", "dist", "build")
                for part in py_file.parts
            ):
                continue

            try:
                rel_path = str(py_file.relative_to(root))
            except Exception:
                continue

            if scope_norm and not rel_path.replace("\\", "/").startswith(scope_norm.replace("\\", "/")):
                continue

            if not include_tests and _is_test_path(rel_path):
                continue

            candidate_files.append(py_file)

        total_files = len(candidate_files)
        files_truncated = False
        file_truncation_warning = None
        if max_files is not None and total_files > max_files:
            candidate_files = candidate_files[:max_files]
            files_truncated = True
            file_truncation_warning = f"File scan truncated: scanned {max_files} of {total_files} files."

        category_counts: dict[str, int] = {}
        owner_counts: dict[str, int] = {}

        for py_file in candidate_files:

            try:
                # [20251220_PERF] v3.0.5 - Use cached AST parsing
                tree = parse_file_cached(py_file)
                if tree is None:
                    continue

                code = py_file.read_text(encoding="utf-8")
                lines = code.splitlines()
                rel_path = str(py_file.relative_to(root))
                is_test_file = _is_test_path(rel_path)

                # [20251226_FEATURE] Enhanced CODEOWNERS with confidence
                owners = None
                owner_confidence = 0.0
                if enable_codeowners or enable_impact_analysis:
                    owners, owner_confidence = _match_owners(codeowners_rules, rel_path, default_owners)

                # [20251226_FEATURE] Enterprise: Track file complexity for impact analysis
                if enable_impact_analysis and rel_path not in file_complexity:
                    # Simple complexity heuristic: count branches and function definitions
                    complexity = 0
                    for n in ast.walk(tree):
                        if isinstance(n, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                            complexity += 1
                        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            complexity += 2
                        elif isinstance(n, ast.ClassDef):
                            complexity += 3
                    file_complexity[rel_path] = complexity

                # [20251226_FEATURE] Pro tier: Track first assignments for assignment context
                first_assigned: set[str] = set()

                # Single-pass AST walk with optimized checks
                for node in ast.walk(tree):
                    node_line = getattr(node, "lineno", 0)
                    node_col = getattr(node, "col_offset", 0)

                    # Skip if already seen this location in this file
                    loc_key = (rel_path, node_line, node_col)
                    if loc_key in seen:
                        continue

                    is_def = False
                    matched = False
                    ref_type = "reference"

                    # Check definitions (FunctionDef, AsyncFunctionDef, ClassDef)
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if node.name == symbol_name:
                            matched = True
                            is_def = True
                            ref_type = "definition"
                            if definition_file is None:
                                definition_file = rel_path
                                definition_line = node_line

                        # [20251226_FEATURE] Pro tier: Check decorators on functions/classes
                        if enable_categorization and hasattr(node, "decorator_list"):
                            for decorator in node.decorator_list:
                                dec_line = getattr(decorator, "lineno", 0)
                                dec_col = getattr(decorator, "col_offset", 0)
                                dec_key = (rel_path, dec_line, dec_col)
                                if dec_key in seen:
                                    continue
                                dec_matched = False
                                if isinstance(decorator, ast.Name) and decorator.id == symbol_name:
                                    dec_matched = True
                                elif isinstance(decorator, ast.Attribute) and decorator.attr == symbol_name:
                                    dec_matched = True
                                elif isinstance(decorator, ast.Call):
                                    dec_func = decorator.func
                                    if isinstance(dec_func, ast.Name) and dec_func.id == symbol_name:
                                        dec_matched = True
                                    elif isinstance(dec_func, ast.Attribute) and dec_func.attr == symbol_name:
                                        dec_matched = True
                                if dec_matched:
                                    seen.add(dec_key)
                                    dec_context = lines[dec_line - 1] if 0 < dec_line <= len(lines) else ""
                                    category_counts["decorator"] = category_counts.get("decorator", 0) + 1
                                    if owners:
                                        for owner in owners:
                                            owner_counts[owner] = owner_counts.get(owner, 0) + 1
                                    references.append(
                                        SymbolReference(
                                            file=rel_path,
                                            line=dec_line,
                                            column=dec_col,
                                            context=dec_context.strip(),
                                            is_definition=False,
                                            reference_type="decorator",
                                            is_test_file=is_test_file,
                                            owners=owners,
                                        )
                                    )
                                    if max_references is not None and len(references) >= max_references:
                                        break

                        # [20251226_FEATURE] Pro tier: Check return type annotation
                        if enable_categorization and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if node.returns is not None:
                                ret_ann = node.returns
                                ret_line = getattr(ret_ann, "lineno", node_line)
                                ret_col = getattr(ret_ann, "col_offset", 0)
                                ret_key = (rel_path, ret_line, ret_col)
                                if ret_key not in seen:
                                    ret_matched = False
                                    if isinstance(ret_ann, ast.Name) and ret_ann.id == symbol_name:
                                        ret_matched = True
                                    elif isinstance(ret_ann, ast.Attribute) and ret_ann.attr == symbol_name:
                                        ret_matched = True
                                    elif isinstance(ret_ann, ast.Subscript):
                                        val = ret_ann.value
                                        if isinstance(val, ast.Name) and val.id == symbol_name:
                                            ret_matched = True
                                        elif isinstance(val, ast.Attribute) and val.attr == symbol_name:
                                            ret_matched = True
                                    if ret_matched:
                                        seen.add(ret_key)
                                        ret_context = lines[ret_line - 1] if 0 < ret_line <= len(lines) else ""
                                        category_counts["type_annotation"] = (
                                            category_counts.get("type_annotation", 0) + 1
                                        )
                                        if owners:
                                            for owner in owners:
                                                owner_counts[owner] = owner_counts.get(owner, 0) + 1
                                        references.append(
                                            SymbolReference(
                                                file=rel_path,
                                                line=ret_line,
                                                column=ret_col,
                                                context=ret_context.strip(),
                                                is_definition=False,
                                                reference_type="type_annotation",
                                                is_test_file=is_test_file,
                                                owners=owners,
                                            )
                                        )

                            # [20251226_FEATURE] Pro tier: Check parameter type annotations
                            for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
                                if arg.annotation is not None:
                                    ann = arg.annotation
                                    ann_line = getattr(ann, "lineno", node_line)
                                    ann_col = getattr(ann, "col_offset", 0)
                                    ann_key = (rel_path, ann_line, ann_col)
                                    if ann_key not in seen:
                                        ann_matched = False
                                        if isinstance(ann, ast.Name) and ann.id == symbol_name:
                                            ann_matched = True
                                        elif isinstance(ann, ast.Attribute) and ann.attr == symbol_name:
                                            ann_matched = True
                                        elif isinstance(ann, ast.Subscript):
                                            val = ann.value
                                            if isinstance(val, ast.Name) and val.id == symbol_name:
                                                ann_matched = True
                                            elif isinstance(val, ast.Attribute) and val.attr == symbol_name:
                                                ann_matched = True
                                        if ann_matched:
                                            seen.add(ann_key)
                                            ann_context = lines[ann_line - 1] if 0 < ann_line <= len(lines) else ""
                                            category_counts["type_annotation"] = (
                                                category_counts.get("type_annotation", 0) + 1
                                            )
                                            if owners:
                                                for owner in owners:
                                                    owner_counts[owner] = owner_counts.get(owner, 0) + 1
                                            references.append(
                                                SymbolReference(
                                                    file=rel_path,
                                                    line=ann_line,
                                                    column=ann_col,
                                                    context=ann_context.strip(),
                                                    is_definition=False,
                                                    reference_type="type_annotation",
                                                    is_test_file=is_test_file,
                                                    owners=owners,
                                                )
                                            )

                    # [20251226_FEATURE] Pro tier: Check annotated variable assignments
                    elif isinstance(node, ast.AnnAssign) and enable_categorization:
                        ann = node.annotation
                        ann_line = getattr(ann, "lineno", node_line)
                        ann_col = getattr(ann, "col_offset", 0)
                        ann_key = (rel_path, ann_line, ann_col)
                        if ann_key not in seen:
                            ann_matched = False
                            if isinstance(ann, ast.Name) and ann.id == symbol_name:
                                ann_matched = True
                            elif isinstance(ann, ast.Attribute) and ann.attr == symbol_name:
                                ann_matched = True
                            elif isinstance(ann, ast.Subscript):
                                val = ann.value
                                if isinstance(val, ast.Name) and val.id == symbol_name:
                                    ann_matched = True
                                elif isinstance(val, ast.Attribute) and val.attr == symbol_name:
                                    ann_matched = True
                            if ann_matched:
                                seen.add(ann_key)
                                ann_context = lines[ann_line - 1] if 0 < ann_line <= len(lines) else ""
                                category_counts["type_annotation"] = category_counts.get("type_annotation", 0) + 1
                                if owners:
                                    for owner in owners:
                                        owner_counts[owner] = owner_counts.get(owner, 0) + 1
                                references.append(
                                    SymbolReference(
                                        file=rel_path,
                                        line=ann_line,
                                        column=ann_col,
                                        context=ann_context.strip(),
                                        is_definition=False,
                                        reference_type="type_annotation",
                                        is_test_file=is_test_file,
                                        owners=owners,
                                    )
                                )

                    # Check imports
                    elif isinstance(node, ast.ImportFrom):
                        for alias in node.names:
                            if alias.name == symbol_name or alias.asname == symbol_name:
                                matched = True
                                ref_type = "import"
                                break
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.asname == symbol_name:
                                matched = True
                                ref_type = "import"
                                break

                    # Check function calls
                    elif isinstance(node, ast.Call):
                        func = node.func
                        if isinstance(func, ast.Name) and func.id == symbol_name:
                            matched = True
                            ref_type = "call"
                        elif isinstance(func, ast.Attribute) and func.attr == symbol_name:
                            matched = True
                            # [20251226_FEATURE] Pro tier: Distinguish method call context
                            if enable_categorization:
                                value = func.value
                                if isinstance(value, ast.Name):
                                    if value.id == "self":
                                        ref_type = "instance_method_call"
                                    elif value.id == "cls":
                                        ref_type = "class_method_call"
                                    elif value.id[0].isupper():
                                        # Heuristic: ClassName.method() is static/class method
                                        ref_type = "static_method_call"
                                    else:
                                        ref_type = "method_call"
                                else:
                                    ref_type = "method_call"
                            else:
                                ref_type = "call"

                    # Check name references (but avoid duplicating Call nodes)
                    elif isinstance(node, ast.Name) and node.id == symbol_name:
                        matched = True
                        if enable_categorization:
                            if isinstance(node.ctx, ast.Store):
                                # [20251226_FEATURE] Pro tier: Track first assignment vs reassignment
                                if symbol_name not in first_assigned:
                                    first_assigned.add(symbol_name)
                                    ref_type = "first_assignment"
                                else:
                                    ref_type = "reassignment"
                            elif isinstance(node.ctx, ast.Load):
                                ref_type = "read"
                            else:
                                ref_type = "reference"

                    if matched:
                        seen.add(loc_key)
                        context = lines[node_line - 1] if 0 < node_line <= len(lines) else ""
                        if enable_categorization:
                            category_counts[ref_type] = category_counts.get(ref_type, 0) + 1
                        if owners:
                            for owner in owners:
                                owner_counts[owner] = owner_counts.get(owner, 0) + 1
                        references.append(
                            SymbolReference(
                                file=rel_path,
                                line=node_line,
                                column=node_col,
                                context=context.strip(),
                                is_definition=is_def,
                                reference_type=(ref_type if enable_categorization else None),
                                is_test_file=is_test_file,
                                owners=owners,
                            )
                        )

                        if max_references is not None and len(references) >= max_references:
                            break

                if max_references is not None and len(references) >= max_references:
                    break

            except (SyntaxError, UnicodeDecodeError):
                # Skip files that can't be parsed
                continue

        # Sort: definitions first, then by file and line
        references.sort(key=lambda r: (not r.is_definition, r.file, r.line))

        # [20251220_FEATURE] v3.0.5 - Communicate truncation
        total_refs = len(references)
        refs_truncated = max_references is not None and total_refs >= max_references
        truncation_msg = None
        if refs_truncated:
            truncation_msg = "Results truncated: output reached the configured maximum reference limit."

        # [20251226_FEATURE] Enterprise: Advanced risk assessment with weighted factors
        change_risk = None
        risk_score = None
        risk_factors: list[str] | None = None
        blast_radius = None
        test_coverage_ratio = None
        complexity_hotspots_list: list[str] | None = None
        impact_mermaid = None
        codeowners_coverage = None

        unique_files = 0
        if enable_codeowners or enable_impact_analysis:
            unique_files = len({r.file for r in references})
            blast_radius = unique_files

            # Calculate test coverage ratio
            test_refs = sum(1 for r in references if r.is_test_file)
            test_coverage_ratio = test_refs / total_refs if total_refs > 0 else 0.0

            # Calculate CODEOWNERS coverage
            owned_refs = sum(1 for r in references if r.owners)
            codeowners_coverage = owned_refs / total_refs if total_refs > 0 else 0.0

        if enable_impact_analysis:
            # [20251226_FEATURE] Enterprise: Weighted risk score calculation
            risk_factors = []
            base_score = 0

            # Factor 1: Reference count (0-25 points)
            if total_refs >= 100:
                base_score += 25
                risk_factors.append(f"High reference count ({total_refs} references)")
            elif total_refs >= 50:
                base_score += 20
                risk_factors.append(f"Moderate reference count ({total_refs} references)")
            elif total_refs >= 20:
                base_score += 10
                risk_factors.append(f"Multiple references ({total_refs} references)")

            # Factor 2: Blast radius / unique files (0-25 points)
            if unique_files >= 20:
                base_score += 25
                risk_factors.append(f"Wide blast radius ({unique_files} files)")
            elif unique_files >= 10:
                base_score += 15
                risk_factors.append(f"Moderate blast radius ({unique_files} files)")
            elif unique_files >= 5:
                base_score += 8
                risk_factors.append(f"Multiple files affected ({unique_files} files)")

            # Factor 3: Test coverage (0-20 points, higher coverage = lower risk)
            if test_coverage_ratio is not None:
                if test_coverage_ratio < 0.1:
                    base_score += 20
                    risk_factors.append(f"Low test coverage ({test_coverage_ratio:.1%})")
                elif test_coverage_ratio < 0.3:
                    base_score += 10
                    risk_factors.append(f"Moderate test coverage ({test_coverage_ratio:.1%})")

            # Factor 4: Complexity hotspots (0-15 points)
            if file_complexity:
                hotspot_threshold = 15
                complexity_hotspots_list = [
                    f
                    for f, c in file_complexity.items()
                    if c >= hotspot_threshold and any(r.file == f for r in references)
                ]
                if len(complexity_hotspots_list) >= 5:
                    base_score += 15
                    risk_factors.append(f"Multiple complexity hotspots ({len(complexity_hotspots_list)} files)")
                elif len(complexity_hotspots_list) >= 2:
                    base_score += 8
                    risk_factors.append(f"Some complexity hotspots ({len(complexity_hotspots_list)} files)")

            # Factor 5: Ownership coverage (0-15 points, better coverage = lower risk)
            if codeowners_coverage is not None and codeowners_coverage < 0.5:
                base_score += 15
                risk_factors.append(f"Low ownership coverage ({codeowners_coverage:.1%})")
            elif codeowners_coverage is not None and codeowners_coverage < 0.8:
                base_score += 5
                risk_factors.append(f"Partial ownership coverage ({codeowners_coverage:.1%})")

            risk_score = min(100, base_score)

            # Determine risk level from score
            if risk_score >= 60:
                change_risk = "high"
            elif risk_score >= 30:
                change_risk = "medium"
            else:
                change_risk = "low"

            # [20251226_FEATURE] Enterprise: Generate impact Mermaid diagram
            if unique_files <= 20:  # Only generate for reasonable sizes
                mermaid_lines = ["graph TD"]
                mermaid_lines.append(f'    SYMBOL["{symbol_name}"]')
                file_nodes: dict[str, str] = {}
                for i, file in enumerate(sorted({r.file for r in references})):
                    node_id = f"F{i}"
                    file_nodes[file] = node_id
                    ref_count = sum(1 for r in references if r.file == file)
                    is_test = any(r.is_test_file for r in references if r.file == file)
                    label = file.replace("/", "_").replace(".", "_")
                    if is_test:
                        mermaid_lines.append(f'    {node_id}["{label} ({ref_count})"]:::test')
                    else:
                        mermaid_lines.append(f'    {node_id}["{label} ({ref_count})"]')
                    mermaid_lines.append(f"    SYMBOL --> {node_id}")
                mermaid_lines.append("    classDef test fill:#90EE90")
                impact_mermaid = "\n".join(mermaid_lines)

        elif enable_codeowners:
            # Simple risk assessment for CODEOWNERS-only (no impact_analysis)
            if total_refs >= 50 or unique_files >= 20:
                change_risk = "high"
            elif total_refs >= 10 or unique_files >= 5:
                change_risk = "medium"
            else:
                change_risk = "low"

        return SymbolReferencesResult(
            success=True,
            symbol_name=symbol_name,
            definition_file=definition_file,
            definition_line=definition_line,
            references=references,
            total_references=total_refs,
            files_scanned=len(candidate_files),
            total_files=total_files,
            files_truncated=files_truncated,
            file_truncation_warning=file_truncation_warning,
            category_counts=category_counts if enable_categorization else None,
            owner_counts=owner_counts if enable_codeowners else None,
            change_risk=change_risk,
            references_truncated=refs_truncated,
            truncation_warning=truncation_msg,
            # [20251226_FEATURE] Enterprise impact analysis fields
            risk_score=risk_score,
            risk_factors=risk_factors,
            blast_radius=blast_radius,
            test_coverage_ratio=test_coverage_ratio,
            complexity_hotspots=complexity_hotspots_list,
            impact_mermaid=impact_mermaid,
            codeowners_coverage=codeowners_coverage,
            # [20250112_FEATURE] Output metadata fields
            tier_applied=tier,
            max_files_applied=max_files,
            max_references_applied=max_references,
            pro_features_enabled=enabled_pro,
            enterprise_features_enabled=enabled_enterprise,
        )

    except Exception as e:
        return SymbolReferencesResult(
            success=False,
            symbol_name=symbol_name,
            error=f"Search failed: {str(e)}",
            tier_applied=tier,
            pro_features_enabled=enabled_pro,
            enterprise_features_enabled=enabled_enterprise,
        )


async def get_symbol_references(
    symbol_name: str,
    project_root: str | None = None,
    scope_prefix: str | None = None,
    include_tests: bool = True,
    ctx: Any | None = None,
) -> SymbolReferencesResult:
    """
    Find all references to a symbol across the project.

    **Tier Behavior:**
    - All tiers: Finds definition and usage references.
    - Community: Applies file/reference limits from the capability matrix.
    - Pro: Adds reference categorization and filtering controls.
    - Enterprise: Adds CODEOWNERS-based ownership attribution and risk metadata.

    [v1.4.0] Use this tool before modifying a function, class, or variable to
    understand its usage across the codebase. Essential for safe refactoring.

    [v3.0.5] Now reports progress as files are scanned.
    [v3.2.8] Tier-based result limiting for Community tier.

    Why AI agents need this:
    - Safe refactoring: know all call sites before changing signatures
    - Impact analysis: understand blast radius of changes
    - No hallucination: real references, not guessed ones

    Example::

        result = await get_symbol_references("process_order")

        # Returns SymbolReferencesResult:
        # - symbol_name: "process_order"
        # - definition_file: "services/order.py"
        # - definition_line: 42
        # - total_references: 7
        # - references: [
        #     SymbolReference(
        #         file="handlers/api.py",
        #         line=156,
        #         column=8,
        #         context="        result = process_order(order_data)",
        #         is_definition=False
        #     ),
        #     SymbolReference(
        #         file="tests/test_order.py",
        #         line=23,
        #         column=4,
        #         context="    process_order(mock_order)",
        #         is_definition=False
        #     ),
        #     ...
        # ]

        # Before changing function signature, check all call sites
        if result.total_references > 0:
            print(f"Warning: {result.total_references} call sites to update")

    Args:
        symbol_name: Name of the function, class, or variable to search for
        project_root: Project root directory (default: server's project root)

    Returns:
        SymbolReferencesResult with definition_file, definition_line, and all references
    """
    # [20251220_FEATURE] v3.0.5 - Progress reporting for file scanning
    if ctx:
        await ctx.report_progress(0, 100, f"Searching for '{symbol_name}'...")

    # [20251225_FEATURE] Capability-driven tier behavior (no upgrade hints)
    # [20251225_BUGFIX] Use the module-local tier helper to match licensing wiring.
    tier = get_current_tier()
    caps = get_tool_capabilities("get_symbol_references", tier) or {}
    limits = caps.get("limits", {}) if isinstance(caps, dict) else {}
    cap_list = caps.get("capabilities", []) if isinstance(caps, dict) else []
    cap_set = set(cap_list) if isinstance(cap_list, (list, set, tuple)) else set()

    max_files = limits.get("max_files_searched")
    if max_files is None:
        max_files = limits.get("max_files")

    max_references = limits.get("max_references")

    enable_categorization = bool(
        {"usage_categorization", "read_write_classification", "import_classification"} & cap_set
    )
    enable_codeowners = bool({"codeowners_integration", "ownership_attribution", "impact_analysis"} & cap_set)

    # Only allow Pro+ filtering controls when capability is present.
    effective_scope = scope_prefix if "scope_filtering" in cap_set else None
    effective_include_tests = include_tests if "test_file_filtering" in cap_set else True

    # [20251226_FEATURE] Enterprise: Enable impact analysis for advanced risk assessment
    enable_impact_analysis = bool({"impact_analysis", "change_risk_assessment"} & cap_set)

    result = await asyncio.to_thread(
        _get_symbol_references_sync,
        symbol_name,
        project_root,
        max_files,
        max_references,
        effective_scope,
        effective_include_tests,
        enable_categorization,
        enable_codeowners,
        enable_impact_analysis,
        tier=tier,
        capabilities=list(cap_set),
    )

    if ctx:
        await ctx.report_progress(100, 100, f"Found {result.total_references} references")

    return result
