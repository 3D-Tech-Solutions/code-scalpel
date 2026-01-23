# Architecture Management Policies

This directory contains policy templates for enforcing architectural constraints and design patterns in your codebase.

## Policy Categories

### 1. Layering & Boundaries
- **layered_architecture.rego** - Enforce layered architecture (UI → Service → Data)
- **module_boundaries.rego** - Prevent cross-module violations
- **package_dependencies.rego** - Control dependency direction

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
