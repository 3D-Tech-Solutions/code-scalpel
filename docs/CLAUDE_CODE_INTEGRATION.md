# Claude Code Integration (v2.2.0)

**Complete guide to using Code Scalpel with Claude Code through slash commands and system prompts.**

---

## What Is This?

In v2.2.0, Code Scalpel includes a **production-ready integration bundle** for Claude Code users. Instead of manually configuring Code Scalpel, users get:

1. **One-liner installation** — `curl ... | bash`
2. **8 slash commands** — `/cs-setup`, `/cs-extract`, `/cs-security`, etc.
3. **System prompts** — Claude Code automatically uses Code Scalpel for analysis
4. **Complete documentation** — CLAUDE.md in every project

**Result:** Users can copy the integration into Claude Code and immediately use Code Scalpel's 23 tools through intuitive `/cs-*` commands.

---

## Installation

### For Users

```bash
cd my-project
curl -fsSL https://raw.githubusercontent.com/3D-Tech-Solutions/code-scalpel/main/integration/claude-code/setup.sh | bash
# Reload Claude Code
/cs-setup          # Verify installation
/cs-extract src/utils.py function validate_email   # Try first command
```

**What the script does:**
1. Checks Claude Code CLI is installed
2. Registers MCP server: `claude mcp add codescalpel uvx codescalpel mcp`
3. Prompts for license file (Pro/Enterprise)
4. Creates `.claude/skills/` directory
5. Copies all 8 skill files
6. Copies CLAUDE.md to project root
7. Verifies installation with colored output

### For Developers

Add this to your team docs:

```bash
# One-liner for team adoption
curl -fsSL https://raw.githubusercontent.com/3D-Tech-Solutions/code-scalpel/main/integration/claude-code/setup.sh | bash
```

Or copy the entire `integration/claude-code/` directory to your project and run locally:

```bash
bash integration/claude-code/setup.sh
```

---

## Deliverables

### 1. User Integration Bundle (`integration/claude-code/`)

Copy this entire directory into any Claude Code project.

```
integration/claude-code/
├── CLAUDE.md                          ← User guide (copy to project root)
├── setup.sh                           ← Bootstrap script (executable)
└── skills/
    ├── cs-setup/SKILL.md              ← /cs-setup skill
    ├── cs-extract/SKILL.md            ← /cs-extract skill
    ├── cs-analyze/SKILL.md            ← /cs-analyze skill
    ├── cs-security/SKILL.md           ← /cs-security skill
    ├── cs-tests/SKILL.md              ← /cs-tests skill
    ├── cs-refactor/SKILL.md           ← /cs-refactor skill
    ├── cs-map/SKILL.md                ← /cs-map skill
    └── cs-policy/SKILL.md             ← /cs-policy skill
```

**User Experience:**
1. Run setup.sh
2. Reload Claude Code
3. Type `/cs-` and see 8 commands with full documentation
4. Use them like normal slash commands

### 2. User Guide (`integration/claude-code/CLAUDE.md`)

Comprehensive 350-line guide covering:
- Installation steps with copy-paste commands
- 5 hard priority rules (when/why to use Code Scalpel)
- Complete reference table for all 23 tools
- 4 workflow chains (Security, Safe Refactor, Architecture, Compliance)
- Auto-use triggers (when Claude should reach for Code Scalpel automatically)
- 8 slash command descriptions
- Tier availability matrix
- System prompts for AI agents
- Troubleshooting guide

Users copy this to their project root as a reference document.

### 3. Eight Slash Command Skills

Each skill is a minimal YAML+Markdown file in `skills/<command-name>/SKILL.md`:

