"""
Configuration initialization module.

[20251219_FEATURE] v3.0.2 - Auto-initialize .code-scalpel configuration
[20251222_FEATURE] v3.1.0 - Complete governance structure with policies
"""

import json
import secrets
from pathlib import Path
from typing import Any

import yaml

from .templates import (
    AGENT_LIMITS_YAML_TEMPLATE,
    ARCHITECTURE_README_TEMPLATE,
    CONFIG_JSON_TEMPLATE,
    DEVOPS_README_TEMPLATE,
    DEVSECOPS_README_TEMPLATE,
    DOCKER_SECURITY_REGO_TEMPLATE,
    ENV_EXAMPLE_TEMPLATE,
    GITIGNORE_TEMPLATE,
    GOVERNANCE_YAML_TEMPLATE,
    HOOKS_README_TEMPLATE,
    IDE_EXTENSION_CONFIG_TEMPLATE,
    LAYERED_ARCHITECTURE_REGO_TEMPLATE,
    POLICIES_README_TEMPLATE,
    POLICY_YAML_TEMPLATE,
    PROJECT_README_TEMPLATE,
    PROJECT_STRUCTURE_REGO_TEMPLATE,
    PROJECT_STRUCTURE_YAML_TEMPLATE,
    README_TEMPLATE,
    SECRET_DETECTION_REGO_TEMPLATE,
)


def generate_secret_key() -> str:
    """
    Generate a cryptographically secure random secret key for HMAC.

    [20241225_FEATURE] v3.3.0 - Auto-generate secure HMAC keys

    Returns:
        64-character hex string (256 bits of entropy)
    """
    return secrets.token_hex(32)


def validate_config_files(config_dir: Path) -> dict[str, Any]:
    """
    Validate configuration file formats (JSON, YAML, Rego).

    [20241225_FEATURE] v3.3.0 - Configuration validation

    Args:
        config_dir: Path to .code-scalpel directory

    Returns:
        Dictionary with validation results
    """
    # Ensure config_dir is a Path object
    if not isinstance(config_dir, Path):
        config_dir = Path(config_dir)

    validation_results = {
        "success": True,
        "errors": [],
        "warnings": [],
        "files_validated": [],
    }

    # Validate JSON files
    json_files = list(config_dir.glob("*.json"))
    for json_file in json_files:
        if json_file.exists():
            try:
                with open(json_file) as f:
                    json.load(f)
                validation_results["files_validated"].append(str(json_file.name))
            except json.JSONDecodeError as e:
                validation_results["success"] = False
                validation_results["errors"].append(f"{json_file.name}: Invalid JSON - {e}")

    # Validate YAML files
    yaml_files = list(config_dir.glob("*.yaml")) + list(config_dir.glob("*.yml"))
    for yaml_file in yaml_files:
        if yaml_file.exists():
            try:
                with open(yaml_file) as f:
                    yaml.safe_load(f)
                validation_results["files_validated"].append(str(yaml_file.name))
            except yaml.YAMLError as e:
                validation_results["success"] = False
                validation_results["errors"].append(f"{yaml_file.name}: Invalid YAML - {e}")

    # Validate Rego files (basic syntax check - just ensure they're readable)
    rego_files = list(config_dir.rglob("*.rego"))
    for rego_file in rego_files:
        if rego_file.exists():
            try:
                with open(rego_file) as f:
                    content = f.read()
                    # Basic check: must contain 'package' declaration
                    if "package" not in content:
                        validation_results["warnings"].append(
                            f"{rego_file.relative_to(config_dir)}: Missing 'package' declaration"
                        )
                validation_results["files_validated"].append(str(rego_file.relative_to(config_dir)))
            except Exception as e:
                validation_results["success"] = False
                validation_results["errors"].append(f"{rego_file.relative_to(config_dir)}: Read error - {e}")

    return validation_results


