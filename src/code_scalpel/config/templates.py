"""
Configuration templates for .code-scalpel directory.

[20251219_FEATURE] v3.0.2 - Auto-initialize .code-scalpel configuration
"""

# Template for policy.yaml
POLICY_YAML_TEMPLATE = """# Code Scalpel Policy Configuration
# Learn more: https://github.com/3D-Tech-Solutions/code-scalpel/blob/main/docs/policy_engine_guide.md

version: "1.0.0"

# Policy enforcement mode
enforcement: "warn"  # Options: "warn", "block", "disabled"

# Security rules
security:
  # Block SQL injection attempts
  sql_injection: true

  # Block command injection attempts
  command_injection: true

  # Block path traversal attempts
  path_traversal: true

  # Block XSS attempts
  xss: true

# Change budgeting - limit blast radius
budgeting:
  enabled: false
  max_files_per_session: 10
  max_lines_per_file: 500
  max_total_changes: 1000

# Audit trail
audit:
  enabled: true
  log_file: ".code-scalpel/audit.log"
"""

# Agent Limits YAML template - v3.4.0+
AGENT_LIMITS_YAML_TEMPLATE = """# Agent Operation Limits
# [20251227_FEATURE] Limits for AI agent operations to prevent runaway usage

version: "1.0"

# Global limits per session
limits:
  max_files_read: 100
  max_tokens_per_session: 50000
  max_api_calls_per_hour: 1000

# Relationships:
# - These limits are checked by the MCP governance layer before tool execution
# - They complement change budgeting (autonomy.governance.change_budgeting in governance.yaml)
# - Change budgeting limits code modifications, these limit agent resource usage
"""

# Template for budget.yaml
BUDGET_YAML_TEMPLATE = """# Code Scalpel Change Budget Configuration
# Learn more: https://github.com/3D-Tech-Solutions/code-scalpel/blob/main/docs/guides/change_budgeting.md

version: "1.0.0"

# Maximum changes allowed per session
budgets:
  # File-level limits
  max_files_modified: 10
  max_files_created: 5
  max_files_deleted: 2

  # Line-level limits (per file)
  max_lines_added: 500
  max_lines_deleted: 300
  max_lines_modified: 400

  # Total session limits
  max_total_line_changes: 1000

# Reset behavior
reset:
  # Options: "session", "daily", "manual"
  mode: "session"

# Exemptions (files that don't count against budget)
exemptions:
  - "tests/**/*.py"
  - "docs/**/*.md"
"""

# Governance YAML template - v3.5.0+ (replaces dev-governance.yaml)
GOVERNANCE_YAML_TEMPLATE = """# Code Scalpel Governance Configuration
# Learn more: https://github.com/3D-Tech-Solutions/code-scalpel/blob/main/docs/governance_guide.md

version: "1.0.0"

# Autonomy governance - controls AI agent behavior and blast radius
autonomy:
  governance:
    change_budgeting:
      enabled: true
      limits:
        max_files_per_session: 10
        max_lines_per_file: 500
        max_total_changes: 1000
      reset:
        mode: "session"  # Options: "session", "daily", "manual"

    blast_radius:
      max_files_per_operation: 10
      max_lines_changed: 500
      max_functions_modified: 5
      max_classes_modified: 3

    enforcement:
      mode: "warn"  # Options: "warn", "block", "disabled"
      fail_on_violation: false
      log_violations: true

# Protected paths - cannot be modified by AI agents
protected_paths:
  - "src/security/**"
  - "src/auth/**"
  - "*.key"
  - "*.pem"
  - ".env"

# Allowed operations - whitelist of permitted AI actions
allowed_operations:
  - "analyze"
  - "extract"
  - "security_scan"
  - "get_file_context"
  - "get_symbol_references"

# Denied operations - blacklist of prohibited AI actions
denied_operations:
  - "delete_file"
  - "bulk_replace"

# Development governance policies - meta-policies for AI development behavior
policies:
  # ============================================================================
  # DOCUMENTATION POLICIES
  # ============================================================================

  - name: mandatory-readme-for-new-modules
    category: documentation
    severity: HIGH
    action: DENY
    description: |
      Every new module directory must have a README.md file explaining its purpose,
      architecture, and usage patterns. READMEs must be placed IN the module directory,
      not in a separate docs folder.
    rule: |
      package code_scalpel.dev_governance

      default allow = false

      # Check if operation creates a new module directory
      creates_new_module {
        input.operation.type == "create_directory"
        input.operation.path contains "src/"
        contains(input.operation.path, "__init__.py")
      }

      # Check if README.md is included in the same operation
      includes_readme {
        some i
        input.operation.files[i].path == concat("/", [input.operation.path, "README.md"])
      }

      # Deny if creating module without README
      allow {
        not creates_new_module
      }

      allow {
        creates_new_module
        includes_readme
      }

    remediation: |
      When creating a new module directory, always include a README.md that contains:
      1. Overview - What this module does
      2. Architecture - Key components and their relationships
      3. Integration - How it connects to the rest of the system
      4. Usage Examples - Common patterns with code samples
      5. Configuration - Required setup or config files
      6. Best Practices - Do's and don'ts

# Audit configuration
audit:
  enabled: true
  log_file: ".code-scalpel/audit.log"
  include_diffs: true
  cryptographic_signing: false
"""

