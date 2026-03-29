# 🔬 Code Scalpel Bootstrap: Copy-Paste Ready Setup

This is a complete, copy-paste-ready prompt you can use in Claude Code to install and learn Code Scalpel in seconds.

---

## 📋 For Claude Desktop / Claude Code Users

Copy everything below and paste it into your Claude Code session:

```
I want to set up Code Scalpel, a powerful MCP server with 23 surgical code analysis tools.

Please:
1. Install Code Scalpel MCP server
2. Verify it's working
3. Teach me when/how to use each major tool category

Code Scalpel gives me deterministic tools instead of text guessing:
- Extract functions/classes without reading entire files (~50 tokens vs 10,000)
- Analyze security vulnerabilities with taint analysis (<10% false positives)
- Generate unit tests from symbolic execution paths
- Refactor safely with behavior verification
- Find all usages of a symbol across a project
- Track data flow across module boundaries

The 23 tools are:
EXTRACTION (6): extract_code, analyze_code, get_project_map, get_call_graph, get_symbol_references, get_file_context
SECURITY (6): security_scan, unified_sink_detect, cross_file_security_scan, scan_dependencies, type_evaporation_scan, get_graph_neighborhood
MODIFICATION (4): update_symbol, rename_symbol, simulate_refactor, validate_paths
TESTING (3): symbolic_execute, generate_unit_tests, crawl_project
ANALYSIS (1): get_cross_file_dependencies
GOVERNANCE (2): code_policy_check, verify_policy_integrity
DISCOVERY (1): get_capabilities

Start me with the setup command and a quick reference of when to use each tool.
```

---

## 🚀 What Happens After You Paste

Claude Code will:

1. **Install the MCP server** with a single command
2. **Verify it's running** and show you the tool list
3. **Teach you the workflow**:
   - When to use surgical extraction vs reading files
   - How to find bugs with taint analysis
   - How to generate comprehensive tests
   - How to refactor safely
   - How to track dependencies across files

---

## 🎯 Installation (Manual if Needed)

If you prefer to install manually:

```bash
# One command to install
claude mcp add codescalpel uvx codescalpel mcp

# Verify it works
uvx codescalpel --version
```

Then restart Claude Code to discover the new MCP server.

---

## 📚 Quick Reference: When to Use Each Tool

### 🔍 **I need to understand code structure**
→ Use `analyze_code` for AST, complexity, imports
→ Use `get_project_map` for high-level architecture
→ Use `get_file_context` for surrounding context

### 🔎 **I need to extract a specific function**
→ Use `extract_code` to get just that function + dependencies
**Saves 95% context** compared to reading the whole file
```bash
/cs-extract src/utils.py function calculate_tax
```

### 🔗 **I need to find where something is used**
→ Use `get_symbol_references` to find all usages across the project
→ Use `get_call_graph` to trace execution flow
→ Use `get_cross_file_dependencies` to see dependency chains

### 🛡️ **I need to find security bugs**
→ Use `security_scan` for taint analysis (SQL injection, XSS, etc.)
→ Use `cross_file_security_scan` to track data across modules
→ Use `scan_dependencies` to find vulnerable packages
**Result: <10% false positives vs 22-31% for other tools**

### ✅ **I need to test code**
→ Use `symbolic_execute` to explore all execution paths
→ Use `generate_unit_tests` to auto-create pytest tests
**Each path gets a test case with concrete inputs**

### 🔧 **I need to refactor safely**
→ Use `simulate_refactor` as a "dry run" to verify behavior
→ Use `rename_symbol` for project-wide refactoring
→ Use `update_symbol` for atomic code replacement

### 📋 **I need to verify compliance**
→ Use `code_policy_check` for organization standards
→ Use `verify_policy_integrity` for policy file signatures
→ Use `validate_paths` for path validation (Docker-aware)

### 📊 **I need project metrics**
→ Use `crawl_project` for lines of code, complexity hotspots
→ Use `get_capabilities` to check tier/license limits

---

## 🎓 Learning Path

### Day 1: Extraction & Navigation
- Learn `extract_code` — Your new best friend (saves 95% context)
- Learn `get_symbol_references` — Find usages in one command
- Learn `get_file_context` — Quick overview without reading whole files

### Day 2: Analysis & Security
- Learn `security_scan` — Find bugs deterministically
- Learn `analyze_code` — Understand code structure
- Learn `get_call_graph` — Trace execution flow

### Day 3: Testing & Refactoring
- Learn `generate_unit_tests` — Auto-create comprehensive tests
- Learn `simulate_refactor` — Verify changes before applying
- Learn `rename_symbol` — Safe project-wide refactoring

### Week 2: Advanced
- Learn `cross_file_security_scan` — Track data across modules
- Learn `get_cross_file_dependencies` — Dependency analysis
- Learn `code_policy_check` — Compliance checking

---

## 💡 Pro Tips

### 1. **Always Extract, Never Read Whole Files**
```bash
# ❌ Don't do this (costs 10,000 tokens)
Read entire src/api.py

# ✅ Do this instead (costs 287 tokens)
/cs-extract src/api.py function process_payment
```

### 2. **Use Taint Analysis for Security**
Instead of guessing where bugs might be:
```bash
# Find SQL injection, XSS, command injection, path traversal automatically
/cs-security src/
```

### 3. **Chain Tools for Complex Tasks**
```bash
# Find a symbol
/cs-extract src/auth.py function authenticate

# See where it's used
/cs-get-symbol-references authenticate

# Verify refactoring
/cs-simulate-refactor src/auth.py "rename authenticate to verifyUser"

# Apply change
/cs-rename-symbol src/auth.py authenticate verifyUser
```

### 4. **Generate Tests from Paths**
```bash
# Let Code Scalpel explore ALL execution paths and create tests
/cs-tests src/utils.py function process_data
```

---

## 🔑 Commands Reference

| What You Need | Command | Time Saved |
|---|---|---|
| Extract a function | `/cs-extract` | 95% context |
| Find usages | `/cs-get-symbol-references` | 100% accuracy |
| Security scan | `/cs-security` | <10% false positives |
| Generate tests | `/cs-tests` | Automated |
| Safe refactor | `/cs-simulate-refactor` then `/cs-rename-symbol` | Safety check |
| Architecture map | `/cs-map` | High-level view |
| Cross-file taint | `/cs-security` + `--cross-file` | End-to-end tracking |

---

## 📖 Full Documentation

- **Installation**: `integration/claude-code/CLAUDE.md`
- **Tool Reference**: `docs/QUICK_REFERENCE.md`
- **Security Deep Dive**: `docs/guides/security_analysis.md`
- **Architecture**: `docs/MCP_DEPLOYMENT_GUIDE.md`

---

## ✨ Get Started Now

**Paste the prompt above into Claude Code and it will:**

1. ✅ Install Code Scalpel
2. ✅ Verify the 23 tools are registered
3. ✅ Show you quick examples of each tool
4. ✅ Teach you when to use what
5. ✅ Set up slash commands for common workflows

**Your code analysis just got 95% more efficient.** 🚀

---

## Questions?

- **Tools not working?** → `uvx codescalpel --version`
- **License issues?** → `uvx codescalpel tier-info`
- **Need help?** → [GitHub Issues](https://github.com/3D-Tech-Solutions/code-scalpel/issues)

**Ready to analyze code surgically instead of guessing?** Paste the prompt above into Claude Code now! 🔬
