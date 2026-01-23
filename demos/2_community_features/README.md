# Demo 2: Community Features (Free Tier)
 
**Duration**: 10-15 minutes
**Audience**: Developers evaluating free vs paid tiers
**Goal**: Showcase the full power of the Community tier (100% free, no credit card required)
 
---
 
## 🎯 Key Message
 
**"All 19 tools available in the free tier - with generous limits for individual developers and small projects"**
 
---
 
## 📋 What's Available in Community Tier
 
| Feature | Community Tier | Notes |
|---------|----------------|-------|
| **All 19 Tools** | ✅ | Every tool, zero cost |
| **Code Extraction** | ✅ | Multi-language support |
| **Security Scanning** | ✅ | OWASP Top 10 detection |
| **Project Analysis** | ✅ | Call graphs, dependencies |
| **Code Modification** | ✅ | Safe refactoring |
| **Test Generation** | ✅ | Basic unit tests |
| **Max Findings** | 50 per scan | Sufficient for most files |
| **File Size Limit** | 1MB | Covers most source files |
| **Vulnerability Types** | OWASP Top 10 | Core security issues |
 
---
 
## 🎬 Demo Script
 
### Part 1: Code Extraction & Analysis (3 minutes)
 
**Scenario**: Understanding an unfamiliar codebase
 
#### 1.1 Extract a Specific Function
 
**Prompt to Claude**:
```
Extract the calculate_total function from demo_app.py including its dependencies
```
 
**Tool Call**: `extract_code`
```json
{
  "file_path": "demo_app.py",
  "symbol_name": "calculate_total",
  "symbol_type": "function",
  "include_context": true,
  "context_depth": 1
}
```
 
**What to Highlight**:
- 🎯 Extracts only what you need (not the entire 300-line file)
- 🔗 Includes dependencies (`calculate_tax`, `apply_discount`)
- 💡 Token efficiency: ~100 tokens vs ~6,000 for full file
 
**Expected Output**:
```python
def calculate_total(subtotal: float, state: str, discount_code: Optional[str] = None) -> Dict[str, float]:
    """Calculate order total including tax and discounts."""
    discount = apply_discount(subtotal, discount_code) if discount_code else 0.0
    discounted_subtotal = subtotal - discount
    tax = calculate_tax(discounted_subtotal, state)
    total = discounted_subtotal + tax
    return {
        "subtotal": round(subtotal, 2),
        "discount": round(discount, 2),
        "tax": round(tax, 2),
        "total": round(total, 2),
    }
 
# Dependencies:
def calculate_tax(amount: float, state: str) -> float: ...
def apply_discount(amount: float, discount_code: str) -> float: ...
```
 
---
 
#### 1.2 Analyze Code Structure
 
**Prompt to Claude**:
```
Analyze the structure of demo_app.py and show me all functions with their complexity
```
 
**Tool Call**: `analyze_code`
```json
{
  "file_path": "demo_app.py",
  "language": "python",
  "include_metrics": true
}
```
 
**What to Highlight**:
- 📊 Instant complexity metrics (no code execution)
- 🏗️ Complete structure overview
- 🎯 Identifies refactoring candidates (high complexity functions)
 
**Expected Output**:
```json
{
  "file_path": "demo_app.py",
  "language": "python",
  "total_lines": 287,
  "functions": [
    {"name": "calculate_tax", "line_start": 34, "complexity": 2},
    {"name": "calculate_total", "line_start": 51, "complexity": 3},
    {"name": "process_payment", "line_start": 81, "complexity": 5},
    {"name": "validate_credit_card", "line_start": 110, "complexity": 6}
  ],
  "classes": [],
  "imports": ["json", "logging", "datetime", "typing", "decimal"],
  "avg_complexity": 4.0
}
```
 
---
 
#### 1.3 Get File Context (Quick Overview)
 
**Prompt to Claude**:
```
Give me a quick overview of demo_app.py - what does it do?
```
 
**Tool Call**: `get_file_context`
```json
{
  "file_path": "demo_app.py"
}
```
 
**What to Highlight**:
- ⚡ Faster than full analysis
- 📝 Perfect for initial orientation
- 🎯 Answers "what does this file do?" in seconds
 
---
 
### Part 2: Security Scanning (3 minutes)
 
**Scenario**: Find security vulnerabilities in code
 
#### 2.1 Basic Security Scan
 
**Setup**: Use the vulnerable sample code (see `vulnerable_app.py`)
 
**Prompt to Claude**:
```
Scan vulnerable_app.py for security vulnerabilities
```
 
