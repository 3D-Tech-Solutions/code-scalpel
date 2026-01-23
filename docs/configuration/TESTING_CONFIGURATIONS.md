# Testing Governance Configurations

[20251218_DOCS] Comprehensive guide to testing different governance configuration profiles robustly.

## Overview

Code Scalpel provides 6 configuration profiles and 42 comprehensive tests covering all scenarios:

- **Default** (`config.json`) - Balanced for production use
- **Restrictive** (`config.restrictive.json`) - Security-critical systems
- **Permissive** (`config.permissive.json`) - Experimental projects
- **CI/CD** (`config.ci-cd.json`) - Automation pipelines
- **Development** (`config.development.json`) - Local development
- **Testing** (`config.testing.json`) - Unit test environments

## Test Coverage

### Profile Tests (8 tests)
Verify each configuration profile loads correctly and has appropriate values:

```bash
pytest tests/test_governance_config_profiles.py::TestConfigurationProfiles -v
```

**Coverage:**
- ✅ Default profile loads with balanced limits
- ✅ Restrictive profile has tighter limits (≤100 lines, ≤3 files, ≤3 iterations)
- ✅ Permissive profile has higher limits (≥2000 lines, ≥50 files, ≥50 iterations)
- ✅ CI/CD profile optimized for automation
- ✅ Development profile developer-friendly
- ✅ Testing profile has minimal limits (50 lines, 2 files, 2 iterations)
- ✅ All profiles are valid JSON
- ✅ Profile hierarchy verified (restrictive < default < permissive)

### Validation Tests (5 tests)
Test configuration validation and error handling:

```bash
pytest tests/test_governance_config_profiles.py::TestConfigurationValidation -v
```

**Coverage:**
- ✅ Invalid JSON raises `JSONDecodeError`
- ✅ Negative values accepted (validation happens at usage time)
- ✅ Zero values allowed
- ✅ Missing optional fields use defaults
- ✅ Extra top-level fields ignored gracefully

### Critical Path Tests (5 tests)
Test critical path pattern matching:

```bash
pytest tests/test_governance_config_profiles.py::TestCriticalPathScenarios -v
```

**Coverage:**
- ✅ Nested directory matching (`src/core/auth/oauth/provider.py` matches `src/core/`)
- ✅ Specific file patterns (`src/*/security/*.py` glob pattern)
- ✅ Windows path normalization
- ✅ Empty critical paths list
- ✅ Overlapping patterns don't break

**Example:**
```python
from code_scalpel.config.governance_config import BlastRadiusConfig

config = BlastRadiusConfig(critical_paths=[
    "src/security/",           # Directory prefix
    "config/production.yaml",  # Exact file
    "src/*/security/*.py"      # Glob pattern
])

# All these return True:
config.is_critical_path("src/security/auth.py")
config.is_critical_path("src/security/crypto/keys.py")
config.is_critical_path("config/production.yaml")
config.is_critical_path("src/api/security/routes.py")
```

### Environment Variable Tests (4 tests)
Test environment variable override scenarios:

```bash
pytest tests/test_governance_config_profiles.py::TestEnvironmentVariablePrecedence -v
```

**Coverage:**
- ✅ Env vars override file config
- ✅ Env vars work without config file
- ✅ Partial overrides (only some fields)
- ✅ Type conversion (strings → integers)

**Example:**
```bash
# Override max lines
export SCALPEL_CHANGE_BUDGET_MAX_LINES=2000

# Override critical paths
export SCALPEL_CRITICAL_PATHS="src/api/,src/db/"

# Override multiple
export SCALPEL_MAX_AUTONOMOUS_ITERATIONS=25
export SCALPEL_AUDIT_RETENTION_DAYS=365

python -c "from code_scalpel.config import GovernanceConfigLoader; \
           print(GovernanceConfigLoader().load().change_budgeting.max_lines_per_change)"
# Output: 2000
```

### Security Tests (2 tests)
Test security-focused configuration scenarios:

