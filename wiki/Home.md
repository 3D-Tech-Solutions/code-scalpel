# Code Scalpel Wiki

**Welcome to the Code Scalpel documentation!**

Code Scalpel is an MCP (Model Context Protocol) server that provides AI agents with surgical precision for code analysis, security scanning, and safe refactoring.

## 🚀 Quick Links

### Getting Started
- **[Installation](Installation)** - Setup and deployment options
- **[Getting Started](Getting-Started)** - Your first Code Scalpel operations
- **[Configuration](Configuration)** - Environment variables and settings

### Core Documentation
- **[MCP Tools Reference](MCP-Tools-Reference)** - Complete tool documentation (22 tools)
- **[Architecture](Architecture)** - Tier system, components, design decisions
- **[Security](Security)** - Policy checking and integrity verification

### Learning & Support
- **[Examples](Examples)** - Code examples and tutorials
- **[Troubleshooting](Troubleshooting)** - Common issues and solutions
- **[Contributing](Contributing)** - Development setup and guidelines
- **[Changelog](Changelog)** - Version history and updates

## What is Code Scalpel?

Code Scalpel is an **MCP server** that enhances AI coding assistants with specialized code analysis tools. You interact with it through **natural conversation**—no Python coding required.

When you talk to Claude, Copilot, or Cursor, they use Code Scalpel's 22 tools behind the scenes:

- 🔍 **Extract code surgically** - "Extract the calculate_tax function" → 50 tokens instead of 10,000
- 🛡️ **Detect vulnerabilities** - "Check this for SQL injection" → Taint analysis across 12+ CWEs
- ✅ **Verify changes** - "Is it safe to refactor this?" → Simulates before applying
- 🧪 **Generate tests** - "Create tests for this function" → Uses symbolic execution
- 🔄 **Refactor safely** - "Rename this across the project" → Updates all references

## How It Works

### Without Code Scalpel
```
You: "Extract the calculate_tax function"
AI: Reads entire 5000-line file → 10,000 tokens consumed
    Manually finds function → Imprecise extraction
    Returns code with irrelevant context
```

### With Code Scalpel (MCP Server)
```
You: "Extract the calculate_tax function"
AI: Uses extract_code tool via MCP → 50 tokens consumed
    Surgical extraction via AST → Exact function + imports only
    Returns clean code ready to use
```

## Key Capabilities

Code Scalpel treats code as a **Graph** (AST + PDG) rather than text, enabling precise operations:

### 1. Surgical Extraction (99% Token Reduction)
Ask: *"Extract the process_payment function from services.py"*
- AI uses MCP tool to extract by name → 50 tokens
- Returns only the function + necessary imports
- No need to read the entire file

### 2. Taint-Based Security Analysis
Ask: *"Check this code for SQL injection vulnerabilities"*
- AI analyzes data flow from sources to sinks
- Detects injection, XSS, command execution, path traversal
- Identifies 12+ CWE vulnerabilities

### 3. Symbolic Execution & Test Generation
Ask: *"Generate tests for this function"*
- AI explores all execution paths
- Creates test cases for edge cases and branches
- Generates pytest or unittest code

### 4. Safe Refactoring
Ask: *"Is it safe to refactor this? Here's my new version:"*
- AI simulates the change first
- Verifies no security issues introduced
- Checks for breaking changes
- Only then applies the update

## Tier System

Code Scalpel offers three tiers:

| Tier | License | Use Case |
|------|---------|----------|
| **Community** | MIT (Free) | Personal projects, learning, open source |
| **Pro** | Commercial | Professional development, unlimited findings |
| **Enterprise** | Commercial | Teams, compliance reporting, audit trails |

**All 22 tools are available in the Community tier!** Higher tiers provide enhanced limits and enterprise features.

## Supported Languages

- **Python** - Full support (AST + PDG + symbolic execution)
- **JavaScript/TypeScript** - AST analysis, call graphs, extraction
- **Java** - AST parsing and analysis
- **Go, Rust, Ruby, PHP** - AST parsing via tree-sitter

## MCP Transports

Code Scalpel works with all major AI coding assistants:

- ✅ **VS Code** (stdio)
- ✅ **GitHub Copilot** (stdio)
- ✅ **Claude Desktop** (stdio)
- ✅ **Cursor** (stdio)
- ✅ **HTTP/SSE** - Remote deployments
- ✅ **Docker** - Containerized environments

## Community & Support

- **GitHub Repository**: [3D-Tech-Solutions/code-scalpel](https://github.com/3D-Tech-Solutions/code-scalpel)
- **Issues**: Report bugs and request features on GitHub
- **Discussions**: Community Q&A and announcements
- **Security**: See [Security Policy](Security) for vulnerability reporting

---

**Ready to get started?** → [Installation Guide](Installation)