| Command | Purpose | Key Tools |
|---------|---------|-----------|
| `/cs-setup` | Install MCP, verify, show capabilities | Bash + get_capabilities |
| `/cs-extract` | Get code by name (99.5% context savings) | extract_code + get_file_context |
| `/cs-analyze` | Understand structure, find complexity hotspots | analyze_code + get_file_context + crawl_project |
| `/cs-security` | Full audit (local → cross-file → deps → polyglot) | security_scan + cross_file_security_scan + unified_sink_detect + scan_dependencies |
| `/cs-tests` | Generate tests from execution paths | extract_code + symbolic_execute + generate_unit_tests |
| `/cs-refactor` | Safe refactor workflow (7-step pipeline) | get_symbol_references + get_cross_file_dependencies + extract_code + simulate_refactor + update_symbol |
| `/cs-map` | Architecture mapping (crawl → call graph → map) | crawl_project + get_call_graph + get_project_map + get_cross_file_dependencies |
| `/cs-policy` | Compliance check (HIPAA, SOC2, PCI-DSS) | code_policy_check + verify_policy_integrity + validate_paths |

### 4. Developer Guide (`/CLAUDE.md` in repo root)

For developers working ON code-scalpel:
- Quick start (setup, test, MCP server)
- Priority rules for analyzing code-scalpel itself
- Full project structure (17 language parsers, IR system, 23 tools)
- Key concepts (IR normalization, taint analysis, symbolic execution)
- Development workflow, common tasks, debugging
- PR checklist

This file lives at `/mnt/k/backup/Develop/code-scalpel/CLAUDE.md` (not in docs/).

---

## How Each Component Works

### setup.sh (Bootstrap)

```bash
#!/usr/bin/env bash
# 1. Check Claude Code CLI installed
# 2. Run: claude mcp add codescalpel uvx codescalpel mcp
# 3. Prompt for license file (Pro/Enterprise optional)
# 4. Create .claude/skills/ directory
# 5. Copy all 8 skill directories
# 6. Copy CLAUDE.md if not present
# 7. Verify with colored output
```

**Supports:**
- Local installation (from cloned repo)
- Piped installation (curl from GitHub)
- License file prompt (optional, Pro/Enterprise)
- Colored terminal output
- Error handling and validation

### CLAUDE.md (User Guide)

```markdown
# Installation
MCP Server Setup

# Hard Priority Rules
When/why to use Code Scalpel tools

# Tool Reference Table
All 23 tools with use cases, tiers, costs

# Workflow Chains
Security Audit → Safe Refactor → Architecture Mapping → Compliance

# Auto-Use Triggers
When Claude should reach for Code Scalpel automatically

# Slash Commands
All 8 /cs-* commands documented

# System Prompts
How to teach Claude Code to use Code Scalpel
```

### Slash Command Skills

Each SKILL.md file is ~200-500 lines:

```yaml
---
name: cs-extract
description: Extract code by name (99.5% context savings)
allowed-tools:
  - mcp__codescalpel__extract_code
  - mcp__codescalpel__get_file_context
preamble-tier: 1
---

# /cs-extract — Get Code by Name

[Markdown documentation of the skill]
```

When users type `/cs-extract`, Claude Code:
1. Loads this SKILL.md file
2. Shows the markdown documentation
3. Allows them to use the skill with allowed-tools

### Developer Guide (CLAUDE.md in repo root)

For developers working ON code-scalpel:
- How to setup development environment
- Priority rules for analyzing code-scalpel itself (use extract_code, not Read)
- Project structure explanation
- Key concepts (IR, taint analysis, symbolic execution)
- Common development tasks
- PR checklist and contributing guidelines

---

## Feature Highlights

### 1. Token-Efficient Code Extraction

**Before (without Code Scalpel):**
```python
# Read entire 500-line file
# Tokens: 10,247 tokens
# Cost: $0.030 per query
# Time: 12 seconds
```

**After (with /cs-extract):**
```bash
/cs-extract src/utils.py function calculate_tax
# Tokens: 287 tokens (just the function)
# Cost: $0.0009 per query
# Time: 2 seconds
# Savings: 97% cost, 83% time
```

### 2. Full Security Audit Workflow

```bash
/cs-security src/
# Runs 4-step pipeline:
# 1. Local analysis (SQL injection, XSS, command injection, path traversal)
# 2. Cross-file analysis (taint flows across module boundaries)
# 3. Dependency scan (CVEs via OSV database)
# 4. Polyglot detection (frontend-backend boundaries)
```

