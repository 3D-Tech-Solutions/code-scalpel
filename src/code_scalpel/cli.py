import argparse
import io
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path

from code_scalpel.mcp.protocol import format_tier_for_display


# [20260311_FEATURE] Keep CLI analyze choices aligned with the local analyzer
# and MCP language surface instead of a stale Python/JS/Java-only subset.
ANALYZE_LANGUAGE_CHOICES = [
    "python",
    "javascript",
    "typescript",
    "java",
    "c",
    "cpp",
    "csharp",
    "go",
    "kotlin",
    "php",
    "ruby",
    "swift",
    "rust",
]

# [20260311_BUGFIX] Symbolic execution and unit-test generation are still backed
# only by the narrower Python/JavaScript/Java engine paths.
SYMBOLIC_LANGUAGE_CHOICES = ["python", "javascript", "java"]


def analyze_file(
    filepath: str, output_format: str = "text", language: str | None = None
) -> int:
    """Analyze a file and print results."""

    path = Path(filepath)
    if not path.exists():
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        return 1

    # [20251219_BUGFIX] v3.0.4 - Extended language detection for TS/JSX/TSX
    if language is None:
        ext = path.suffix.lower()
        extension_map = {
            ".py": "python",
            ".pyw": "python",
            ".js": "javascript",
            ".mjs": "javascript",
            ".cjs": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".mts": "typescript",
            ".cts": "typescript",
            ".java": "java",
            # [20260302_FEATURE] C/C++/C# extensions added in v2.0.0
            ".c": "c",
            ".h": "c",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".c++": "cpp",
            ".hpp": "cpp",
            ".hxx": "cpp",
            ".hh": "cpp",
            ".h++": "cpp",
            ".inl": "cpp",
            ".cs": "csharp",
            # [20260304_FEATURE] Go/Kotlin/Ruby/PHP/Swift extensions
            ".go": "go",
            ".kt": "kotlin",
            ".kts": "kotlin",
            ".rb": "ruby",
            ".rake": "ruby",
            ".gemspec": "ruby",
            ".php": "php",
            ".php3": "php",
            ".php4": "php",
            ".php5": "php",
            ".phtml": "php",
            ".swift": "swift",
            ".rs": "rust",
        }
        if ext in extension_map:
            language = extension_map[ext]
        else:
            print(
                f"Warning: Unknown extension {path.suffix}, defaulting to Python",
                file=sys.stderr,
            )
            language = "python"

    try:
        code = path.read_text(encoding="utf-8")
        # [20251219_BUGFIX] v3.0.4 - Strip UTF-8 BOM if present
        if code.startswith("\ufeff"):
            code = code[1:]
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return 1

    return analyze_code(code, output_format, filepath, language)


