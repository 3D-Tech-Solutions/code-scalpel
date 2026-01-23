# DevOps Policies

This directory contains policy templates for DevOps practices, infrastructure validation, and deployment safety.

## Policy Categories

### 1. Infrastructure as Code (IaC)
- **terraform_validation.rego** - Validate Terraform configurations
- **kubernetes_manifests.rego** - Validate K8s manifest safety
- **docker_security.rego** - Dockerfile best practices

### 2. Deployment Safety
- **deployment_checklist.rego** - Enforce pre-deployment checks
- **rollback_capability.rego** - Ensure rollback mechanisms
- **feature_flags.rego** - Validate feature flag usage

### 3. Resource Management
- **resource_limits.rego** - Enforce CPU/memory limits
- **cost_controls.rego** - Prevent expensive configurations
- **scaling_policies.rego** - Validate autoscaling rules

### 4. Configuration Management
- **environment_parity.rego** - Ensure dev/staging/prod consistency
- **config_validation.rego** - Validate environment configs
- **secret_rotation.rego** - Enforce secret rotation policies

## Usage

Enable these policies in `.code-scalpel/policy.yaml`:

```yaml
policies:
  devops:
    - name: terraform-validation
      file: policies/devops/terraform_validation.rego
      severity: HIGH
      action: DENY
    
    - name: kubernetes-security
      file: policies/devops/kubernetes_manifests.rego
      severity: CRITICAL
      action: DENY
    
    - name: docker-security
      file: policies/devops/docker_security.rego
      severity: HIGH
      action: WARN
```

## Examples

See `examples/policy_examples/devops/` for usage examples.

---

*Part of Code Scalpel v3.1+ Policy Engine*