**Tool Call**: `security_scan`
```json
{
  "file_path": "vulnerable_app.py",
  "language": "python",
  "vulnerability_types": ["sql_injection", "xss", "command_injection"]
}
```
 
**What to Highlight**:
- 🔒 Detects OWASP Top 10 vulnerabilities
- 📍 Shows exact line numbers
- ⚠️ Explains the risk
- 📊 Community tier: Up to 50 findings
 
**Expected Output**:
```json
{
  "findings": [
    {
      "type": "sql_injection",
      "severity": "high",
      "line": 15,
      "code": "cursor.execute(f\"SELECT * FROM users WHERE id = {user_id}\")",
      "message": "Potential SQL injection via string formatting",
      "cwe": "CWE-89"
    },
    {
      "type": "xss",
      "severity": "medium",
      "line": 42,
      "code": "return f\"<h1>Welcome {username}</h1>\"",
      "message": "Unescaped user input in HTML output",
      "cwe": "CWE-79"
    }
  ],
  "total_findings": 2,
  "tier_info": {
    "current_tier": "community",
    "max_findings": 50,
    "findings_returned": 2
  }
}
```
 
**Talking Point**:
> "Community tier includes full security scanning. For most files, 50 findings is more than enough. If you hit the limit on large files, that's when Pro tier makes sense."
 
---
 
#### 2.2 Dependency Vulnerability Scan
 
**Prompt to Claude**:
```
Check my project dependencies for known CVEs
```
 
**Tool Call**: `scan_dependencies`
```json
{
  "project_root": ".",
  "package_manager": "pip",
  "include_dev": false
}
```
 
**What to Highlight**:
- 🔍 Scans package dependencies
- 🚨 Identifies known CVEs from OSV database
- 📦 Works with pip, npm, yarn, maven, gradle
 
**Expected Output**:
```json
{
  "vulnerable_packages": [
    {
      "name": "requests",
      "version": "2.25.0",
      "vulnerabilities": [
        {
          "id": "CVE-2023-32681",
          "severity": "medium",
          "summary": "Proxy-Authorization header leak",
          "fixed_in": "2.31.0"
        }
      ]
    }
  ],
  "total_vulnerabilities": 1,
  "recommendation": "Update requests to 2.31.0 or higher"
}
```
 
---
 
### Part 3: Project Navigation & Understanding (3 minutes)
 
**Scenario**: Map out a new codebase
 
#### 3.1 Get Project Structure
 
**Prompt to Claude**:
```
Show me the overall structure of this project
```
 
**Tool Call**: `get_project_map`
```json
{
  "project_root": ".",
  "include_tests": false,
  "max_depth": 3
}
```
 
**What to Highlight**:
- 🗺️ Visual project hierarchy
- 📁 Module organization
- 🔗 Dependency relationships
 
**Expected Output**:
```json
{
  "project_root": "/demo_project",
  "structure": {
    "src/": {
      "app.py": {"type": "module", "functions": 8, "classes": 2},
      "auth/": {
        "login.py": {"type": "module", "functions": 5},
        "session.py": {"type": "module", "functions": 3}
      },
      "api/": {
        "routes.py": {"type": "module", "functions": 12},
        "handlers.py": {"type": "module", "functions": 7}
      }
    },
    "tests/": {
      "test_auth.py": {"type": "test", "test_count": 15}
    }
  }
}
```
 
---
 
#### 3.2 Find All References to a Symbol
 
**Prompt to Claude**:
```
Find all places where the calculate_tax function is used
```
 
**Tool Call**: `get_symbol_references`
```json
{
  "symbol_name": "calculate_tax",
  "project_root": ".",
  "include_tests": true
}
```
 
**What to Highlight**:
- 🔍 Project-wide symbol search
- 🎯 Essential for safe refactoring
- ✅ Includes test usage
 
**Expected Output**:
```json
{
  "symbol_name": "calculate_tax",
  "references": [
    {
      "file": "demo_app.py",
      "line": 15,
      "context": "def calculate_total(...): tax = calculate_tax(...)"
    },
    {
      "file": "invoice.py",
      "line": 42,
      "context": "tax_amount = calculate_tax(subtotal, state)"
    },
    {
      "file": "tests/test_tax.py",
      "line": 8,
      "context": "assert calculate_tax(100, 'CA') == 7.25"
    }
  ],
  "total_references": 3
}
```
 
---
 
#### 3.3 Build a Call Graph
 
