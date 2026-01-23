# Governance Configuration Schema

<!-- [20251218_FEATURE] Immutable configuration for Change Budgeting and Blast Radius control -->

## Overview

This document defines the configuration schema for governance controls including Change Budgeting and Blast Radius limits. These settings can be configured in `.vscode/mcp.json` (workspace-specific) or environment variables (system-wide), with cryptographic integrity protection to prevent tampering.

## Configuration Locations

### 1. VS Code MCP Configuration (Workspace-Specific)

**File:** `.vscode/mcp.json`

```json
{
  "servers": {
    "code-scalpel": {
      "type": "stdio",
      "command": "/path/to/code-scalpel",
      "args": ["mcp", "--root", "${workspaceFolder}"],
      "env": {
        "SCALPEL_CONFIG": "${workspaceFolder}/.code-scalpel/config.json",
        "SCALPEL_CONFIG_HASH": "sha256:abc123..."
      }
    }
  }
}
```

### 2. Scalpel Configuration File (Immutable)

**File:** `.code-scalpel/config.json`

```json
{
  "version": "3.0.0",
  "governance": {
    "change_budgeting": {
      "enabled": true,
      "max_lines_per_change": 500,
      "max_files_per_change": 10,
      "max_complexity_delta": 50,
      "require_justification": true,
      "budget_refresh_interval_hours": 24
    },
    "blast_radius": {
      "enabled": true,
      "max_affected_functions": 20,
      "max_affected_classes": 5,
      "max_call_graph_depth": 3,
      "warn_on_public_api_changes": true,
      "block_on_critical_paths": true,
      "critical_paths": [
        "src/core/",
        "src/security/",
        "src/symbolic_execution_tools/",
        "src/mcp/server.py"
      ],
      "critical_path_max_lines": 50,
      "critical_path_max_complexity_delta": 10
    },
    "autonomy_constraints": {
      "max_autonomous_iterations": 10,
      "require_approval_for_breaking_changes": true,
      "require_approval_for_security_changes": true,
      "sandbox_execution_required": true
    },
    "audit": {
      "log_all_changes": true,
      "log_rejected_changes": true,
      "retention_days": 90
    }
  }
}
```

### 3. Environment Variables (System-Wide Override)

Override individual settings via environment variables with `SCALPEL_` prefix:

```bash
# Change Budgeting
export SCALPEL_CHANGE_BUDGET_MAX_LINES=500
export SCALPEL_CHANGE_BUDGET_MAX_FILES=10
export SCALPEL_CHANGE_BUDGET_MAX_COMPLEXITY_DELTA=50

# Blast Radius
export SCALPEL_BLAST_RADIUS_MAX_FUNCTIONS=20
export SCALPEL_BLAST_RADIUS_MAX_CLASSES=5
export SCALPEL_BLAST_RADIUS_MAX_DEPTH=3

# Critical Paths (comma-separated)
export SCALPEL_CRITICAL_PATHS="src/core/,src/security/,src/mcp/server.py"
export SCALPEL_CRITICAL_PATH_MAX_LINES=50
export SCALPEL_CRITICAL_PATH_MAX_COMPLEXITY_DELTA=10

# Autonomy
export SCALPEL_MAX_AUTONOMOUS_ITERATIONS=10
export SCALPEL_REQUIRE_APPROVAL_BREAKING=true
export SCALPEL_REQUIRE_APPROVAL_SECURITY=true
```

## Critical Paths

<!-- [20251218_FEATURE] Critical paths for enhanced governance in sensitive code areas -->

Critical paths allow you to designate specific directories or files that require stricter change controls. This is essential for:

- **Core Infrastructure**: Security modules, authentication, authorization
- **Data Processing**: Payment processing, PII handling, encryption
- **Public APIs**: Interfaces with external systems or downstream consumers
- **Safety-Critical Code**: Medical devices, autonomous systems, financial calculations

### Defining Critical Paths

Critical paths are glob-style patterns matching file or directory paths:

```json
{
  "blast_radius": {
    "critical_paths": [
      "src/core/",                    // Entire core directory
      "src/security/",                // Security module
      "src/mcp/server.py",           // Specific critical file
      "src/payments/**/*.py",         // All Python files in payments
      "src/*/authentication.py"       // Authentication files anywhere
    ]
  }
}
```

### Enhanced Controls for Critical Paths