# Template for README.md in .code-scalpel/
README_TEMPLATE = """# Code Scalpel Configuration Directory

This directory contains configuration files for Code Scalpel policy engine and governance features.

## Files

- `governance.yaml` - Governance and autonomy settings (change budgeting, blast radius, enforcement)
- `policy.yaml` - Security policies (SQL injection, command injection, etc.)
- `agent_limits.yaml` - Agent operation budgets (max files, tokens, API calls)
- `config.json` - Minimal metadata (version/profile only)
- `policy.manifest.json` - Signed manifest for tamper detection (optional)
- `audit.log` - Audit trail of policy decisions (auto-generated)
- `autonomy_audit/` - Autonomy engine audit logs (auto-generated)

## Environment Variables

Check `../.env.example` in the project root for required environment variables:

- **SCALPEL_MANIFEST_SECRET** - Required for cryptographic policy verification
- **SCALPEL_TOTP_SECRET** - Optional, for TOTP-based human verification

Copy `.env.example` to `.env` and update with your actual secrets.

## Getting Started

1. **Review `governance.yaml`** - Configure autonomy limits and blast radius controls
2. **Review `policy.yaml`** - Configure security rules and enforcement mode
3. **Review `agent_limits.yaml`** - Set agent operation limits (optional)
4. **Set environment variables** - Copy `.env.example` to `.env` and configure secrets
5. **Enable audit logging** - Track all policy decisions

## Documentation

- [Policy Engine Guide](https://github.com/3D-Tech-Solutions/code-scalpel/blob/main/docs/policy_engine_guide.md)
- [Governance Configuration](https://github.com/3D-Tech-Solutions/code-scalpel/blob/main/docs/governance_guide.md)
- [Change Budgeting Guide](https://github.com/3D-Tech-Solutions/code-scalpel/blob/main/docs/guides/change_budgeting.md)
- [Tamper Resistance](https://github.com/3D-Tech-Solutions/code-scalpel/blob/main/docs/security/tamper_resistance.md)
- [Code Scalpel Directory Configuration](https://github.com/3D-Tech-Solutions/code-scalpel/blob/main/docs/configuration/Code_Scalpel_Directory_Configuration.md)
- [Configuration Guide](https://github.com/3D-Tech-Solutions/code-scalpel/blob/main/docs/configuration/Configuration_Guide.md)

## Cryptographic Verification (Optional)

To enable tamper-resistant policies:

```bash
# Generate signed manifest
code-scalpel policy sign

# Verify integrity
code-scalpel policy verify
```

Learn more: https://github.com/3D-Tech-Solutions/code-scalpel
"""

# Template for config.json (main governance configuration)
CONFIG_JSON_TEMPLATE = """{
  "version": "1.0.0",
  "profile": "default",
  "description": "Default balanced configuration"
}
"""

# .gitignore template for .code-scalpel/
GITIGNORE_TEMPLATE = """# Runtime audit logs
audit.log
autonomy_audit/

# Policy override responses (generated at runtime)
override_response.json

# Signed manifest (optional - commit if using tamper resistance)
# policy.manifest.json
"""

