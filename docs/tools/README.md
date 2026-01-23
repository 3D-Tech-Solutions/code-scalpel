# Code Scalpel Tool Documentation

> [20260103_DOCS] Organized tool documentation structure with layered approach

This directory contains comprehensive documentation for all Code Scalpel MCP tools, organized by audience and depth.

---

## Documentation Layers

Code Scalpel uses a **layered documentation strategy** to serve different audiences:

```
Deep Dive (Technical Reference)
    ↓
User Guides (Practical Usage)
    ↓
Quick Reference (Fast Lookup)
    ↓
Marketing (High-Level Overview)
```

### Directory Structure

```
docs/tools/
├── deep_dive/          ← Comprehensive technical documentation
├── user_guides/        ← Practical how-to guides
├── quick_reference/    ← One-page summaries
└── marketing/          ← Feature highlights and comparisons
```

---

## 1. Deep Dive Documentation

**Location:** `deep_dive/`  
**Audience:** Developers, Technical Stakeholders, Contributors  
**Purpose:** Complete technical reference for each tool  

**Contents:**
- Complete API specification
- Comprehensive usage examples
- Architecture and implementation details
- Testing evidence and coverage metrics
- Performance benchmarks
- Security analysis and threat models
- Integration patterns
- Known limitations and roadmap

**Files:**
- `ANALYZE_CODE_DEEP_DIVE.md`
- `EXTRACT_CODE_DEEP_DIVE.md`
- `SECURITY_SCAN_DEEP_DIVE.md`
- [One file per tool...]

**When to Read:**
- Implementing new integrations
- Understanding tool internals
- Contributing to the codebase
- Troubleshooting complex issues
- Performance tuning

---

## 2. User Guides

**Location:** `user_guides/`  
**Audience:** End Users, AI Agents, Integrators  
**Purpose:** Practical guides focused on accomplishing tasks  

**Contents:**
- Step-by-step tutorials
- Common workflows and patterns
- Best practices
- Integration examples
- Tips and tricks
- Troubleshooting common issues

**Files:**
- `analyze_code_guide.md`
- `extract_code_guide.md`
- `security_scan_guide.md`
- [One file per tool...]

**When to Read:**
- Getting started with a tool
- Learning best practices
- Solving practical problems
- Understanding common workflows

---

## 3. Quick Reference

**Location:** `quick_reference/`  
**Audience:** Experienced Users, Fast Lookups  
**Purpose:** Concise reference for quick parameter/API lookups  

**Contents:**
- Function signatures
- Parameter tables
- Return value structures
- Common error codes
- Minimal examples

**Format:**
- Single page per tool (< 2 printed pages)
- Table-heavy layout
- Minimal prose
- Quick lookup optimized

**Files:**
- `analyze_code_reference.md`
- `extract_code_reference.md`
- `security_scan_reference.md`
- [One file per tool...]

**When to Read:**
- Need to recall parameter names
- Quick syntax check
- Looking up error codes
- Verifying return structure

---

## 4. Marketing Documentation

**Location:** `marketing/`  
**Audience:** Decision Makers, Evaluators, Sales  
**Purpose:** High-level feature highlights and comparisons  

**Contents:**
- Tool capabilities overview
- Key benefits and value propositions
- Competitive advantages
- Use case highlights
- Tool comparison matrices

**Files:**
- `tool_capabilities.md` - Overview of all tools
- `tool_comparisons.md` - Comparison with alternatives
- `value_proposition.md` - Business case for Code Scalpel

**When to Read:**
- Evaluating Code Scalpel
- Understanding capabilities at high level
- Comparing with alternatives
- Building business case

---

## Available Tools (v1.0.0)

Code Scalpel provides **22 MCP tools** for surgical code operations:

### Code Analysis Tools
- **analyze_code** - Parse and extract code structure
- **get_file_context** - Get file overview without full content
- **get_project_map** - Generate comprehensive project structure map
- **crawl_project** - Project-wide analysis

### Code Extraction Tools
- **extract_code** - Surgical extraction by symbol name
- **get_symbol_references** - Find all uses of a symbol
- **get_cross_file_dependencies** - Analyze cross-file dependency chains

### Code Modification Tools
- **update_symbol** - Safely replace functions/classes/methods
- **rename_symbol** - Safely rename symbols across the codebase

### Code Flow Analysis Tools
- **get_call_graph** - Generate call graphs and trace execution flow
- **get_graph_neighborhood** - Extract k-hop neighborhood subgraph
- **symbolic_execute** - Symbolic path exploration with Z3