**Prompt to Claude**:
```
Show me the call graph for the process_payment function
```
 
**Tool Call**: `get_call_graph`
```json
{
  "entry_point": "process_payment",
  "file_path": "demo_app.py",
  "max_depth": 2
}
```
 
**What to Highlight**:
- 🕸️ Visualize function dependencies
- 🎯 Understand code flow
- 🔍 Trace execution paths
 
**Expected Output**:
```json
{
  "entry_point": "process_payment",
  "call_graph": {
    "process_payment": {
      "calls": [
        {"function": "validate_credit_card", "file": "demo_app.py", "line": 95},
        {"function": "log_transaction", "file": "demo_app.py", "line": 102}
      ]
    },
    "validate_credit_card": {
      "calls": []
    }
  }
}
```
 
---
 
### Part 4: Code Modification & Testing (3 minutes)
 
**Scenario**: Safely modify code with confidence
 
#### 4.1 Simulate a Refactor (Dry Run)
 
**Prompt to Claude**:
```
Simulate renaming calculate_tax to compute_sales_tax
```
 
**Tool Call**: `simulate_refactor`
```json
{
  "changes": [
    {
      "file": "demo_app.py",
      "old_symbol": "calculate_tax",
      "new_symbol": "compute_sales_tax"
    }
  ],
  "strict_mode": true
}
```
 
**What to Highlight**:
- ✅ Preview changes before applying
- 🔍 Syntax validation
- 🚫 Catches breaking changes
 
**Expected Output**:
```json
{
  "simulation_result": "success",
  "changes_preview": [
    {
      "file": "demo_app.py",
      "line": 34,
      "old": "def calculate_tax(amount: float, state: str) -> float:",
      "new": "def compute_sales_tax(amount: float, state: str) -> float:"
    },
    {
      "file": "demo_app.py",
      "line": 55,
      "old": "tax = calculate_tax(discounted_subtotal, state)",
      "new": "tax = compute_sales_tax(discounted_subtotal, state)"
    }
  ],
  "total_changes": 2,
  "syntax_valid": true,
  "warnings": []
}
```
 
---
 
#### 4.2 Generate Unit Tests
 
**Prompt to Claude**:
```
Generate unit tests for the calculate_tax function
```
 
**Tool Call**: `generate_unit_tests`
```json
{
  "file_path": "demo_app.py",
  "symbol_name": "calculate_tax",
  "test_framework": "pytest",
  "coverage_target": "basic"
}
```
 
**What to Highlight**:
- 🧪 Automatic test generation
- 📊 Basic coverage in Community tier
- ⚡ Saves hours of manual test writing
 
**Expected Output**:
```python
import pytest
from demo_app import calculate_tax
 
def test_calculate_tax_california():
    """Test California tax rate (7.25%)"""
    assert calculate_tax(100.0, "CA") == 7.25
 
def test_calculate_tax_new_york():
    """Test New York tax rate (4%)"""
    assert calculate_tax(100.0, "NY") == 4.0
 
def test_calculate_tax_unknown_state():
    """Test unknown state defaults to 0%"""
    assert calculate_tax(100.0, "XX") == 0.0
 
def test_calculate_tax_zero_amount():
    """Test zero amount"""
    assert calculate_tax(0.0, "CA") == 0.0
```
 
---
 
#### 4.3 Safe Symbol Renaming
 
**Prompt to Claude**:
```
Rename the apply_discount function to calculate_discount across the project
```
 
**Tool Call**: `rename_symbol`
```json
{
  "old_name": "apply_discount",
  "new_name": "calculate_discount",
  "scope": "project",
  "create_backup": true
}
```
 
**What to Highlight**:
- 🔒 Automatic backup creation
- 🎯 Project-wide rename
- ✅ Maintains code consistency
 
---
 
### Part 5: Cross-File Analysis (2 minutes)
 
**Scenario**: Understand dependencies across modules
 
#### 5.1 Trace Cross-File Dependencies
 
**Prompt to Claude**:
```
Show me all the dependencies for the auth module
```
 
**Tool Call**: `get_cross_file_dependencies`
```json
{
  "file_path": "auth/login.py",
  "max_depth": 2
}
```
 
**What to Highlight**:
- 🕸️ Import chain visualization
- 🔍 Circular dependency detection
- 🎯 Understand coupling
 
**Expected Output**:
```json
{
  "file": "auth/login.py",
  "dependencies": {
    "direct": [
      "auth/session.py",
      "utils/crypto.py"
    ],
    "indirect": [
      "config/settings.py",
      "db/models.py"
    ]
  },
  "circular_dependencies": [],
  "total_depth": 2
}
```
 
