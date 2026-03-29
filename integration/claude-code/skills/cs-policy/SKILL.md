---
name: cs-policy
description: |
  Verify code compliance with policies and standards: HIPAA, SOC2, PCI-DSS,
  custom style guides. Validate policy file integrity with cryptographic verification.
allowed-tools:
  - mcp__codescalpel__validate_paths
  - mcp__codescalpel__code_policy_check
  - mcp__codescalpel__verify_policy_integrity
preamble-tier: 1
---

# /cs-policy — Compliance & Policy Enforcement

Check your code against regulatory standards, style guides, and custom policies.
Verify policy files are authentic using cryptographic signatures.

## Usage

```bash
/cs-policy
/cs-policy src/ --standards HIPAA,SOC2
/cs-policy . --rules company-style-guide.yaml
```

## Standard Compliance

### HIPAA (Health Insurance Portability and Accountability Act)
For healthcare applications handling protected health information (PHI):
- Encryption requirements
- Access logging
- Data retention policies
- Patient consent handling
- Audit trail requirements

### SOC2 (Service Organization Control 2)
For cloud/SaaS providers:
- Security controls
- Availability requirements
- Processing integrity
- Confidentiality safeguards
- Privacy controls

### PCI-DSS (Payment Card Industry Data Security Standard)
For applications handling credit card data:
- Encryption of cardholder data
- Access controls
- Network segmentation
- Vulnerability management
- Logging and monitoring
- Password requirements

## Custom Policies

Define your own compliance rules in YAML:

```yaml
rules:
  no_hardcoded_secrets:
    description: "Never hardcode passwords, API keys, or tokens"
    patterns:
      - '["'\'']password["'\'']'
      - 'PRIVATE_KEY'
      - 'API_KEY.*=.*["'\'']'
    severity: critical

  require_docstrings:
    description: "All public functions must have docstrings"
    file_patterns: ["*.py"]
    severity: warning
```

## How It Works

### Step 1: Validate Paths
Checks that all files referenced in policies are accessible.
Prevents false negatives from missing or mounted files.

### Step 2: Check Code Against Rules
Scans your codebase for violations:
- Pattern matching (regex-based rules)
- Structural analysis (AST-based rules)
- Dependency checking
- Configuration validation

### Step 3: Verify Policy Integrity
Cryptographically verify policy files haven't been tampered with:
- Checks HMAC signatures
- Validates policy source
- Detects unauthorized modifications

## Compliance Report

Results organized by:
- **Violations by severity:** Critical, High, Medium, Low, Info
- **Violations by file:** Which files have issues
- **Violations by rule:** Which policies are broken

### Example Report

```
Compliance Report

CRITICAL (3 violations):
  ✗ src/api/auth.py:45 — Hardcoded password
  ✗ src/config.py:12 — API key in source code
  ✗ src/utils.py:89 — Unencrypted database credential

HIGH (5 violations):
  ✗ src/services/payment.py — Missing docstring
  ✗ src/models/user.py — SQL injection risk
  [...]

Policy Integrity: ✓ Valid (signed 2026-03-20)
```

## When to Use This

✅ Before releasing to production
✅ Preparing for compliance audits
✅ During code review (check for policy violations)
✅ Setting team standards
✅ Onboarding new developers (verify they follow rules)
✅ Regular compliance sweeps

## Fixing Violations

For each violation:
1. Use `/cs-extract` to view the code
2. Use `/cs-refactor` to fix it safely
3. Re-run `/cs-policy` to confirm

Example:

```bash
# Find violations
/cs-policy src/api/

# View and fix the code
/cs-extract src/api/auth.py function authenticate

# Refactor safely
/cs-refactor src/api/auth.py function authenticate

# Verify it's fixed
/cs-policy src/api/
```

## Pro Tips

- **Run early and often** — Make compliance part of your development workflow
- **Auto-fix where possible** — Some violations can be auto-corrected
- **Policy as code** — Version control your policies in git
- **Team alignment** — Share policy files across your team
- **Audit trail** — Policy violations are logged for compliance records

## Tier Availability

| Feature | Community | Pro | Enterprise |
|---------|-----------|-----|------------|
| Basic code policy check | ✓ | ✓ | ✓ |
| HIPAA/SOC2/PCI-DSS rules | | ✓ | ✓ |
| Custom policy files | | | ✓ |
| Policy integrity verification | ✓ | ✓ | ✓ |
| Compliance reporting | | ✓ | ✓ |

## Next Steps

1. Define your policies (YAML or use standard presets)
2. Run `/cs-policy` to scan
3. Fix violations with `/cs-refactor`
4. Set up CI/CD checks to enforce policies before merging

See `CLAUDE.md` for the complete compliance workflow.