# .env.example template for environment variables documentation
ENV_EXAMPLE_TEMPLATE = """# Code Scalpel Environment Variables
# =====================================
# Copy this file to .env and update with your actual secrets
# DO NOT commit .env file to version control

# ----------------------------------------------------------------------------
# Policy Engine Secrets
# ----------------------------------------------------------------------------

# SCALPEL_MANIFEST_SECRET (REQUIRED for production with cryptographic verification)
# Used to sign and verify policy manifests to prevent tampering
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SCALPEL_MANIFEST_SECRET=your-64-char-hex-secret-key-here

# SCALPEL_TOTP_SECRET (Optional - for human override verification)
# Used for TOTP-based human verification when overriding policy decisions
# Generate with: python -c "import secrets; print(secrets.token_hex(16))"
# SCALPEL_TOTP_SECRET=your-32-char-hex-totp-secret-here

# ----------------------------------------------------------------------------
# Additional Configuration (Optional)
# ----------------------------------------------------------------------------

# Enable debug logging for policy engine
# DEBUG_POLICY_ENGINE=false

# Custom policy file location
# SCALPEL_POLICY_PATH=.code-scalpel/policy.yaml
"""

# Dev Governance YAML template - v3.1.0+
DEV_GOVERNANCE_YAML_TEMPLATE = """# Development Governance Policies
# These policies govern AI agent behavior during development
# to enforce best practices, architectural consistency, and project management discipline

version: "1.0"
policy_type: "development_governance"
description: |
  Meta-policies that govern how AI agents should approach development tasks.
  These policies ensure consistency, quality, and adherence to project standards.

policies:
  # ============================================================================
  # DOCUMENTATION POLICIES
  # ============================================================================

  - name: mandatory-readme-for-new-modules
    category: documentation
    severity: HIGH
    action: DENY
    description: |
      Every new module directory must have a README.md file explaining its purpose,
      architecture, and usage patterns. READMEs must be placed IN the module directory,
      not in a separate docs folder.
    rule: |
      package code_scalpel.dev_governance

      default allow = false

      # Check if operation creates a new module directory
      creates_new_module {
        input.operation.type == "create_directory"
        input.operation.path contains "src/"
        contains(input.operation.path, "__init__.py")
      }

      # Check if README.md is included in the same operation
      includes_readme {
        some i
        input.operation.files[i].path == concat("/", [input.operation.path, "README.md"])
      }

      # Deny if creating module without README
      allow {
        not creates_new_module
      }

      allow {
        creates_new_module
        includes_readme
      }

    remediation: |
      When creating a new module directory, always include a README.md that contains:
      1. Overview - What this module does
      2. Architecture - Key components and their relationships
      3. Integration - How it connects to the rest of the system
      4. Usage Examples - Common patterns with code samples
      5. Configuration - Required setup or config files
      6. Best Practices - Do's and don'ts
"""

# Project Structure YAML template - v3.1.0+
PROJECT_STRUCTURE_YAML_TEMPLATE = """# Code Scalpel Project Structure Configuration
# Enforces consistent code organization and documentation standards

project_config:
  name: "code-scalpel"
  type: "python-library"
  strictness: high
  auto_fix: false  # Require manual review for production library

  # File location rules - where different file types belong
  file_locations:
    # Core modules
    core_module: "src/code_scalpel/"
    submodule: "src/code_scalpel/*/"

    # Specific component types
    policy_file: ".code-scalpel/policies/"
    rego_policy: ".code-scalpel/policies/"

    # Analysis engines
    pdg_tool: "src/code_scalpel/pdg_tools/"
    graph_engine: "src/code_scalpel/graph_engine/"
    ir_component: "src/code_scalpel/ir/"
    symbolic_execution: "src/code_scalpel/symbolic_execution_tools/"

    # Integrations
    ai_integration: "src/code_scalpel/integrations/"
    mcp_server: "src/code_scalpel/mcp/"

    # Language support
    parser: "src/code_scalpel/code_parsers/"
    polyglot_analyzer: "src/code_scalpel/polyglot/"

    # Governance & security
    policy_engine: "src/code_scalpel/policy_engine/"
    governance: "src/code_scalpel/governance/"
    security_tool: "src/code_scalpel/security/"

    # Testing
    unit_test: "tests/unit/"
    integration_test: "tests/integration/"
    e2e_test: "tests/e2e/"
    benchmark: "benchmarks/"

    # Documentation
    api_docs: "docs/api/"
    guide: "docs/guides/"
    feature_doc: "docs/features/"
    testing_doc: "docs/testing/"
    summary: "docs/summaries/"

    # Examples
    example_code: "examples/"
    example_policy: "examples/policy_examples/"

    # Configuration
    config_file: "config/"
    docker_file: "./"  # Dockerfile in root
    ci_config: ".github/workflows/"
"""