```bash
pytest tests/test_governance_config_profiles.py::TestSecurityScenarios -v
```

**Coverage:**
- ✅ Restrictive config blocks large changes (≤100 lines, requires justification, sandbox, audit)
- ✅ Production-suitable defaults (conservative limits, sandbox required, audit enabled)

### Use Case Tests (2 tests)
Test real-world use case configurations:

```bash
pytest tests/test_governance_config_profiles.py::TestUseCaseScenarios -v
```

**Coverage:**
- ✅ Financial application config (100 lines, 3 files, 7-year audit retention)
- ✅ Experimental prototype config (5000 lines, 100 files, no approval required)

## Running Tests

### Run All Profile Tests (42 tests)
```bash
pytest tests/test_governance_config_profiles.py -v
```

### Run Specific Test Class
```bash
pytest tests/test_governance_config_profiles.py::TestConfigurationProfiles -v
pytest tests/test_governance_config_profiles.py::TestCriticalPathScenarios -v
```

### Run Specific Test
```bash
pytest tests/test_governance_config_profiles.py::TestConfigurationProfiles::test_restrictive_profile_loads -v
```

### Run with Coverage
```bash
pytest tests/test_governance_config_profiles.py --cov=src/code_scalpel/config --cov-report=term-missing
```

## Profile Selection Guide

### When to Use Each Profile

| Profile | Use Case | Max Lines | Max Files | Iterations | Sandbox |
|---------|----------|-----------|-----------|------------|---------|
| **Restrictive** | Financial apps, healthcare, security-critical | 100 | 3 | 3 | Required |
| **Default** | Production applications | 500 | 10 | 10 | Required |
| **Development** | Local development | 750 | 15 | 15 | Optional |
| **CI/CD** | Automated pipelines | 1000 | 20 | 20 | Required |
| **Permissive** | Experimental projects | 2000 | 50 | 50 | Optional |
| **Testing** | Unit test environments | 50 | 2 | 2 | Optional |

### Selection Criteria

**Choose Restrictive when:**
- Handling sensitive data (PII, financial, health)
- Regulatory compliance required (SOX, HIPAA, PCI-DSS)
- High security risk environment
- Production critical systems

**Choose Default when:**
- Standard production application
- Balanced security and productivity
- No special compliance requirements
- General SaaS application

**Choose Permissive when:**
- Rapid prototyping phase
- Research/experimental project
- Internal tools with low risk
- Early MVP development

**Choose CI/CD when:**
- Automated deployment pipelines
- Continuous integration testing
- Infrastructure as code
- Automated refactoring tasks

**Choose Development when:**
- Local developer machines
- Feature branch development
- Interactive debugging
- Learning/exploration

**Choose Testing when:**
- Unit test suites
- Integration tests with tight constraints
- Test-driven development
- Validation of budgeting logic

## Custom Configuration Testing

### Create Custom Profile
```json
{
  "governance": {
    "change_budgeting": {
      "enabled": true,
      "max_lines_per_change": 300,
      "max_files_per_change": 5,
      "max_complexity_delta": 30,
      "require_justification": true,
      "budget_refresh_interval_hours": 24
    },
    "blast_radius": {
      "enabled": true,
      "max_affected_functions": 15,
      "max_affected_classes": 3,
      "max_call_graph_depth": 2,
      "warn_on_public_api_changes": true,
      "block_on_critical_paths": true,
      "critical_paths": [
        "src/payment/",
        "src/auth/"
      ],
      "critical_path_max_lines": 30,
      "critical_path_max_complexity_delta": 5
    },
    "autonomy_constraints": {
      "max_autonomous_iterations": 5,
      "require_approval_for_breaking_changes": true,
      "require_approval_for_security_changes": true,
      "sandbox_execution_required": true
    },
    "audit": {
      "log_all_changes": true,
      "log_rejected_changes": true,
      "retention_days": 180
    }
  }
}
```

