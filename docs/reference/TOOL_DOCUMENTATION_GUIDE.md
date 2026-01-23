# Tool Documentation Guide

> [20260103_DOCS] Created guide for using the tool documentation template system

**Purpose:** This guide explains how to create, organize, and maintain documentation for Code Scalpel tools using the deep dive template.

---

## Table of Contents

1. [Overview](#overview)
2. [Documentation Structure](#documentation-structure)
3. [Using the Template](#using-the-template)
4. [Organization Strategy](#organization-strategy)
5. [Audience-Specific Documentation](#audience-specific-documentation)
6. [Quality Standards](#quality-standards)
7. [Review Process](#review-process)
8. [Examples](#examples)

---

## Overview

### Documentation Philosophy

Code Scalpel tool documentation follows a **layered documentation strategy**:

1. **Deep Dive (Technical)** - Comprehensive reference for developers and technical stakeholders
2. **User Guide (Practical)** - Focused on usage patterns and examples
3. **Quick Reference (Concise)** - One-page summaries for quick lookups
4. **Marketing (High-Level)** - Feature highlights for decision-makers

This guide focuses on creating the **Deep Dive** documentation, which serves as the source of truth for all other documentation layers.

### Why Deep Dive First?

The deep dive template captures **everything** about a tool:
- Complete technical specifications
- All testing evidence
- Performance data
- Security analysis
- Integration patterns
- Known limitations

Once the deep dive exists, you can **extract** subsets for specific audiences without losing information.

---

## Documentation Structure

### File Naming Convention

**Deep Dive Documentation:**
```
docs/tools/deep_dive/TOOL_NAME_DEEP_DIVE.md
```

**Examples:**
- `docs/tools/deep_dive/ANALYZE_CODE_DEEP_DIVE.md`
- `docs/tools/deep_dive/EXTRACT_CODE_DEEP_DIVE.md`
- `docs/tools/deep_dive/SECURITY_SCAN_DEEP_DIVE.md`

### Directory Organization

```
docs/
├── reference/
│   ├── TOOL_DOCUMENTATION_TEMPLATE.md  ← Template file
│   └── TOOL_DOCUMENTATION_GUIDE.md     ← This file
├── tools/
│   ├── deep_dive/                      ← Comprehensive technical docs
│   │   ├── ANALYZE_CODE_DEEP_DIVE.md
│   │   ├── EXTRACT_CODE_DEEP_DIVE.md
│   │   └── [other tools...]
│   ├── user_guides/                    ← Practical usage guides
│   │   ├── analyze_code_guide.md
│   │   ├── extract_code_guide.md
│   │   └── [other tools...]
│   ├── quick_reference/                ← One-page summaries
│   │   ├── analyze_code_reference.md
│   │   ├── extract_code_reference.md
│   │   └── [other tools...]
│   └── marketing/                      ← High-level feature docs
│       ├── tool_capabilities.md
│       └── tool_comparisons.md
└── INDEX.md                            ← Master documentation index
```

### Cross-Referencing

All tool documentation should cross-reference related tools and resources:

```markdown
## Related Documentation
- **Deep Dive:** [Link to deep dive]
- **User Guide:** [Link to user guide]
- **Quick Reference:** [Link to quick reference]
- **Related Tools:** [Links to related tool docs]
- **Architecture:** [Link to architecture docs]
```

---

## Using the Template

### Step-by-Step Process

#### 1. Copy the Template

```bash
cd /mnt/k/backup/Develop/code-scalpel/docs
cp reference/TOOL_DOCUMENTATION_TEMPLATE.md tools/deep_dive/[TOOL_NAME]_DEEP_DIVE.md
```

#### 2. Fill in Metadata

Start with the header section:
```markdown
# [Tool Name] - Deep Dive Documentation

**Document Type:** Tool Deep Dive Reference  
**Version:** 3.1.0  
**Last Updated:** 2026-01-03  
**Status:** Stable  
**Tier Availability:** All Tiers
```

#### 3. Complete Executive Summary

The executive summary is critical - it should be completable in 15 minutes and give readers immediate context.

**Required Elements:**
- Purpose statement (1 paragraph)
- Key benefits (3-5 bullet points)
- Quick stats table (version, coverage, performance)
- When to use this tool (primary/secondary use cases)

#### 4. Document Technical Details

Work through each section systematically:

**Core Sections (Must Complete):**
- ✅ Technical Overview
- ✅ Features and Capabilities
- ✅ API Specification
- ✅ Usage Examples (minimum 3)
- ✅ Testing Evidence

**Important Sections (Should Complete):**
- Performance Characteristics
- Security Considerations
- Integration Patterns
- Known Limitations

**Optional Sections (Complete if Applicable):**
- Tier-Specific Behavior (if tiers differ)
- Architecture and Implementation (if complex)
- Troubleshooting (if common issues exist)

#### 5. Gather Evidence

**Testing Evidence:**
```bash
# Run tests for specific tool
pytest tests/test_[tool_name].py -v --cov

# Generate coverage report
pytest --cov=src/code_scalpel/[module] --cov-report=json
```

**Performance Evidence:**
```bash
# Run benchmarks
python benchmarks/[tool_name]_benchmark.py

# Generate performance report
python scripts/generate_performance_report.py [tool_name]
```

**Security Evidence:**
```bash
# Run security scans
python -m code_scalpel.mcp_tools.security_scan tests/fixtures/[tool]_test_cases/
```

#### 6. Add Real Examples

**Do:**
- Use real code from `examples/` directory
- Test all examples before documenting
- Show both success and error cases
- Include output/results

**Don't:**
- Use pseudo-code or placeholder examples
- Skip error handling
- Show only happy path
- Omit expected output

#### 7. Document Limitations Honestly

Code Scalpel values **honest uncertainty**. Document:
- Current limitations
- Known bugs or issues
- Unsupported edge cases
- Future plans to address

**Example:**
```markdown
### Known Limitations

#### Cross-Module Variable Tracking
**Impact:** Variables passed across >5 module boundaries may lose taint tracking  
**Workaround:** Use `explicit_taint=True` parameter for deep call chains  
**Planned Fix:** v1.0.0 (Q2 2026)
```

#### 8. Quality Check

Before marking documentation as complete:

- [ ] All code examples execute successfully
- [ ] All links are valid (internal and external)
- [ ] Test coverage numbers are current
- [ ] Performance benchmarks are recent (< 1 month old)
- [ ] Security scan results are current
- [ ] Spelling and grammar checked
- [ ] Peer reviewed by another team member
- [ ] Matches template structure

---

## Organization Strategy

### Progressive Disclosure

Documentation should support multiple reading styles:

**Skim Readers (5 minutes):**
- Executive Summary
- Quick Stats
- Key Features

**Implementers (30 minutes):**
- API Specification
- Usage Examples
- Integration Patterns

**Deep Dive (2-4 hours):**
- Architecture Details
- Testing Evidence
- Performance Analysis
- Security Considerations

### Content Hierarchy

```
Executive Summary (Always)
    ↓
Technical Overview (Core Users)
    ↓
Detailed Specifications (Implementers)
    ↓
Advanced Topics (Power Users)
    ↓
Appendices (Reference)
```

### Linking Strategy

**Internal Links:**
```markdown
See [API Specification](#api-specification) for details.
```

**Cross-Document Links:**
```markdown
See [analyze_code Deep Dive](../tools/deep_dive/ANALYZE_CODE_DEEP_DIVE.md)
```

**External Links:**
```markdown
See [Z3 Solver Documentation](https://z3prover.github.io/)
```

---

## Audience-Specific Documentation

### From Deep Dive to Other Formats

Once the deep dive is complete, extract content for specific audiences:

#### User Guide (Practical)

**Extract:**
- Usage Examples section
- Integration Patterns section
- Troubleshooting section
- Basic API specification (simplified)

**Add:**
- Step-by-step tutorials
- Common workflows
- Best practices
- Tips and tricks

**Omit:**
- Internal architecture details
- Complete test evidence
- Detailed benchmarks
- Security threat models

#### Quick Reference (Concise)

**Extract:**
- API Specification (signatures only)
- Parameter tables
- Return value structure
- Error codes

**Format:**
- Single page (aim for < 2 printed pages)
- Table-heavy format
- Minimal prose
- Quick lookup optimized

**Example Structure:**
```markdown
# Tool Name - Quick Reference

## Signature
[Function signature]

## Parameters
[Table]

## Returns
[Table]

## Examples
[1-2 minimal examples]

## Common Errors
[Table]
```

#### Marketing (High-Level)

**Extract:**
- Purpose Statement
- Key Benefits
- Key Features (headlines only)
- Performance highlights
- Use cases

**Add:**
- Competitive advantages
- ROI/value proposition
- Customer testimonials (if any)
- Screenshots/diagrams

**Omit:**
- Technical implementation details
- Complete API specification
- Testing methodology
- Code examples

### Audience Matrix

| Section | Deep Dive | User Guide | Quick Ref | Marketing |
|---------|-----------|------------|-----------|-----------|
| Executive Summary | ✅ Full | ⚠️ Adapted | ❌ Skip | ✅ Expanded |
| Technical Overview | ✅ Full | ⚠️ Simplified | ❌ Skip | ❌ Skip |
| API Specification | ✅ Full | ⚠️ Essential | ✅ Tables Only | ❌ Skip |
| Usage Examples | ✅ Full | ✅ Full + More | ⚠️ Minimal | ⚠️ Screenshots |
| Architecture | ✅ Full | ❌ Skip | ❌ Skip | ❌ Skip |
| Testing Evidence | ✅ Full | ❌ Skip | ❌ Skip | ⚠️ Highlights |
| Performance | ✅ Full | ⚠️ Summary | ❌ Skip | ⚠️ Key Metrics |
| Security | ✅ Full | ⚠️ Summary | ❌ Skip | ⚠️ Highlights |
| Integration | ✅ Full | ✅ Full | ⚠️ Minimal | ❌ Skip |
| Limitations | ✅ Full | ✅ Important | ❌ Skip | ❌ Skip |
| Troubleshooting | ✅ Full | ✅ Full | ⚠️ Common | ❌ Skip |

---

## Quality Standards

### Documentation Quality Checklist

#### Content Quality

- [ ] **Accuracy:** All technical details verified against source code
- [ ] **Completeness:** All template sections addressed (or marked N/A)
- [ ] **Currency:** Test results and benchmarks < 1 month old
- [ ] **Clarity:** Technical terms defined on first use
- [ ] **Examples:** All code examples tested and working

#### Structural Quality

- [ ] **Navigation:** Table of contents present and correct
- [ ] **Hierarchy:** Proper heading levels (# → ## → ###)
- [ ] **Links:** All internal/external links validated
- [ ] **Formatting:** Consistent markdown formatting
- [ ] **Diagrams:** Mermaid diagrams render correctly

#### Evidence Quality

- [ ] **Test Coverage:** Actual coverage numbers from test runs
- [ ] **Performance:** Real benchmark results, not estimates
- [ ] **Security:** Actual scan results from security tools
- [ ] **Integration:** Examples tested against actual MCP clients

#### Professional Quality

- [ ] **Tone:** Professional, clinical, no emojis
- [ ] **Grammar:** Spell-checked and grammar-checked
- [ ] **Consistency:** Terminology consistent with other docs
- [ ] **Tags:** Change tags included `[YYYYMMDD_DOCS]`

### Evidence Requirements

All claims must be backed by evidence:

**Performance Claims:**
```markdown
❌ "This tool is very fast"
✅ "Processes 1,000 LOC files in < 50ms (avg: 42ms, p95: 48ms)"
```

**Feature Claims:**
```markdown
❌ "Supports multiple languages"
✅ "Supports Python 3.9+, JavaScript ES2020+, TypeScript 4.5+, Java 11+"
```

**Security Claims:**
```markdown
❌ "Highly secure"
✅ "Zero critical vulnerabilities in v1.0.0 security scan (2026-01-03)"
```

### Version Control

**Document Versioning:**
- Document version tracks tool version
- Update "Last Updated" date on every change
- Maintain "Change History" section

**Example Change History:**
```markdown
**Change History:**
- 2026-01-03: Initial deep dive creation for v1.0.0
- 2026-01-15: Updated performance benchmarks
- 2026-02-01: Added new integration example
- 2026-02-10: Updated for v1.0.0 release
```

---

## Review Process

### Self-Review Checklist

Before submitting for peer review:

1. **Run all examples** - Ensure every code block executes
2. **Validate links** - Check all markdown links work
3. **Verify evidence** - Confirm all numbers/claims are current
4. **Check formatting** - Ensure consistent markdown style
5. **Spell check** - Run spell checker
6. **Read aloud** - Read document aloud to catch awkward phrasing

### Peer Review Checklist

Reviewer should check:

1. **Technical Accuracy** - Are technical details correct?
2. **Completeness** - Are all critical sections complete?
3. **Clarity** - Is the documentation understandable?
4. **Examples** - Do examples work? Are they clear?
5. **Evidence** - Is all evidence valid and current?
6. **Consistency** - Does terminology match other docs?

### Review Timeline

| Stage | Duration | Responsible |
|-------|----------|-------------|
| Initial Draft | 4-8 hours | Author |
| Self-Review | 1-2 hours | Author |
| Peer Review | 2-4 hours | Reviewer |
| Revisions | 1-2 hours | Author |
| Final Approval | 30 min | Tech Lead |

### Approval Criteria

Documentation is approved when:

- ✅ All quality checklist items passed
- ✅ Peer reviewer approves
- ✅ All code examples tested
- ✅ Evidence verified
- ✅ Links validated
- ✅ No spelling/grammar errors

---

## Examples

### Example 1: analyze_code Tool

**File:** `docs/tools/deep_dive/ANALYZE_CODE_DEEP_DIVE.md`

**Key Sections:**
- Executive Summary: What AST analysis provides
- Technical Overview: How the parser works (tree-sitter)
- API Specification: Function signature, parameters, return structure
- Usage Examples: 5 examples covering Python, JS, TS, Java
- Testing Evidence: 500+ unit tests, 98% coverage
- Performance: Benchmarks for various file sizes
- Integration: Claude, Copilot, LangChain examples

### Example 2: security_scan Tool

**File:** `docs/tools/deep_dive/SECURITY_SCAN_DEEP_DIVE.md`

**Key Sections:**
- Executive Summary: Taint-based vulnerability detection
- Technical Overview: Taint tracking algorithm (PDG-based)
- Features: CWE coverage matrix (20+ vulnerability types)
- API Specification: Parameters for controlling scan depth
- Usage Examples: SQL injection, XSS, command injection detection
- Testing Evidence: 1,200+ security test cases
- Security: Threat model for the security tool itself
- Known Limitations: Limitations of static analysis

### Example 3: extract_code Tool

**File:** `docs/tools/deep_dive/EXTRACT_CODE_DEEP_DIVE.md`

**Key Sections:**
- Executive Summary: Token-efficient code extraction
- Technical Overview: Surgical extraction vs full-file reading
- API Specification: Parameters for symbol extraction
- Usage Examples: Extract function, class, method with dependencies
- Performance: Token cost comparison (50 tokens vs 10,000)
- Integration: How AI agents use this for context efficiency

---

## Maintenance

### Regular Updates

**Quarterly Review (Every 3 months):**
- [ ] Update performance benchmarks
- [ ] Re-run test suite, update coverage numbers
- [ ] Update security scan results
- [ ] Check for broken links
- [ ] Update version numbers if tool changed

**After Version Release:**
- [ ] Update document version to match tool version
- [ ] Add release notes to change history
- [ ] Update any changed API signatures
- [ ] Add new features/capabilities
- [ ] Update known limitations

**When Issues Reported:**
- [ ] Add to "Known Limitations" if confirmed
- [ ] Update "Troubleshooting" with new issue/solution
- [ ] Add to test evidence if new tests added

### Deprecation Process

When deprecating a tool or feature:

1. **Mark as Deprecated:** Add deprecation notice to executive summary
2. **Update Status:** Change status from "Stable" to "Deprecated"
3. **Document Timeline:** Specify when feature will be removed
4. **Provide Migration Path:** Document how to migrate to alternative
5. **Keep Documentation:** Don't delete, mark as archived

**Example Deprecation Notice:**
```markdown
> **DEPRECATED:** This tool is deprecated as of v1.0.0 and will be removed in v4.0.0.
> Use [new_tool_name](link) instead. See [migration guide](link).
```

---

## Appendix: Template Customization

### Adding Custom Sections

If a tool needs additional sections not in the template:

1. Add section after the most relevant existing section
2. Follow markdown heading hierarchy
3. Update table of contents
4. Document why this section was added

**Example:**
```markdown
## Machine Learning Model Details
> This section added for ML-based tools to document training data and model architecture
```

### Omitting Sections

If a section doesn't apply:

1. Don't delete the section heading
2. Add "N/A" note explaining why
3. Keep section in TOC

**Example:**
```markdown
## Tier-Specific Behavior

**N/A:** This tool has identical behavior across all tiers. No tier-specific limitations apply.
```

### Tool Categories

Different tool categories may emphasize different sections:

**Analysis Tools** (analyze_code, get_project_map):
- Emphasize: Architecture, Performance
- De-emphasize: Security Considerations

**Modification Tools** (update_symbol, rename_symbol):
- Emphasize: Safety Guarantees, Testing Evidence
- De-emphasize: Performance (correctness over speed)

**Security Tools** (security_scan, cross_file_security_scan):
- Emphasize: CWE Coverage, Security Testing, False Positive Rate
- De-emphasize: Performance (thoroughness over speed)

**Utility Tools** (validate_paths, get_file_context):
- Emphasize: Usage Examples, Integration Patterns
- De-emphasize: Architecture (simple tools)

---

## Getting Help

**Questions about the template?**
- Check this guide first
- Review example deep dive documents
- Ask in team documentation channel

**Questions about a specific tool?**
- Review tool source code in `src/code_scalpel/`
- Check tool tests in `tests/`
- Consult tool author/maintainer

**Documentation standards questions?**
- See [CONTRIBUTING.md](../../CONTRIBUTING.md)
- See [Documentation Organization](../DOCUMENT_ORGANIZATION.md)
- See [Comprehensive Guide](../COMPREHENSIVE_GUIDE.md)

---

**Document Version:** 1.0.0  
**Last Updated:** 2026-01-03  
**Maintained By:** Code Scalpel Documentation Team