When a change affects files matching critical paths, stricter limits apply:

| Setting | Regular Code | Critical Path Code |
|---------|--------------|-------------------|
| Max Lines Changed | 500 (default) | 50 (default) |
| Max Complexity Increase | 50 (default) | 10 (default) |
| Approval Required | Configurable | Always required |
| Blast Radius Analysis | Standard | Enhanced depth |

### Pattern Matching Rules

Critical path patterns use glob syntax:
- `src/core/` - Matches directory and all subdirectories
- `src/security/*.py` - Matches Python files directly in security/
- `src/**/auth*.py` - Matches auth files anywhere under src/
- `src/mcp/server.py` - Matches specific file exactly

**Important:** Paths are relative to project root. Use forward slashes (/) even on Windows.

### Use Cases

#### Example 1: Financial Services

```json
{
  "blast_radius": {
    "critical_paths": [
      "src/trading/",
      "src/compliance/",
      "src/audit/",
      "src/calculations/interest.py",
      "src/calculations/risk.py"
    ],
    "critical_path_max_lines": 25,
    "critical_path_max_complexity_delta": 5
  }
}
```

**Rationale:** Trading algorithms and compliance code require maximum scrutiny. Even small changes need careful review.

#### Example 2: Healthcare Application

```json
{
  "blast_radius": {
    "critical_paths": [
      "src/patient_data/",
      "src/diagnosis/",
      "src/prescription/",
      "src/phi_handling/"
    ],
    "critical_path_max_lines": 50,
    "critical_path_max_complexity_delta": 10,
    "block_on_critical_paths": true
  }
}
```

**Rationale:** HIPAA compliance and patient safety require blocking autonomous changes to PHI and medical logic.

#### Example 3: Open Source Security Infrastructure

```json
{
  "blast_radius": {
    "critical_paths": [
      "src/symbolic_execution_tools/security_analyzer.py",
      "src/mcp/server.py",
      "src/ast_tools/security_scanner.py",
      "src/policy_engine/"
    ],
    "critical_path_max_lines": 30,
    "critical_path_max_complexity_delta": 8,
    "warn_on_public_api_changes": true
  }
}
```

**Rationale:** Security analysis tools themselves require extra scrutiny to prevent introducing blind spots.

### Checking if Path is Critical

To check if a file is considered critical:

```python
from pathlib import Path
from code_scalpel.config.governance_config import GovernanceConfigLoader

loader = GovernanceConfigLoader()
config = loader.load()

def is_critical_path(file_path: str) -> bool:
    """Check if file matches any critical path pattern."""
    from fnmatch import fnmatch
    path = Path(file_path).as_posix()
    
    for pattern in config.blast_radius.critical_paths:
        if fnmatch(path, pattern) or path.startswith(pattern):
            return True
    return False

# Example usage
if is_critical_path("src/security/auth.py"):
    print("WARNING: Modifying critical security code!")
    print(f"Max lines allowed: {config.blast_radius.critical_path_max_lines}")
```

## Immutability Protection

### Configuration Hash Validation

To prevent tampering, configuration files use SHA-256 hash verification:

```python
# Generate hash for config.json
import hashlib
import json

with open('.code-scalpel/config.json', 'rb') as f:
    config_hash = hashlib.sha256(f.read()).hexdigest()
    print(f"SCALPEL_CONFIG_HASH=sha256:{config_hash}")
```

Set the hash in `.vscode/mcp.json`:

```json
{
  "servers": {
    "code-scalpel": {
      "env": {
        "SCALPEL_CONFIG_HASH": "sha256:abc123..."
      }
    }
  }
}
```

### Signed Configuration (Enterprise)

For enterprise deployments, use HMAC-SHA256 signed configurations:

```bash
# Generate signed config
export SCALPEL_CONFIG_SECRET="your-secret-key"
python -c "
import hmac
import hashlib
with open('.code-scalpel/config.json', 'rb') as f:
    sig = hmac.new(b'your-secret-key', f.read(), hashlib.sha256).hexdigest()
    print(f'SCALPEL_CONFIG_SIGNATURE={sig}')
"
```

## Configuration Schema Reference

