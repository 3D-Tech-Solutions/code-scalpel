import argparse
import json
import os
import sys
from pathlib import Path


def analyze_file(filepath: str, output_format: str = "text", language: str | None = None) -> int:
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
                print(f"   - {dc.code_type} '{dc.name}' (lines {dc.line_start}-{dc.line_end})")
                print(f"     Reason: {dc.reason}")

        if result.security_issues:
            print(f"\n[WARNING] Security Issues ({len(result.security_issues)}):")
            for issue in result.security_issues:
                print(f"   - {issue.get('type', 'Unknown')}: {issue.get('description', 'No description')}")

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
            print(f"\n[WARNING] Found {result.vulnerability_count} vulnerability(ies):\n")
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
            print(f"\n[WARNING] Found {result.vulnerability_count} vulnerability(ies):\n")
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


def init_configuration(target_dir: str = ".", force: bool = False) -> int:
    """Initialize .code-scalpel configuration directory.

    [20251219_FEATURE] v3.0.2 - Auto-initialize configuration for first-time users.
    Creates .code-scalpel/ with config.json, policy.yaml, budget.yaml, README.md, .gitignore.
    """
    from .config import init_config_dir

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
            else:
                print("\n[OK] Configuration directory already exists.")
                print(f"   Path: {result['path']}")
                print("\nUse --force to attempt reinitialization.")
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
        print(f"\n[VALIDATION] Checked {len(validation['files_validated'])} configuration files:")
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
        print("   4. Test with: code-scalpel verify-policies")

    print("\nNext steps:")
    print("   1. Review policy.yaml to configure security rules")
    print("   2. Review agent_limits.yaml to set change limits")
    print("   3. Read README.md for configuration guidance")
    print("   4. Add .code-scalpel/ to version control (recommended)")
    print("   5. Set SCALPEL_MANIFEST_SECRET in CI/CD for policy verification")

    return 0


def start_server(host: str = "127.0.0.1", port: int = 5000) -> int:
    """Start the REST API server (legacy, for non-MCP clients).

    [20251223_SECURITY] Default binding is localhost-only.
    Use --host 0.0.0.0 to allow LAN access on trusted networks.
    """
    from .integrations.rest_api_server import run_server

    print(f"Starting Code Scalpel REST API Server on {host}:{port}")
    print(f"   Health check: http://{host}:{port}/health")
    print(f"   Analyze endpoint: POST http://{host}:{port}/analyze")
    print(f"   Refactor endpoint: POST http://{host}:{port}/refactor")
    print(f"   Security endpoint: POST http://{host}:{port}/security")
    print("\nNote: For MCP-compliant clients (Claude Desktop, Cursor), use 'code-scalpel mcp' instead.")
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
) -> int:
    """Start the MCP-compliant server (for AI clients like Claude Desktop, Cursor)."""
    import importlib
    import inspect

    # [20260122_BUGFIX] Honor monkeypatched MCP server for tests to avoid starting real servers
    try:
        mcp_server = importlib.import_module("code_scalpel.mcp.server")
        run_server = mcp_server.run_server
    except Exception:
        from .mcp.archive.server import run_server  # pragma: no cover

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

    # [20251215_FEATURE] Determine protocol based on SSL config
    use_https = ssl_certfile and ssl_keyfile
    protocol = "https" if use_https else "http"

    if transport == "stdio":
        # NOTE: CLI tests expect this banner on stdout.
        # The MCP stdio integration tests invoke `code_scalpel.mcp.server` directly.
        print("Starting Code Scalpel MCP Server (stdio transport)")
        print("   This server communicates via stdin/stdout.")
        print("   Add to your Claude Desktop config or use with MCP Inspector.")
        print("\nPress Ctrl+C to stop.\n")
    else:
        print(f"Starting Code Scalpel MCP Server ({protocol.upper()} transport) on {host}:{port}")
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


def _license_install(source_path: str, dest_path: str | None = None, force: bool = False) -> int:
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
    print(f"✓ Tier: {data.tier}")
    print(f"✓ Installed to: {dest}")
    return 0


def verify_policies_command(policy_dir: str = ".code-scalpel", manifest_source: str = "file") -> int:
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
        print("Find your secret in: .env (if using code-scalpel init)")
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


def regenerate_manifest_command(policy_dir: str = ".code-scalpel", signed_by: str = "code-scalpel") -> int:
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
        policy_files.extend([str(f.relative_to(policy_path)) for f in policy_path.glob(pattern)])

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
        print("   2. Verify integrity: code-scalpel verify-policies")
        return 0

    except Exception as e:
        print(f"\n[ERROR] Failed to regenerate manifest: {e}")