# Policies main README template
POLICIES_README_TEMPLATE = """# Policy Templates

This directory contains production-ready policy templates for enforcing governance across architecture, DevOps, and DevSecOps.

## Directory Structure

```
policies/
├── architecture/          # Architecture management
│   ├── README.md
│   ├── layered_architecture.rego
│   └── module_boundaries.rego
│
├── devops/               # DevOps best practices
│   ├── README.md
│   ├── docker_security.rego
│   └── kubernetes_manifests.rego
│
├── devsecops/            # DevSecOps automation
│   ├── README.md
│   ├── secret_detection.rego
│   └── sbom_validation.rego
│
└── project/              # Project structure
    ├── README.md
    └── structure.rego
```

## Quick Start

### 1. Enable Policies

Edit `.code-scalpel/policy.yaml`:

```yaml
policies:
  architecture:
    - name: layered-architecture
      file: policies/architecture/layered_architecture.rego
      severity: HIGH
      action: DENY

  devops:
    - name: docker-security
      file: policies/devops/docker_security.rego
      severity: HIGH
      action: DENY

  devsecops:
    - name: secret-detection
      file: policies/devsecops/secret_detection.rego
      severity: CRITICAL
      action: DENY
```

### 2. Test Policies

```bash
code-scalpel policy validate
code-scalpel policy test --category architecture
```

### 3. Customize

Copy template .rego files and modify rules to match your project requirements.

---

*Part of Code Scalpel v3.1+ Policy Engine*
"""

# Architecture policies README
ARCHITECTURE_README_TEMPLATE = """# Architecture Management Policies

This directory contains policy templates for enforcing architectural constraints and design patterns in your codebase.

## Policy Categories

### 1. Layering & Boundaries
- **layered_architecture.rego** - Enforce layered architecture (UI → Service → Data)
- **module_boundaries.rego** - Prevent cross-module violations

### 2. Design Patterns
- **dependency_injection.rego** - Enforce DI instead of singletons
- **interface_segregation.rego** - Validate interface design
- **clean_architecture.rego** - Enforce Clean Architecture principles

### 3. Code Organization
- **folder_structure.rego** - Enforce consistent folder organization
- **naming_conventions.rego** - Validate naming patterns
- **file_size_limits.rego** - Prevent monolithic files

## Usage

Enable these policies in `.code-scalpel/policy.yaml`:

```yaml
policies:
  architecture:
    - name: layered-architecture
      file: policies/architecture/layered_architecture.rego
      severity: HIGH
      action: DENY

    - name: module-boundaries
      file: policies/architecture/module_boundaries.rego
      severity: CRITICAL
      action: DENY
```

## Examples

See `examples/policy_examples/architecture/` for usage examples.

---

*Part of Code Scalpel v3.1+ Policy Engine*
"""

# DevOps policies README
DEVOPS_README_TEMPLATE = """# DevOps Policies

This directory contains policy templates for DevOps practices, infrastructure validation, and deployment safety.

## Policy Categories

### 1. Infrastructure as Code (IaC)
- **docker_security.rego** - Dockerfile best practices
- **kubernetes_manifests.rego** - Validate K8s manifest safety

### 2. Deployment Safety
- **deployment_checklist.rego** - Enforce pre-deployment checks
- **rollback_capability.rego** - Ensure rollback mechanisms

### 3. Resource Management
- **resource_limits.rego** - Enforce CPU/memory limits
- **cost_controls.rego** - Prevent expensive configurations

## Usage

Enable these policies in `.code-scalpel/policy.yaml`:

```yaml
policies:
  devops:
    - name: docker-security
      file: policies/devops/docker_security.rego
      severity: HIGH
      action: WARN

    - name: kubernetes-security
      file: policies/devops/kubernetes_manifests.rego
      severity: CRITICAL
      action: DENY
```

## Examples

See `examples/policy_examples/devops/` for usage examples.

---

*Part of Code Scalpel v3.1+ Policy Engine*
"""