### Change Budgeting Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable change budgeting |
| `max_lines_per_change` | integer | `500` | Maximum lines modified per change |
| `max_files_per_change` | integer | `10` | Maximum files modified per change |
| `max_complexity_delta` | integer | `50` | Maximum cyclomatic complexity increase |
| `require_justification` | boolean | `true` | Require reason for large changes |
| `budget_refresh_interval_hours` | integer | `24` | Budget reset interval |

### Blast Radius Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable blast radius control |
| `max_affected_functions` | integer | `20` | Max functions impacted by change |
| `max_affected_classes` | integer | `5` | Max classes impacted by change |
| `max_call_graph_depth` | integer | `3` | Max depth for impact analysis |
| `warn_on_public_api_changes` | boolean | `true` | Warn when public API modified |
| `block_on_critical_paths` | boolean | `true` | Block changes to critical code paths |
| `critical_paths` | array[string] | `[]` | Directories/files requiring extra scrutiny |
| `critical_path_max_lines` | integer | `50` | Max lines changed in critical paths |
| `critical_path_max_complexity_delta` | integer | `10` | Max complexity increase in critical paths |

### Autonomy Constraints

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `max_autonomous_iterations` | integer | `10` | Max autonomous fix attempts |
| `require_approval_for_breaking_changes` | boolean | `true` | Human approval for breaking changes |
| `require_approval_for_security_changes` | boolean | `true` | Human approval for security changes |
| `sandbox_execution_required` | boolean | `true` | Require sandboxed testing before apply |

### Audit Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `log_all_changes` | boolean | `true` | Log all code modifications |
| `log_rejected_changes` | boolean | `true` | Log rejected changes |
| `retention_days` | integer | `90` | Log retention period |

## Usage Examples

### Example 1: Restrictive Configuration (Security-Critical Projects)

```json
{
  "governance": {
    "change_budgeting": {
      "enabled": true,
      "max_lines_per_change": 100,
      "max_files_per_change": 3,
      "max_complexity_delta": 10,
      "require_justification": true
    },
    "blast_radius": {
      "enabled": true,
      "max_affected_functions": 5,
      "max_affected_classes": 2,
      "max_call_graph_depth": 2,
      "block_on_critical_paths": true,
      "critical_paths": [
        "src/core/",
        "src/security/",
        "src/symbolic_execution_tools/security_analyzer.py"
      ],
      "critical_path_max_lines": 25,
      "critical_path_max_complexity_delta": 5
    },
    "autonomy_constraints": {
      "max_autonomous_iterations": 3,
      "require_approval_for_breaking_changes": true,
      "require_approval_for_security_changes": true,
      "sandbox_execution_required": true
    }
  }
}
```

### Example 2: Permissive Configuration (Experimental Projects)

```json
{
  "governance": {
    "change_budgeting": {
      "enabled": true,
      "max_lines_per_change": 2000,
      "max_files_per_change": 50,
      "max_complexity_delta": 200,
      "require_justification": false
    },
    "blast_radius": {
      "enabled": true,
      "max_affected_functions": 100,
      "max_affected_classes": 20,
      "max_call_graph_depth": 5,
      "warn_on_public_api_changes": false,
      "block_on_critical_paths": false,
      "critical_paths": [],
      "critical_path_max_lines": 200,
      "critical_path_max_complexity_delta": 50
    },
    "autonomy_constraints": {
      "max_autonomous_iterations": 50,
      "require_approval_for_breaking_changes": false,
      "require_approval_for_security_changes": true,
      "sandbox_execution_required": true
    }
  }
}
```

### Example 3: Team-Specific Configuration (Gradual Rollout)

```json
{
  "governance": {
    "change_budgeting": {
      "enabled": true,
      "max_lines_per_change": 300,
      "max_files_per_change": 5,
      "budget_refresh_interval_hours": 8
    },
    "blast_radius": {
      "enabled": true,
      "max_affected_functions": 15,
      "max_affected_classes": 4,
      "warn_on_public_api_changes": true
    },
    "autonomy_constraints": {
      "max_autonomous_iterations": 5,
      "require_approval_for_breaking_changes": true,
      "sandbox_execution_required": true
    }
  }
}
```

## Implementation

### Configuration Loader (src/code_scalpel/config/governance_config.py)