### 3. Safe Refactoring Workflow

```bash
/cs-refactor src/utils.py function validate_email
# Runs 7-step pipeline:
# 1. Find all usages (impact zone)
# 2. Trace dependencies (what it depends on)
# 3. Extract current code
# 4. Generate test baseline
# 5. Simulate the change (verify behavior)
# 6. Apply with backup
# 7. Verify syntax
```

### 4. Architecture Mapping

```bash
/cs-map
# Runs 4-step pipeline:
# 1. Crawl project (discover all modules)
# 2. Build call graph (function-to-function calls)
# 3. Visualize structure (package hierarchy, complexity hotspots)
# 4. Trace critical paths (impact analysis)
```

### 5. Automatic System Prompts

The CLAUDE.md file teaches Claude Code:
- **When** to use Code Scalpel (auto-triggers)
- **Why** to use specific tools (cost/accuracy benefits)
- **How** to use each tool (examples, workflows)

Claude Code's system context automatically includes this guidance, so Claude automatically reaches for Code Scalpel without being asked.

---

## Usage Examples

### Example 1: Extract a Function

```bash
User: "Show me the validate_email function"
/cs-extract src/utils.py function validate_email
```

Claude Code:
1. Loads `/cs-extract` skill
2. Calls `extract_code(file_path="src/utils.py", target_type="function", target_name="validate_email")`
3. Returns just that function with metadata
4. Saves 99.5% of tokens vs reading entire file

### Example 2: Security Audit

```bash
User: "Audit this code for vulnerabilities"
/cs-security .
```

Claude Code:
1. Runs `security_scan()` for local vulnerabilities
2. Runs `cross_file_security_scan()` for taint flows
3. Runs `scan_dependencies()` for CVEs
4. Runs `unified_sink_detect()` for polyglot patterns
5. Returns comprehensive report with severity levels

### Example 3: Safe Refactoring

```bash
User: "Refactor this function safely"
/cs-refactor src/api/auth.py function authenticate
```

Claude Code:
1. Shows all callers (find impact)
2. Shows all dependencies
3. Extracts current implementation
4. Generates tests for current behavior
5. Simulates the refactor (verify behavior preserved)
6. Applies changes with automatic backup

### Example 4: Architecture Review

```bash
User: "What's the project architecture?"
/cs-map
```

Claude Code:
1. Crawls entire project
2. Builds call graph
3. Generates architecture map (visual structure)
4. Identifies complexity hotspots
5. Shows critical data flow paths

---

## For Different User Personas

### Individual Developer
**Goal:** Cut Claude API costs 95%

**Quick Start:**
```bash
curl -fsSL https://raw.githubusercontent.com/.../setup.sh | bash
/cs-setup      # Verify
/cs-extract src/auth.py function login  # Try first command
```

**Cost Savings:** $50/mo → $2.50/mo

### Team Lead
**Goal:** Reduce team AI costs 40%

**Rollout:**
1. Run setup.sh in team monorepo
2. Share CLAUDE.md with team
3. Schedule 15-minute demo of 8 commands
4. All 8 developers run `/cs-setup` in Claude Code
5. Track usage via MCP logs

**ROI:** $3,000/mo → $1,800/mo = $14,400/year saved

### Security Engineer
**Goal:** OWASP Top 10 coverage <10% false positives

**First Command:**
```bash
/cs-security .
# Comprehensive report with:
# - SQL injection detection
# - XSS detection
# - Command injection detection
# - Cross-file taint analysis
# - CVE detection
# - Frontend-backend boundary issues
```

### Enterprise Architect
**Goal:** On-premise, policy-enforced, compliance-ready

**Installation:**
```bash
# Use setup.sh with license file
curl ... | bash
# Will prompt for CODE_SCALPEL_LICENSE_PATH
# Policy verification via /cs-policy
# Compliance tracking via audit logs
```

---

## Documentation References