# DevSecOps policies README
DEVSECOPS_README_TEMPLATE = """# DevSecOps Policies

This directory contains policy templates for security-first DevOps practices, automated security checks, and compliance enforcement.

## Policy Categories

### 1. Secret Management
- **secret_detection.rego** - Detect hardcoded secrets
- **secret_rotation.rego** - Enforce rotation policies

### 2. Dependency Security
- **sbom_validation.rego** - Software Bill of Materials checks
- **vulnerability_scanning.rego** - Known CVE detection
- **license_compliance.rego** - License policy enforcement

### 3. Container Security
- **image_scanning.rego** - Container image security
- **registry_compliance.rego** - Approved registries only

## Usage

Enable these policies in `.code-scalpel/policy.yaml`:

```yaml
policies:
  devsecops:
    - name: secret-detection
      file: policies/devsecops/secret_detection.rego
      severity: CRITICAL
      action: DENY

    - name: sbom-validation
      file: policies/devsecops/sbom_validation.rego
      severity: HIGH
      action: WARN
```

## Examples

See `examples/policy_examples/devsecops/` for usage examples.

---

*Part of Code Scalpel v3.1+ Policy Engine*
"""

# Project policies README
PROJECT_README_TEMPLATE = """# Project Structure Policies

This directory contains policies that enforce consistent code organization and documentation standards for the Code Scalpel project.

## Overview

The project structure policy ensures:
- **Consistent file placement** - Similar code in similar directories
- **Complete documentation** - README.md in every meaningful directory
- **Clean architecture** - Core analysis isolated from integrations
- **Naming conventions** - PEP 8 compliance and project standards
- **Module boundaries** - Preventing circular dependencies

## Policy: structure.rego

Enforces Code Scalpel's project structure conventions.

### Configuration

Configuration file: [.code-scalpel/project-structure.yaml](../../project-structure.yaml)

## Usage

Enable in `.code-scalpel/policy.yaml`:

```yaml
policies:
  project:
    - name: structure
      file: policies/project/structure.rego
      severity: HIGH
      action: DENY
```

---

*Part of Code Scalpel v3.1+ Policy Engine*
"""

# Layered Architecture Rego Policy
LAYERED_ARCHITECTURE_REGO_TEMPLATE = """package code_scalpel.architecture

# Layered Architecture Policy
# Enforces clean separation between presentation, business, and data layers

import future.keywords.if
import future.keywords.in

# Define layer patterns
presentation_patterns := {
    "*/ui/*", "*/views/*", "*/controllers/*", "*/pages/*",
    "*/components/*", "*/routes/*", "*/middleware/*"
}

application_patterns := {
    "*/services/*", "*/usecases/*", "*/application/*",
    "*/handlers/*", "*/commands/*", "*/queries/*"
}

domain_patterns := {
    "*/domain/*", "*/entities/*", "*/models/*",
    "*/business/*", "*/core/*"
}

infrastructure_patterns := {
    "*/infrastructure/*", "*/persistence/*", "*/repositories/*",
    "*/database/*", "*/api/*", "*/adapters/*", "*/external/*"
}

# Check if a file belongs to a specific layer
is_in_layer(file_path, patterns) if {
    some pattern in patterns
    glob.match(pattern, [], file_path)
}

# Determine file's layer
file_layer(file_path) := "presentation" if {
    is_in_layer(file_path, presentation_patterns)
}

file_layer(file_path) := "application" if {
    is_in_layer(file_path, application_patterns)
}

file_layer(file_path) := "domain" if {
    is_in_layer(file_path, domain_patterns)
}

file_layer(file_path) := "infrastructure" if {
    is_in_layer(file_path, infrastructure_patterns)
}

# Violation: Presentation calling Infrastructure directly
violation[{"msg": msg, "severity": "HIGH"}] if {
    some imp in input.imports
    file_layer(input.file) == "presentation"
    file_layer(imp.target) == "infrastructure"
    msg := sprintf("Presentation layer (%s) cannot import Infrastructure layer (%s)",
                   [input.file, imp.target])
}

# Violation: Domain calling any other layer
violation[{"msg": msg, "severity": "CRITICAL"}] if {
    some imp in input.imports
    file_layer(input.file) == "domain"
    file_layer(imp.target) != "domain"
    msg := sprintf("Domain layer (%s) must not import other layers (%s)",
                   [input.file, imp.target])
}
"""

