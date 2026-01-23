# Code Scalpel: Surgical Code Operations for AI Agents

**v1.0.0 | January 19, 2026 | General Availability**

Code Scalpel is the bridge between **Generative AI** and **Reliable Software Engineering**.

It is an **MCP (Model Context Protocol) server** designed to be the primary toolset for AI agents (like Claude, GitHub Copilot, and Cursor) to perceive, analyze, and modify codebases with surgical precision.

## 🚀 Quick Start (3 Steps)

**New to Code Scalpel?** Start here:

1. **[📖 Beginner's Guide](docs/getting_started/getting_started.md)** — Plain English explanation of what Code Scalpel is and how to use it.
2. **[✅ Setup Checklist](docs/SETUP_CHECKLIST.md)** — Step-by-step setup in 5 minutes.
3. **Start using it** — Integrate with Claude, Copilot, or Cursor, then ask your AI assistant to help with your code.

**Want Pro or Enterprise?** Visit [CodeScalpel.dev](https://codescalpel.dev) to learn about beta licensing options.

**Developers?** See [Installation & Integration](#installation--integration) and [Documentation](#documentation) below.

---

## The Problem: Why Agents Struggle with Code

Today's AI agents treat code as **text**. They read file contents, guess line numbers, and generate diffs. This leads to:
- **Hallucination**: "Replace line 50" fails when the file changed.
- **Context Window Exhaustion**: Reading 10 files to find one definition.
- **Security Blindness**: Generating SQL injection vulnerabilities because they lack taint analysis.
- **Regression**: Making changes that break existing behavior without verification.

## The Solution: Tools, Not Text

Code Scalpel treats code as a **Graph** (AST + PDG). It gives agents deterministic tools to interact with the codebase:
- **Don't read the file** → `extract_code("process_payment")`
- **Don't guess the line** → `update_symbol("process_payment", new_code)`
- **Don't guess dependencies** → `get_cross_file_dependencies("Order")`
- **Don't assume safety** → `security_scan(code)`

---

## ✨ Key Capabilities at Launch (v1.0)

Code Scalpel launches with **22 specialized tools** divided into five surgical disciplines.

### 1. Surgical Extraction & Analysis (6 Tools)
- **`extract_code`**: Surgically extract functions/classes by name, including necessary imports.
- **`analyze_code`**: Parse structure, complexity, imports, and definitions.
- **`get_project_map`**: Instant cognitive map of the project structure.
- **`get_call_graph`**: Trace execution flow and relationships across files.
- **`get_symbol_references`**: Find all usages of a symbol across the project.
- **`get_file_context`**: Get surrounding context for any code location.

### 2. Taint-Based Security (6 Tools)
- **`security_scan`**: Trace data flow from user input to dangerous sinks (12+ CWEs).
- **`unified_sink_detect`**: Polyglot detection of dangerous functions.
- **`cross_file_security_scan`**: Track tainted data across modules.
- **`scan_dependencies`**: Check for vulnerable dependencies (CVE scanning via OSV).
- **`type_evaporation_scan`**: Detect TypeScript type system vulnerabilities.
- **`get_graph_neighborhood`**: Extract k-hop security context.

### 3. Safe Modification (4 Tools)
- **`update_symbol`**: Atomic replacement of code blocks with safety checks.
- **`rename_symbol`**: Project-wide refactoring with reference updates.
- **`simulate_refactor`**: "Dry run" verification before applying changes.
- **`validate_paths`**: Pre-flight path validation for file operations.

### 4. Verification & Testing (4 Tools)
- **`symbolic_execute`**: Z3 theorem prover to explore code paths.
- **`generate_unit_tests`**: Auto-generate test cases from execution paths.
- **`crawl_project`**: Project-wide analysis of structure and metrics.
- **`verify_policy_integrity`**: Cryptographic policy file verification.

### 5. Advanced Analysis (2 Tools)
- **`get_cross_file_dependencies`**: Analyze complex dependency chains.
- **`code_policy_check`**: Evaluate code against compliance standards.

---

## 🔌 Installation & Integration

### 1. Install from PyPI
```bash
pip install code-scalpel
```

### 2. Initialize Configuration
```bash
code-scalpel init
```

This creates a `.code-scalpel` directory with:
- `limits.toml` - Resource limits based on your tier
- `config.json` - Tool behavior configuration
- `license/` - Directory for your license file

### 3. Run the MCP Server

**Option A: Stdio (Recommended)**
```bash
code-scalpel mcp --stdio
```

**Option B: HTTP**
```bash
code-scalpel mcp --http --port 8080
```

**Option C: Docker**
```bash
docker run -p 8080:8080 code-scalpel:latest mcp --http --host 0.0.0.0 --port 8080
```

### 4. Integrate with Your AI Agent

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "code-scalpel",
      "args": ["mcp", "--stdio"],
      "env": {
        "CODE_SCALPEL_PROJECT_ROOT": "/path/to/your/project"
      }
    }
  }
}
```

**Custom MCP Client:**
```bash
curl -X POST http://127.0.0.1:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"tool": "analyze_code", "params": {"code": "..."}}'
```

See [Release Notes v1.0.0](docs/release_notes/RELEASE_NOTES_v1.0.0.md) for complete setup guide with all transport options, environment variables, and configuration details.

---

## How We're Different

### Code Scalpel vs Python `scalpel` Library

Code Scalpel is NOT a fork of the `scalpel` Python library. It's a completely independent, production-grade MCP server:

| Feature | Code Scalpel | Python `scalpel` |
|---------|--------------|------------------|
| **Interface** | MCP server (primary) | CLI tool only |
| **AI Agent Ready** | ✅ Yes | ❌ No |
| **Tools** | 22 specialized tools | Limited utilities |
| **Security Scanning** | Taint analysis (12 CWEs) | Basic pattern matching |
| **Symbolic Execution** | Z3-powered | ❌ Not supported |
| **Test Generation** | ✅ Auto-generate | ❌ Not supported |
| **Refactor Verification** | ✅ Behavior check | ❌ Manual |
| **Cross-file Analysis** | ✅ Full tracking | Limited |

### Code Scalpel vs IDE Extensions

| Feature | Code Scalpel | VS Code Pylance | Copilot |
|---------|--------------|-----------------|---------|
| **Interface** | MCP server | IDE plugin | Chat-only |
| **Code Extraction** | ✅ By name, safe | ⚠️ Line-based | ❌ Not precise |
| **Security Analysis** | ✅ 22 tools, taint | ⚠️ Limited | ⚠️ Generalist |
| **Test Generation** | ✅ Symbolic | ❌ No | ⚠️ Variable |
| **Independent of IDE** | ✅ Works anywhere | ❌ IDE-bound | ❌ Web-bound |
| **Offline Capable** | ✅ Yes | ✅ Yes | ❌ No |

---

## 📖 Documentation

- **[Release Notes v1.0.0](docs/release_notes/RELEASE_NOTES_v1.0.0.md)** — Complete setup guide with MCP server configuration
- **[Comprehensive Guide](docs/COMPREHENSIVE_GUIDE.md)** — Full feature documentation and examples
- **[MCP Configuration](docs/deployment/mcp_configuration.md)** — Environment variables and .code-scalpel options
- **[Deployment Guide](docs/deployment/)** — Docker, Kubernetes, and cloud deployment
- **[Examples](examples/)** — Code examples for different frameworks

---

## 🔐 Security & Safety

Code Scalpel uses **taint-based analysis** to detect real vulnerabilities:
- SQL Injection, XSS, Command Injection, Path Traversal
- NoSQL Injection, LDAP Injection, XPath Injection
- Email/Format String/Regex DoS attacks

All analysis is performed on **your infrastructure** — no code leaves your environment.

---

## 📊 Tier Access Control

Code Scalpel supports three access tiers:

- **Community** (Free) - Core tools with limits, perfect for individual developers
- **Pro** - Extended analysis with higher limits for teams
- **Enterprise** - Unlimited scope, compliance reporting, custom governance

Your tier is determined by the license file in `.code-scalpel/license/license.jwt`.

---

## 🤝 Contributing

Code Scalpel is open source under the MIT License. We welcome contributions:

1. Clone: `git clone https://github.com/3D-Tech-Solutions/code-scalpel.git`
2. Install dev deps: `pip install -e '.[dev]'`
3. Run tests: `pytest tests/`
4. Submit PR to main

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## 📄 License

Code Scalpel uses a **dual-license model**:

- **Community Edition**: [MIT License](LICENSE) (free, open source)
  - Core functionality with basic limits
  - Perfect for individual developers and small projects
  - No license file required
  
- **Pro & Enterprise Editions**: Commercial License (currently in Beta)
  - Pro: Enhanced analysis with expanded limits for teams
  - Enterprise: Unlimited capabilities, advanced security, compliance reporting
  - Requires valid signed license token

**Important:** Attempting to circumvent license authentication will void your license and terminate all rights to use Pro/Enterprise features. See [LICENSE](LICENSE) Part 2 for full commercial terms.

For commercial licensing inquiries: https://github.com/3d-tech-solutions/code-scalpel

---

## 🎉 Thank You

Code Scalpel v1.0.0 represents months of development, testing, and refinement. Thank you to:
- Community users who provided feedback during pre-releases
- Open source projects we depend on
- Everyone who contributed to making this possible

**Let's build better code together!** 🚀

---

**Latest Release:** v1.0.0 (January 19, 2026)  
**Status:** General Availability  
**License:** MIT