def init_config_dir(target_dir: str = ".", mode: str = "full") -> dict:
    """
    Initialize .code-scalpel configuration directory with templates.

    Args:
        target_dir: Directory where .code-scalpel should be created (default: current dir)
        mode: Initialization mode.
            - "full": CLI-style init (creates policy manifest + generates secret + writes .env)
            - "templates_only": create `.code-scalpel/` structure without secrets/manifest

    Returns:
        Dictionary with status information
    """
    # [20251230_FEATURE] Allow MCP server to auto-init without creating secrets by default.
    mode = (mode or "full").strip().lower()
    if mode not in {"full", "templates_only"}:
        return {
            "success": False,
            "message": f"Invalid init mode: {mode}. Expected 'full' or 'templates_only'.",
            "path": str(Path(target_dir).resolve() / ".code-scalpel"),
            "files_created": [],
        }

    target_path = Path(target_dir).resolve()
    config_dir = target_path / ".code-scalpel"

    # Check if directory already exists
    if config_dir.exists():
        return {
            "success": False,
            "message": f"Configuration directory already exists: {config_dir}",
            "path": str(config_dir),
            "files_created": [],
        }

    # Create directory
    config_dir.mkdir(parents=True, exist_ok=True)

    files_created = []

    # Create policy.yaml
    policy_file = config_dir / "policy.yaml"
    policy_file.write_text(POLICY_YAML_TEMPLATE)
    files_created.append("policy.yaml")

    # Create agent_limits.yaml
    agent_limits_file = config_dir / "agent_limits.yaml"
    agent_limits_file.write_text(AGENT_LIMITS_YAML_TEMPLATE)
    files_created.append("agent_limits.yaml")

    # Create README.md
    readme_file = config_dir / "README.md"
    readme_file.write_text(README_TEMPLATE)
    files_created.append("README.md")

    # Create .gitignore
    gitignore_file = config_dir / ".gitignore"
    gitignore_file.write_text(GITIGNORE_TEMPLATE)
    files_created.append(".gitignore")

    # Create config.json
    config_file = config_dir / "config.json"
    config_file.write_text(CONFIG_JSON_TEMPLATE)
    files_created.append("config.json")

    # Create .env.example with environment variable documentation
    # NOTE: Server auto-init mode should not write env files by default.
    if mode == "full":
        env_example_file = target_path / ".env.example"
        env_example_file.write_text(ENV_EXAMPLE_TEMPLATE)
        files_created.append(".env.example")

    # Initialize empty audit.log
    audit_log_file = config_dir / "audit.log"
    audit_log_file.touch()
    files_created.append("audit.log")

    # ========================================================================
    # v3.1.0+ Governance Structure
    # ========================================================================

    # Create governance.yaml
    governance_file = config_dir / "governance.yaml"
    governance_file.write_text(GOVERNANCE_YAML_TEMPLATE)
    files_created.append("governance.yaml")

    # Create project-structure.yaml
    project_structure_file = config_dir / "project-structure.yaml"
    project_structure_file.write_text(PROJECT_STRUCTURE_YAML_TEMPLATE)
    files_created.append("project-structure.yaml")

    # Create policies directory structure
    policies_dir = config_dir / "policies"
    policies_dir.mkdir(exist_ok=True)

    # Policies main README
    policies_readme = policies_dir / "README.md"
    policies_readme.write_text(POLICIES_README_TEMPLATE)
    files_created.append("policies/README.md")

    # Architecture policies
    arch_dir = policies_dir / "architecture"
    arch_dir.mkdir(exist_ok=True)
    (arch_dir / "README.md").write_text(ARCHITECTURE_README_TEMPLATE)
    (arch_dir / "layered_architecture.rego").write_text(LAYERED_ARCHITECTURE_REGO_TEMPLATE)
    files_created.append("policies/architecture/README.md")
    files_created.append("policies/architecture/layered_architecture.rego")

    # DevOps policies
    devops_dir = policies_dir / "devops"
    devops_dir.mkdir(exist_ok=True)
    (devops_dir / "README.md").write_text(DEVOPS_README_TEMPLATE)
    (devops_dir / "docker_security.rego").write_text(DOCKER_SECURITY_REGO_TEMPLATE)
    files_created.append("policies/devops/README.md")
    files_created.append("policies/devops/docker_security.rego")

    # DevSecOps policies
    devsecops_dir = policies_dir / "devsecops"
    devsecops_dir.mkdir(exist_ok=True)
    (devsecops_dir / "README.md").write_text(DEVSECOPS_README_TEMPLATE)
    (devsecops_dir / "secret_detection.rego").write_text(SECRET_DETECTION_REGO_TEMPLATE)
    files_created.append("policies/devsecops/README.md")
    files_created.append("policies/devsecops/secret_detection.rego")

    # Project structure policies
    project_dir = policies_dir / "project"
    project_dir.mkdir(exist_ok=True)
    (project_dir / "README.md").write_text(PROJECT_README_TEMPLATE)
    (project_dir / "structure.rego").write_text(PROJECT_STRUCTURE_REGO_TEMPLATE)
    files_created.append("policies/project/README.md")
    files_created.append("policies/project/structure.rego")

    # ========================================================================
    # [20251229_FEATURE] v3.3.0 - License Directory
    # ========================================================================
    license_dir = config_dir / "license"
    license_dir.mkdir(exist_ok=True)

    license_readme = license_dir / "README.md"
    license_readme.write_text("""# Code Scalpel License Directory

This directory stores license keys and cached license state.

- `license.jwt`: Place your Pro/Enterprise license key here.
- `license_state.json`: Automatically generated cache of license validation results.

Do not commit `license.jwt` to version control if it contains sensitive information.
""")
    files_created.append("license/README.md")

    # ========================================================================
    # [20260116_FEATURE] v3.4.0 - Claude Code Hooks Configuration
    # ========================================================================
    # Create IDE extension configuration
    ide_config_file = config_dir / "ide-extension.json"
    ide_config_file.write_text(IDE_EXTENSION_CONFIG_TEMPLATE)
    files_created.append("ide-extension.json")

    # Create hooks README
    hooks_readme_file = config_dir / "HOOKS_README.md"
    hooks_readme_file.write_text(HOOKS_README_TEMPLATE)
    files_created.append("HOOKS_README.md")

    # ========================================================================
    # [20241225_FEATURE] v3.3.0 - Policy Integrity Manifest
    # ========================================================================

    if mode == "templates_only":
        return {
            "success": True,
            "message": "Configuration directory created successfully (templates only)",
            "path": str(config_dir),
            "files_created": files_created,
            "validation": validate_config_files(config_dir),
            "manifest_secret": None,
        }

    # Generate secure HMAC key
    secret_key = generate_secret_key()

    # Get list of all policy files to include in manifest
    policy_files = [
        "policy.yaml",
        "governance.yaml",
        "project-structure.yaml",
        "policies/architecture/layered_architecture.rego",
        "policies/devops/docker_security.rego",
        "policies/devsecops/secret_detection.rego",
        "policies/project/structure.rego",
    ]

    # Import crypto_verify dynamically to avoid circular import
    from ..policy_engine.crypto_verify import CryptographicPolicyVerifier

    try:
        # Create signed manifest
        manifest = CryptographicPolicyVerifier.create_manifest(
            policy_files=policy_files,
            secret_key=secret_key,
            signed_by="code-scalpel init (auto-generated)",
            policy_dir=str(config_dir),
        )

        # Save manifest
        manifest_path = CryptographicPolicyVerifier.save_manifest(manifest, str(config_dir))
        # [20251230_BUGFIX] init creates policy.manifest.json (not policy_manifest.json)
        files_created.append("policy.manifest.json")

        # Create .env.example with HMAC secret documentation
        env_content = f"""# Code Scalpel Environment Variables
# Generated by: code-scalpel init
# Documentation: https://github.com/3D-Tech-Solutiions/code-scalpel/wiki/Configuration#environment-variables

# ========================================================================
# POLICY INTEGRITY VERIFICATION
# ========================================================================
# CRITICAL: This secret is required for verify_policy_integrity to work.
#
# The HMAC secret verifies that policy files haven't been tampered with.
# If an agent modifies a policy file, the hash won't match the manifest.
#
# Security Model: FAIL CLOSED
# - Missing secret -> DENY ALL operations
# - Invalid signature -> DENY ALL operations
# - Hash mismatch -> DENY ALL operations
#
# GENERATED SECRET (DO NOT COMMIT THIS VALUE):
SCALPEL_MANIFEST_SECRET={secret_key}
#
# PRODUCTION DEPLOYMENT:
# 1. Copy this secret to your CI/CD system (GitHub Secrets, etc.)
# 2. Never commit the actual secret to git
# 3. Rotate this secret if compromised
# 4. After rotation, regenerate manifest: code-scalpel regenerate-manifest
# ========================================================================
"""
        env_file = target_path / ".env"
        env_file.write_text(env_content)
        files_created.append(".env")

        # Update .gitignore to exclude .env but include .env.example
        gitignore_content = gitignore_file.read_text()
        if ".env\n" not in gitignore_content:
            gitignore_file.write_text(gitignore_content + "\n# Environment variables with secrets\n.env\n")

        # Validate all config files
        validation = validate_config_files(config_dir)

    except Exception as e:
        # If manifest generation fails, still report success but add warning
        validation = {
            "success": True,
            "errors": [],
            "warnings": [f"Failed to generate policy manifest: {e}"],
            "files_validated": [],
        }

    return {
        "success": True,
        "message": "Configuration directory created successfully",
        "path": str(config_dir),
        "files_created": files_created,
        "validation": validation,
        "manifest_secret": secret_key if "manifest" in locals() else None,
    }