# Docker Security Rego Policy
DOCKER_SECURITY_REGO_TEMPLATE = """package code_scalpel.devops

# Dockerfile Security Policy
# Enforces Docker container security best practices

import future.keywords.if
import future.keywords.in

# Check for secrets in Dockerfile
has_secrets(content) if {
    regex.match("(?i)(password|api[_-]?key|secret|token|credential)\\\\s*=", content)
}

# Check for root user
uses_root_user(lines) if {
    not any([line |
        line := lines[_]
        startswith(line, "USER ")
    ])
}

uses_root_user(lines) if {
    some line in lines
    line == "USER root"
}

# Check for :latest tag
uses_latest_tag(lines) if {
    some line in lines
    startswith(line, "FROM ")
    contains(line, ":latest")
}

# Violation: Secrets detected
violation[{"msg": "Dockerfile contains hardcoded secrets", "severity": "CRITICAL"}] if {
    has_secrets(input.content)
}

# Violation: Running as root
violation[{"msg": "Dockerfile must specify non-root USER", "severity": "HIGH"}] if {
    uses_root_user(input.lines)
}

# Violation: Using :latest tag
violation[{"msg": "Dockerfile must use specific image tags, not :latest", "severity": "MEDIUM"}] if {
    uses_latest_tag(input.lines)
}
"""

# Secret Detection Rego Policy
SECRET_DETECTION_REGO_TEMPLATE = """package code_scalpel.devsecops

# Secret Detection Policy
# Detects hardcoded secrets, API keys, tokens, and credentials

import future.keywords.if
import future.keywords.in

# AWS Access Keys
has_aws_key(content) if {
    regex.match("AKIA[0-9A-Z]{16}", content)
}

# GitHub Tokens
has_github_token(content) if {
    regex.match("ghp_[A-Za-z0-9]{36}", content)
}

# Generic API Keys
has_api_key(content) if {
    regex.match("(?i)api[_-]?key['\\\"]?\\\\s*[:=]\\\\s*['\\\"][A-Za-z0-9_\\\\-]{20,}['\\\"]", content)
}

# Private Keys
has_private_key(content) if {
    contains(content, "BEGIN RSA PRIVATE KEY")
}

has_private_key(content) if {
    contains(content, "BEGIN PRIVATE KEY")
}

# Violations
violation[{"msg": "AWS access key detected", "severity": "CRITICAL", "line": line}] if {
    some line
    has_aws_key(input.lines[line])
}

violation[{"msg": "GitHub token detected", "severity": "CRITICAL", "line": line}] if {
    some line
    has_github_token(input.lines[line])
}

violation[{"msg": "API key detected", "severity": "HIGH", "line": line}] if {
    some line
    has_api_key(input.lines[line])
}

violation[{"msg": "Private key detected", "severity": "CRITICAL", "line": line}] if {
    some line
    has_private_key(input.lines[line])
}
"""

# Project Structure Rego Policy
PROJECT_STRUCTURE_REGO_TEMPLATE = """# Code Scalpel Project Structure Policy
# Enforces consistent organization across the codebase

package project.structure

import future.keywords.if
import future.keywords.in

# Configuration loaded from .code-scalpel/project-structure.yaml
config := data.project_config

# FILE LOCATION RULES
violation[{"msg": msg, "severity": "HIGH", "file": file.path}] if {
    file := input.files[_]
    file_type := detect_file_type(file)
    file_type != "unknown"
    expected_dir := config.file_locations[file_type]
    expected_dir != null
    not path_matches(file.path, expected_dir)
    msg := sprintf("File type '%s' must be in '%s/', found in '%s'",
                   [file_type, expected_dir, file.path])
}

# README REQUIREMENTS
violation[{"msg": msg, "severity": "MEDIUM", "directory": dir}] if {
    dir := input.directories[_]
    not is_excluded_dir(dir)
    not has_readme(dir)
    msg := sprintf("Directory '%s' must have README.md", [dir])
}

# Helper functions
detect_file_type(file) := "test_file" if {
    startswith(file.name, "test_")
    endswith(file.name, ".py")
}

detect_file_type(file) := "policy_file" if {
    endswith(file.name, ".rego")
}

detect_file_type(file) := "unknown" if {
    true
}

path_matches(path, pattern) if {
    glob.match(pattern, [], path)
}

is_excluded_dir(dir) if {
    excluded := {"__pycache__", ".pytest_cache", "node_modules", ".venv", ".git"}
    some ex in excluded
    contains(dir, ex)
}

has_readme(dir) if {
    some file in input.files
    file.path == concat("/", [dir, "README.md"])
}
"""

# [20260116_FEATURE] v3.4.0 - Claude Code hooks configuration templates