### Test Custom Profile
```python
from pathlib import Path
from code_scalpel.config import GovernanceConfigLoader

# Load custom config
loader = GovernanceConfigLoader(Path(".code-scalpel/config.custom.json"))
config = loader.load()

# Verify values
assert config.change_budgeting.max_lines_per_change == 300
assert config.blast_radius.is_critical_path("src/payment/processor.py")
assert config.autonomy_constraints.max_autonomous_iterations == 5
```

## Integration Testing

### Test with AutonomyEngine
```python
from code_scalpel.autonomy.engine import AutonomyEngine
from code_scalpel.config import GovernanceConfigLoader

# Load restrictive config
config = GovernanceConfigLoader(
    Path(".code-scalpel/config.restrictive.json")
).load()

# Create engine with config
engine = AutonomyEngine(config=config)

# Engine should respect limits
assert engine.change_budgeting.max_lines_per_change == 100
```

### Test Critical Path Enforcement
```python
config = loader.load()

# Check if file is critical
if config.blast_radius.is_critical_path("src/security/auth.py"):
    max_lines = config.blast_radius.critical_path_max_lines  # 50
    max_complexity = config.blast_radius.critical_path_max_complexity_delta  # 10
else:
    max_lines = config.change_budgeting.max_lines_per_change  # 500
    max_complexity = config.change_budgeting.max_complexity_delta  # 50
```

## Troubleshooting

### Config Not Loading
```bash
# Check file exists
ls -la .code-scalpel/config.json

# Check JSON validity
python -m json.tool .code-scalpel/config.json

# Check permissions
chmod 644 .code-scalpel/config.json
```

### Environment Variables Not Working
```bash
# Verify env var is set
echo $SCALPEL_CHANGE_BUDGET_MAX_LINES

# Check precedence (env should win)
export SCALPEL_CHANGE_BUDGET_MAX_LINES=999
python -c "from code_scalpel.config import GovernanceConfigLoader; \
           print(GovernanceConfigLoader().load().change_budgeting.max_lines_per_change)"
```

### Hash Validation Failing
```bash
# Calculate expected hash
sha256sum .code-scalpel/config.json

# Set hash
export SCALPEL_CONFIG_HASH="sha256:abc123..."

# Load should succeed if hash matches
python -c "from code_scalpel.config import GovernanceConfigLoader; \
           GovernanceConfigLoader().load()"
```

## Best Practices

### 1. Profile Inheritance
Start with a base profile and override specific fields:

```bash
# Use restrictive as base
cp .code-scalpel/config.restrictive.json .code-scalpel/config.custom.json

# Override via environment
export SCALPEL_CHANGE_BUDGET_MAX_LINES=200
```

### 2. Version Control
Commit all profile files to git:

```bash
git add .code-scalpel/config*.json
git commit -m "Add governance config profiles"
```

### 3. Environment-Specific Configs
Use different configs per environment:

```bash
# Development
export SCALPEL_CONFIG=".code-scalpel/config.development.json"

# Staging
export SCALPEL_CONFIG=".code-scalpel/config.ci-cd.json"

# Production
export SCALPEL_CONFIG=".code-scalpel/config.restrictive.json"
```

### 4. Test Config Changes
Always test config changes before deploying:

```bash
# Test specific profile
pytest tests/test_governance_config_profiles.py::TestConfigurationProfiles::test_restrictive_profile_loads

# Test custom profile
pytest tests/test_governance_config.py --config-path=.code-scalpel/config.custom.json
```

### 5. Audit Configuration
Log which config is active:

```python
import logging
from code_scalpel.config import GovernanceConfigLoader

loader = GovernanceConfigLoader()
config = loader.load()

logging.info(f"Loaded config with max_lines={config.change_budgeting.max_lines_per_change}")
logging.info(f"Critical paths: {config.blast_radius.critical_paths}")
```

## See Also

- [Governance Configuration Schema](governance_config_schema.md)
- [Policy Engine Guide](../policy_engine_guide.md)
- [Autonomy Integration](../AUTONOMY_INTEGRATION_SUMMARY.md)
- [Change Budgeting Guide](../guides/change_budgeting.md)