```python
import os
import json
import hashlib
import hmac
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

@dataclass
class ChangeBudgetingConfig:
    enabled: bool = True
    max_lines_per_change: int = 500
    max_files_per_change: int = 10
    max_complexity_delta: int = 50
    require_justification: bool = True
    budget_refresh_interval_hours: int = 24

@dataclass
class BlastRadiusConfig:
    enabled: bool = True
    max_affected_functions: int = 20
    max_affected_classes: int = 5
    max_call_graph_depth: int = 3
    warn_on_public_api_changes: bool = True
    block_on_critical_paths: bool = True
    critical_paths: list[str] = None
    critical_path_max_lines: int = 50
    critical_path_max_complexity_delta: int = 10
    
    def __post_init__(self):
        if self.critical_paths is None:
            self.critical_paths = []

@dataclass
class AutonomyConstraintsConfig:
    max_autonomous_iterations: int = 10
    require_approval_for_breaking_changes: bool = True
    require_approval_for_security_changes: bool = True
    sandbox_execution_required: bool = True

@dataclass
class AuditConfig:
    log_all_changes: bool = True
    log_rejected_changes: bool = True
    retention_days: int = 90

@dataclass
class GovernanceConfig:
    change_budgeting: ChangeBudgetingConfig
    blast_radius: BlastRadiusConfig
    autonomy_constraints: AutonomyConstraintsConfig
    audit: AuditConfig

class GovernanceConfigLoader:
    """Load and validate governance configuration with integrity protection."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.cwd() / ".code-scalpel" / "config.json"
    
    def load(self) -> GovernanceConfig:
        """Load configuration with hash validation."""
        # Check for environment variable overrides
        config_path_env = os.getenv("SCALPEL_CONFIG")
        if config_path_env:
            self.config_path = Path(config_path_env)
        
        # Load and validate configuration
        if self.config_path.exists():
            config_data = self._load_and_validate()
        else:
            config_data = self._get_defaults()
        
        # Apply environment variable overrides
        config_data = self._apply_env_overrides(config_data)
        
        return self._parse_config(config_data)
    
    def _load_and_validate(self) -> dict:
        """Load config file and validate integrity."""
        with open(self.config_path, 'rb') as f:
            content = f.read()
        
        # Validate hash if provided
        expected_hash = os.getenv("SCALPEL_CONFIG_HASH")
        if expected_hash:
            actual_hash = f"sha256:{hashlib.sha256(content).hexdigest()}"
            if actual_hash != expected_hash:
                raise ValueError(
                    f"Configuration hash mismatch. Expected {expected_hash}, "
                    f"got {actual_hash}. Configuration may have been tampered with."
                )
        
        # Validate HMAC signature if secret provided
        secret = os.getenv("SCALPEL_CONFIG_SECRET")
        expected_sig = os.getenv("SCALPEL_CONFIG_SIGNATURE")
        if secret and expected_sig:
            actual_sig = hmac.new(
                secret.encode(), content, hashlib.sha256
            ).hexdigest()
            if actual_sig != expected_sig:
                raise ValueError(
                    "Configuration signature invalid. Configuration may have been tampered with."
                )
        
        return json.loads(content)
    
    def _get_defaults(self) -> dict:
        """Return default configuration."""
        return {
            "governance": {
                "change_budgeting": {
                    "enabled": True,
                    "max_lines_per_change": 500,
                    "max_files_per_change": 10,
                    "max_complexity_delta": 50,
                    "require_justification": True,
                    "budget_refresh_interval_hours": 24
                },
                "blast_radius": {
                    "enabled": True,
                    "max_affected_functions": 20,
                    "max_affected_classes": 5,
                    "max_call_graph_depth": 3,
                    "warn_on_public_api_changes": True,
                    "block_on_critical_paths": True,
                    "critical_paths": [],
                    "critical_path_max_lines": 50,
                    "critical_path_max_complexity_delta": 10
                },
                "autonomy_constraints": {
                    "max_autonomous_iterations": 10,
                    "require_approval_for_breaking_changes": True,
                    "require_approval_for_security_changes": True,
                    "sandbox_execution_required": True
                },
                "audit": {
                    "log_all_changes": True,
                    "log_rejected_changes": True,
                    "retention_days": 90
                }
            }
        }
    
    def _apply_env_overrides(self, config: dict) -> dict:
        """Apply environment variable overrides."""
        gov = config.get("governance", {})
        
        # Change Budgeting overrides
        cb = gov.get("change_budgeting", {})
        cb["max_lines_per_change"] = int(os.getenv(
            "SCALPEL_CHANGE_BUDGET_MAX_LINES",
            cb.get("max_lines_per_change", 500)
        ))
        cb["max_files_per_change"] = int(os.getenv(
            "SCALPEL_CHANGE_BUDGET_MAX_FILES",
            cb.get("max_files_per_change", 10)
        ))
        cb["max_complexity_delta"] = int(os.getenv(
            "SCALPEL_CHANGE_BUDGET_MAX_COMPLEXITY_DELTA",
            cb.get("max_complexity_delta", 50)
        ))
        
        # Blast Radius overrides
        br = gov.get("blast_radius", {})
        br["max_affected_functions"] = int(os.getenv(
            "SCALPEL_BLAST_RADIUS_MAX_FUNCTIONS",
            br.get("max_affected_functions", 20)
        ))
        br["max_affected_classes"] = int(os.getenv(
            "SCALPEL_BLAST_RADIUS_MAX_CLASSES",
            br.get("max_affected_classes", 5)
        ))
        br["max_call_graph_depth"] = int(os.getenv(
            "SCALPEL_BLAST_RADIUS_MAX_DEPTH",
            br.get("max_call_graph_depth", 3)
        ))
        
        # Critical Paths overrides
        critical_paths_env = os.getenv("SCALPEL_CRITICAL_PATHS")
        if critical_paths_env:
            br["critical_paths"] = [p.strip() for p in critical_paths_env.split(",")]
        br["critical_path_max_lines"] = int(os.getenv(
            "SCALPEL_CRITICAL_PATH_MAX_LINES",
            br.get("critical_path_max_lines", 50)
        ))
        br["critical_path_max_complexity_delta"] = int(os.getenv(
            "SCALPEL_CRITICAL_PATH_MAX_COMPLEXITY_DELTA",
            br.get("critical_path_max_complexity_delta", 10)
        ))
        
        # Autonomy overrides
        ac = gov.get("autonomy_constraints", {})
        ac["max_autonomous_iterations"] = int(os.getenv(
            "SCALPEL_MAX_AUTONOMOUS_ITERATIONS",
            ac.get("max_autonomous_iterations", 10)
        ))
        ac["require_approval_for_breaking_changes"] = os.getenv(
            "SCALPEL_REQUIRE_APPROVAL_BREAKING",
            str(ac.get("require_approval_for_breaking_changes", True))
        ).lower() == "true"
        ac["require_approval_for_security_changes"] = os.getenv(
            "SCALPEL_REQUIRE_APPROVAL_SECURITY",
            str(ac.get("require_approval_for_security_changes", True))
        ).lower() == "true"
        
        return config
    
    def _parse_config(self, config_data: dict) -> GovernanceConfig:
        """Parse config dict into typed dataclasses."""
        gov = config_data.get("governance", {})
        
        return GovernanceConfig(
            change_budgeting=ChangeBudgetingConfig(**gov.get("change_budgeting", {})),
            blast_radius=BlastRadiusConfig(**gov.get("blast_radius", {})),
            autonomy_constraints=AutonomyConstraintsConfig(**gov.get("autonomy_constraints", {})),
            audit=AuditConfig(**gov.get("audit", {}))
        )
```

## Security Considerations

1. **Hash Validation**: Always set `SCALPEL_CONFIG_HASH` to detect tampering
2. **Signature Verification**: Use `SCALPEL_CONFIG_SECRET` for enterprise deployments
3. **File Permissions**: Set `.code-scalpel/config.json` to read-only (`chmod 444`)
4. **Audit Logging**: Enable audit logging to track all configuration changes
5. **Version Control**: Commit `.code-scalpel/config.json` to git for team consistency

## Migration from Previous Versions

For projects using older Code Scalpel versions without governance config:

1. Run `code-scalpel init-governance` to create `.code-scalpel/config.json`
2. Review and adjust settings for your project's risk tolerance
3. Generate and set `SCALPEL_CONFIG_HASH`
4. Update `.vscode/mcp.json` with hash environment variable
5. Test with `code-scalpel check-governance` to validate configuration

## See Also

- [Policy Engine Guide](../policy_engine_guide.md) - Policy-based access control
- [Autonomy Integration](../autonomy_integration_summary.md) - Autonomous change management
- [Security Documentation](../../SECURITY.md) - Overall security practices