### Security Analysis Tools
- **security_scan** - Taint-based vulnerability detection
- **unified_sink_detect** - Unified polyglot sink detection
- **cross_file_security_scan** - Cross-module taint tracking
- **type_evaporation_scan** - Detect TypeScript type evaporation
- **scan_dependencies** - Scan for vulnerable dependencies (OSV API)

### Policy & Compliance Tools
- **code_policy_check** - Check code against style and compliance rules

### Testing Tools
- **generate_unit_tests** - Symbolic execution test generation
- **simulate_refactor** - Verify refactor preserves behavior

### Utility Tools
- **validate_paths** - Validate path accessibility for Docker
- **verify_policy_integrity** - Cryptographic policy file verification

---

## Documentation Status

### Completed Deep Dives

| Tool | Status | Last Updated | Coverage |
|------|--------|--------------|----------|
| (TBD) | ⬜ Not Started | - | - |

### In Progress

| Tool | Author | Target Date | Status |
|------|--------|-------------|--------|
| (TBD) | - | - | - |

### Planned

All 20 tools will have deep dive documentation by Q1 2026.

---

## Creating New Tool Documentation

### Quick Start

1. **Copy the template:**
   ```bash
   cp docs/reference/TOOL_DOCUMENTATION_TEMPLATE.md \
      docs/tools/deep_dive/[TOOL_NAME]_DEEP_DIVE.md
   ```

2. **Read the guide:**
   See [TOOL_DOCUMENTATION_GUIDE.md](../reference/TOOL_DOCUMENTATION_GUIDE.md)

3. **Fill in sections:**
   Start with Executive Summary, then API Specification, then Examples

4. **Gather evidence:**
   Run tests, benchmarks, security scans

5. **Submit for review:**
   Have another team member review before publishing

### Documentation Standards

- **Accuracy:** All technical details verified against source code
- **Evidence:** All claims backed by test results/benchmarks
- **Examples:** All code examples tested and working
- **Clarity:** Technical terms defined on first use
- **Links:** All internal/external links validated
- **Professional:** Clinical tone, no emojis

See [TOOL_DOCUMENTATION_GUIDE.md](../reference/TOOL_DOCUMENTATION_GUIDE.md) for complete standards.

---

## Finding Documentation

### By Tool Name

All tools follow consistent naming:
- Deep Dive: `[TOOL_NAME]_DEEP_DIVE.md`
- User Guide: `[tool_name]_guide.md`
- Quick Reference: `[tool_name]_reference.md`

### By Use Case

See the master [INDEX.md](../INDEX.md) for documentation organized by:
- Use case (analysis, extraction, modification, security)
- Language support (Python, JavaScript, TypeScript, Java)
- Tier availability (Community, Pro, Enterprise)

### By Audience

- **Developers:** Start with `user_guides/`
- **Contributors:** Start with `deep_dive/`
- **Quick Lookup:** Start with `quick_reference/`
- **Evaluators:** Start with `marketing/`

---

## Contributing

### Adding New Tool Documentation

1. Create deep dive using template
2. Extract user guide from deep dive
3. Create quick reference from API spec
4. Update this README with tool listing
5. Update [INDEX.md](../INDEX.md)

### Updating Existing Documentation

1. Update deep dive (source of truth)
2. Propagate changes to derivative docs
3. Update "Last Updated" date
4. Add to change history
5. Re-run quality checklist

### Documentation Review

All documentation changes require:
- Self-review using quality checklist
- Peer review by another team member
- All code examples tested
- All links validated

---

## Resources

- **Template:** [TOOL_DOCUMENTATION_TEMPLATE.md](../reference/TOOL_DOCUMENTATION_TEMPLATE.md)
- **Guide:** [TOOL_DOCUMENTATION_GUIDE.md](../reference/TOOL_DOCUMENTATION_GUIDE.md)
- **Master Index:** [INDEX.md](../INDEX.md)
- **Contributing:** [CONTRIBUTING.md](../../CONTRIBUTING.md)

---

## Contact

**Questions about tool documentation?**
- GitHub Issues: [code-scalpel/issues](https://github.com/codefin-ai/code-scalpel/issues)
- Documentation Team: [Contact Info]

**Want to contribute?**
See [CONTRIBUTING.md](../../CONTRIBUTING.md)

---

**Last Updated:** 2026-01-03  
**Version:** 1.0.0  
**Maintained By:** Code Scalpel Documentation Team