---
 
## 🎤 Presentation Talking Points
 
### Opening (30 seconds)
 
> "Code Scalpel's Community tier is completely free and includes all 19 tools. Unlike other tools that gate features behind paywalls, we give you full access with generous limits designed for individual developers and small teams."
 
### During Demo (per section)
 
**Code Extraction**:
> "Notice how we extracted just the function we needed - not the entire file. This saves tokens, reduces costs, and gives the AI exactly the context it needs. No more hallucinations from information overload."
 
**Security Scanning**:
> "The free tier detects all OWASP Top 10 vulnerabilities. The 50-finding limit means you can scan most files completely. If you're working on a massive enterprise codebase and hitting limits, that's when Pro makes sense."
 
**Project Navigation**:
> "Understanding unfamiliar code is the #1 time sink for developers. These tools let you map architecture, trace dependencies, and find references in seconds instead of hours."
 
**Code Modification**:
> "Safe refactoring is critical. Simulate changes first, generate tests automatically, and rename symbols project-wide with automatic backups. All free."
 
### Closing (30 seconds)
 
> "Everything you've seen today is included in the free Community tier. No credit card, no trial period, no strings attached. This is production-ready tooling for serious development work. When you need unlimited findings, advanced security features, or enterprise compliance - that's when Pro and Enterprise tiers add value. But for most developers, Community tier is all you need."
 
---
 
## 📊 Community vs Pro Comparison
 
Use this slide during the demo to preview Pro tier:
 
| Feature | Community (Free) | Pro ($29-49/mo) |
|---------|------------------|-----------------|
| All tools | ✅ | ✅ |
| Max findings | 50 per scan | ♾️ Unlimited |
| File size | 1MB | 10MB |
| OWASP Top 10 detection | ✅ | ✅ |
| Sanitizer recognition | ❌ | ✅ |
| Confidence scoring | ❌ | ✅ |
| NoSQL/LDAP injection | ❌ | ✅ |
| Secret detection | ❌ | ✅ |
| Remediation suggestions | ❌ | ✅ |
| Data-driven tests | ❌ | ✅ |
 
**Call to Action**:
> "If you're hitting the 50-finding limit frequently or need advanced security features, check out Demo 3 to see what Pro tier unlocks."
 
---
 
## ❓ Anticipated Questions
 
**Q: Is the Community tier time-limited?**
A: No. Community tier is free forever. No trial expiration, no credit card required.
 
**Q: What's the catch?**
A: No catch. We want individuals and small teams to use Code Scalpel. When you grow or need advanced features, you can upgrade. But you're never forced to.
 
**Q: Can I use this commercially?**
A: Yes! Community tier has no commercial restrictions. Use it for work, side projects, open source - whatever you need.
 
**Q: How many projects can I analyze?**
A: Unlimited. There's no project limit in any tier.
 
**Q: Do I need to create an account?**
A: No account needed for Community tier. Just install and use.
 
**Q: When should I upgrade to Pro?**
A: When you regularly hit the 50-finding limit, need files >1MB, or want advanced security features like sanitizer recognition and confidence scoring.
 
**Q: Can I downgrade from Pro back to Community?**
A: Yes, anytime. No lock-in.
 
---
 
## 🎁 Demo Files Included
 
All sample code for this demo:
 
- `demo_app.py` - Clean code for extraction/analysis demos
- `vulnerable_app.py` - Intentionally vulnerable code for security demos
- `sample_project/` - Multi-file project for cross-file demos
- `run_demo.sh` - Automated demo script with all prompts
 
---
 
## 🎯 Success Criteria
 
After this demo, viewers should:
- ✅ Understand that Community tier is fully featured (not a crippled trial)
- ✅ See the practical value of each tool category
- ✅ Know when Community tier is sufficient vs when to upgrade
- ✅ Feel confident installing and using Code Scalpel
- ✅ Be excited about the free tier capabilities
 
---
 
## 🔗 Next Steps
 
After this demo:
1. ✅ Viewers understand Community tier value
2. 🎯 Watch **Demo 3: Pro Features** to see upgrade benefits
3. 📚 Try the [Interactive Tutorial](https://code-scalpel.dev/tutorial)
4. 💬 Join [Discord Community](https://discord.gg/code-scalpel)
 
---
 
**End of Demo 2**
 
*Total time: 10-15 minutes | Difficulty: Intermediate | Target: Evaluators*