# Claude settings.json template with governance hooks
CLAUDE_SETTINGS_TEMPLATE = """{
  "hooks": {
    "PreToolUse": [
      {
        "name": "code-scalpel-governance",
        "match": {
          "tools": ["Edit", "Write", "Bash", "MultiEdit"]
        },
        "command": "code-scalpel hook pre-tool-use",
        "timeout": 10000,
        "onFailure": "block"
      }
    ],
    "PostToolUse": [
      {
        "name": "code-scalpel-audit",
        "match": {
          "tools": ["Edit", "Write", "Bash", "MultiEdit"]
        },
        "command": "code-scalpel hook post-tool-use",
        "timeout": 5000,
        "onFailure": "warn"
      }
    ]
  }
}
"""

# Enterprise managed settings template
CLAUDE_MANAGED_SETTINGS_TEMPLATE = """{
  "hooks": {
    "PreToolUse": [
      {
        "name": "enterprise-governance",
        "match": {
          "tools": ["Edit", "Write", "Bash", "MultiEdit"]
        },
        "command": "code-scalpel hook pre-tool-use",
        "timeout": 10000,
        "onFailure": "block"
      }
    ],
    "PostToolUse": [
      {
        "name": "enterprise-audit",
        "match": {
          "tools": ["Edit", "Write", "Bash", "MultiEdit"]
        },
        "command": "code-scalpel hook post-tool-use",
        "timeout": 5000,
        "onFailure": "warn"
      }
    ]
  },
  "allowManagedHooksOnly": true
}
"""

# IDE extension configuration template
IDE_EXTENSION_CONFIG_TEMPLATE = """{
  "enforcement": {
    "enabled": true,
    "mode": "warn",
    "override": {
      "allowed": true,
      "requireJustification": true,
      "requireApproval": false,
      "notifyChannel": null
    }
  },
  "policies": {
    "syntaxValidation": true,
    "securityScan": true,
    "changeBudget": true,
    "customPolicies": true
  },
  "exclusions": {
    "paths": [
      "**/node_modules/**",
      "**/.git/**",
      "**/dist/**",
      "**/build/**",
      "**/__pycache__/**"
    ],
    "operators": []
  },
  "audit": {
    "logAllSaves": true,
    "logReadOnly": false,
    "destination": ".code-scalpel/audit.jsonl"
  }
}
"""

# Hooks README template
HOOKS_README_TEMPLATE = """# Code Scalpel Claude Code Hooks

This directory contains configuration for Claude Code governance hooks that enforce
Code Scalpel policies on all file operations.

## Quick Start

```bash
# Install Claude Code hooks
code-scalpel install-hooks

# Install git hooks
code-scalpel install-git-hooks
```

## How It Works

### Layer 1: Claude Code Hooks

Claude Code hooks intercept tool usage before and after execution:

- **PreToolUse**: Validates file operations against governance policies
- **PostToolUse**: Logs all operations to the audit trail

Configuration in `.claude/settings.json`:
```json
{
  "hooks": {
    "PreToolUse": [{
      "name": "code-scalpel-governance",
      "match": {"tools": ["Edit", "Write", "Bash", "MultiEdit"]},
      "command": "code-scalpel hook pre-tool-use",
      "onFailure": "block"
    }]
  }
}
```

### Layer 2: Git Hooks

Git hooks provide commit-time enforcement:

- **pre-commit**: Verifies audit coverage for all staged changes
- **commit-msg**: Logs commits to audit trail

### Enforcement Modes

| Mode | Behavior |
|------|----------|
| `audit-only` | Log all operations without blocking |
| `warn` | Warn on violations, allow operations |
| `block` | Block operations that violate policy |

## Commands

```bash
# Claude Code hooks
code-scalpel install-hooks      # Install hooks to .claude/settings.json
code-scalpel install-hooks --user  # Install to user-level settings
code-scalpel uninstall-hooks    # Remove hooks

# Git hooks
code-scalpel install-git-hooks  # Install git pre-commit/commit-msg hooks
code-scalpel verify-audit-coverage <file>  # Check audit coverage

# Manual hook invocation (used by hooks internally)
code-scalpel hook pre-tool-use  # Run governance validation
code-scalpel hook post-tool-use # Run audit logging
```

## Documentation

See `docs/architecture/IDE_ENFORCEMENT_GOVERNANCE.md` for full documentation.
"""
