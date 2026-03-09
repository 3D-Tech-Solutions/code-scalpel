# Code Scalpel Capability Files

This directory contains the golden capability files for Code Scalpel's tier-based feature gating system.

These files document the **22 core tools** used in the commercial/product-facing count.
They intentionally exclude **`get_capabilities`**, which is a runtime introspection
surface that lets agents inspect the current tier/license limits.

## Files

- **`community.json`** - Capabilities for the COMMUNITY tier (all 22 core tools available)
- **`pro.json`** - Capabilities for the PRO tier (all 22 core tools available)
- **`enterprise.json`** - Capabilities for the ENTERPRISE tier (all 22 core tools available)
- **`schema.json`** - JSON Schema for validating capability files

## Usage

These files serve two purposes:

### 1. **Regression Testing** (Primary)
The golden files are compared against dynamically-generated capabilities during CI/CD:
- Tool count must match (always 22 core tools)
- Available count must match (22 core tools available at all tiers)
- Tool limits must match the limits.toml configuration

```bash
# In CI: Generate capabilities and compare against golden files
python3 scripts/generate_capabilities.py
pytest tests/capabilities/test_capability_snapshot.py
```

If there's a mismatch, the test fails and requires manual approval to update the golden files.

### 2. **Documentation**
The files serve as clear documentation of what's available at each tier:
- Agents can read these files to understand capabilities
- Customers can see exactly what they're paying for
- Implementation details are separated from user-facing limits

## Updating Golden Files

Golden files should only be updated when:
1. **New tool added** - Add it to the resolver with appropriate tier limits
2. **Tool removed** - Remove it from the resolver (rare)
3. **Limits changed intentionally** - Update limits.toml first, then regenerate
4. **New tier created** - Create new golden file

### To Regenerate:
```bash
# Option 1: Automatic (recommended)
python3 scripts/generate_capabilities.py

# Option 2: Via test suite
pytest tests/capabilities/test_capability_snapshot.py --regenerate-capabilities
```

## File Structure

Each file contains:
```json
{
  "tier": "pro",
  "generated_at": "2026-01-27T14:09:07.492883Z",
  "tool_count": 22,
  "available_count": 19,
  "capabilities": {
    "tool_id": {
      "tool_id": "analyze_code",
      "tier": "pro",
      "available": true,
      "limits": {
        "max_file_size_mb": 10,
        "languages": ["python", "javascript", "typescript", "java", "c", "cpp", "csharp"]
      }
    },
    ...
  }
}
```

## Blocking Criteria

In the CI/CD pipeline, the following changes to capabilities WILL block a release:

1. **Tool count changed** - Adding/removing tools must be intentional
2. **Capability became unavailable** - Tier limits must not retroactively remove tools
3. **Limits decreased** - Only increases are allowed (or explicit pricing approval)
4. **Schema invalid** - Capabilities must validate against schema.json

## Tier Availability Summary

All 22 core tools are available in all tiers (Community, Pro, Enterprise). The tiers differ in their **usage limits**, not tool availability:

### Tool Categories

**20 Development Tools** (tier-gated limits):
- analyze_code, code_policy_check, crawl_project, cross_file_security_scan, extract_code
- generate_unit_tests, get_call_graph, get_cross_file_dependencies, get_file_context
- get_graph_neighborhood, get_project_map, get_symbol_references, rename_symbol
- scan_dependencies, security_scan, simulate_refactor, symbolic_execute
- type_evaporation_scan, unified_sink_detect, update_symbol

**2 Core System Tools** (no tier gating):
- validate_paths, verify_policy_integrity

### Limit Escalation Example

Graph-oriented tools remain Python-first overall. `get_call_graph` now includes
an initial local JavaScript/TypeScript parity slice plus a narrow Java slice:
Community surfaces canonical local Java callable nodes/calls, while
Pro/Enterprise additionally resolve cross-file Java type/static imports,
typed imported instance calls, superclass method dispatch, and field-backed
instance calls when the field type is statically declared.
`get_graph_neighborhood` now includes local JavaScript/TypeScript function
parity plus JS/TS method neighborhoods when advanced resolution is available,
and `get_cross_file_dependencies` now includes an initial local JS/TS
graph-backed parity slice.

```
Tool: extract_code
├── Community: max_depth=1, include_cross_file_deps=False
├── Pro: max_depth=unlimited, include_cross_file_deps=True
└── Enterprise: max_depth=unlimited, include_cross_file_deps=True (+ governance)

Tool: get_call_graph
├── Community: max_depth=10, max_nodes=200
├── Pro: unlimited
└── Enterprise: unlimited (+ governance)

Tool: validate_paths (System Tool)
├── Community: max_paths=100
├── Pro: unlimited
└── Enterprise: unlimited
```

| Category | Community | Pro | Enterprise |
|----------|-----------|-----|------------|
| Development Tools (20) | ✓ Solo dev limits (≤500 files) | ✓ Unlimited | ✓ Unlimited + Governance |
| System Tools (2) | ✓ Standard | ✓ Standard | ✓ Standard |
| **Total Core Tools** | **22** | **22** | **22** |
| **Unique Capabilities** | 78 | 217 | 356 (139 governance-only) |