def _analyze_javascript(code: str, output_format: str, source: str) -> int:
    """Analyze JavaScript code using SymbolicAnalyzer."""
    from .symbolic_execution_tools import SymbolicAnalyzer

    analyzer = SymbolicAnalyzer()
    try:
        result = analyzer.analyze(code, language="javascript")
    except Exception as e:
        print(f"Error analyzing JavaScript code: {e}", file=sys.stderr)
        return 1

    if output_format == "json":
        output = {
            "source": source,
            "language": "javascript",
            "success": True,
            "paths": [
                {
                    "id": p.path_id,
                    "status": p.status.value,
                    "model": p.model,
                }
                for p in result.paths
            ],
            "feasible_count": result.feasible_count,
            "infeasible_count": result.infeasible_count,
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\nCode Scalpel Analysis (JavaScript): {source}")
        print("=" * 60)
        print(f"Feasible paths: {result.feasible_count}")
        print(f"Infeasible paths: {result.infeasible_count}")
        print("-" * 60)
        for p in result.get_feasible_paths():
            print(f"Path {p.path_id}: {p.status.value}")
            if p.model:
                print(f"  Model: {p.model}")

    return 0


def _analyze_java(code: str, output_format: str, source: str) -> int:
    """Analyze Java code using SymbolicAnalyzer."""
    from .symbolic_execution_tools import SymbolicAnalyzer

    analyzer = SymbolicAnalyzer()
    try:
        result = analyzer.analyze(code, language="java")
    except Exception as e:
        print(f"Error analyzing Java code: {e}", file=sys.stderr)
        return 1

    if output_format == "json":
        output = {
            "source": source,
            "language": "java",
            "success": True,
            "paths": [
                {
                    "id": p.path_id,
                    "status": p.status.value,
                    "model": p.model,
                }
                for p in result.paths
            ],
            "feasible_count": result.feasible_count,
            "infeasible_count": result.infeasible_count,
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\nCode Scalpel Analysis (Java): {source}")
        print("=" * 60)
        print(f"Feasible paths: {result.feasible_count}")
        print(f"Infeasible paths: {result.infeasible_count}")
        print("-" * 60)
        for p in result.get_feasible_paths():
            print(f"Path {p.path_id}: {p.status.value}")
            if p.model:
                print(f"  Model: {p.model}")

    return 0


def _analyze_polyglot(code: str, output_format: str, source: str, language: str) -> int:
    """Analyze non-Python/JS/Java code via the polyglot IR extractor.

    [20260304_FEATURE] Routes C/C++/C#/TS/Go/PHP/Ruby/Kotlin/Swift
    through PolyglotExtractor for consistent IR-based analysis.
    """
    from .code_parsers.extractor import Language as ExtractorLanguage, PolyglotExtractor
    from .ir.nodes import IRClassDef, IRFunctionDef

    try:
        lang_enum = ExtractorLanguage(language)
    except ValueError:
        lang_enum = ExtractorLanguage.AUTO

    try:
        extractor = PolyglotExtractor(code, file_path=source, language=lang_enum)
        extractor._parse()
        ir_module = extractor._ir_module
    except Exception as e:
        print(f"Error analyzing {language} code: {e}", file=sys.stderr)
        return 1

    functions = []
    classes = []
    if ir_module is not None:
        for node in getattr(ir_module, "body", []):
            line_start = node.loc.line if node.loc else None
            line_end = node.loc.end_line if node.loc else None
            if isinstance(node, IRFunctionDef):
                functions.append(
                    {"name": node.name, "line_start": line_start, "line_end": line_end}
                )
            elif isinstance(node, IRClassDef):
                classes.append(
                    {"name": node.name, "line_start": line_start, "line_end": line_end}
                )

    if output_format == "json":
        output = {
            "source": source,
            "language": language,
            "success": True,
            "functions": functions,
            "classes": classes,
            "metrics": {"num_functions": len(functions), "num_classes": len(classes)},
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\nCode Scalpel Analysis ({language.upper()}): {source}")
        print("=" * 60)
        print(f"Functions found: {len(functions)}")
        for f in functions:
            line_info = f" (line {f['line_start']})" if f.get("line_start") else ""
            print(f"  - {f['name']}{line_info}")
        print(f"Classes found: {len(classes)}")
        for c in classes:
            line_info = f" (line {c['line_start']})" if c.get("line_start") else ""
            print(f"  - {c['name']}{line_info}")
    return 0


def analyze_code(
    code: str,
    output_format: str = "text",
    source: str = "<string>",
    language: str = "python",
) -> int:
    """Analyze code string and print results."""
    if language == "javascript":
        return _analyze_javascript(code, output_format, source)
    if language == "java":
        return _analyze_java(code, output_format, source)
    # [20260304_FEATURE] Route non-Python/JS/Java through polyglot extractor
    if language in (
        "c",
        "cpp",
        "csharp",
        "typescript",
        "go",
        "php",
        "ruby",
        "kotlin",
        "swift",
        "rust",
    ):
        return _analyze_polyglot(code, output_format, source, language)

    from .code_analyzer import AnalysisLevel, CodeAnalyzer

    analyzer = CodeAnalyzer(level=AnalysisLevel.STANDARD)

    try:
        result = analyzer.analyze(code)
    except Exception as e:
        print(f"Error analyzing code: {e}", file=sys.stderr)
        return 1

    if output_format == "json":
        output = {
            "source": source,
            "success": not result.errors,
            "metrics": {
                "lines_of_code": result.metrics.lines_of_code,
                "num_functions": result.metrics.num_functions,
                "num_classes": result.metrics.num_classes,
                "cyclomatic_complexity": result.metrics.cyclomatic_complexity,
                "analysis_time_seconds": result.metrics.analysis_time_seconds,
            },
            "dead_code": [
                {
                    "name": dc.name,
                    "type": dc.code_type,
                    "line_start": dc.line_start,
                    "line_end": dc.line_end,
                    "reason": dc.reason,
                }
                for dc in result.dead_code
            ],
            "security_issues": result.security_issues,
            "suggestions": [
                {
                    "type": s.refactor_type,
                    "description": s.description,
                    "priority": s.priority,
                }
                for s in result.refactor_suggestions
            ],
            "errors": result.errors,
        }
        print(json.dumps(output, indent=2))
    else:
        # Text format
        print(f"\nCode Scalpel Analysis: {source}")
        print("=" * 60)

        print("\nMetrics:")
        print(f"   Lines of code: {result.metrics.lines_of_code}")
        print(f"   Functions: {result.metrics.num_functions}")
        print(f"   Classes: {result.metrics.num_classes}")
        print(f"   Cyclomatic complexity: {result.metrics.cyclomatic_complexity}")
        print(f"   Analysis time: {result.metrics.analysis_time_seconds:.3f}s")

        if result.dead_code:
            print(f"\nDead Code Detected ({len(result.dead_code)} items):")
            for dc in result.dead_code:
                print(
                    f"   - {dc.code_type} '{dc.name}' (lines {dc.line_start}-{dc.line_end})"
                )
                print(f"     Reason: {dc.reason}")

        if result.security_issues:
            print(f"\n[WARNING] Security Issues ({len(result.security_issues)}):")
            for issue in result.security_issues:
                print(
                    f"   - {issue.get('type', 'Unknown')}: {issue.get('description', 'No description')}"
                )

        if result.refactor_suggestions:
            print(f"\nSuggestions ({len(result.refactor_suggestions)}):")
            for s in result.refactor_suggestions[:5]:  # Show top 5
                print(f"   - [{s.refactor_type}] {s.description}")

        if result.errors:
            print("\n[ERROR] Errors:")
            for err in result.errors:
                print(f"   - {err}")

        print()

    return 0 if not result.errors else 1


def scan_security(filepath: str, output_format: str = "text") -> int:
    """Scan a file for security vulnerabilities using taint analysis."""
    from .symbolic_execution_tools import analyze_security

    path = Path(filepath)
    if not path.exists():
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        return 1

    try:
        code = path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return 1

    try:
        result = analyze_security(code)
    except Exception as e:
        print(f"Error during security analysis: {e}", file=sys.stderr)
        return 1

    if output_format == "json":
        output = {
            "source": str(filepath),
            "has_vulnerabilities": result.has_vulnerabilities,
            "vulnerability_count": result.vulnerability_count,
            "vulnerabilities": [
                {
                    "type": v.vulnerability_type,
                    "cwe": v.cwe_id,
                    "source": v.taint_source.name,
                    "sink": v.sink_type.name,
                    "line": v.sink_location[0] if v.sink_location else None,
                    "taint_path": v.taint_path,
                }
                for v in result.vulnerabilities
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\nCode Scalpel Security Scan: {filepath}")
        print("=" * 60)

        if not result.has_vulnerabilities:
            print("\n[OK] No vulnerabilities detected.")
        else:
            print(
                f"\n[WARNING] Found {result.vulnerability_count} vulnerability(ies):\n"
            )
            for i, v in enumerate(result.vulnerabilities, 1):
                print(f"  {i}. {v.vulnerability_type} ({v.cwe_id})")
                print(f"     Source: {v.taint_source.name}")
                print(f"     Sink: {v.sink_type.name}")
                if v.sink_location:
                    print(f"     Line: {v.sink_location[0]}")
                print(f"     Taint Path: {' -> '.join(v.taint_path)}")
                print()

        print(result.summary())

    return 0 if not result.has_vulnerabilities else 2


def scan_code_security(code: str, output_format: str = "text") -> int:
    """Scan code string for security vulnerabilities."""
    from .symbolic_execution_tools import analyze_security

    try:
        result = analyze_security(code)
    except Exception as e:
        print(f"Error during security analysis: {e}", file=sys.stderr)
        return 1

    if output_format == "json":
        output = {
            "source": "<string>",
            "has_vulnerabilities": result.has_vulnerabilities,
            "vulnerability_count": result.vulnerability_count,
            "vulnerabilities": [
                {
                    "type": v.vulnerability_type,
                    "cwe": v.cwe_id,
                    "source": v.taint_source.name,
                    "sink": v.sink_type.name,
                    "line": v.sink_location[0] if v.sink_location else None,
                    "taint_path": v.taint_path,
                }
                for v in result.vulnerabilities
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        print("\nCode Scalpel Security Scan: <string>")
        print("=" * 60)

        if not result.has_vulnerabilities:
            print("\n[OK] No vulnerabilities detected.")
        else:
            print(
                f"\n[WARNING] Found {result.vulnerability_count} vulnerability(ies):\n"
            )
            for i, v in enumerate(result.vulnerabilities, 1):
                print(f"  {i}. {v.vulnerability_type} ({v.cwe_id})")
                print(f"     Source: {v.taint_source.name}")
                print(f"     Sink: {v.sink_type.name}")
                if v.sink_location:
                    print(f"     Line: {v.sink_location[0]}")
                print(f"     Taint Path: {' -> '.join(v.taint_path)}")
                print()

        print(result.summary())

    return 0 if not result.has_vulnerabilities else 2


def check_configuration(
    target_dir: str = ".", json_output: bool = False, fix: bool = False
) -> int:
    """Check .code-scalpel directory for missing configuration files.

    [20260224_FEATURE] check command - inspect an existing .code-scalpel dir and
    report which expected files are present, missing-but-recommended, or missing-and-required.

    [20260224_FEATURE] Extended with file integrity validation: detects empty files,
    JSON/YAML parse errors, and Rego files missing a 'package' declaration.

    [20260224_FEATURE] --fix flag: calls add_missing_config_files before reporting
    so missing files are filled in and the output reflects the post-fix state.
    """
    import json as _json

    from .config.init_config import add_missing_config_files, validate_config_files

    target_path = Path(target_dir).resolve()
    config_dir = target_path / ".code-scalpel"

    # ------------------------------------------------------------------ #
    # Catalogue of files produced by `codescalpel init`                    #
    # Grouped by importance so the user knows what actually matters.       #
    # ------------------------------------------------------------------ #
    REQUIRED: list[tuple[str, str]] = [
        ("config.json", "Core settings (tier, paths, feature flags)"),
        ("policy.yaml", "Security & coding-style policy rules"),
        ("budget.yaml", "Change-budget limits for AI operations"),
        ("response_config.json", "Response verbosity & token-efficiency settings"),
    ]
    RECOMMENDED: list[tuple[str, str]] = [
        ("dev-governance.yaml", "Development governance rules"),
        ("project-structure.yaml", "Project structure expectations"),
        ("response_config.schema.json", "JSON schema for response_config.json"),
        ("policy.manifest.json", "Cryptographic manifest for policy integrity"),
        ("audit.log", "Audit trail for agent operations"),
        ("license/README.md", "License directory with setup instructions"),
        (
            "policies/architecture/layered_architecture.rego",
            "Architecture boundary policy",
        ),
        ("policies/devops/docker_security.rego", "Docker security policy"),
        ("policies/devsecops/secret_detection.rego", "Secret detection policy"),
        ("policies/project/structure.rego", "Project structure policy"),
    ]
    OPTIONAL: list[tuple[str, str]] = [
        (".gitignore", "Prevents accidental secret commits from this directory"),
        ("README.md", "Configuration reference documentation"),
        ("ide-extension.json", "IDE extension settings"),
        ("HOOKS_README.md", "Git hooks integration guide"),
        (".env.example", "Example environment variables template"),
    ]

    # ------------------------------------------------------------------ #
    # Existence check                                                       #
    # ------------------------------------------------------------------ #
    def _check(entries: list[tuple[str, str]]) -> tuple[list[str], list[str]]:
        present, missing = [], []
        for name, _ in entries:
            (present if (config_dir / name).exists() else missing).append(name)
        return present, missing

    if not config_dir.exists():
        if json_output:
            print(
                _json.dumps(
                    {
                        "success": False,
                        "error": "no_config_dir",
                        "message": f".code-scalpel directory not found at {config_dir}",
                        "suggestion": f"Run: codescalpel init --dir {target_dir}",
                    },
                    indent=2,
                )
            )
        else:
            print(f"[ERROR] .code-scalpel directory not found: {config_dir}")
            print(f"\nRun 'codescalpel init --dir {target_dir}' to create it.")
        return 1

    # ------------------------------------------------------------------ #
    # --fix: fill in missing files before reporting                         #
    # ------------------------------------------------------------------ #
    _fixed: dict | None = None
    if fix:
        _fixed = add_missing_config_files(str(target_path))

    req_present, req_missing = _check(REQUIRED)
    rec_present, rec_missing = _check(RECOMMENDED)
    opt_present, opt_missing = _check(OPTIONAL)

    all_missing = req_missing + rec_missing + opt_missing
    all_present = req_present + rec_present + opt_present

    # ------------------------------------------------------------------ #
    # Integrity check (parse errors, empty files)                          #
    # ------------------------------------------------------------------ #
    integrity = validate_config_files(config_dir)

    # Detect empty files among all present catalogue entries.
    empty_files: list[str] = []
    for name in all_present:
        fpath = config_dir / name
        if fpath.is_file() and fpath.stat().st_size == 0:
            empty_files.append(name)

    # Build a set of file names (relative to config_dir) that have parse errors.
    _parse_error_names: set[str] = set()
    for err in integrity["errors"]:
        # Errors look like "config.json: Invalid JSON - ..." or
        # "policies/arch/layered.rego: Read error - ..."
        _parse_error_names.add(err.split(":")[0].strip())

    # Required files that fail integrity (either empty or parse error).
    req_integrity_failures = [
        n for n in req_present if n in empty_files or n in _parse_error_names
    ]

    integrity_ok = integrity["success"] and not empty_files

    # ------------------------------------------------------------------ #
    # JSON output                                                          #
    # ------------------------------------------------------------------ #
    if json_output:
        details: dict[str, dict] = {}
        req_map = dict(REQUIRED)
        rec_map = dict(RECOMMENDED)
        for name, desc in REQUIRED + RECOMMENDED + OPTIONAL:
            level = (
                "required"
                if name in req_map
                else ("recommended" if name in rec_map else "optional")
            )
            present = (config_dir / name).exists()
            file_integrity: dict = {}
            if present:
                fpath = config_dir / name
                is_empty = fpath.is_file() and fpath.stat().st_size == 0
                parse_error = next(
                    (e for e in integrity["errors"] if e.startswith(name + ":")),
                    None,
                )
                file_integrity = {
                    "empty": is_empty,
                    "parse_error": parse_error,
                    "ok": not is_empty and parse_error is None,
                }
            details[name] = {
                "present": present,
                "level": level,
                "description": desc,
                **({"integrity": file_integrity} if present else {}),
            }
        print(
            _json.dumps(
                {
                    "success": len(req_missing) == 0 and not req_integrity_failures,
                    "config_dir": str(config_dir),
                    "fix_applied": _fixed,
                    "summary": {
                        "required_missing": len(req_missing),
                        "recommended_missing": len(rec_missing),
                        "optional_missing": len(opt_missing),
                        "total_present": len(all_present),
                    },
                    "integrity": {
                        "ok": integrity_ok,
                        "errors": integrity["errors"],
                        "warnings": integrity["warnings"]
                        + [f"{f}: file is empty" for f in empty_files],
                        "files_validated": integrity["files_validated"],
                    },
                    "files": details,
                    "suggestion": (
                        f"Run 'codescalpel init --dir {target_dir}' to add missing defaults "
                        "without overwriting existing files."
                        if all_missing
                        else "All files are present."
                    ),
                },
                indent=2,
            )
        )
        return 0 if (not req_missing and not req_integrity_failures) else 1

    # ------------------------------------------------------------------ #
    # Human-readable output                                                #
    # ------------------------------------------------------------------ #
    print("Code Scalpel Configuration Check")
    print("=" * 60)
    print(f"Directory: {config_dir}")
    print()

    if _fixed is not None:
        if _fixed["files_added"]:
            print(f"[FIX] Added {len(_fixed['files_added'])} missing file(s):")
            for _f in _fixed["files_added"]:
                print(f"   + {_f}")
        else:
            print("[FIX] Nothing to add \u2014 all files already present.")
        print()

    def _print_group(
        label: str,
        entries: list[tuple[str, str]],
        present: list[str],
        missing_icon: str,
    ) -> None:
        print(f"{label}")
        desc_map = dict(entries)
        for name in [e[0] for e in entries]:
            if name in present:
                # Add integrity annotation if there's an issue
                if name in empty_files:
                    print(f"   ⚠️   {name}  [EMPTY FILE]")
                elif name in _parse_error_names:
                    err = next(
                        (e for e in integrity["errors"] if e.startswith(name + ":")), ""
                    )
                    print(
                        f"   ❌  {name}  [PARSE ERROR: {err.split(':', 1)[-1].strip()}]"
                    )
                else:
                    print(f"   ✅  {name}")
            else:
                print(f"   {missing_icon}  {name}")
                print(f"         {desc_map[name]}")
        print()

    _print_group("Required files:", REQUIRED, req_present, "❌")
    _print_group("Recommended files:", RECOMMENDED, rec_present, "⚠️ ")
    _print_group("Optional files:", OPTIONAL, opt_present, "○ ")

    # ------------------------------------------------------------------ #
    # Integrity warnings                                                   #
    # ------------------------------------------------------------------ #
    if integrity["warnings"]:
        print("Integrity warnings:")
        for w in integrity["warnings"]:
            print(f"   ⚠️   {w}")
        if empty_files:
            for f in empty_files:
                print(f"   ⚠️   {f}: file is empty (0 bytes)")
        print()
    elif empty_files:
        print("Integrity warnings:")
        for f in empty_files:
            print(f"   ⚠️   {f}: file is empty (0 bytes)")
        print()

    # ------------------------------------------------------------------ #
    # Summary & suggestion                                                 #
    # ------------------------------------------------------------------ #
    if not all_missing and integrity_ok:
        print("[OK] All expected configuration files are present and valid.")
        return 0

    print("-" * 60)
    if req_missing:
        print(
            f"[FAIL]  {len(req_missing)} required file(s) missing — some features will not work."
        )
    if req_integrity_failures:
        print(
            f"[FAIL]  {len(req_integrity_failures)} required file(s) have integrity errors — {', '.join(req_integrity_failures)}"
        )
    if rec_missing:
        print(
            f"[WARN]  {len(rec_missing)} recommended file(s) missing — some features may be degraded."
        )
    if opt_missing:
        print(f"[INFO]  {len(opt_missing)} optional file(s) missing.")
    if empty_files and not req_integrity_failures:
        print(f"[WARN]  {len(empty_files)} file(s) are empty: {', '.join(empty_files)}")
    print()
    if all_missing and not fix:
        if req_missing or rec_missing:
            print("Add missing files (safe \u2014 never overwrites existing files):")
            print(f"   codescalpel init --dir {target_dir}")
            print(
                f"   codescalpel check --fix --dir {target_dir}  # check + fix in one step"
            )
        else:
            print("Optional files can be added if needed:")
            print(f"   codescalpel init --dir {target_dir}")

    return 0 if (not req_missing and not req_integrity_failures) else 1


def init_configuration(target_dir: str = ".", force: bool = False) -> int:
    """Initialize .code-scalpel configuration directory.

    [20251219_FEATURE] v3.0.2 - Auto-initialize configuration for first-time users.
    Creates .code-scalpel/ with config.json, policy.yaml, budget.yaml, README.md, .gitignore.

    [20260224_FEATURE] When .code-scalpel already exists, seamlessly add any
    files that were introduced in newer releases without touching existing ones.
    This makes `codescalpel init` safe to re-run after upgrading.
    """
    from .config import init_config_dir
    from .config.init_config import add_missing_config_files

    print("Code Scalpel Configuration Initialization")
    print("=" * 60)

    result = init_config_dir(target_dir)

    if not result["success"]:
        if "already exists" in result["message"]:
            if force:
                print("\n[WARNING] Directory exists, but --force specified.")
                print(f"   Path: {result['path']}")
                print("\n[SKIP] Use manual deletion if you need to reinitialize.")
                return 1
            # Directory already exists — fill in any files missing from this version.
            print(
                "\n[INFO] Configuration directory already exists — checking for missing files..."
            )
            print(f"   Path: {result['path']}")
            update = add_missing_config_files(target_dir)
            if update["files_added"]:
                print(f"\n[UPDATED] Added {len(update['files_added'])} new file(s):")
                for f in update["files_added"]:
                    print(f"   + {f}")
            else:
                print("\n[OK] All files are already present — nothing to add.")
            if update["files_skipped"]:
                print(
                    f"\n   Kept {len(update['files_skipped'])} existing file(s) unchanged."
                )
            print()
            print("Tip: run 'codescalpel check' to verify the configuration.")
            return 0
        else:
            print(f"\n[ERROR] {result['message']}")
            return 1

    print("\n[SUCCESS] Configuration directory created:")
    print(f"   Path: {result['path']}")
    print(f"\nCreated {len(result['files_created'])} files:")
    for filename in result["files_created"]:
        print(f"   - {filename}")

    # [20241225_FEATURE] v3.3.0 - Show validation results
    if "validation" in result:
        validation = result["validation"]
        print(
            f"\n[VALIDATION] Checked {len(validation['files_validated'])} configuration files:"
        )
        if validation["success"]:
            print("   ✅ All files have valid syntax")
        else:
            print("   ❌ Found validation errors:")
            for error in validation["errors"]:
                print(f"      - {error}")
        if validation["warnings"]:
            print("   ⚠️  Warnings:")
            for warning in validation["warnings"]:
                print(f"      - {warning}")

    # [20241225_FEATURE] v3.3.0 - Show manifest info
    if result.get("manifest_secret"):
        print("\n[SECURITY] Policy Integrity Manifest Generated:")
        print("   ✅ Cryptographic manifest created: policy_manifest.json")
        print("   ✅ HMAC secret saved to: .env")
        print("   ⚠️  CRITICAL: The .env file contains a secret key!")
        print("   ⚠️  DO NOT commit .env to git (already in .gitignore)")
        print("\n   Next steps for production:")
        print("   1. Copy SCALPEL_MANIFEST_SECRET from .env to your CI/CD secrets")
        print("   2. Delete .env locally (or keep for development)")
        print("   3. Commit policy_manifest.json to git")
        print("   4. Test with: codescalpel verify-policies")

    print("\nNext steps:")
    print("   1. Review policy.yaml to configure security rules")
    print("   2. Review budget.yaml to set change limits")
    print("   3. Read README.md for configuration guidance")
    print("   4. Add .code-scalpel/ to version control (recommended)")
    print("   5. Set SCALPEL_MANIFEST_SECRET in CI/CD for policy verification")

    return 0


def start_server(host: str = "127.0.0.1", port: int = 5000) -> int:
    """Start the REST API server (legacy, for non-MCP clients).

    [20251223_SECURITY] Default binding is localhost-only.
    Use --host 0.0.0.0 to allow LAN access on trusted networks.
    """
    from .integrations.rest_api_server import run_server  # type: ignore[reportAttributeAccessIssue]

    print(f"Starting Code Scalpel REST API Server on {host}:{port}")
    print(f"   Health check: http://{host}:{port}/health")
    print(f"   Analyze endpoint: POST http://{host}:{port}/analyze")
    print(f"   Refactor endpoint: POST http://{host}:{port}/refactor")
    print(f"   Security endpoint: POST http://{host}:{port}/security")
    print(
        "\nNote: For MCP-compliant clients (Claude Desktop, Cursor), use 'codescalpel mcp' instead."
    )
    print("Press Ctrl+C to stop the server.\n")

    try:
        run_server(host=host, port=port, debug=False)
    except KeyboardInterrupt:
        print("\nServer stopped.")

    return 0


def start_mcp_server(
    transport: str = "stdio",
    host: str = "127.0.0.1",
    port: int = 8080,
    allow_lan: bool = False,
    root_path: str | None = None,
    tier: str | None = None,
    ssl_certfile: str | None = None,
    ssl_keyfile: str | None = None,
    license_file: str | None = None,
    mismatch_action: str | None = None,
) -> int:
    """Start the MCP-compliant server (for AI clients like Claude Desktop, Cursor).

    [20260125_FEATURE] Phase 3: Transport Optimization
    - TIER 1 (PRIMARY): stdio - optimized for local clients (Claude Desktop, Cursor)
      * Direct bidirectional pipe communication
      * Zero network overhead
      * Minimal latency (microseconds)
      * No SSL/TLS complexity
      * Default and recommended for Claude Desktop integration

    - TIER 2 (FALLBACK): HTTP (sse or streamable-http) - for network deployments
      * Required for remote/network clients
      * Higher latency due to network stack
      * Optional HTTPS support (--ssl-cert, --ssl-key)
      * Useful for Docker, Kubernetes, multi-machine setups
    """
    import inspect

    # Prefer archive.server if present; fall back to mcp.server for older layouts.
    try:
        from .mcp.archive.server import run_server
    except Exception:
        try:
            from .mcp.server import run_server
        except Exception:
            # Let the original ImportError propagate with clear message
            raise

    # [20251228_FEATURE] Support explicit license file path for deployments.
    # Fail fast to avoid silently falling back to other discovery paths.
    if license_file:
        license_path = Path(license_file).expanduser()
        if not (license_path.exists() and license_path.is_file()):
            print(f"Error: License file not found: {license_file}", file=sys.stderr)
            return 1
        try:
            license_path.open("rb").close()
        except OSError as e:
            print(
                f"Error: License file not readable: {license_file} ({e})",
                file=sys.stderr,
            )
            return 1
        os.environ["CODE_SCALPEL_LICENSE_PATH"] = str(license_path)

    if mismatch_action:
        os.environ["CODE_SCALPEL_VERSION_MISMATCH_ACTION"] = mismatch_action

    # [20251215_FEATURE] Determine protocol based on SSL config
    use_https = ssl_certfile and ssl_keyfile
    protocol = "https" if use_https else "http"

    if transport == "stdio":
        # For stdio transport, avoid writing informational banners to stdout
        # because stdout is reserved for the MCP JSON-RPC stream. Use stderr
        # for human-facing messages to avoid corrupting the protocol.
        print("Starting Code Scalpel MCP Server (stdio transport)", file=sys.stderr)
        print("   This server communicates via stdin/stdout.", file=sys.stderr)
        print(
            "   Add to your Claude Desktop config or use with MCP Inspector.",
            file=sys.stderr,
        )
        print("\nIMPORTANT: Do not type commands here!", file=sys.stderr)
        print(
            "   This terminal is now a JSON-RPC pipe for MCP communication.",
            file=sys.stderr,
        )
        print(
            "   Any text you type will be ignored (it's not valid JSON-RPC).",
            file=sys.stderr,
        )
        print("\nPress Ctrl+C to stop.\n", file=sys.stderr)
    else:
        print(
            f"Starting Code Scalpel MCP Server ({protocol.upper()} transport) on {host}:{port}"
        )
        endpoint_path = "/mcp" if transport == "streamable-http" else "/sse"
        print(f"   MCP endpoint: {protocol}://{host}:{port}{endpoint_path}")
        if use_https:
            print("   SSL/TLS: ENABLED")
        if allow_lan:
            print("   LAN access: ENABLED (host validation disabled)")
            print("   WARNING: Only use on trusted networks!")
        print("\nPress Ctrl+C to stop.\n")

    # [20251216_BUGFIX] Avoid passing SSL kwargs when not configured to maintain compatibility with minimal run_server signatures
    server_kwargs = {
        "transport": transport,
        "host": host,
        "port": port,
        "allow_lan": allow_lan,
        "root_path": root_path,
        "tier": tier,
    }
    if use_https:
        server_kwargs.update(
            {
                "ssl_certfile": ssl_certfile,
                "ssl_keyfile": ssl_keyfile,
            }
        )

    def _filter_kwargs_for_callable(func, kwargs: dict) -> dict:
        try:
            sig = inspect.signature(func)
        except Exception:
            return kwargs

        # If the callable accepts **kwargs, keep all.
        for param in sig.parameters.values():
            if param.kind == inspect.Parameter.VAR_KEYWORD:
                return kwargs

        allowed = set(sig.parameters.keys())
        return {k: v for k, v in kwargs.items() if k in allowed}

    try:
        run_server(**_filter_kwargs_for_callable(run_server, server_kwargs))
    except KeyboardInterrupt:
        if transport == "stdio":
            print("\nMCP Server stopped.", file=sys.stderr)
        else:
            print("\nMCP Server stopped.")

    return 0


def _license_install(
    source_path: str, dest_path: str | None = None, force: bool = False
) -> int:
    """[20251228_FEATURE] Implements `code-scalpel license install`.

    Args:
        source_path: Path to the license JWT file provided by the user.
        dest_path: Optional explicit destination path. Defaults to XDG user config.
        force: Overwrite destination if it exists.
    """

    from code_scalpel.licensing.jwt_validator import JWTLicenseValidator

    src = Path(source_path).expanduser()
    if not (src.exists() and src.is_file()):
        print(f"Error: License file not found: {source_path}", file=sys.stderr)
        return 1

    try:
        token = src.read_text(encoding="utf-8").strip()
    except OSError as e:
        print(f"Error: License file not readable: {source_path} ({e})", file=sys.stderr)
        return 1

    if not token:
        print("Error: License file is empty", file=sys.stderr)
        return 1

    validator = JWTLicenseValidator()
    data = validator.validate_token(token)
    if not data.is_valid:
        msg = data.error_message or "Invalid license"
        print(f"Error: {msg}", file=sys.stderr)
        return 1

    # Default destination: XDG user config
    if dest_path is None:
        xdg_home = Path(os.getenv("XDG_CONFIG_HOME") or (Path.home() / ".config"))
        dest = xdg_home / "code-scalpel" / "license.jwt"
    else:
        dest = Path(dest_path).expanduser()

    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and not force:
        print(
            f"Error: Destination already exists: {dest} (use --force to overwrite)",
            file=sys.stderr,
        )
        return 1

    try:
        dest.write_text(token + "\n", encoding="utf-8")
        try:
            os.chmod(dest, 0o600)
        except OSError:
            # Best-effort; permissions may be controlled externally (Windows, some FS).
            pass
    except OSError as e:
        print(f"Error: Failed to write license to {dest} ({e})", file=sys.stderr)
        return 1

    # Do not print token content.
    print("✓ License valid")
    print(f"✓ Tier: {format_tier_for_display(data.tier)}")
    print(f"✓ Installed to: {dest}")
    return 0


def verify_policies_command(
    policy_dir: str = ".code-scalpel", manifest_source: str = "file"
) -> int:
    """Verify policy integrity using cryptographic signatures.

    [20241225_FEATURE] v3.3.0 - CLI command for policy verification
    """
    import os

    from .policy_engine.crypto_verify import CryptographicPolicyVerifier

    print("Code Scalpel Policy Integrity Verification")
    print("=" * 60)

    # Check for HMAC secret
    secret = os.getenv("SCALPEL_MANIFEST_SECRET")
    if not secret:
        print("\n[ERROR] SCALPEL_MANIFEST_SECRET environment variable not set")
        print("\nThis secret is required to verify policy integrity.")
        print("Find your secret in: .env (if using codescalpel init)")
        print("\nFor production:")
        print("   export SCALPEL_MANIFEST_SECRET=<your-secret-key>")
        return 1

    try:
        verifier = CryptographicPolicyVerifier(
            policy_dir=policy_dir, secret_key=secret, manifest_source=manifest_source
        )
        result = verifier.verify_all_policies()

        if result.success:
            print("\n[SUCCESS] ✅ All policies verified successfully")
            print(f"   Verified {result.files_verified} policy files")
            if verifier.manifest:
                print(f"   Manifest signed by: {verifier.manifest.signed_by}")
                print(f"   Manifest created: {verifier.manifest.created_at}")
            return 0
        else:
            print("\n[FAILURE] ❌ Policy verification failed")
            print(f"\n   Error: {result.error}")
            if result.files_failed:
                print("\n   Failed files:")
                for filepath in result.files_failed:
                    print(f"      - {filepath}")
            return 2

    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}")
        return 1


def regenerate_manifest_command(
    policy_dir: str = ".code-scalpel", signed_by: str = "code-scalpel"
) -> int:
    """Regenerate policy manifest after policy changes.

    [20241225_FEATURE] v3.3.0 - CLI command for manifest regeneration
    """
    import os
    from pathlib import Path

    from .config.init_config import generate_secret_key
    from .policy_engine.crypto_verify import CryptographicPolicyVerifier

    print("Code Scalpel Policy Manifest Regeneration")
    print("=" * 60)

    # Check for existing secret or generate new one
    secret = os.getenv("SCALPEL_MANIFEST_SECRET")
    if not secret:
        print("\n[WARNING] SCALPEL_MANIFEST_SECRET not set, generating new secret...")
        secret = generate_secret_key()
        print(f"\n   New secret: {secret}")
        print("   ⚠️  Save this secret securely!")
        print("   ⚠️  Add it to .env: SCALPEL_MANIFEST_SECRET=<secret>")

    policy_path = Path(policy_dir)
    if not policy_path.exists():
        print(f"\n[ERROR] Policy directory not found: {policy_dir}")
        return 1

    # Find all policy files
    policy_files = []
    for pattern in ["*.yaml", "*.yml", "policies/**/*.rego"]:
        policy_files.extend(
            [str(f.relative_to(policy_path)) for f in policy_path.glob(pattern)]
        )

    if not policy_files:
        print(f"\n[ERROR] No policy files found in {policy_dir}")
        return 1

    print(f"\n[INFO] Found {len(policy_files)} policy files:")
    for filepath in sorted(policy_files):
        print(f"   - {filepath}")

    try:
        # Create manifest
        manifest = CryptographicPolicyVerifier.create_manifest(
            policy_files=policy_files,
            secret_key=secret,
            signed_by=signed_by,
            policy_dir=policy_dir,
        )

        # Save manifest
        manifest_path = CryptographicPolicyVerifier.save_manifest(manifest, policy_dir)

        print("\n[SUCCESS] ✅ Manifest regenerated successfully")
        print(f"   Saved to: {manifest_path}")
        print(f"   Signed by: {signed_by}")
        print("\nNext steps:")
        print("   1. Commit policy_manifest.json to git")
        print("   2. Verify integrity: codescalpel verify-policies")
        return 0

    except Exception as e:
        print(f"\n[ERROR] Failed to regenerate manifest: {e}")
        return 1


def show_capabilities(
    tier: str | None = None,
    tool_filter: str | None = None,
    json_output: bool = False,
) -> int:
    """Show available tools and limits via the MCP capability surface.

    [20260311_REFACTOR] Keep the direct helper aligned with the main CLI command
    by routing it through the shared CLI-to-MCP bridge instead of maintaining a
    second standalone formatting path.
    """
    from code_scalpel.cli_tools.tool_bridge import invoke_tool_with_format

    return invoke_tool_with_format(
        "get_capabilities",
        {
            "tier": tier,
            "tool_name": tool_filter,
        },
        "json" if json_output else "text",
    )


def _build_tool_args(
    args: argparse.Namespace, field_map: dict[str, str]
) -> dict[str, object]:
    """Build MCP tool args from an argparse namespace.

    [20260311_REFACTOR] Centralize CLI->MCP argument extraction so handler
    updates stay localized and command drift does not reappear tool-by-tool.
    """
    return {
        tool_key: getattr(args, arg_name) for tool_key, arg_name in field_map.items()
    }


def _invoke_cli_tool(
    args: argparse.Namespace,
    tool_name: str,
    field_map: dict[str, str],
    *,
    default_output_format: str = "text",
) -> int:
    """Invoke an MCP-backed CLI command with shared argument and format handling."""
    return _invoke_tool_args(
        tool_name,
        _build_tool_args(args, field_map),
        output_format="json" if getattr(args, "json", False) else default_output_format,
    )


def _invoke_tool_args(
    tool_name: str,
    tool_args: dict[str, object],
    *,
    output_format: str = "text",
) -> int:
    """Invoke an MCP-backed CLI command with a prebuilt tool argument dict."""
    from code_scalpel.cli_tools.tool_bridge import invoke_tool_with_format

    return invoke_tool_with_format(
        tool_name,
        tool_args,
        output_format,
    )


def _write_tool_output_file(
    output_path: str,
    tool_name: str,
    tool_args: dict[str, object],
    success_message: str,
) -> int:
    """Capture text-formatted tool output into a file after a successful CLI run.

    [20260311_REFACTOR] Keep file emission for bridge-backed commands in one
    place so stdout capture mechanics and error handling do not diverge.
    """
    from code_scalpel.cli_tools.tool_bridge import invoke_tool

    buffer = io.StringIO()
    original_stdout = sys.stdout
    try:
        sys.stdout = buffer
        invoke_tool(tool_name, tool_args)
    finally:
        sys.stdout = original_stdout

    try:
        Path(output_path).write_text(buffer.getvalue(), encoding="utf-8")
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        return 1

    print(success_message)
    return 0


# [20260205_FEATURE] Phase 1 Pilot: MCP Tool CLI Handlers
def handle_extract_code(args: argparse.Namespace) -> int:
    """Handle 'codescalpel extract-code' command."""
    # [20260311_BUGFIX] Keep legacy --class behavior working while exposing the
    # actual MCP target shape for function, class, and method extraction.
    target_type = args.target_type
    if getattr(args, "class_name", None) and target_type == "function":
        target_type = "method"

    tool_args = _build_tool_args(
        args,
        {
            "target_name": "target_name",
            "file_path": "file_path",
            "code": "code",
            "include_cross_file_deps": "include_cross_file_deps",
            "include_context": "include_context",
        },
    )
    tool_args["target_type"] = target_type

    exit_code = _invoke_tool_args(
        "extract_code",
        tool_args,
        output_format="json" if args.json else "text",
    )

    # If output file specified, write result
    if exit_code == 0 and args.output and not args.json:
        return _write_tool_output_file(
            args.output,
            "extract_code",
            tool_args,
            f"✓ Extracted code written to {args.output}",
        )

    return exit_code


def handle_analyze(args: argparse.Namespace) -> int:
    """Handle 'codescalpel analyze' command via the MCP tool boundary."""
    tool_args = _build_tool_args(
        args,
        {
            "code": "code",
            "file_path": "file",
        },
    )
    tool_args["language"] = args.language or "auto"

    return _invoke_tool_args(
        "analyze_code",
        tool_args,
        output_format="json" if args.json else "text",
    )


def handle_scan(args: argparse.Namespace) -> int:
    """Handle 'codescalpel scan' command via the MCP tool boundary."""
    return _invoke_cli_tool(
        args,
        "security_scan",
        {
            "code": "code",
            "file_path": "file",
            "confidence_threshold": "confidence_threshold",
        },
    )


def handle_capabilities(args: argparse.Namespace) -> int:
    """Handle 'codescalpel capabilities' command via the MCP tool boundary."""
    return _invoke_cli_tool(
        args,
        "get_capabilities",
        {
            "tier": "tier",
            "tool_name": "tool",
        },
    )


def handle_get_call_graph(args: argparse.Namespace) -> int:
    """Handle 'codescalpel get-call-graph' command."""
    tool_args = _build_tool_args(
        args,
        {
            "project_root": "project_root",
            "entry_point": "entry_point",
            "depth": "depth",
            "paths_from": "paths_from",
            "paths_to": "paths_to",
        },
    )

    exit_code = _invoke_tool_args(
        "get_call_graph",
        tool_args,
        output_format="json" if args.json else args.format,
    )

    # If output file specified, write result
    if exit_code == 0 and args.output:
        return _write_tool_output_file(
            args.output,
            "get_call_graph",
            tool_args,
            f"✓ Call graph written to {args.output}",
        )

    return exit_code


def handle_rename_symbol(args: argparse.Namespace) -> int:
    """Handle 'codescalpel rename-symbol' command."""
    return _invoke_cli_tool(
        args,
        "rename_symbol",
        {
            "file_path": "file_path",
            "target_type": "target_type",
            "target_name": "target_name",
            "new_name": "new_name",
            "create_backup": "create_backup",
        },
    )


# [20260205_FEATURE] Phase 2: Analysis Tool Handlers
def handle_get_file_context(args: argparse.Namespace) -> int:
    """Handle 'codescalpel get-file-context' command."""
    return _invoke_cli_tool(
        args,
        "get_file_context",
        {"file_path": "file_path"},
    )


def handle_get_symbol_references(args: argparse.Namespace) -> int:
    """Handle 'codescalpel get-symbol-references' command."""
    return _invoke_cli_tool(
        args,
        "get_symbol_references",
        {
            "symbol_name": "symbol_name",
            "project_root": "project_root",
            "scope_prefix": "scope_prefix",
            "include_tests": "include_tests",
        },
    )


def handle_get_graph_neighborhood(args: argparse.Namespace) -> int:
    """Handle 'codescalpel get-graph-neighborhood' command."""
    return _invoke_cli_tool(
        args,
        "get_graph_neighborhood",
        {
            "center_node_id": "node_id",
            "project_root": "project_root",
            "k": "k",
            "direction": "direction",
            "max_nodes": "max_nodes",
            "min_confidence": "min_confidence",
        },
    )


def handle_get_project_map(args: argparse.Namespace) -> int:
    """Handle 'codescalpel get-project-map' command."""
    return _invoke_cli_tool(
        args,
        "get_project_map",
        {
            "project_root": "project_root",
            "include_complexity": "include_complexity",
            "complexity_threshold": "complexity_threshold",
            "include_circular_check": "include_circular_check",
            "detect_service_boundaries": "detect_service_boundaries",
            "min_isolation_score": "min_isolation_score",
        },
        default_output_format=args.format,
    )


def handle_get_cross_file_dependencies(args: argparse.Namespace) -> int:
    """Handle 'codescalpel get-cross-file-dependencies' command."""
    return _invoke_cli_tool(
        args,
        "get_cross_file_dependencies",
        {
            "target_file": "target_file",
            "target_symbol": "target_symbol",
            "project_root": "project_root",
            "max_depth": "max_depth",
            "include_code": "include_code",
            "include_diagram": "include_diagram",
            "confidence_decay_factor": "confidence_decay_factor",
            "max_files": "max_files",
            "timeout_seconds": "timeout_seconds",
        },
    )


def handle_crawl_project(args: argparse.Namespace) -> int:
    """Handle 'codescalpel crawl-project' command."""
    return _invoke_cli_tool(
        args,
        "crawl_project",
        {
            "root_path": "root_path",
            "exclude_dirs": "exclude_dirs",
            "complexity_threshold": "complexity_threshold",
            "include_report": "include_report",
            "pattern": "pattern",
            "pattern_type": "pattern_type",
        },
    )


# [20260205_FEATURE] Phase 3: Security Tool Handlers
def handle_cross_file_security_scan(args: argparse.Namespace) -> int:
    """Handle 'codescalpel cross-file-security-scan' command."""
    return _invoke_cli_tool(
        args,
        "cross_file_security_scan",
        {
            "project_root": "project_root",
            "entry_points": "entry_points",
            "max_depth": "max_depth",
            "include_diagram": "include_diagram",
            "timeout_seconds": "timeout_seconds",
            "max_modules": "max_modules",
            "confidence_threshold": "confidence_threshold",
        },
    )


def handle_type_evaporation_scan(args: argparse.Namespace) -> int:
    """Handle 'codescalpel type-evaporation-scan' command."""
    return _invoke_cli_tool(
        args,
        "type_evaporation_scan",
        {
            "frontend_file_path": "frontend_file",
            "backend_file_path": "backend_file",
            "frontend_code": "frontend_code",
            "backend_code": "backend_code",
        },
    )


def handle_unified_sink_detect(args: argparse.Namespace) -> int:
    """Handle 'codescalpel unified-sink-detect' command."""
    return _invoke_cli_tool(
        args,
        "unified_sink_detect",
        {
            "code": "code",
            "language": "language",
            "confidence_threshold": "confidence_threshold",
        },
    )


def handle_symbolic_execute(args: argparse.Namespace) -> int:
    """Handle 'codescalpel symbolic-execute' command."""
    return _invoke_cli_tool(
        args,
        "symbolic_execute",
        {
            "code": "code",
            "language": "language",
            "max_paths": "max_paths",
            "max_depth": "max_depth",
        },
    )


# [20260205_FEATURE] Phase 4: Refactoring & Testing Tool Handlers
def handle_update_symbol(args: argparse.Namespace) -> int:
    """Handle 'codescalpel update-symbol' command."""
    return _invoke_cli_tool(
        args,
        "update_symbol",
        {
            "file_path": "file_path",
            "target_type": "target_type",
            "target_name": "target_name",
            "new_code": "new_code",
            "operation": "operation",
            "new_name": "new_name",
            "create_backup": "create_backup",
        },
    )


def handle_simulate_refactor(args: argparse.Namespace) -> int:
    """Handle 'codescalpel simulate-refactor' command."""
    return _invoke_cli_tool(
        args,
        "simulate_refactor",
        {
            "original_code": "original_code",
            "new_code": "new_code",
            "patch": "patch",
            "strict_mode": "strict_mode",
        },
    )


def handle_generate_unit_tests(args: argparse.Namespace) -> int:
    """Handle 'codescalpel generate-unit-tests' command."""
    return _invoke_cli_tool(
        args,
        "generate_unit_tests",
        {
            "file_path": "file_path",
            "function_name": "function",
            "language": "language",
            "framework": "framework",
        },
    )


# [20260205_FEATURE] Phase 5: Validation & Policy Tool Handlers
def handle_validate_paths(args: argparse.Namespace) -> int:
    """Handle 'codescalpel validate-paths' command."""
    return _invoke_cli_tool(
        args,
        "validate_paths",
        {
            "paths": "paths",
            "project_root": "project_root",
        },
    )


def handle_scan_dependencies(args: argparse.Namespace) -> int:
    """Handle 'codescalpel scan-dependencies' command."""
    return _invoke_cli_tool(
        args,
        "scan_dependencies",
        {
            "path": "path",
            "project_root": "project_root",
            "include_dev": "include_dev",
            "scan_vulnerabilities": "scan_vulnerabilities",
            "timeout": "timeout",
        },
    )


def handle_code_policy_check(args: argparse.Namespace) -> int:
    """Handle 'codescalpel code-policy-check' command."""
    return _invoke_cli_tool(
        args,
        "code_policy_check",
        {
            "paths": "paths",
            "rules": "rules",
            "compliance_standards": "compliance_standards",
            "generate_report": "generate_report",
        },
    )


def handle_verify_policy_integrity(args: argparse.Namespace) -> int:
    """Handle 'codescalpel verify-policy-integrity' command."""
    return _invoke_cli_tool(
        args,
        "verify_policy_integrity",
        {
            "policy_dir": "policy_dir",
            "manifest_source": "manifest_source",
        },
    )


def handle_check(args: argparse.Namespace) -> int:
    """Handle 'codescalpel check' command."""
    return check_configuration(args.dir, args.json, args.fix)


def handle_init(args: argparse.Namespace) -> int:
    """Handle 'codescalpel init' command."""
    return init_configuration(args.dir, args.force)


def handle_verify_policies(args: argparse.Namespace) -> int:
    """Handle 'codescalpel verify-policies' command."""
    return verify_policies_command(args.dir, args.manifest_source)


def handle_regenerate_manifest(args: argparse.Namespace) -> int:
    """Handle 'codescalpel regenerate-manifest' command."""
    return regenerate_manifest_command(args.dir, args.signed_by)


def handle_server(args: argparse.Namespace) -> int:
    """Handle 'codescalpel server' command."""
    return start_server(args.host, args.port)


def _filter_kwargs_for_callable(func, kwargs: dict[str, object]) -> dict[str, object]:
    """Filter CLI-built kwargs to those accepted by a callable.

    [20260311_REFACTOR] Preserve older tests and stubs that patch server
    helpers with narrower signatures while keeping the CLI startup path table-
    driven.
    """
    import inspect

    try:
        sig = inspect.signature(func)
    except Exception:
        return kwargs

    for param in sig.parameters.values():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return kwargs

    allowed = set(sig.parameters.keys())
    return {key: value for key, value in kwargs.items() if key in allowed}


def handle_license(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """Handle 'codescalpel license' command family."""
    if args.license_command == "install":
        return _license_install(
            args.license_file, dest_path=args.dest, force=args.force
        )

    parser.print_help()
    return 1


def handle_mcp(args: argparse.Namespace) -> int:
    """Handle 'codescalpel mcp' command."""
    transport = args.transport
    if args.http:
        transport = "sse"

    start_kwargs: dict[str, object] = {
        "transport": transport,
        "host": args.host,
        "port": args.port,
        "allow_lan": getattr(args, "allow_lan", False),
        "root_path": getattr(args, "root", None),
        "tier": getattr(args, "tier", None),
    }
    if getattr(args, "license_file", None):
        start_kwargs["license_file"] = args.license_file
    if getattr(args, "ssl_cert", None) and getattr(args, "ssl_key", None):
        start_kwargs.update(
            {
                "ssl_certfile": args.ssl_cert,
                "ssl_keyfile": args.ssl_key,
            }
        )
    if getattr(args, "mismatch_action", None):
        start_kwargs["mismatch_action"] = args.mismatch_action

    return start_mcp_server(
        **_filter_kwargs_for_callable(start_mcp_server, start_kwargs)
    )


def handle_version(_args: argparse.Namespace) -> int:
    """Handle 'codescalpel version' command."""
    from . import __version__

    print(f"Code Scalpel v{__version__}")
    print(f"Python {sys.version}")
    return 0


def handle_release(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """Handle 'codescalpel release' command family."""
    from code_scalpel.release.cli import (
        release_execute,
        release_plan,
        release_prepare,
        release_publish,
    )

    if args.release_command == "plan":
        return release_plan()
    if args.release_command == "prepare":
        return release_prepare()
    if args.release_command == "execute":
        return release_execute(
            skip_github=args.skip_github,
            skip_pypi=args.skip_pypi,
        )
    if args.release_command == "publish":
        return release_publish(
            tag=args.tag,
            skip_github=args.skip_github,
            skip_pypi=args.skip_pypi,
        )

    parser.print_help()
    return 1


def _dispatch_with_guard(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
    handler: Callable[[argparse.Namespace], int],
    predicate: Callable[[argparse.Namespace], bool],
) -> int:
    """Run a CLI handler only when its command-specific inputs are valid."""
    if predicate(args):
        return handler(args)
    parser.print_help()
    return 1


def main() -> int:
    """Main CLI entry point."""
    from . import __version__

    parser = argparse.ArgumentParser(
        prog="codescalpel",
        description="AI Agent toolkit for code analysis using ASTs, PDGs, and Symbolic Execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  codescalpel analyze myfile.py              Analyze a Python file
  codescalpel analyze --code "def f(): pass" Analyze code string
  codescalpel analyze myfile.py --json       Output as JSON
  codescalpel scan myfile.py                 Security vulnerability scan
  codescalpel scan myfile.py --json          Security scan with JSON output
  codescalpel capabilities                   Show available tools for your tier
  codescalpel capabilities --tier pro        Show tools available at PRO tier
  codescalpel mcp                            TIER 1: Start MCP server (stdio, Claude Desktop)
  codescalpel mcp --http --port 8080         TIER 2: Start MCP server (HTTP fallback)
  codescalpel mcp --http --allow-lan         TIER 2: Start MCP server (HTTP with LAN)
  codescalpel mcp --http --ssl-cert cert.pem --ssl-key key.pem  HTTPS for production/Claude
  codescalpel server --port 5000             Start REST API server (legacy)
  codescalpel version                        Show version info

For production deployments with Claude API, use HTTPS:
  codescalpel mcp --http --ssl-cert /path/to/cert.pem --ssl-key /path/to/key.pem

For more information, visit: https://github.com/3D-Tech-Solutions/code-scalpel
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze code")
    analyze_parser.add_argument("file", nargs="?", help="File to analyze")
    analyze_parser.add_argument("--code", "-c", help="Code string to analyze")
    analyze_parser.add_argument(
        "--json", "-j", action="store_true", help="Output as JSON"
    )
    analyze_parser.add_argument(
        "--language",
        "-l",
        choices=ANALYZE_LANGUAGE_CHOICES,
        help="Source language (default: auto-detect or python)",
    )

    # Scan command (Security Analysis)
    scan_parser = subparsers.add_parser(
        "scan", help="Scan for security vulnerabilities (SQLi, XSS, etc.)"
    )
    scan_parser.add_argument("file", nargs="?", help="Python file to scan")
    scan_parser.add_argument("--code", "-c", help="Code string to scan")
    scan_parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    scan_parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.7,
        help="Minimum confidence threshold between 0.0 and 1.0 (default: 0.7)",
    )

    # [20260205_FEATURE] Phase 1 Pilot: MCP Tool CLI Access
    # Extract Code command
    extract_parser = subparsers.add_parser(
        "extract-code",
        help="Surgically extract code with dependencies (MCP tool)",
    )
    extract_parser.add_argument(
        "file_path",
        nargs="?",
        help="Path to file containing code",
    )
    extract_parser.add_argument(
        "--code",
        help="Inline source code to extract from instead of a file",
    )
    extract_parser.add_argument(
        "--name",
        "-n",
        dest="target_name",
        help="Target symbol name to extract",
    )
    extract_parser.add_argument(
        "--function",
        "-f",
        dest="target_name",
        help="Deprecated alias for --name when extracting a function or method",
    )
    extract_parser.add_argument(
        "--class",
        "-c",
        dest="class_name",
        help="Deprecated compatibility flag; if provided with --function, extraction defaults to method mode",
    )
    extract_parser.add_argument(
        "--type",
        dest="target_type",
        choices=["function", "class", "method"],
        default="function",
        help="Target symbol type (default: function)",
    )
    extract_parser.add_argument(
        "--include-deps",
        action="store_true",
        dest="include_cross_file_deps",
        help="Include cross-file dependencies (Pro+ tier)",
    )
    extract_parser.add_argument(
        "--include-context",
        action="store_true",
        help="Include surrounding code context",
    )
    extract_parser.add_argument(
        "--output",
        "-o",
        help="Output file (default: stdout)",
    )
    extract_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )
    extract_parser.set_defaults(target_name=None)

    # Get Call Graph command
    call_graph_parser = subparsers.add_parser(
        "get-call-graph",
        help="Generate function call graph (MCP tool)",
    )
    call_graph_parser.add_argument(
        "--project-root",
        help="Project root directory (default: current directory)",
    )
    call_graph_parser.add_argument(
        "--entry-point",
        help="Optional entry point function or file:function target",
    )
    call_graph_parser.add_argument(
        "--depth",
        type=int,
        default=10,
        help="Maximum traversal depth (default: 10)",
    )
    call_graph_parser.add_argument(
        "--paths-from",
        help="Source function for path queries",
    )
    call_graph_parser.add_argument(
        "--paths-to",
        help="Sink function for path queries",
    )
    call_graph_parser.add_argument(
        "--output",
        "-o",
        help="Output file (default: stdout)",
    )
    call_graph_parser.add_argument(
        "--format",
        choices=["mermaid", "json"],
        default="mermaid",
        help="Output format (default: mermaid)",
    )
    call_graph_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output full response as JSON",
    )

    # Rename Symbol command
    rename_parser = subparsers.add_parser(
        "rename-symbol",
        help="Safely rename a function, class, or method (MCP tool)",
    )
    rename_parser.add_argument("file_path", help="Path to file containing symbol")
    rename_parser.add_argument("target_name", help="Current name of the symbol")
    rename_parser.add_argument("new_name", help="New name for the symbol")
    rename_parser.add_argument(
        "--type",
        dest="target_type",
        choices=["function", "class", "method"],
        default="function",
        help="Type of symbol (default: function)",
    )
    rename_parser.add_argument(
        "--no-backup",
        action="store_false",
        dest="create_backup",
        help="Do not create backup before renaming",
    )
    rename_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )

    # [20260205_FEATURE] Phase 2: Analysis Tools
    # Get File Context command
    file_context_parser = subparsers.add_parser(
        "get-file-context",
        help="Get file overview with structure analysis (MCP tool)",
    )
    file_context_parser.add_argument("file_path", help="Path to file to analyze")
    file_context_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )

    # Get Symbol References command
    symbol_refs_parser = subparsers.add_parser(
        "get-symbol-references",
        help="Find all references to a symbol across project (MCP tool)",
    )
    symbol_refs_parser.add_argument("symbol_name", help="Symbol name to search for")
    symbol_refs_parser.add_argument(
        "--project-root",
        help="Project root directory (default: current directory)",
    )
    symbol_refs_parser.add_argument(
        "--scope-prefix",
        help="Optional scope prefix to filter results",
    )
    symbol_refs_parser.add_argument(
        "--no-tests",
        action="store_false",
        dest="include_tests",
        help="Exclude test files from search",
    )
    symbol_refs_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )

    # Get Graph Neighborhood command
    graph_neighborhood_parser = subparsers.add_parser(
        "get-graph-neighborhood",
        help="Get k-hop neighborhood of a node in call graph (MCP tool)",
    )
    graph_neighborhood_parser.add_argument(
        "node_id",
        help="Node ID (function name) to analyze",
    )
    graph_neighborhood_parser.add_argument(
        "--project-root",
        help="Project root directory (default: current directory)",
    )
    graph_neighborhood_parser.add_argument(
        "--k",
        type=int,
        default=2,
        help="Number of hops (default: 2)",
    )
    graph_neighborhood_parser.add_argument(
        "--max-nodes",
        type=int,
        default=100,
        help="Maximum nodes to include (default: 100)",
    )
    graph_neighborhood_parser.add_argument(
        "--direction",
        choices=["incoming", "outgoing", "both"],
        default="both",
        help="Direction of edges to follow (default: both)",
    )
    graph_neighborhood_parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="Minimum edge confidence to follow (default: 0.0)",
    )
    graph_neighborhood_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )

    # Get Project Map command
    project_map_parser = subparsers.add_parser(
        "get-project-map",
        help="Generate project structure map (MCP tool)",
    )
    project_map_parser.add_argument(
        "--project-root",
        help="Project root directory (default: current directory)",
    )
    project_map_parser.add_argument(
        "--no-complexity",
        action="store_false",
        dest="include_complexity",
        help="Skip complexity analysis",
    )
    project_map_parser.add_argument(
        "--complexity-threshold",
        type=int,
        default=10,
        help="Complexity hotspot threshold (default: 10)",
    )
    project_map_parser.add_argument(
        "--no-circular-check",
        action="store_false",
        dest="include_circular_check",
        help="Skip circular dependency analysis",
    )
    project_map_parser.add_argument(
        "--detect-service-boundaries",
        action="store_true",
        help="Request service boundary suggestions",
    )
    project_map_parser.add_argument(
        "--min-isolation-score",
        type=float,
        default=0.6,
        help="Isolation score threshold for service boundary detection (default: 0.6)",
    )
    project_map_parser.add_argument(
        "--format",
        choices=["mermaid", "json", "text"],
        default="text",
        help="Output format (default: text)",
    )
    project_map_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output full response as JSON",
    )

    # Get Cross-File Dependencies command
    cross_deps_parser = subparsers.add_parser(
        "get-cross-file-dependencies",
        help="Analyze cross-file dependencies (MCP tool)",
    )
    cross_deps_parser.add_argument(
        "target_file",
        help="Path to the file containing the target symbol",
    )
    cross_deps_parser.add_argument(
        "target_symbol",
        help="Function, method, or class name to analyze",
    )
    cross_deps_parser.add_argument(
        "--project-root",
        help="Project root directory (default: current directory)",
    )
    cross_deps_parser.add_argument(
        "--max-depth",
        type=int,
        default=3,
        help="Maximum dependency depth (default: 3)",
    )
    cross_deps_parser.add_argument(
        "--no-code",
        action="store_false",
        dest="include_code",
        help="Exclude combined source code from output",
    )
    cross_deps_parser.add_argument(
        "--no-diagram",
        action="store_false",
        dest="include_diagram",
        help="Exclude Mermaid dependency diagram",
    )
    cross_deps_parser.add_argument(
        "--confidence-decay-factor",
        type=float,
        default=0.9,
        help="Confidence decay factor per depth level (default: 0.9)",
    )
    cross_deps_parser.add_argument(
        "--max-files",
        type=int,
        help="Maximum number of files to include",
    )
    cross_deps_parser.add_argument(
        "--timeout-seconds",
        type=float,
        help="Timeout for dependency analysis",
    )
    cross_deps_parser.add_argument(
        "--include-external",
        action="store_true",
        help="Deprecated compatibility flag; external library inclusion is determined by the MCP tool",
    )
    cross_deps_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )

    # Crawl Project command
    crawl_parser = subparsers.add_parser(
        "crawl-project",
        help="Crawl and analyze project directory (MCP tool)",
    )
    crawl_parser.add_argument(
        "--root-path",
        help="Root directory to crawl (default: current directory)",
    )
    crawl_parser.add_argument(
        "--exclude-dirs",
        nargs="*",
        help="Directories to exclude (e.g., node_modules __pycache__)",
    )
    crawl_parser.add_argument(
        "--complexity-threshold",
        type=int,
        default=10,
        help="Complexity threshold for analysis (default: 10)",
    )
    crawl_parser.add_argument(
        "--pattern",
        help="File pattern to match (regex or glob)",
    )
    crawl_parser.add_argument(
        "--pattern-type",
        choices=["regex", "glob"],
        default="regex",
        help="Pattern type (default: regex)",
    )
    crawl_parser.add_argument(
        "--no-report",
        action="store_false",
        dest="include_report",
        help="Exclude detailed report",
    )
    crawl_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )

    # [20260205_FEATURE] Phase 3: Security Tools
    # Cross-File Security Scan command
    cross_file_scan_parser = subparsers.add_parser(
        "cross-file-security-scan",
        help="Cross-file taint analysis for security vulnerabilities (MCP tool)",
    )
    cross_file_scan_parser.add_argument(
        "--project-root",
        help="Project root directory (default: current directory)",
    )
    cross_file_scan_parser.add_argument(
        "--entry-point",
        dest="entry_points",
        action="append",
        help="Entry point to analyze; repeat for multiple entry points",
    )
    cross_file_scan_parser.add_argument(
        "--max-depth",
        type=int,
        default=5,
        help="Maximum analysis depth (default: 5)",
    )
    cross_file_scan_parser.add_argument(
        "--no-diagram",
        action="store_false",
        dest="include_diagram",
        help="Exclude Mermaid taint flow diagram",
    )
    cross_file_scan_parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=120.0,
        help="Timeout for analysis in seconds (default: 120)",
    )
    cross_file_scan_parser.add_argument(
        "--max-modules",
        type=int,
        default=500,
        help="Maximum modules to analyze (default: 500)",
    )
    cross_file_scan_parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.7,
        help="Minimum confidence for reporting (default: 0.7)",
    )
    cross_file_scan_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )

    # Type Evaporation Scan command
    type_evap_parser = subparsers.add_parser(
        "type-evaporation-scan",
        help="Detect type system evaporation vulnerabilities (MCP tool)",
    )
    type_evap_parser.add_argument(
        "--frontend-file",
        help="Frontend TypeScript file path",
    )
    type_evap_parser.add_argument(
        "--backend-file",
        help="Backend Python file path",
    )
    type_evap_parser.add_argument(
        "--frontend-code",
        help="Frontend TypeScript code (alternative to file)",
    )
    type_evap_parser.add_argument(
        "--backend-code",
        help="Backend Python code (alternative to file)",
    )
    type_evap_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )

    # Unified Sink Detect command
    sink_detect_parser = subparsers.add_parser(
        "unified-sink-detect",
        help="Detect security sinks across multiple languages (MCP tool)",
    )
    sink_detect_parser.add_argument(
        "code",
        help="Code to analyze",
    )
    sink_detect_parser.add_argument(
        "--language",
        default="auto",
        help="Programming language (default: auto-detect)",
    )
    sink_detect_parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.7,
        help="Confidence threshold for detections (default: 0.7)",
    )
    sink_detect_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )

    # Symbolic Execute command
    symbolic_parser = subparsers.add_parser(
        "symbolic-execute",
        help="Perform symbolic execution analysis (MCP tool)",
    )
    symbolic_parser.add_argument(
        "code",
        help="Source code to analyze symbolically",
    )
    symbolic_parser.add_argument(
        "--language",
        choices=SYMBOLIC_LANGUAGE_CHOICES,
        default="python",
        help="Source language (default: python)",
    )
    symbolic_parser.add_argument(
        "--max-paths",
        type=int,
        help="Maximum paths to explore",
    )
    symbolic_parser.add_argument(
        "--max-depth",
        type=int,
        help="Maximum execution depth",
    )
    symbolic_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )

    # [20260205_FEATURE] Phase 4: Refactoring & Testing Tools
    # Update Symbol command
    update_symbol_parser = subparsers.add_parser(
        "update-symbol",
        help="Update symbol implementation (MCP tool)",
    )
    update_symbol_parser.add_argument(
        "file_path", help="Path to file containing symbol"
    )
    update_symbol_parser.add_argument("target_name", help="Symbol name to update")
    update_symbol_parser.add_argument(
        "new_code",
        nargs="?",
        help="Replacement implementation for operation=replace",
    )
    update_symbol_parser.add_argument(
        "--type",
        dest="target_type",
        choices=["function", "class", "method"],
        default="function",
        help="Type of symbol (default: function)",
    )
    update_symbol_parser.add_argument(
        "--operation",
        choices=["replace", "rename"],
        default="replace",
        help="Update operation to perform (default: replace)",
    )
    update_symbol_parser.add_argument(
        "--new-name",
        help="New symbol name for operation=rename",
    )
    update_symbol_parser.add_argument(
        "--no-backup",
        action="store_false",
        dest="create_backup",
        help="Do not create backup before updating",
    )
    update_symbol_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )

    # Simulate Refactor command
    sim_refactor_parser = subparsers.add_parser(
        "simulate-refactor",
        help="Simulate refactoring impact before applying (MCP tool)",
    )
    sim_refactor_parser.add_argument(
        "original_code",
        help="Original source code before the refactor",
    )
    sim_refactor_parser.add_argument(
        "--new-code",
        help="New source code after the refactor",
    )
    sim_refactor_parser.add_argument(
        "--patch",
        help="Patch or diff describing the refactor",
    )
    sim_refactor_parser.add_argument(
        "--strict-mode",
        action="store_true",
        help="Enable stricter validation checks",
    )
    sim_refactor_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )

    # Generate Unit Tests command
    gen_tests_parser = subparsers.add_parser(
        "generate-unit-tests",
        help="AI-powered unit test generation (MCP tool)",
    )
    gen_tests_parser.add_argument(
        "file_path",
        help="Path to file to generate tests for",
    )
    gen_tests_parser.add_argument(
        "--function",
        help="Specific function to test",
    )
    gen_tests_parser.add_argument(
        "--language",
        choices=SYMBOLIC_LANGUAGE_CHOICES,
        default="python",
        help="Source language (default: python)",
    )
    gen_tests_parser.add_argument(
        "--framework",
        choices=["pytest", "unittest", "jest", "mocha"],
        default="pytest",
        help="Test framework (default: pytest)",
    )
    gen_tests_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )

    # [20260205_FEATURE] Phase 5: Validation & Policy Tools
    # Validate Paths command
    validate_paths_parser = subparsers.add_parser(
        "validate-paths",
        help="Validate import paths in project (MCP tool)",
    )
    validate_paths_parser.add_argument(
        "paths",
        nargs="+",
        help="One or more paths to validate",
    )
    validate_paths_parser.add_argument(
        "--project-root",
        help="Project root for relative path resolution",
    )
    validate_paths_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )

    # Scan Dependencies command
    scan_deps_parser = subparsers.add_parser(
        "scan-dependencies",
        help="Scan project dependencies for issues (MCP tool)",
    )
    scan_deps_parser.add_argument(
        "--path",
        help="Specific requirements or package file to scan",
    )
    scan_deps_parser.add_argument(
        "--project-root",
        help="Project root directory (default: current directory)",
    )
    scan_deps_parser.add_argument(
        "--include-dev",
        action="store_true",
        help="Include development dependencies",
    )
    scan_deps_parser.add_argument(
        "--no-vulnerabilities",
        action="store_false",
        dest="scan_vulnerabilities",
        help="Skip vulnerability lookups",
    )
    scan_deps_parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Dependency scan timeout in seconds (default: 30)",
    )
    scan_deps_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )

    # Code Policy Check command
    policy_check_parser = subparsers.add_parser(
        "code-policy-check",
        help="Check code against policy rules (MCP tool)",
    )
    policy_check_parser.add_argument(
        "paths",
        nargs="+",
        help="One or more paths to check",
    )
    policy_check_parser.add_argument(
        "--rule",
        dest="rules",
        action="append",
        help="Specific rule to enforce; repeat for multiple rules",
    )
    policy_check_parser.add_argument(
        "--compliance-standard",
        dest="compliance_standards",
        action="append",
        help="Compliance standard to audit; repeat for multiple standards",
    )
    policy_check_parser.add_argument(
        "--generate-report",
        action="store_true",
        help="Generate a compliance report when supported by the current tier",
    )
    policy_check_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )

    # Verify Policy Integrity command
    verify_integrity_parser = subparsers.add_parser(
        "verify-policy-integrity",
        help="Verify policy file integrity (MCP tool)",
    )
    verify_integrity_parser.add_argument(
        "--policy-dir",
        default=".code-scalpel",
        help="Policy directory (default: .code-scalpel)",
    )
    verify_integrity_parser.add_argument(
        "--manifest-source",
        choices=["file", "git", "env"],
        default="file",
        help="Manifest source to verify against (default: file)",
    )
    verify_integrity_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )

    # Check command (Configuration Audit) - [20260224_FEATURE]
    check_parser = subparsers.add_parser(
        "check", help="Check .code-scalpel directory for missing configuration files"
    )
    check_parser.add_argument(
        "--dir",
        "-d",
        default=".",
        help="Target directory containing .code-scalpel (default: current directory)",
    )
    check_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output results as JSON",
    )
    check_parser.add_argument(
        "--fix",
        "-F",
        action="store_true",
        help="Automatically add any missing files before reporting (safe \u2014 never overwrites existing)",
    )

    # Init command (Configuration Setup) - [20251219_FEATURE] v3.0.2
    init_parser = subparsers.add_parser(
        "init", help="Initialize .code-scalpel configuration directory"
    )
    init_parser.add_argument(
        "--dir",
        "-d",
        default=".",
        help="Target directory (default: current directory)",
    )
    init_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force initialization even if directory exists",
    )

    # Server command (REST API - legacy)
    server_parser = subparsers.add_parser(
        "server", help="Start REST API server (legacy)"
    )
    server_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    server_parser.add_argument(
        "--port", "-p", type=int, default=5000, help="Port to bind to (default: 5000)"
    )

    # MCP command (Model Context Protocol - recommended)
    # [20260125_FEATURE] Phase 3: stdio is Tier 1 (primary, most optimized)
    # HTTP (sse/streamable-http) is Tier 2 fallback for network deployments
    mcp_parser = subparsers.add_parser(
        "mcp",
        help="Start MCP server (for Claude Desktop, Cursor) - TIER 1: stdio (recommended)",
    )
    mcp_parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport type (default: stdio for Claude Desktop, Cursor) - TIER 1: stdio (optimized), TIER 2: sse/streamable-http (fallback)",
    )
    mcp_parser.add_argument(
        "--http",
        action="store_true",
        help="TIER 2: Use HTTP transport (fallback for network deployments, less optimized than stdio)",
    )
    mcp_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to for HTTP (default: 127.0.0.1)",
    )
    mcp_parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=8080,
        help="Port for HTTP transport (default: 8080)",
    )
    mcp_parser.add_argument(
        "--allow-lan",
        action="store_true",
        help="Allow LAN connections (disables host validation, use on trusted networks only)",
    )
    mcp_parser.add_argument(
        "--root",
        default=None,
        help="Project root directory for context resources (default: current directory)",
    )
    mcp_parser.add_argument(
        "--tier",
        choices=["community", "pro", "enterprise"],
        default=None,
        help="Tool tier (default: enterprise or CODE_SCALPEL_TIER/SCALPEL_TIER)",
    )
    mcp_parser.add_argument(
        "--license-file",
        default=None,
        help="Path to license JWT file (sets CODE_SCALPEL_LICENSE_PATH)",
    )
    # [20251215_FEATURE] SSL/TLS support for HTTPS - required for Claude API and production
    mcp_parser.add_argument(
        "--ssl-cert",
        default=None,
        help="Path to SSL certificate file for HTTPS (required for Claude API)",
    )
    mcp_parser.add_argument(
        "--ssl-key",
        default=None,
        help="Path to SSL private key file for HTTPS (required for Claude API)",
    )
    # [20260220_FEATURE] Configurable version mismatch handling
    mcp_parser.add_argument(
        "--mismatch-action",
        choices=["warn", "error", "ignore", "auto-upgrade"],
        default=None,
        help="Action to take if PyPI version is newer than current version (default: warn)",
    )

    # License management commands
    license_parser = subparsers.add_parser(
        "license", help="Manage Code Scalpel licenses"
    )
    license_subparsers = license_parser.add_subparsers(dest="license_command")

    install_parser = license_subparsers.add_parser(
        "install", help="Validate and install a license JWT"
    )
    install_parser.add_argument(
        "license_file",
        help="Path to the license JWT file to install",
    )
    install_parser.add_argument(
        "--dest",
        default=None,
        help="Optional destination path (default: ~/.config/codescalpel/license.jwt)",
    )
    install_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite destination if it already exists",
    )

    # Version command
    subparsers.add_parser("version", help="Show version information")

    # Capabilities command - [20260127_FEATURE] Show tier-aware tool capabilities
    capabilities_parser = subparsers.add_parser(
        "capabilities",
        help="Show available tools and limits for your license tier",
    )
    capabilities_parser.add_argument(
        "--tier",
        choices=["community", "pro", "enterprise"],
        default=None,
        help="Optional tier to inspect (default: current license tier)",
    )
    capabilities_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )
    capabilities_parser.add_argument(
        "--tool",
        "-t",
        default=None,
        help="Show details for a specific tool (default: show all tools)",
    )

    # [20241225_FEATURE] v3.3.0 - Policy verification commands
    verify_parser = subparsers.add_parser(
        "verify-policies",
        help="Verify policy integrity using cryptographic signatures",
    )
    verify_parser.add_argument(
        "--dir",
        default=".code-scalpel",
        help="Policy directory (default: .code-scalpel)",
    )
    verify_parser.add_argument(
        "--manifest-source",
        choices=["git", "env", "file"],
        default="file",
        help="Where to load manifest from (default: file)",
    )

    regenerate_parser = subparsers.add_parser(
        "regenerate-manifest",
        help="Regenerate policy manifest after changes",
    )
    regenerate_parser.add_argument(
        "--dir",
        default=".code-scalpel",
        help="Policy directory (default: .code-scalpel)",
    )
    regenerate_parser.add_argument(
        "--signed-by",
        default="codescalpel regenerate-manifest",
        help="Signer identity for manifest",
    )

    # Release management commands
    release_parser = subparsers.add_parser(
        "release",
        help="Manage code releases (version, changelog, GitHub, PyPI)",
    )
    release_subparsers = release_parser.add_subparsers(
        dest="release_command",
        help="Release subcommands",
    )

    # plan subcommand (no arguments needed)
    release_subparsers.add_parser(
        "plan",
        help="Preview the next release without making changes",
    )

    # prepare subcommand (no arguments needed)
    release_subparsers.add_parser(
        "prepare",
        help="Prepare release in dry-run mode",
    )

    # execute subcommand
    execute_parser = release_subparsers.add_parser(
        "execute",
        help="Execute complete release (prepare + GitHub + PyPI)",
    )
    execute_parser.add_argument(
        "--skip-github",
        action="store_true",
        help="Skip GitHub release creation",
    )
    execute_parser.add_argument(
        "--skip-pypi",
        action="store_true",
        help="Skip PyPI publishing",
    )

    # publish subcommand
    publish_parser = release_subparsers.add_parser(
        "publish",
        help="Publish existing release to PyPI and GitHub",
    )
    publish_parser.add_argument(
        "--tag",
        help="Git tag to publish (default: latest)",
    )
    publish_parser.add_argument(
        "--skip-github",
        action="store_true",
        help="Skip GitHub release",
    )
    publish_parser.add_argument(
        "--skip-pypi",
        action="store_true",
        help="Skip PyPI publishing",
    )

    args = parser.parse_args()

    # [20260311_REFACTOR] Route CLI commands through a table-driven dispatcher so
    # new commands do not require extending a fragile if/elif chain.
    command_dispatch: dict[str, Callable[[], int]] = {
        "analyze": lambda: _dispatch_with_guard(
            args,
            analyze_parser,
            handle_analyze,
            lambda namespace: bool(namespace.code or namespace.file),
        ),
        "scan": lambda: _dispatch_with_guard(
            args,
            scan_parser,
            handle_scan,
            lambda namespace: bool(namespace.code or namespace.file),
        ),
        "extract-code": lambda: _dispatch_with_guard(
            args,
            extract_parser,
            handle_extract_code,
            lambda namespace: bool(
                namespace.target_name and (namespace.file_path or namespace.code)
            ),
        ),
        "get-call-graph": lambda: handle_get_call_graph(args),
        "rename-symbol": lambda: handle_rename_symbol(args),
        "get-file-context": lambda: handle_get_file_context(args),
        "get-symbol-references": lambda: handle_get_symbol_references(args),
        "get-graph-neighborhood": lambda: handle_get_graph_neighborhood(args),
        "get-project-map": lambda: handle_get_project_map(args),
        "get-cross-file-dependencies": lambda: handle_get_cross_file_dependencies(args),
        "crawl-project": lambda: handle_crawl_project(args),
        "cross-file-security-scan": lambda: handle_cross_file_security_scan(args),
        "type-evaporation-scan": lambda: handle_type_evaporation_scan(args),
        "unified-sink-detect": lambda: handle_unified_sink_detect(args),
        "symbolic-execute": lambda: handle_symbolic_execute(args),
        "update-symbol": lambda: handle_update_symbol(args),
        "simulate-refactor": lambda: handle_simulate_refactor(args),
        "generate-unit-tests": lambda: handle_generate_unit_tests(args),
        "validate-paths": lambda: handle_validate_paths(args),
        "scan-dependencies": lambda: handle_scan_dependencies(args),
        "code-policy-check": lambda: handle_code_policy_check(args),
        "verify-policy-integrity": lambda: handle_verify_policy_integrity(args),
        "check": lambda: handle_check(args),
        "init": lambda: handle_init(args),
        "verify-policies": lambda: handle_verify_policies(args),
        "regenerate-manifest": lambda: handle_regenerate_manifest(args),
        "server": lambda: handle_server(args),
        "license": lambda: handle_license(args, license_parser),
        "mcp": lambda: handle_mcp(args),
        "capabilities": lambda: handle_capabilities(args),
        "version": lambda: handle_version(args),
        "release": lambda: handle_release(args, release_parser),
    }

    runner = command_dispatch.get(args.command)
    if runner is not None:
        return runner()

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
