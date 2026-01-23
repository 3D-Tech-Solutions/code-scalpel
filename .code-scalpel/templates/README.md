# Templates

> [20251230_DOCS] Centralized example/template files for `.code-scalpel/`.

This directory contains **copy-ready templates** and **example configurations**.

## Files

- `policy.yaml.example` - Production-ready starter policy set (copy to `../policy.yaml`)
- `policy_override.yaml` - Example override file (copy to `../policy_override.yaml` if needed)
- `policy_test.yaml` - Example test policy set (copy to `../policy_test.yaml` if needed)
- `limits.local.toml.example` - Example local limits override (copy to `../limits.local.toml` if needed)
- `test_write.json` - Example payload for write / mutation testing

## Quick Start

```bash
# Create active policy from template
cp .code-scalpel/templates/policy.yaml.example .code-scalpel/policy.yaml
```
