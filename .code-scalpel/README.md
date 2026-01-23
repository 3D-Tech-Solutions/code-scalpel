# Code Scalpel Governance Configuration

This directory contains all governance policies and configurations for Code Scalpel v3.0+, including runtime code policies, change budgets, and **development governance** (meta-policies for AI agent behavior).

## Table of Contents

- [Quick Start](#quick-start)
- [Policy Types](#policy-types)
- [Directory Structure](#directory-structure)
- [Available Configuration Profiles](#available-configuration-profiles)
- [Development Governance (NEW)](#development-governance)
- [Policy Engine (OPA/Rego)](#policy-engine-oparego)
- [Complete Configuration Schema Reference](#complete-configuration-schema-reference)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)

## Quick Start

```bash
# Initialize governance for a new project
code-scalpel init --governance

# Check if an operation is allowed
code-scalpel check --operation operation.json

# Check development governance (AI agent behavior)
code-scalpel dev-check --task "add new feature"

# Generate compliance report
code-scalpel compliance-report --period weekly
```

## Policy Types

Code Scalpel uses **three complementary policy systems**:

### 1. Code Modification Policies (`policy.yaml`)
**What:** Govern what code changes are allowed  
**Examples:** SQL injection prevention, XSS prevention, dangerous functions  
**Enforced by:** `PolicyEngine` class (OPA/Rego)  
**When:** Before every AI agent code modification

### 2. Change Budget Policies (`budget.yaml`)
**What:** Govern how much code can be changed  
**Examples:** Max files (10), max lines (500), forbidden paths  
**Enforced by:** `ChangeBudget` class  
**When:** Before every AI agent operation

### 3. Development Governance Policies (`dev-governance.yaml`) ⭐ **NEW**
**What:** Govern how AI agents approach development  
**Examples:** 
- Always create README in new module directories
- Update backlog when completing tasks
- Respect architectural boundaries
- Require tests for new features
- Document design decisions

**Enforced by:** `UnifiedGovernance` with development mode  
**When:** During AI agent task planning and execution

## Directory Structure

> [20251230_DOCS] **Directory contract:** `.code-scalpel/` is an optional, project-local configuration directory.
> 
> - **Zero-config mode:** MCP tools can run without `.code-scalpel/` (they fall back to defaults).
> - **Governed mode (recommended):** Add `.code-scalpel/` to your repo to make behavior deterministic and auditable.

### Root Files (`.code-scalpel/`)

**Core Configuration**
- `config.json` - **Master Configuration:** Defines blast radius, critical paths, and active governance profile.
- `governance.yaml` - **Behavior Policies:** Rules for AI agent workflows (e.g., "Always add READMEs", "No direct commits to main"). (Formerly `dev-governance.yaml`)
- `policy.yaml` - **Security Policies:** OPA/Rego rules for code analysis (allow/deny logic).
- `limits.toml` - **Tier Limits:** Defines tool capabilities (file sizes, depth) for Community/Pro/Enterprise tiers.

**Operational/Validation**
- `budget.yaml` - **Change Budget:** Persists the current session's usage against defined limits (max lines/files changed).
- `architecture.toml` - **Architecture:** Defines architectural constraints and custom metrics for `analyze_code`.
- `project-structure.yaml` - **Structure Rules:** Defines expected directory layout for validation tools.
- `policy.manifest.json` - **Integrity:** HMAC-signed manifest ensuring policy files haven't been tampered with.

**Optimization**
- `response_config.json` - **Token Optimization:** Configures which fields are returned by MCP tools to save tokens.
- `response_config.schema.json` - **Schema:** JSON Schema for validating `response_config.json`.

**Documentation**
- `README.md` - This file.
- `GOVERNANCE_PROFILES.md` - Guide to selecting the right `config.json` profile (Permissive vs. Restrictive).

**Runtime/Logs (Usually .gitignored)**
- `audit.jsonl` - **Operational Log:** JSON-lines log of every tool execution and governance decision.
- `audit.log` - **Security Log:** Cryptographically signed, tamper-evident audit trail of governance events.
- `complexity_history.json` - **Metrics History:** Tracks complexity trends over time for the `crawl_project` tool.

### Subdirectories

**`examples/`**
- Usage examples and reference configurations (e.g., `profiles/config.ci-cd.json`, `policies/test_policy.yaml`).

**`templates/`**
- Copy-ready templates for new projects (e.g., `limits.toml`, `policy.yaml`).

**`policies/`**
- Reusable Rego policy packs referenced by `policy.yaml` (e.g., `architecture/`, `devops/`).

**`license/` & `archive/`**
- Storage for JWT licenses and historical artifacts.

**Sensitive Files (DO NOT COMMIT)**
- `*.pem`, `*.key` - Private keys used for signing manifests (e.g., `development-2025-01.private.pem`).

### Current layout (v3.3.0)

```
.code-scalpel/
├── README.md                  # This file
├── config.json                # Governance config (primary)
├── config.*.json              # Optional profiles (restrictive/permissive/testing/ci-cd/etc.)
├── budget.yaml                # Change budget constraints
├── policy.yaml                # Policy engine configuration (OPA/Rego)
├── policies/                  # Rego packs referenced by policy.yaml
├── policy.manifest.json       # Policy integrity manifest (optional)
├── limits.toml                # Tier/tool limits (project-level)
├── response_config.json       # MCP response shaping
├── response_config.schema.json
├── project-structure.yaml     # Project structure expectations
├── dev-governance.yaml        # Development governance policies
├── dev-governance.minimal.yaml
├── templates/                 # Copy-ready example files
├── license/                   # Local license + state (do not commit)
├── archive/                   # License downloads (do not commit)
├── audit.log                  # Generated audit log (do not commit)
├── audit.jsonl                # Generated structured audit (do not commit)
└── autonomy_audit/            # Generated autonomy audit artifacts (do not commit)
```

## Development Governance

### Overview

Development governance policies ensure AI agents follow software engineering best practices:

| Category | Examples |
|----------|----------|
| **Documentation** | Always create README in new modules, update docs on major changes |
| **Architecture** | Respect layer boundaries (MCP → Autonomy → Governance → Tools → Parsers) |
| **Project Management** | Update TODO.md/BACKLOG.md when completing tasks |
| **Code Quality** | Require tests for new features, run linting before commit |
| **Security** | No secrets in code, require security review for auth changes |

### Example: Creating a New Module

**Without Dev Governance:**
```bash
mkdir src/code_scalpel/new_feature
touch src/code_scalpel/new_feature/__init__.py
# ✅ Allowed, but no documentation
```

**With Dev Governance:**
```bash
mkdir src/code_scalpel/new_feature
touch src/code_scalpel/new_feature/__init__.py
# ❌ DENIED: Missing README.md (policy: mandatory-readme-for-new-modules)

# Must include:
cat > src/code_scalpel/new_feature/README.md << EOF
# New Feature Module
## Overview
...
EOF
# ✅ ALLOWED
```

### AI Agent Instructions

Development governance includes explicit instructions for AI agents:

**Always:**
- Create READMEs in module directories (not separate docs/)
- Update TODO.md or BACKLOG.md when completing tasks
- Run tests after making changes
- Follow FAIL CLOSED principle for security
- Document design decisions

**Never:**
- Commit secrets or credentials
- Bypass security checks
- Modify core security code without review
- Create circular dependencies
- Hardcode environment-specific values

**Configuration:** See [dev-governance.yaml](dev-governance.yaml) for complete policy definitions.

## Available Configuration Profiles

### 1. `config.json` (Default)
**Use case:** Balanced configuration for general production use
- Max lines: 500
- Max files: 10
- Max iterations: 10
- Critical paths: Core security modules

### 2. `config.restrictive.json`
**Use case:** Security-critical projects (financial services, healthcare, infrastructure)
- Max lines: 100
- Max files: 3
- Max iterations: 3
- Extensive critical paths
- 365-day audit retention

### 3. `config.permissive.json`
**Use case:** Experimental projects, prototyping, trusted dev environments
- Max lines: 2000
- Max files: 50
- Max iterations: 50
- No critical paths
- Minimal restrictions

### 4. `config.ci-cd.json`
**Use case:** CI/CD pipelines with automated testing
- Max lines: 1000
- Max files: 20
- Max iterations: 20
- Optimized for fast feedback
- No approval for breaking changes

### 5. `config.development.json`
**Use case:** Active development with moderate controls
- Max lines: 750
- Max files: 15
- Max iterations: 15
- Developer-friendly balance

### 6. `config.testing.json`
**Use case:** Testing governance features, unit tests
- Max lines: 50 (intentionally low)
- Max files: 2
- Max iterations: 2
- Minimal limits for fast test execution

---

## Policy Engine (OPA/Rego)

This directory also contains **policy files** for Code Scalpel's Policy Engine (v2.5.0 "Guardian"), which provides declarative access control using Open Policy Agent (OPA) and Rego language.

### Policy vs Governance Config

| Aspect | Policy Engine (policy.yaml) | Governance Config (config.json) |
|--------|----------------------------|--------------------------------|
| **Purpose** | Access control - what operations are allowed | Change limits - how much change is allowed |
| **Language** | Rego (declarative rules) | JSON (configuration) |
| **Evaluation** | Query-based (can this operation proceed?) | Metric-based (does change exceed limits?) |
| **Use Cases** | Security policies, compliance rules | Budget control, blast radius |
| **Examples** | "Block SQL injection", "Require tests" | "Max 500 lines", "Max 10 files" |

Both systems work together:
1. **Policy Engine** checks if operation is allowed (authorization)
2. **Governance Config** checks if change size is acceptable (limits)

### Quick Start - Policy Engine

1. **Copy the example policy:**
   ```bash
  cp .code-scalpel/templates/policy.yaml.example .code-scalpel/policy.yaml
   ```

2. **Install OPA CLI:**
   ```bash
   # macOS
   brew install opa
   
   # Linux
   curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64
   chmod +x opa
   sudo mv opa /usr/local/bin/
   ```

3. **Test your policies:**
   ```bash
   opa check .code-scalpel/policy.yaml
   ```

4. **Use in your code:**
   ```python
   from code_scalpel.policy_engine import PolicyEngine
   
   engine = PolicyEngine(".code-scalpel/policy.yaml")
   result = engine.evaluate(operation="modify", target="src/core/auth.py")
   ```

### Policy File Structure

```yaml
version: "1.0"
policies:
  - name: "prevent-sql-injection"
    description: "Block code patterns vulnerable to SQL injection"
    rule: |
      package scalpel.security
      
      deny[msg] {
        # Rego rule logic
        input.operation == "modify"
        contains(input.code, "execute(") 
        not contains(input.code, "parameterized")
        msg = "SQL injection risk: use parameterized queries"
      }
    severity: "CRITICAL"  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    action: "DENY"         # DENY, WARN, AUDIT
```

### Available Policy Files

| File | Purpose |
|------|---------|
| `policy.yaml` | Active production policies (create from example) |
| `templates/policy.yaml.example` | Template with production-ready policies |
| `templates/policy_override.yaml` | Temporary policy overrides (copy into place if needed) |
| `templates/policy_test.yaml` | Test policies for validation (copy into place if needed) |

### Example Policies

See `templates/policy.yaml.example` for production-ready templates:
- **SQL Injection Prevention** - Detect unsafe SQL execution
- **Spring Security Enforcement** (Java) - Require @PreAuthorize annotations
- **Safe File Operations** - Prevent path traversal vulnerabilities
- **Complexity Budgeting** - Enforce cyclomatic complexity limits
- **Hardcoded Secret Detection** - Block secrets in code
- **Audit Trail** - Log all critical operations

### Policy Engine Security Model

**Fail CLOSED:** All errors result in DENY (never fails open)

**Key Features:**
- Full audit trail for all policy decisions
- Human override requires justification
- Single-use override codes (expire after 1 use)
- Time-limited overrides (1 hour default)
- Cryptographic policy integrity verification (HMAC-SHA256)

### Policy Documentation

Full policy engine documentation:
- **Complete Guide:** [docs/policy_engine_guide.md](../docs/policy_engine_guide.md)
- **Acceptance Criteria:** [docs/v2.5.0_policy_engine_acceptance.md](../docs/v2.5.0_policy_engine_acceptance.md)
- **Usage Examples:** [examples/policy_engine_example.py](../examples/policy_engine_example.py)
- **Integrity Verification:** See [docs/policy_engine.md](../docs/policy_engine.md#integrity-verification)

---

## Usage Examples

### Option 1: Symlink to Active Configuration
```bash
# Use restrictive config
ln -sf config.restrictive.json config.json

# Use permissive config
ln -sf config.permissive.json config.json

# Use CI/CD config
ln -sf config.ci-cd.json config.json
```

### Option 2: Environment Variable Override
```bash
# Point to specific config
export SCALPEL_CONFIG=/path/to/code-scalpel/.code-scalpel/config.restrictive.json

# Or use environment variables to override specific settings
export SCALPEL_CHANGE_BUDGET_MAX_LINES=1000
export SCALPEL_CRITICAL_PATHS="src/core/,src/security/"
```

### Option 3: Pass Config Path Directly
```python
from code_scalpel.config.governance_config import GovernanceConfigLoader
from pathlib import Path

# Load specific config
loader = GovernanceConfigLoader(
    config_path=Path(".code-scalpel/config.restrictive.json")
)
config = loader.load()

# Access configuration values
print(f"Max lines: {config.change_budgeting.max_lines_per_change}")
print(f"Critical paths: {config.blast_radius.critical_paths}")
```

### Option 4: Programmatic Configuration
```python
from code_scalpel.config.governance_config import (
    GovernanceConfig,
    ChangeBudgetingConfig,
    BlastRadiusConfig,
    AutonomyConstraintsConfig,
    AuditConfig
)

# Build configuration programmatically
config = GovernanceConfig(
    change_budgeting=ChangeBudgetingConfig(
        enabled=True,
        max_lines_per_change=500,
        max_files_per_change=10,
        max_complexity_delta=50
    ),
    blast_radius=BlastRadiusConfig(
        enabled=True,
        max_affected_functions=20,
        critical_paths=["src/core/", "src/security/"]
    ),
    autonomy_constraints=AutonomyConstraintsConfig(
        max_autonomous_iterations=10,
        sandbox_execution_required=True
    ),
    audit=AuditConfig(
        log_all_changes=True,
        retention_days=90
    )
)
```

### Option 5: Environment Variable Overrides (Advanced)
```bash
# Override multiple settings at once
export SCALPEL_CHANGE_BUDGET_MAX_LINES=1000
export SCALPEL_CHANGE_BUDGET_MAX_FILES=20
export SCALPEL_CRITICAL_PATHS="src/core/,src/security/,src/mcp/server.py"
export SCALPEL_CRITICAL_PATH_MAX_LINES=50
export SCALPEL_MAX_AUTONOMOUS_ITERATIONS=15

# Load config (env vars override file values)
python -c "
from code_scalpel.config.governance_config import GovernanceConfigLoader
config = GovernanceConfigLoader().load()
print(f'Max lines: {config.change_budgeting.max_lines_per_change}')  # 1000 from env
"
```

### Option 6: Per-Project Configuration
```bash
# Project A (financial services) - restrictive
cd /projects/banking-app
export SCALPEL_CONFIG=/configs/financial-restrictive.json
code-scalpel mcp

# Project B (prototype) - permissive
cd /projects/experimental-feature
export SCALPEL_CONFIG=/configs/prototype-permissive.json
code-scalpel mcp

# Project C (uses default)
cd /projects/standard-web-app
# Automatically loads .code-scalpel/config.json from project root
code-scalpel mcp
```

## Complete Configuration Schema Reference

### Root Schema

```json
{
  "version": "string (REQUIRED)",
  "profile": "string (OPTIONAL)",
  "description": "string (OPTIONAL)",
  "governance": { ... }  // REQUIRED
}
```

#### Root Fields

| Field | Type | Required | Description | Valid Values | Default |
|-------|------|----------|-------------|--------------|---------|
| `version` | string | **YES** | Schema version for compatibility checking | `"3.0.0"` (current) | None |
| `profile` | string | NO | Human-readable profile identifier | Any string (e.g., "default", "restrictive") | None |
| `description` | string | NO | Explanation of configuration purpose | Any descriptive text | None |
| `governance` | object | **YES** | Main governance settings container | Valid governance object | None |

---

## Field Reference

### Section 1: Change Budgeting (`governance.change_budgeting`)

Controls the maximum scope of changes an autonomous agent can make in a single operation.

```json
{
  "governance": {
    "change_budgeting": {
      "enabled": true,
      "max_lines_per_change": 500,
      "max_files_per_change": 10,
      "max_complexity_delta": 50,
      "require_justification": true,
      "budget_refresh_interval_hours": 24
    }
  }
}
```

#### `enabled` (boolean, REQUIRED)
**Description:** Master switch for change budgeting enforcement.

**Valid Values:**
- `true` - Enforce all change budgeting limits
- `false` - Disable change budgeting (NOT RECOMMENDED for production)

**Default:** `true`

**Behavior:**
- When `false`, all other change budgeting settings are ignored
- Agent can make unlimited changes (dangerous in production)
- Useful only for testing or highly trusted environments

**Example:**
```json
"enabled": true  // Always use this in production
```

---

#### `max_lines_per_change` (integer, REQUIRED)
**Description:** Maximum number of lines (additions + deletions) an agent can modify in a single autonomous operation.

**Valid Values:**
- Minimum: `1`
- Maximum: `100000` (practical limit)
- Recommended: `100-2000` depending on risk tolerance

**Default:** `500`

**Calculation:**
```
total_lines = lines_added + lines_deleted + lines_modified
```

**Examples:**
```json
"max_lines_per_change": 100   // Restrictive (security-critical)
"max_lines_per_change": 500   // Balanced (default)
"max_lines_per_change": 2000  // Permissive (experimental)
```

**Behavior:**
- Agent operations exceeding this limit are **rejected**
- Rejection logged in audit trail
- Agent receives clear error message with current/allowed limits
- Critical paths may have **stricter limits** (see `critical_path_max_lines`)

**Use Cases:**
| Lines | Use Case | Risk Level |
|-------|----------|------------|
| 50-100 | Security-critical code, financial systems | Very Low |
| 200-500 | Production systems, moderate risk tolerance | Low |
| 500-1000 | Development environments, CI/CD | Medium |
| 1000-2000 | Prototypes, experimental features | High |
| 2000+ | Trusted environments only | Very High |

---

#### `max_files_per_change` (integer, REQUIRED)
**Description:** Maximum number of files an agent can modify in a single operation.

**Valid Values:**
- Minimum: `1`
- Maximum: `1000` (practical limit)
- Recommended: `3-50` depending on project size

**Default:** `10`

**Behavior:**
- Counts only **modified** files (reads don't count)
- File creation, modification, and deletion all count
- Exceeding limit causes immediate rejection

**Examples:**
```json
"max_files_per_change": 3    // Restrictive (surgical changes only)
"max_files_per_change": 10   // Balanced (small features)
"max_files_per_change": 50   // Permissive (major refactors)
```

**Use Cases:**
| Files | Use Case | Typical Operations |
|-------|----------|-------------------|
| 1-3 | Bug fixes, single feature | Fix function, add test |
| 5-10 | Feature additions | Add module + tests + docs |
| 10-20 | Refactoring | Rename across files |
| 20-50 | Major features | New subsystem |
| 50+ | Framework changes | Architecture updates |

---

#### `max_complexity_delta` (integer, REQUIRED)
**Description:** Maximum increase in cyclomatic complexity allowed per change.

**Valid Values:**
- Minimum: `0` (no complexity increase allowed)
- Maximum: `1000` (practical limit)
- Recommended: `10-100` depending on tolerance

**Default:** `50`

**Cyclomatic Complexity Explained:**
```
Complexity = 1 (base) + number of decision points
Decision points: if, while, for, case, try/catch, &&, ||
```

**Examples:**
```python
# Complexity = 1 (no decision points)
def add(a, b):
    return a + b

# Complexity = 2 (one if statement)
def max_value(a, b):
    if a > b:
        return a
    return b

# Complexity = 5 (multiple branches)
def categorize(score):
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"
```

**Configuration Examples:**
```json
"max_complexity_delta": 10   // Restrictive (simple changes only)
"max_complexity_delta": 50   // Balanced (moderate logic)
"max_complexity_delta": 200  // Permissive (complex features)
```

**Behavior:**
- Calculated **per file** then summed across all changed files
- Negative deltas (simplification) are always allowed
- Exceeding limit triggers rejection + recommendation to simplify
- Critical paths have **stricter limits** (see `critical_path_max_complexity_delta`)

**Use Cases:**
| Delta | Use Case | Example Change |
|-------|----------|----------------|
| 0-10 | Refactoring, simplification | Extract function |
| 10-50 | Feature addition | Add validation |
| 50-100 | Complex features | State machine |
| 100-200 | Framework code | Plugin system |
| 200+ | Avoid (tech debt risk) | Monolithic functions |

---

#### `require_justification` (boolean, REQUIRED)
**Description:** Whether agent must provide a reason for changes approaching limits.

**Valid Values:**
- `true` - Require justification when exceeding 80% of any limit
- `false` - No justification required

**Default:** `true`

**Behavior:**
- Triggered at **80% of any limit**:
  - 80% of `max_lines_per_change`
  - 80% of `max_files_per_change`
  - 80% of `max_complexity_delta`
- Agent must provide structured justification:
  ```json
  {
    "reason": "Adding user authentication system",
    "alternatives_considered": ["External auth service", "Simple password"],
    "risk_assessment": "Medium - new security code",
    "rollback_plan": "Revert commit, disable feature flag"
  }
  ```
- Justifications logged in audit trail

**Examples:**
```json
"require_justification": true   // Recommended for production
"require_justification": false  // Only for trusted/testing environments
```

---

#### `budget_refresh_interval_hours` (integer, REQUIRED)
**Description:** How often the change budget resets (in hours).

**Valid Values:**
- Minimum: `1` (hourly reset)
- Maximum: `8760` (yearly reset)
- Recommended: `4-24` for most use cases

**Default:** `24` (daily reset)

**Behavior:**
- Budget tracks **cumulative changes** within interval
- After interval expires, budget resets to zero
- Prevents "death by a thousand cuts" attack where agent makes many small changes

**Examples:**
```json
"budget_refresh_interval_hours": 1    // Hourly (CI/CD)
"budget_refresh_interval_hours": 8    // Work day (dev)
"budget_refresh_interval_hours": 24   // Daily (default)
"budget_refresh_interval_hours": 168  // Weekly (permissive)
```

**Use Cases:**
| Interval | Use Case | Rationale |
|----------|----------|-----------|
| 1-4h | CI/CD pipelines | Fast feedback, frequent runs |
| 8h | Development hours | Aligns with work day |
| 24h | Production systems | Standard daily limit |
| 168h | Experimental projects | Weekly sprint cycles |

---

### Section 2: Blast Radius (`governance.blast_radius`)

Controls how far changes can propagate through the codebase via dependencies and call graphs.

```json
{
  "governance": {
    "blast_radius": {
      "enabled": true,
      "max_affected_functions": 20,
      "max_affected_classes": 5,
      "max_call_graph_depth": 3,
      "warn_on_public_api_changes": true,
      "block_on_critical_paths": true,
      "critical_paths": ["src/core/", "src/security/"],
      "critical_path_max_lines": 50,
      "critical_path_max_complexity_delta": 10
    }
  }
}
```

#### `enabled` (boolean, REQUIRED)
**Description:** Master switch for blast radius analysis.

**Valid Values:**
- `true` - Analyze and enforce blast radius limits
- `false` - Skip blast radius checks (NOT RECOMMENDED)

**Default:** `true`

**Behavior:**
- When `false`, impact analysis is skipped entirely
- Dangerous: allows cascading changes with no visibility
- Only disable for small projects or testing

---

#### `max_affected_functions` (integer, REQUIRED)
**Description:** Maximum number of functions that can be impacted by a change (directly or indirectly via call graph).

**Valid Values:**
- Minimum: `1`
- Maximum: `10000` (practical limit)
- Recommended: `5-100` depending on codebase size

**Default:** `20`

**Impact Calculation:**
```
affected_functions = directly_modified_functions +
                     functions_that_call_modified_functions +
                     functions_called_by_modified_functions
```

**Examples:**
```json
"max_affected_functions": 5    // Restrictive (isolated changes)
"max_affected_functions": 20   // Balanced
"max_affected_functions": 100  // Permissive (major refactors)
```

**Behavior:**
- Code Scalpel builds call graph using AST analysis
- Counts all functions within `max_call_graph_depth` hops
- Exceeding limit causes rejection with impact report
- Report includes: function names, call chains, risk assessment

**Use Cases:**
| Functions | Use Case | Example |
|-----------|----------|---------|
| 1-5 | Bug fixes | Fix validation logic |
| 5-20 | Features | Add new endpoint |
| 20-50 | Refactoring | Rename utility |
| 50-100 | Architecture | Change interface |
| 100+ | High risk | Framework update |

---

#### `max_affected_classes` (integer, REQUIRED)
**Description:** Maximum number of classes that can be impacted by a change.

**Valid Values:**
- Minimum: `1`
- Maximum: `1000` (practical limit)
- Recommended: `2-20` depending on OOP usage

**Default:** `5`

**Examples:**
```json
"max_affected_classes": 2    // Restrictive (single responsibility)
"max_affected_classes": 5    // Balanced
"max_affected_classes": 20   // Permissive (major features)
```

**Behavior:**
- Counts classes with direct modifications OR inheritance relationships
- Includes parent classes, child classes, and implementing classes
- Particularly important for OOP-heavy codebases (Java, TypeScript)

---

#### `max_call_graph_depth` (integer, REQUIRED)
**Description:** How many hops through the call graph to analyze for impact.

**Valid Values:**
- Minimum: `1` (direct callers/callees only)
- Maximum: `10` (practical limit, performance impact)
- Recommended: `2-4` for balance of safety and performance

**Default:** `3`

**Call Graph Depth Visualization:**
```
Depth 1: Function A modifies Function B
         → Impact: A, B (2 functions)

Depth 2: Function A → Function B → Function C
         → Impact: A, B, C (3 functions)

Depth 3: Function A → Function B → Function C → Function D
         → Impact: A, B, C, D (4 functions)
```

**Examples:**
```json
"max_call_graph_depth": 1    // Very fast, limited safety
"max_call_graph_depth": 3    // Balanced (default)
"max_call_graph_depth": 5    // Thorough analysis, slower
```

**Performance Considerations:**
| Depth | Analysis Time | Use Case |
|-------|---------------|----------|
| 1 | < 1s | Quick checks, CI/CD |
| 2-3 | 1-5s | Standard (recommended) |
| 4-5 | 5-30s | Thorough analysis |
| 6+ | 30s-5min | Deep systems (rare) |

---

#### `warn_on_public_api_changes` (boolean, REQUIRED)
**Description:** Whether to warn (but not block) when public API is modified.

**Valid Values:**
- `true` - Generate warnings for public API changes
- `false` - No special handling for public APIs

**Default:** `true`

**Public API Detection:**
- Python: Functions/classes without leading underscore in top-level modules
- TypeScript: Exported functions/classes
- Java: Public visibility modifier
- JavaScript: Exported members

**Behavior:**
- Generates **warning** (not rejection)
- Warning includes: API surface change description, downstream impact estimate
- Agent should provide migration guide in justification
- Useful for library maintainers

**Examples:**
```json
"warn_on_public_api_changes": true   // Recommended for libraries
"warn_on_public_api_changes": false  // OK for internal-only code
```

---

#### `block_on_critical_paths` (boolean, REQUIRED)
**Description:** Whether changes to critical paths should be **blocked** (vs. just warned).

**Valid Values:**
- `true` - **Block** changes to critical paths, require human approval
- `false` - **Warn** but allow changes to critical paths

**Default:** `true`

**Behavior When `true`:**
- Any file matching `critical_paths` patterns triggers **rejection**
- Agent receives error: "Critical path modification requires human approval"
- Change must go through manual review process
- Audit trail logs blocked attempts

**Behavior When `false`:**
- Files matching `critical_paths` generate **warnings**
- Agent can proceed but with stricter limits (`critical_path_max_lines`)
- Logged for review but not blocked

**Examples:**
```json
"block_on_critical_paths": true   // Recommended for production (fail-safe)
"block_on_critical_paths": false  // Only for trusted dev environments
```

**Use Cases:**
| Setting | Use Case | Risk Tolerance |
|---------|----------|----------------|
| `true` | Production, financial, healthcare | Zero risk |
| `false` | Development, prototyping | Moderate risk |

---

#### `critical_paths` (array of strings, REQUIRED)
**Description:** Glob patterns matching directories or files that require extra scrutiny.

**Valid Values:**
- Array of glob pattern strings
- Empty array `[]` disables critical path protection
- Patterns relative to project root

**Default:** `[]` (no critical paths)

**Glob Pattern Syntax:**
```
src/core/              → Match entire directory and subdirectories
src/security/*.py      → Match Python files directly in security/
src/**/auth*.py        → Match auth files anywhere under src/
src/mcp/server.py      → Match specific file exactly
```

**Pattern Matching Rules:**
- **Forward slashes** only (even on Windows)
- **Trailing slash** for directories includes all subdirectories
- `*` matches any characters except `/`
- `**` matches any characters including `/` (recursive)
- Case-sensitive on Unix, case-insensitive on Windows

**Examples:**
```json
// Security-critical project
"critical_paths": [
  "src/core/",
  "src/security/",
  "src/symbolic_execution_tools/security_analyzer.py",
  "src/mcp/server.py",
  "src/policy_engine/"
]

// Financial services
"critical_paths": [
  "src/trading/",
  "src/compliance/",
  "src/audit/",
  "src/calculations/"
]

// Healthcare application
"critical_paths": [
  "src/patient_data/",
  "src/diagnosis/",
  "src/prescription/",
  "src/phi_handling/"
]

// Web application
"critical_paths": [
  "src/authentication/",
  "src/authorization/",
  "config/security.yaml"
]
```

**Validation:**
- Patterns validated at config load time
- Invalid patterns logged as warnings
- Files matched against patterns using `fnmatch` (Python standard library)

**Performance:**
- Pattern matching is O(n*m) where n=files changed, m=patterns
- Keep patterns count reasonable (< 50 for best performance)

---

#### `critical_path_max_lines` (integer, REQUIRED)
**Description:** Stricter line limit for files matching critical paths.

**Valid Values:**
- Minimum: `1`
- Maximum: `10000` (but should be much lower than `max_lines_per_change`)
- Recommended: `25-100` (stricter than standard limit)

**Default:** `50`

**Relationship to `max_lines_per_change`:**
```
critical_path_max_lines < max_lines_per_change
```

**Examples:**
```json
// Standard limit: 500, Critical limit: 50
{
  "change_budgeting": {
    "max_lines_per_change": 500
  },
  "blast_radius": {
    "critical_path_max_lines": 50  // 10x stricter
  }
}

// Restrictive configuration
{
  "change_budgeting": {
    "max_lines_per_change": 100
  },
  "blast_radius": {
    "critical_path_max_lines": 25  // 4x stricter
  }
}
```

**Behavior:**
- Applies **in addition to** standard line limits
- **Smallest limit wins**:
  ```
  effective_limit = min(max_lines_per_change, critical_path_max_lines)
  ```
- Rejection message specifies which limit was exceeded

**Use Cases:**
| Lines | Use Case | Example |
|-------|----------|---------|
| 10-25 | Bug fixes only | Fix validation |
| 25-50 | Small features | Add field |
| 50-100 | Moderate features | New endpoint |
| 100+ | Avoid (defeats purpose) | Major refactor |

---

#### `critical_path_max_complexity_delta` (integer, REQUIRED)
**Description:** Stricter complexity increase limit for critical paths.

**Valid Values:**
- Minimum: `0` (no complexity increase)
- Maximum: `1000` (but should be much lower than `max_complexity_delta`)
- Recommended: `5-20` (significantly stricter)

**Default:** `10`

**Examples:**
```json
// Standard delta: 50, Critical delta: 10
{
  "change_budgeting": {
    "max_complexity_delta": 50
  },
  "blast_radius": {
    "critical_path_max_complexity_delta": 10  // 5x stricter
  }
}
```

**Behavior:**
- Forces simpler logic in security-critical code
- Encourages extracting complex logic to non-critical modules
- Helps maintain audit-ability of critical paths

---

### Section 3: Autonomy Constraints (`governance.autonomy_constraints`)

Controls autonomous agent behavior and escalation policies.

```json
{
  "governance": {
    "autonomy_constraints": {
      "max_autonomous_iterations": 10,
      "require_approval_for_breaking_changes": true,
      "require_approval_for_security_changes": true,
      "sandbox_execution_required": true
    }
  }
}
```

#### `max_autonomous_iterations` (integer, REQUIRED)
**Description:** Maximum number of fix attempts before escalating to human.

**Valid Values:**
- Minimum: `1` (single attempt only)
- Maximum: `100` (practical limit, avoid infinite loops)
- Recommended: `3-20` depending on trust level

**Default:** `10`

**Fix Loop Behavior:**
```
Iteration 1: Attempt fix → Test → Success? → Done
                                 ↓ Failure
Iteration 2: Adjust fix → Test → Success? → Done
                                 ↓ Failure
...
Iteration N: Max reached → ESCALATE TO HUMAN
```

**Examples:**
```json
"max_autonomous_iterations": 3    // Restrictive (quick escalation)
"max_autonomous_iterations": 10   // Balanced
"max_autonomous_iterations": 50   // Permissive (patient agent)
```

**Termination Conditions:**
1. **Success** - Fix passes all tests
2. **Max attempts** - Exceeded `max_autonomous_iterations`
3. **Timeout** - Exceeded time limit (300s default)
4. **Repeated error** - Same error seen twice
5. **No valid fixes** - Error-to-diff engine can't generate fixes

**Use Cases:**
| Iterations | Use Case | Rationale |
|------------|----------|-----------|
| 1-3 | Security-critical | Fast human escalation |
| 5-10 | Standard production | Balanced autonomy |
| 10-20 | Development | More exploration |
| 20-50 | Experimental | Maximum autonomy |
| 50+ | Not recommended | Likely infinite loop |

---

#### `require_approval_for_breaking_changes` (boolean, REQUIRED)
**Description:** Whether breaking changes need human approval before application.

**Valid Values:**
- `true` - Block breaking changes, require manual review
- `false` - Allow breaking changes autonomously

**Default:** `true`

**Breaking Change Detection:**
- **Function signature changes** (parameters added/removed/reordered)
- **Public API removals** (exported functions/classes deleted)
- **Return type changes** (incompatible types)
- **Exception behavior changes** (new exceptions thrown)

**Examples:**
```python
# Breaking change: Added required parameter
# BEFORE
def calculate_tax(amount):
    return amount * 0.1

# AFTER
def calculate_tax(amount, rate):  # ← BREAKING: 'rate' is required
    return amount * rate

# Non-breaking: Added optional parameter
def calculate_tax(amount, rate=0.1):  # ← OK: 'rate' has default
    return amount * rate
```

**Configuration:**
```json
"require_approval_for_breaking_changes": true   // Recommended for libraries/APIs
"require_approval_for_breaking_changes": false  // OK for internal code
```

**Behavior When `true`:**
- Agent detects breaking change via static analysis
- Operation immediately paused
- Notification sent to configured approval channel
- Human must explicitly approve or reject
- Audit trail logs approval decision

---

#### `require_approval_for_security_changes` (boolean, REQUIRED)
**Description:** Whether security-related changes need human approval.

**Valid Values:**
- `true` - Block security changes, require manual review
- `false` - Allow security changes autonomously (DANGEROUS)

**Default:** `true` (strongly recommended)

**Security Change Detection:**
- Modifications to files matching `critical_paths`
- Changes to authentication/authorization code
- Cryptography-related modifications
- Input validation changes
- SQL/database query modifications

**Examples:**
```json
"require_approval_for_security_changes": true   // ALWAYS use this
"require_approval_for_security_changes": false  // Only for testing
```

**Behavior:**
- More conservative than `block_on_critical_paths`
- Applies even if `block_on_critical_paths` is `false`
- Combines with critical path detection for defense in depth

---

#### `sandbox_execution_required` (boolean, REQUIRED)
**Description:** Whether all changes must be validated in sandbox before applying to main codebase.

**Valid Values:**
- `true` - Require sandbox validation (STRONGLY RECOMMENDED)
- `false` - Apply changes directly (VERY DANGEROUS)

**Default:** `true`

**Sandbox Features:**
- **Isolated filesystem** - Changes don't affect main tree
- **Resource limits** - CPU, memory, disk quotas enforced
- **Network isolation** - No external connections (configurable)
- **Test execution** - Run full test suite in sandbox
- **Rollback** - Automatic cleanup after validation

**Examples:**
```json
"sandbox_execution_required": true   // ALWAYS use this
"sandbox_execution_required": false  // NEVER use in production
```

**Behavior When `true`:**
1. Agent proposes change
2. Change applied to sandbox copy of project
3. Tests run in sandbox
4. If tests pass → Apply to main tree
5. If tests fail → Reject, try next fix attempt
6. Sandbox cleaned up automatically

**Performance Impact:**
- Adds 2-30 seconds per validation (depends on test suite size)
- Worth it for safety guarantee
- Only disable for testing the governance system itself

---

### Section 4: Audit (`governance.audit`)

Controls audit trail logging and retention.

```json
{
  "governance": {
    "audit": {
      "log_all_changes": true,
      "log_rejected_changes": true,
      "retention_days": 90
    }
  }
}
```

#### `log_all_changes` (boolean, REQUIRED)
**Description:** Whether to log all autonomous changes to audit trail.

**Valid Values:**
- `true` - Log every change (recommended)
- `false` - No audit logging (NOT RECOMMENDED)

**Default:** `true`

**Logged Information:**
- Timestamp (ISO 8601)
- Agent identifier
- Operation type (fix, refactor, feature)
- Files modified (with before/after hashes)
- Change justification (if provided)
- Test results
- Approval status

**Log Format:**
```json
{
  "id": "change_20251218_143022_abc123",
  "timestamp": "2025-12-18T14:30:22Z",
  "agent": "claude-3-opus",
  "operation": "fix_syntax_error",
  "files": [
    {
      "path": "src/utils.py",
      "before_hash": "sha256:abc...",
      "after_hash": "sha256:def...",
      "lines_changed": 5
    }
  ],
  "justification": "Fixed missing colon in function definition",
  "test_results": {
    "passed": 150,
    "failed": 0,
    "duration_ms": 2500
  },
  "success": true
}
```

**Examples:**
```json
"log_all_changes": true   // Recommended for all environments
"log_all_changes": false  // Only if storage is critically limited
```

---

#### `log_rejected_changes` (boolean, REQUIRED)
**Description:** Whether to log changes that were rejected due to governance violations.

**Valid Values:**
- `true` - Log rejections (recommended for security analysis)
- `false` - Don't log rejections

**Default:** `true`

**Use Cases for Rejection Logs:**
- **Security monitoring** - Detect malicious agents
- **Configuration tuning** - Identify if limits too strict
- **Audit compliance** - Prove governance enforcement
- **Debugging** - Understand why agent failed

**Logged Information:**
```json
{
  "id": "rejection_20251218_143055_xyz789",
  "timestamp": "2025-12-18T14:30:55Z",
  "agent": "gpt-4",
  "operation": "add_feature",
  "rejection_reason": "Exceeded max_lines_per_change",
  "attempted_lines": 750,
  "limit": 500,
  "files": ["src/module.py", "src/utils.py"],
  "governance_profile": "restrictive"
}
```

**Examples:**
```json
"log_rejected_changes": true   // Recommended for security
"log_rejected_changes": false  // Only to reduce log volume
```

---

#### `retention_days` (integer, REQUIRED)
**Description:** How many days to retain audit logs before automatic deletion.

**Valid Values:**
- Minimum: `1` (delete after 1 day)
- Maximum: `3650` (10 years)
- Recommended: `30-365` depending on compliance requirements

**Default:** `90` (3 months)

**Compliance Guidelines:**
| Retention | Use Case | Standard |
|-----------|----------|----------|
| 7-30 days | Development | N/A |
| 90 days | Standard business | General best practice |
| 180 days | Financial services | SOX (informal) |
| 365 days | Healthcare | HIPAA (minimum) |
| 2555 days (7 years) | Financial (formal) | SOX, SEC |

**Examples:**
```json
"retention_days": 30    // Development
"retention_days": 90    // Standard (default)
"retention_days": 365   // Healthcare/Financial
"retention_days": 2555  // SEC compliance (7 years)
```

**Storage Estimates:**
```
Average log entry: ~2 KB
1000 changes/day * 2 KB * 90 days = ~180 MB
1000 changes/day * 2 KB * 365 days = ~730 MB
```

**Behavior:**
- Automatic cleanup runs daily
- Logs older than `retention_days` are permanently deleted
- Export logs before retention expires if needed
- Complies with GDPR "right to erasure" requirements

---

## Security and Integrity

### Hash Validation (Tamper Detection)

**Purpose:** Detect unauthorized modifications to configuration files.

**Step 1: Generate Hash**
```bash
# Generate SHA-256 hash
sha256sum .code-scalpel/config.json
# Output: 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08  .code-scalpel/config.json
```

**Step 2: Set Hash in Environment**
```bash
# Option A: Environment variable
export SCALPEL_CONFIG_HASH="sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"

# Option B: In .vscode/mcp.json (recommended)
{
  "servers": {
    "code-scalpel": {
      "env": {
        "SCALPEL_CONFIG": "${workspaceFolder}/.code-scalpel/config.json",
        "SCALPEL_CONFIG_HASH": "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
      }
    }
  }
}
```

**Step 3: Verification Behavior**
```python
# When config is loaded:
# 1. Read file content
# 2. Calculate SHA-256 hash
# 3. Compare with SCALPEL_CONFIG_HASH
# 4. If mismatch → REJECT with error
# 5. If match or no hash set → ALLOW
```

**Error Example:**
```
ValueError: Configuration hash mismatch.
Expected: sha256:9f86d0...
Got:      sha256:abc123...
Configuration may have been tampered with.
```

**Best Practices:**
- ✅ **DO** set hash in production environments
- ✅ **DO** store hash in version control (it's not a secret)
- ✅ **DO** update hash after legitimate config changes
- ❌ **DON'T** disable hash checking in production
- ❌ **DON'T** share configs without verifying hash

---

### HMAC Signature (Enterprise / High Security)

**Purpose:** Cryptographically sign configuration with a secret key. More secure than SHA-256 alone because attacker needs the secret.

**Step 1: Generate Secret Key**
```bash
# Generate random secret (store in secrets manager)
python3 -c "import secrets; print(secrets.token_hex(32))"
# Output: 5f4dcc3b5aa765d61d8327deb882cf992f6c6d2a7e1b5c3d4e5f6a7b8c9d0e1f
```

**Step 2: Generate HMAC Signature**
```bash
export SCALPEL_CONFIG_SECRET="5f4dcc3b5aa765d61d8327deb882cf992f6c6d2a7e1b5c3d4e5f6a7b8c9d0e1f"

python3 -c "
import hmac
import hashlib
import os

secret = os.getenv('SCALPEL_CONFIG_SECRET').encode()
with open('.code-scalpel/config.json', 'rb') as f:
    content = f.read()
    signature = hmac.new(secret, content, hashlib.sha256).hexdigest()
    print(f'SCALPEL_CONFIG_SIGNATURE={signature}')
"
# Output: SCALPEL_CONFIG_SIGNATURE=a3f5c8b9e1d4f7a2c6e9b3d1f5a8c2e7b4d9f1a6c3e8b2d5f9a1c7e4b8d3f6a9
```

**Step 3: Set Secret and Signature**
```bash
# Store secret in secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)
# Then set in environment:
export SCALPEL_CONFIG_SECRET="5f4dcc3b5aa765d61d8327deb882cf992f6c6d2a7e1b5c3d4e5f6a7b8c9d0e1f"
export SCALPEL_CONFIG_SIGNATURE="a3f5c8b9e1d4f7a2c6e9b3d1f5a8c2e7b4d9f1a6c3e8b2d5f9a1c7e4b8d3f6a9"
```

**Verification Process:**
1. Read config file
2. Calculate HMAC using secret
3. Compare with `SCALPEL_CONFIG_SIGNATURE`
4. If mismatch → REJECT (tampering detected)
5. If match → ALLOW

**Security Properties:**
- ✅ **Prevents modification** even if attacker has filesystem access
- ✅ **Requires secret key** to create valid signature
- ✅ **Detects bit-level changes** instantly
- ✅ **Non-repudiation** - proves config came from authorized source

**Key Management Best Practices:**
```bash
# AWS Secrets Manager
aws secretsmanager get-secret-value \
  --secret-id code-scalpel/config-secret \
  --query SecretString \
  --output text

# HashiCorp Vault
vault kv get -field=secret secret/code-scalpel/config

# Kubernetes Secret
kubectl get secret code-scalpel-config-secret -o jsonpath='{.data.secret}' | base64 -d
```

**Rotation Strategy:**
```bash
# 1. Generate new secret
NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# 2. Generate new signature with new secret
NEW_SIG=$(python3 -c "
import hmac
import hashlib
with open('.code-scalpel/config.json', 'rb') as f:
    sig = hmac.new('$NEW_SECRET'.encode(), f.read(), hashlib.sha256).hexdigest()
    print(sig)
")

# 3. Update secrets manager
# 4. Deploy new secret to production
# 5. Verify all services pick up new secret
# 6. Invalidate old secret
```

---

### File Permissions (Defense in Depth)

**Additional Layer:** Set restrictive file permissions on configuration.

```bash
# Make config read-only (cannot modify)
chmod 444 .code-scalpel/config.json

# Make directory read-only
chmod 555 .code-scalpel/

# Verify permissions
ls -la .code-scalpel/
# -r--r--r-- 1 user group  2048 Dec 18 14:30 config.json
```

**Note:** This alone is NOT sufficient (can be bypassed with `chmod +w`), but combined with hash/HMAC verification provides defense in depth.

---

### Git-Based Integrity (Recommended)

**Best Practice:** Store signed manifests in git for audit trail.

```bash
# 1. Generate policy manifest with hashes
python3 scripts/generate_policy_manifest.py \
  --policy-dir .code-scalpel \
  --output policy.manifest.json \
  --sign

# 2. Commit manifest to git
git add .code-scalpel/policy.manifest.json
git commit -m "chore: update policy manifest"
git push

# 3. At runtime, verify against committed manifest
# (See docs/configuration/governance_config_schema.md for implementation)
```

**Benefits:**
- ✅ **Version controlled** - Full history of config changes
- ✅ **Code review** - Changes go through PR process
- ✅ **Audit trail** - Who changed what and when
- ✅ **Rollback** - Revert to previous config easily

## Testing Configurations

To test a specific configuration:
```bash
# Unit tests with testing config
SCALPEL_CONFIG=.code-scalpel/config.testing.json pytest tests/

# Integration tests with restrictive config
SCALPEL_CONFIG=.code-scalpel/config.restrictive.json pytest tests/integration/

# Development testing
SCALPEL_CONFIG=.code-scalpel/config.development.json code-scalpel mcp
```

## Comparison Table

| Feature | Restrictive | Default | Development | CI/CD | Permissive | Testing |
|---------|-------------|---------|-------------|-------|------------|---------|
| Max Lines | 100 | 500 | 750 | 1000 | 2000 | 50 |
| Max Files | 3 | 10 | 15 | 20 | 50 | 2 |
| Max Iterations | 3 | 10 | 15 | 20 | 50 | 2 |
| Critical Path Lines | 25 | 50 | 75 | 100 | 200 | 10 |
| Approval Required | Always | Yes | Yes | Security Only | Security Only | Always |
| Audit Retention | 365d | 90d | 60d | 60d | 30d | 7d |

---

## Troubleshooting

### Problem: Config Not Loading

**Symptoms:**
```
WARNING: No governance configuration found, using defaults
```

**Solutions:**
1. **Check file location:**
   ```bash
   # Config must be at project root
   ls -la .code-scalpel/config.json
   ```

2. **Check file permissions:**
   ```bash
   # Must be readable
   chmod 444 .code-scalpel/config.json
   ```

3. **Check JSON syntax:**
   ```bash
   # Validate JSON
   python3 -c "import json; json.load(open('.code-scalpel/config.json'))"
   ```

4. **Check environment variable:**
   ```bash
   # If set, must point to valid file
   echo $SCALPEL_CONFIG
   ```

---

### Problem: Hash Validation Failure

**Symptoms:**
```
ValueError: Configuration hash mismatch
Expected: sha256:abc123...
Got:      sha256:def456...
```

**Solutions:**
1. **Regenerate hash after legitimate changes:**
   ```bash
   sha256sum .code-scalpel/config.json
   # Update SCALPEL_CONFIG_HASH with new value
   ```

2. **Check for whitespace differences:**
   ```bash
   # Show file with special characters
   cat -A .code-scalpel/config.json
   # Look for unexpected ^M (carriage returns) or trailing spaces
   ```

3. **Temporarily disable hash checking for debugging:**
   ```bash
   unset SCALPEL_CONFIG_HASH
   # Test without hash validation
   # Then re-enable and fix the hash
   ```

---

### Problem: Changes Rejected with "Exceeded max_lines_per_change"

**Symptoms:**
```
ERROR: Change rejected - Exceeded max_lines_per_change
Attempted: 750 lines
Limit: 500 lines
```

**Solutions:**
1. **Reduce change scope:**
   - Break change into smaller commits
   - Extract unrelated changes to separate operations

2. **Use permissive config for development:**
   ```bash
   ln -sf config.development.json .code-scalpel/config.json
   ```

3. **Temporarily override via environment:**
   ```bash
   SCALPEL_CHANGE_BUDGET_MAX_LINES=1000 code-scalpel mcp
   ```

4. **Review if limits are too strict:**
   - Check comparison table in this README
   - Adjust config to match your project's needs

---

### Problem: Critical Path Blocking Legitimate Changes

**Symptoms:**
```
ERROR: Critical path modification requires human approval
File: src/security/auth.py
Pattern: src/security/
```

**Solutions:**
1. **Set `block_on_critical_paths` to false:**
   ```json
   "blast_radius": {
     "block_on_critical_paths": false  // Warn instead of block
   }
   ```

2. **Remove path from critical_paths:**
   ```json
   "critical_paths": [
     "src/core/",
     // "src/security/",  // Commented out
     "src/mcp/server.py"
   ]
   ```

3. **Use separate config for development:**
   ```bash
   # Development config has fewer critical paths
   ln -sf config.development.json .code-scalpel/config.json
   ```

---

### Problem: Sandbox Execution Slow

**Symptoms:**
- Long wait times (> 60 seconds) for validation
- Timeout errors

**Solutions:**
1. **Optimize test suite:**
   ```bash
   # Run only affected tests
   pytest --lf --ff  # last failed, failed first
   ```

2. **Use faster sandbox isolation:**
   ```python
   # In sandbox configuration
   isolation_level="process"  # Faster than "container"
   ```

3. **Increase timeout:**
   ```python
   sandbox = SandboxExecutor(max_cpu_seconds=120)  # Default: 60
   ```

---

### Problem: Environment Variables Not Working

**Symptoms:**
```
# Set variable but config still uses file values
export SCALPEL_CHANGE_BUDGET_MAX_LINES=1000
# Config shows max_lines_per_change: 500
```

**Solutions:**
1. **Check variable name spelling:**
   ```bash
   # Correct prefix: SCALPEL_ (not CODESCALPEL_ or CODE_SCALPEL_)
   env | grep SCALPEL
   ```

2. **Export variables (don't just set):**
   ```bash
   # Wrong
   SCALPEL_CHANGE_BUDGET_MAX_LINES=1000
   
   # Correct
   export SCALPEL_CHANGE_BUDGET_MAX_LINES=1000
   ```

3. **Check loading order:**
   ```python
   # Env vars override file values
   # But SCALPEL_CONFIG points to a different file
   # Resolution: unset SCALPEL_CONFIG
   ```

---

## Best Practices

### For Production Environments

**✅ DO:**
1. **Use restrictive or default config**
   ```bash
   ln -sf config.restrictive.json .code-scalpel/config.json
   ```

2. **Enable hash validation**
   ```bash
   export SCALPEL_CONFIG_HASH="sha256:$(sha256sum .code-scalpel/config.json | cut -d' ' -f1)"
   ```

3. **Enable HMAC signatures (enterprise)**
   ```bash
   # Store secret in secrets manager
   export SCALPEL_CONFIG_SECRET="<from-secrets-manager>"
   ```

4. **Set comprehensive critical paths**
   ```json
   "critical_paths": [
     "src/core/",
     "src/security/",
     "src/authentication/",
     "src/payment/",
     "config/"
   ]
   ```

5. **Require approvals for breaking changes**
   ```json
   "require_approval_for_breaking_changes": true,
   "require_approval_for_security_changes": true
   ```

6. **Enable full audit logging**
   ```json
   "log_all_changes": true,
   "log_rejected_changes": true,
   "retention_days": 365
   ```

**❌ DON'T:**
1. ❌ Use permissive config in production
2. ❌ Disable sandbox execution
3. ❌ Set `block_on_critical_paths` to false
4. ❌ Allow autonomous breaking changes
5. ❌ Skip hash validation

---

### For Development Environments

**✅ DO:**
1. **Use development or permissive config**
   ```bash
   ln -sf config.development.json .code-scalpel/config.json
   ```

2. **Allow faster iterations**
   ```json
   "max_autonomous_iterations": 20,  // More patient
   "budget_refresh_interval_hours": 4  // Shorter cycle
   ```

3. **Keep sandbox enabled**
   ```json
   "sandbox_execution_required": true  // Safety still important
   ```

4. **Log everything for debugging**
   ```json
   "log_all_changes": true,
   "log_rejected_changes": true
   ```

**✅ CONSIDER:**
- Higher line limits (750-1000)
- More files per change (15-20)
- Fewer critical paths
- Shorter audit retention (30-60 days)

---

### For CI/CD Pipelines

**✅ DO:**
1. **Use dedicated CI/CD config**
   ```bash
   export SCALPEL_CONFIG=.code-scalpel/config.ci-cd.json
   ```

2. **Optimize for speed**
   ```json
   "budget_refresh_interval_hours": 1,  // Per build
   "max_autonomous_iterations": 20,      // Thorough
   "require_justification": false        // Automated
   ```

3. **Still require sandbox**
   ```json
   "sandbox_execution_required": true  // Catch issues early
   ```

4. **Set appropriate limits**
   ```json
   "max_lines_per_change": 1000,  // Larger features OK
   "max_files_per_change": 20      // Multi-file changes
   ```

---

### For Security-Critical Projects

**✅ DO:**
1. **Use restrictive config**
   ```bash
   ln -sf config.restrictive.json .code-scalpel/config.json
   ```

2. **Minimize autonomous changes**
   ```json
   "max_lines_per_change": 100,
   "max_files_per_change": 3,
   "max_autonomous_iterations": 3
   ```

3. **Extensive critical paths**
   ```json
   "critical_paths": [
     "src/",  // Everything is critical
     "config/",
     "*.yaml",
     "*.env"
   ]
   ```

4. **Maximum restrictions**
   ```json
   "block_on_critical_paths": true,
   "require_approval_for_breaking_changes": true,
   "require_approval_for_security_changes": true
   ```

5. **Long audit retention**
   ```json
   "retention_days": 2555  // 7 years (SOX/SEC compliance)
   ```

---

### Configuration Review Checklist

Before deploying new configuration, verify:

- [ ] **JSON is valid** - `python3 -m json.tool config.json`
- [ ] **All required fields present** - Check against schema
- [ ] **Limits appropriate for risk level** - Security vs. velocity tradeoff
- [ ] **Critical paths cover sensitive code** - Review with security team
- [ ] **Hash generated and set** - `SCALPEL_CONFIG_HASH` configured
- [ ] **Tested in non-production** - Validate with test config first
- [ ] **Documented justification** - Why these specific limits?
- [ ] **Approved by team lead** - Get sign-off for production configs
- [ ] **Version controlled** - Committed to git
- [ ] **Audit trail configured** - Logging enabled, retention set

---

## Configuration Lifecycle

### 1. Initial Setup
```bash
# Choose appropriate profile
cp .code-scalpel/config.restrictive.json .code-scalpel/config.json

# Generate hash
HASH=$(sha256sum .code-scalpel/config.json | cut -d' ' -f1)
echo "SCALPEL_CONFIG_HASH=sha256:$HASH" >> .env

# Commit to version control
git add .code-scalpel/config.json .env
git commit -m "feat: add governance configuration"
```

### 2. Testing & Validation
```bash
# Test with testing config first
SCALPEL_CONFIG=.code-scalpel/config.testing.json pytest tests/

# Validate production config
python3 -c "
from code_scalpel.config.governance_config import GovernanceConfigLoader
config = GovernanceConfigLoader().load()
print(f'Loaded: {config.change_budgeting.max_lines_per_change} lines max')
"
```

### 3. Deployment
```bash
# Deploy to production with hash validation
export SCALPEL_CONFIG=/prod/.code-scalpel/config.json
export SCALPEL_CONFIG_HASH="sha256:$(sha256sum $SCALPEL_CONFIG | cut -d' ' -f1)"

# Verify config loaded correctly
code-scalpel --validate-config
```

### 4. Monitoring & Tuning
```bash
# Review audit logs weekly
cat .code-scalpel/autonomy_audit/*.json | jq '.rejection_reason' | sort | uniq -c

# Adjust limits based on actual usage
# If seeing many rejections for legitimate changes, increase limits
# If seeing risky changes approved, decrease limits
```

### 5. Regular Review (Monthly/Quarterly)
```bash
# Generate configuration usage report
python3 scripts/analyze_config_usage.py \
  --audit-dir .code-scalpel/autonomy_audit \
  --output config-report.html

# Review with team:
# - Are limits still appropriate?
# - Should critical paths change?
# - Are there new security concerns?
```

---

## Migration Guide

### From No Configuration (Defaults)
```bash
# 1. Create config directory
mkdir -p .code-scalpel

# 2. Copy default config
cp /usr/share/code-scalpel/templates/config.json .code-scalpel/

# 3. Customize for your project
nano .code-scalpel/config.json

# 4. Test configuration
SCALPEL_CONFIG=.code-scalpel/config.json code-scalpel --validate-config
```

### From `.code-scalpel/` to `.code-scalpel/`

**If you have existing `.code-scalpel/` directory:**

1. **.code-scalpel/ contains policy engine files** (policy.yaml, etc.)
   - **Keep it!** Policy engine is separate from governance config
   - Both directories coexist without conflicts

2. **Create new .code-scalpel/ for governance**
   ```bash
   mkdir -p .code-scalpel
   cp config.default.json .code-scalpel/config.json
   ```

3. **Directory structure:**
   ```
   project/
   ├── .code-scalpel/              # Policy engine (v2.5.0)
  │   ├── policy.yaml             # OPA/Rego policies (active)
  │   ├── templates/              # Copy-ready templates/examples
  │   │   ├── policy.yaml.example
  │   │   └── policy_test.yaml
  │   └── README.md
   └── .code-scalpel/         # Governance config (v3.0.0)
       ├── config.json        # Active config
       ├── config.restrictive.json
       └── README.md
   ```

4. **No conflicts** - Systems are independent:
   - Policy engine: Access control (what operations allowed)
   - Governance config: Change limits (how much change allowed)

---

## Advanced Topics

### Custom Profiles for Teams

Create team-specific profiles:

```json
// config.backend-team.json
{
  "profile": "backend-team",
  "description": "Backend team with moderate database access",
  "governance": {
    "change_budgeting": {
      "max_lines_per_change": 750
    },
    "blast_radius": {
      "critical_paths": [
        "src/database/",
        "src/api/v1/"  // V1 API is stable
      ]
    }
  }
}

// config.frontend-team.json
{
  "profile": "frontend-team",
  "description": "Frontend team with UI focus",
  "governance": {
    "change_budgeting": {
      "max_lines_per_change": 1000  // More UI code
    },
    "blast_radius": {
      "critical_paths": [
        "src/auth/",  // Auth UI is critical
        "src/payment/"  // Payment flow
      ]
    }
  }
}
```

### Dynamic Configuration (Advanced)

Load configuration based on environment:

```python
import os
from pathlib import Path
from code_scalpel.config.governance_config import GovernanceConfigLoader

# Determine environment
env = os.getenv("ENV", "development")

# Map environment to config
config_map = {
    "production": "config.restrictive.json",
    "staging": "config.default.json",
    "development": "config.development.json",
    "ci": "config.ci-cd.json"
}

# Load appropriate config
config_file = config_map.get(env, "config.json")
loader = GovernanceConfigLoader(config_path=Path(f".code-scalpel/{config_file}"))
config = loader.load()
```

---

## Documentation

- **Full specification:** `docs/configuration/governance_config_schema.md`
- **Development roadmap:** `DEVELOPMENT_ROADMAP.md` (v3.0.0 section)
- **Policy engine docs:** `docs/policy_engine_guide.md`
- **Autonomy guide:** `docs/autonomy_quickstart.md`
- **Security documentation:** `SECURITY.md`

---

## Support

**Questions?**
- GitHub Issues: https://github.com/tescolopio/code-scalpel/issues
- Documentation: `docs/` directory
- Examples: `examples/` directory

**Found a bug?**
- Report with: Config file, error message, Code Scalpel version
- Include: Minimal reproduction case

**Feature requests?**
- Open GitHub issue with `[FEATURE]` prefix
- Describe use case and proposed configuration option