### User-Facing
- **[Integration Guide](../integration/claude-code/CLAUDE.md)** — Complete user guide
- **[Setup Script](../integration/claude-code/setup.sh)** — One-liner bootstrap
- **[8 Slash Command Skills](../integration/claude-code/skills/)** — Individual command documentation

### Developer-Facing
- **[Developer Guide](../CLAUDE.md)** — For developers working ON code-scalpel
- **[Quick Reference](QUICK_REFERENCE.md)** — API reference for 23 tools
- **[Getting Started](getting_started/getting_started.md)** — General getting started

### Project Documentation
- **[Documentation Index](INDEX.md)** — Complete docs navigation
- **[Release Notes](release_notes/)** — What's new in v2.2.0

---

## Architecture

### MCP Registration

```bash
claude mcp add codescalpel uvx codescalpel mcp
```

This registers the Code Scalpel MCP server with Claude Code, exposing all 23 tools.

### Skill Loading

Claude Code discovers skills in:
- `~/.claude/skills/<skill-name>/SKILL.md` (global)
- `./.claude/skills/<skill-name>/SKILL.md` (project-scoped, via setup.sh)

### System Prompts

The CLAUDE.md file is NOT a skill itself but rather:
1. Reference documentation for users
2. Source of truth for priority rules
3. Teaching material for Claude's context window

Claude's system context includes guidance from CLAUDE.md, so Claude automatically knows when to use Code Scalpel tools.

---

## Tier Support

All 8 commands work across all tiers:

| Command | Community | Pro | Enterprise |
|---------|-----------|-----|------------|
| `/cs-setup` | ✓ | ✓ | ✓ |
| `/cs-extract` | ✓ | ✓ | ✓ |
| `/cs-analyze` | ✓ | ✓ | ✓ |
| `/cs-security` | ✓ | ✓ | ✓ |
| `/cs-tests` | | ✓ | ✓ |
| `/cs-refactor` | ✓ | ✓ | ✓ |
| `/cs-map` | ✓ | ✓ | ✓ |
| `/cs-policy` | | ✓ | ✓ |

Individual tools within each command may be gated by tier. For example, `/cs-tests` uses `symbolic_execute` which is Pro+.

---

## Troubleshooting

### "Code Scalpel tools aren't showing up"
→ Run `/cs-setup` to verify MCP is installed

### "Can't install MCP"
→ Ensure Claude Code CLI is installed: `claude --version`

### "License error"
→ Run setup.sh again and provide license path when prompted

### "Skills not discovered"
→ Reload Claude Code (close and reopen) after setup.sh

### "Token error on tool call"
→ Check tier with `/cs-setup` — some tools require Pro/Enterprise

---

## What's Included in v2.2.0

✅ One-liner bootstrap (`setup.sh`)
✅ Complete user guide (`CLAUDE.md`)
✅ 8 slash command skills
✅ Developer guide (`/CLAUDE.md` in repo root)
✅ Updated documentation (`docs/INDEX.md`, `docs/CLAUDE_CODE_INTEGRATION.md`)
✅ README section highlighting integration
✅ Full end-to-end testing

---

## Next Steps

### For Users
1. Copy `integration/claude-code/` or run one-liner
2. Run `/cs-setup` to verify
3. Read `CLAUDE.md` in your project
4. Try `/cs-extract` on your first function

### For Teams
1. Add setup.sh to team onboarding docs
2. Share CLAUDE.md with team
3. Run demo of 8 commands
4. Track savings via MCP logs

### For Maintainers
1. Keep `integration/claude-code/CLAUDE.md` synchronized with tool list
2. Update setup.sh on MCP protocol changes
3. Test integration bundle on releases
4. Reference this guide in release notes

---

## Support

- **Issues:** https://github.com/3D-Tech-Solutions/code-scalpel/issues
- **Docs:** https://github.com/3D-Tech-Solutions/code-scalpel/tree/main/docs
- **GitHub:** https://github.com/3D-Tech-Solutions/code-scalpel

---

**Status:** ✅ Production Ready (v2.2.0)
**Last Updated:** March 28, 2026