def list_tools_command(tier: str | None = None, json_output: bool = False) -> int:
    """List available MCP tools for the specified or current tier."""
    from .licensing.features import TOOL_CAPABILITIES

    if tier is None:
        # Get current tier from environment or default
        tier = os.getenv("CODE_SCALPEL_TIER", os.getenv("SCALPEL_TIER", "enterprise")).lower()

    # Tool descriptions (simplified)
    tool_descriptions = {
        "analyze_code": "Parse Python/Java code structure and extract functions/classes",
        "code_policy_check": "Check code against style guides and compliance standards",
        "crawl_project": "Crawl project directory and analyze Python files",
        "cross_file_security_scan": "Perform cross-file security analysis tracking taint flow",
        "extract_code": "Extract code elements with optional dependency context",
        "generate_unit_tests": "Generate unit tests from code using symbolic execution",
        "get_call_graph": "Build call graph showing function relationships",
        "get_cross_file_dependencies": "Analyze cross-file dependencies for a symbol",
        "get_file_context": "Get file overview without reading full content",
        "get_graph_neighborhood": "Extract k-hop neighborhood subgraph around a node",
        "get_project_map": "Generate comprehensive project structure map",
        "get_symbol_references": "Find all references to a symbol across project",
        "rename_symbol": "Rename function/class/method in file",
        "scan_dependencies": "Scan project dependencies for vulnerabilities",
        "security_scan": "Scan code for security vulnerabilities using taint analysis",
        "simulate_refactor": "Simulate code change and check for safety issues",
        "symbolic_execute": "Perform symbolic execution on Python code",
        "type_evaporation_scan": "Detect type system evaporation vulnerabilities",
        "unified_sink_detect": "Unified polyglot sink detection with confidence thresholds",
        "update_symbol": "Safely replace function/class/method in file",
        "validate_paths": "Validate paths are accessible before operations",
        "verify_policy_integrity": "Verify policy file integrity using signatures",
    }

    available_tools = []
    for tool_name in tool_descriptions.keys():
        tool_caps = TOOL_CAPABILITIES.get(tool_name, {})
        tier_caps = tool_caps.get(tier, {})
        if tier_caps.get("enabled", True):  # Assume enabled if not specified
            available_tools.append({
                "name": tool_name,
                "description": tool_descriptions[tool_name],
                "tier": tier,
                "limits": tier_caps.get("limits", {}),
            })

    if json_output:
        print(json.dumps({
            "tier": tier,
            "tools": available_tools,
            "total": len(available_tools)
        }, indent=2))
    else:
        print(f"Code Scalpel MCP Tools (Tier: {tier})")
        print("=" * 50)
        for tool in available_tools:
            print(f"• {tool['name']}: {tool['description']}")
            if tool['limits']:
                limits_str = ", ".join(f"{k}={v}" for k, v in tool['limits'].items())
                print(f"  Limits: {limits_str}")
        print(f"\nTotal tools available: {len(available_tools)}")

    return 0


