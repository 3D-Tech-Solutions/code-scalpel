# Policy Templates

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
└── devsecops/            # DevSecOps automation
    ├── README.md
    ├── secret_detection.rego
    └── sbom_validation.rego
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
# Validate policy syntax
opa check policies/

# Test specific policy
opa test policies/architecture/layered_architecture.rego

# Run all policy checks
code-scalpel policy-check --all-policies
```

### 3. Integrate with CI/CD

```bash
# GitHub Actions
code-scalpel policy-check --fail-on-violation

# Pre-commit hook
code-scalpel policy-check --staged-files
```

## Policy Categories

### Architecture (2 policies)
Enforce architectural patterns and module boundaries:
- **Layered Architecture** - Clean separation of concerns
- **Module Boundaries** - Encapsulation and public APIs

### DevOps (2 policies)
Automate infrastructure security:
- **Docker Security** - Container best practices
- **Kubernetes Security** - K8s hardening

### DevSecOps (2 policies)
Shift security left:
- **Secret Detection** - No hardcoded credentials
- **SBOM Validation** - Supply chain security

## Customization

### Create Custom Policy

```rego
package mycompany.custom

# Custom rule example
violation[{"msg": msg}] if {
    file := input.files[_]
    # Your custom logic here
    msg := "Custom violation detected"
}

allow if {
    count(violation) == 0
}

deny[msg] if {
    v := violation[_]
    msg := v.msg
}
```

### Test Custom Policy

```bash
# Create test file
cat > policies/custom/test.rego << 'REGO'
package mycompany.custom_test

import data.mycompany.custom

test_custom_rule {
    custom.allow with input as {
        "files": [{"path": "test.py", "content": "print('test')"}]
    }
}
REGO

# Run tests
opa test policies/custom/
```

## Best Practices

1. **Start Small** - Enable one policy at a time
2. **Use WARN First** - Test with warnings before DENY
3. **Document Policies** - Add comments explaining rules
4. **Version Control** - Track policy changes in git
5. **Regular Reviews** - Update policies as needs evolve

## Severity Guidelines

| Severity | Use Case | Example |
|----------|----------|---------|
| CRITICAL | Security vulnerabilities | Secrets in code |
| HIGH | Best practice violations | No Docker USER |
| MEDIUM | Maintainability issues | Deprecated packages |
| LOW | Style/convention | Missing comments |

## Integration Examples

### GitHub Actions
```yaml
- name: Policy Check
  run: code-scalpel policy-check --all-policies
```

### Pre-commit Hook
```bash
#!/bin/bash
code-scalpel policy-check --staged-files
```

### VS Code
```json
{
  "code-scalpel.policyCheck.onSave": true,
  "code-scalpel.policyCheck.policies": "all"
}
```

## Resources

- [OPA Documentation](https://www.openpolicyagent.org/docs/latest/)
- [Rego Playground](https://play.openpolicyagent.org/)
- [Policy Testing](https://www.openpolicyagent.org/docs/latest/policy-testing/)
- [Code Scalpel Policy Engine](../../src/code_scalpel/policy_engine/README.md)

---

**Version:** v3.2.0  
**Last Updated:** December 21, 2025