def main() -> int:
    """Main CLI entry point."""
    from . import __version__

    parser = argparse.ArgumentParser(
        prog="code-scalpel",
        description="AI Agent toolkit for code analysis using ASTs, PDGs, and Symbolic Execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  code-scalpel analyze myfile.py              Analyze a Python file
  code-scalpel analyze --code "def f(): pass" Analyze code string
  code-scalpel analyze myfile.py --json       Output as JSON
  code-scalpel scan myfile.py                 Security vulnerability scan
  code-scalpel scan myfile.py --json          Security scan with JSON output
  code-scalpel tools                          List available MCP tools
  code-scalpel tools --tier pro               List tools for Pro tier
  code-scalpel mcp                            Start MCP server (stdio, for Claude Desktop)
  code-scalpel mcp --http --port 8080         Start MCP server (HTTP transport)
  code-scalpel mcp --http --allow-lan         Start MCP server with LAN access
  code-scalpel mcp --http --ssl-cert cert.pem --ssl-key key.pem  HTTPS for production/Claude
  code-scalpel server --port 5000             Start REST API server (legacy)
  code-scalpel version                        Show version info

For production deployments with Claude API, use HTTPS:
  code-scalpel mcp --http --ssl-cert /path/to/cert.pem --ssl-key /path/to/key.pem

For more information, visit: https://github.com/3D-Tech-Solutions/code-scalpel
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze code")
    analyze_parser.add_argument("file", nargs="?", help="File to analyze")
    analyze_parser.add_argument("--code", "-c", help="Code string to analyze")
    analyze_parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    analyze_parser.add_argument(
        "--language",
        "-l",
        choices=["python", "javascript", "java"],
        help="Source language (default: auto-detect or python)",
    )

    # Scan command (Security Analysis)
    scan_parser = subparsers.add_parser("scan", help="Scan for security vulnerabilities (SQLi, XSS, etc.)")
    scan_parser.add_argument("file", nargs="?", help="Python file to scan")
    scan_parser.add_argument("--code", "-c", help="Code string to scan")
    scan_parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    # Init command (Configuration Setup) - [20251219_FEATURE] v3.0.2
    init_parser = subparsers.add_parser("init", help="Initialize .code-scalpel configuration directory")
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
    server_parser = subparsers.add_parser("server", help="Start REST API server (legacy)")
    server_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    server_parser.add_argument("--port", "-p", type=int, default=5000, help="Port to bind to (default: 5000)")

    # MCP command (Model Context Protocol - recommended)
    mcp_parser = subparsers.add_parser("mcp", help="Start MCP server (for Claude Desktop, Cursor)")
    mcp_parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport type (default: stdio)",
    )
    mcp_parser.add_argument(
        "--http",
        action="store_true",
        help="Use HTTP transport (alias for --transport sse)",
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

    # License management commands
    license_parser = subparsers.add_parser("license", help="Manage Code Scalpel licenses")
    license_subparsers = license_parser.add_subparsers(dest="license_command")

    install_parser = license_subparsers.add_parser("install", help="Validate and install a license JWT")
    install_parser.add_argument(
        "license_file",
        help="Path to the license JWT file to install",
    )
    install_parser.add_argument(
        "--dest",
        default=None,
        help="Optional destination path (default: ~/.config/code-scalpel/license.jwt)",
    )
    install_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite destination if it already exists",
    )

    # Version command
    subparsers.add_parser("version", help="Show version information")

    # Tools command - [20260123_FEATURE] List available MCP tools
    tools_parser = subparsers.add_parser("tools", help="List available MCP tools for current tier")
    tools_parser.add_argument(
        "--tier",
        choices=["community", "pro", "enterprise"],
        default=None,
        help="Tool tier to show (default: current license tier)",
    )
    tools_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
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
        default="code-scalpel regenerate-manifest",
        help="Signer identity for manifest",
    )

    args = parser.parse_args()

    if args.command == "analyze":
        output_format = "json" if args.json else "text"
        if args.code:
            return analyze_code(args.code, output_format, language=args.language or "python")
        elif args.file:
            return analyze_file(args.file, output_format, language=args.language)
        else:
            analyze_parser.print_help()
            return 1

    elif args.command == "scan":
        output_format = "json" if args.json else "text"
        if args.code:
            return scan_code_security(args.code, output_format)
        elif args.file:
            return scan_security(args.file, output_format)
        else:
            scan_parser.print_help()
            return 1

    elif args.command == "init":  # [20251219_FEATURE] v3.0.2
        return init_configuration(args.dir, args.force)

    elif args.command == "verify-policies":  # [20241225_FEATURE] v3.3.0
        return verify_policies_command(args.dir, args.manifest_source)

    elif args.command == "regenerate-manifest":  # [20241225_FEATURE] v3.3.0
        return regenerate_manifest_command(args.dir, args.signed_by)

    elif args.command == "server":
        return start_server(args.host, args.port)

    elif args.command == "license":
        if args.license_command == "install":
            return _license_install(args.license_file, dest_path=args.dest, force=args.force)

        license_parser.print_help()
        return 1

    elif args.command == "mcp":
        transport = args.transport
        if args.http:
            transport = "sse"

        allow_lan = getattr(args, "allow_lan", False)
        root_path = getattr(args, "root", None)
        tier = getattr(args, "tier", None)
        ssl_certfile = getattr(args, "ssl_cert", None)
        ssl_keyfile = getattr(args, "ssl_key", None)
        license_file = getattr(args, "license_file", None)

        # Build kwargs for server startup
        start_kwargs = {
            "transport": transport,
            "host": args.host,
            "port": args.port,
            "allow_lan": allow_lan,
            "root_path": root_path,
            "tier": tier,
        }
        if license_file:
            start_kwargs["license_file"] = license_file
        if ssl_certfile and ssl_keyfile:
            start_kwargs.update(
                {
                    "ssl_certfile": ssl_certfile,
                    "ssl_keyfile": ssl_keyfile,
                }
            )

        # Keep main() compatible with older stubs/tests by filtering unknown kwargs.
        import inspect

        def _filter_kwargs_for_callable(func, kwargs: dict) -> dict:
            try:
                sig = inspect.signature(func)
            except Exception:
                return kwargs

            for param in sig.parameters.values():
                if param.kind == inspect.Parameter.VAR_KEYWORD:
                    return kwargs

            allowed = set(sig.parameters.keys())
            return {k: v for k, v in kwargs.items() if k in allowed}

        return start_mcp_server(**_filter_kwargs_for_callable(start_mcp_server, start_kwargs))

    elif args.command == "version":
        print(f"Code Scalpel v{__version__}")
        print(f"Python {sys.version}")
        return 0

    elif args.command == "tools":  # [20260123_FEATURE]
        return list_tools_command(args.tier, args.json)

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
