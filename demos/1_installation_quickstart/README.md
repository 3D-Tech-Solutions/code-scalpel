# Demo 1: Installation & Quick Start
 
**Duration**: 5 minutes
**Audience**: First-time users, prospects, conference talks
**Goal**: Get from zero to running MCP server with first tool call
 
---
 
## 🎯 What You'll Demonstrate
 
1. Install Code Scalpel in under 60 seconds
2. Configure MCP server in Claude Desktop
3. Make your first tool call
4. Experience the "aha moment" of token efficiency
 
---
 
## 📋 Prerequisites
 
- Python 3.10 or higher
- pip or uvx installed
- Claude Desktop (or MCP-compatible client)
 
---
 
## 🎬 Demo Script
 
### Step 1: Installation (30 seconds)
 
**Narration**:
> "Let's install Code Scalpel. It's available on PyPI, so installation is just one command."
 
**Commands**:
```bash
# Option A: Using pip
pip install code-scalpel
 
# Option B: Using uvx (recommended for isolated environments)
uvx code-scalpel --version
 
# Verify installation
python -m code_scalpel --version
```
 
**Expected Output**:
```
Code Scalpel v1.0.0
MCP Server Ready
```
 
**Talking Points**:
- ✅ No complex setup or configuration
- ✅ Works on Windows, Mac, Linux
- ✅ Zero external dependencies beyond Python
 
---
 
### Step 2: Configure MCP Server (90 seconds)
 
**Narration**:
> "Now let's configure the MCP server in Claude Desktop. We'll add Code Scalpel to the MCP servers configuration."
 
**File**: `~/.claude_desktop_config.json` (Mac/Linux) or `%APPDATA%/Claude/claude_desktop_config.json` (Windows)
 
**Configuration**:
```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "python",
      "args": ["-m", "code_scalpel.mcp"],
      "env": {
        "SCALPEL_ROOT": "/path/to/your/project"
      }
    }
  }
}
```
 
**Talking Points**:
- ✅ Standard MCP server configuration
- ✅ `SCALPEL_ROOT` points to your codebase
- ✅ Works with any MCP-compatible client (Claude Desktop, VS Code, Cursor)
 
**Demo Tip**:
> Replace `/path/to/your/project` with the actual path to the demo codebase (e.g., the `vulnerable_webapp` folder in this demos directory).
 
---
 
### Step 3: Restart Claude Desktop (10 seconds)
 
**Narration**:
> "Restart Claude Desktop to load the new MCP server."
 
**Action**:
1. Quit Claude Desktop completely
2. Reopen Claude Desktop
3. Look for the 🔌 MCP icon in the interface
 
**Verification**:
- You should see "code-scalpel" listed in available MCP servers
- Status should show as "connected"
 
---
 
### Step 4: First Tool Call - Extract Code (2 minutes)
 
**Narration**:
> "Let's make our first tool call. We'll use the `extract_code` tool to surgically extract a single function from a large file."
 
**Setup**: Create a sample Python file with multiple functions:
 
**File**: `demo_app.py`
```python
# This file is 500 lines long (simulated)
# ... lots of code ...
 
def calculate_tax(amount: float, state: str) -> float:
    """Calculate sales tax based on state."""
    tax_rates = {
        "CA": 0.0725,
        "NY": 0.04,
        "TX": 0.0625,
        "FL": 0.06,
    }
    rate = tax_rates.get(state, 0.0)
    return amount * rate
 
def process_payment(amount: float, method: str) -> dict:
    """Process payment with given method."""
    # ... implementation ...
    pass
 
# ... many more functions ...
```
 
**Prompt to Claude**:
```
Extract the calculate_tax function from demo_app.py
```
 
**What Claude Does** (visible to user):
```
Using tool: extract_code
├─ file_path: demo_app.py
├─ symbol_name: calculate_tax
├─ symbol_type: function
└─ include_context: true
```
 
**Expected Output**:
```python
def calculate_tax(amount: float, state: str) -> float:
    """Calculate sales tax based on state."""
    tax_rates = {
        "CA": 0.0725,
        "NY": 0.04,
        "TX": 0.0625,
        "FL": 0.06,
    }
    rate = tax_rates.get(state, 0.0)
    return amount * rate
```
 
---
 
### Step 5: The "Aha Moment" - Token Efficiency (90 seconds)
 
**Narration**:
> "Here's the magic. Instead of sending the entire 500-line file to the AI (which would cost ~10,000 tokens), Code Scalpel extracted just the function we needed - only ~50 tokens. That's a 200x reduction in token usage."
 
**Visual Comparison** (show on screen):
 
```
WITHOUT Code Scalpel:
📄 Full file: 500 lines → ~10,000 tokens
💰 Cost: $0.15 per request (at $15/million tokens)
⏱️ Latency: 2-3 seconds to process
 
WITH Code Scalpel:
🎯 Extracted function: 10 lines → ~50 tokens
💰 Cost: $0.0075 per request
⏱️ Latency: 0.1 seconds to extract + process
```
 
**Key Talking Points**:
- ✅ **200x token reduction** for large files
- ✅ **20x cost savings** on AI API calls
- ✅ **Faster responses** - less data to process
- ✅ **Better context** - AI sees only what it needs
 
---
 
### Step 6: Try Another Tool - Analyze Code (60 seconds)
 
**Narration**:
> "Let's try another tool. We'll analyze the entire file to get its structure without executing any code."
 
**Prompt to Claude**:
```
Analyze the structure of demo_app.py
```
 
**Expected Output**:
```json
{
  "file_path": "demo_app.py",
  "language": "python",
  "functions": [
    {"name": "calculate_tax", "line_start": 4, "complexity": 2},
    {"name": "process_payment", "line_start": 15, "complexity": 5}
  ],
  "classes": [],
  "imports": [],
  "total_lines": 500,
  "avg_complexity": 3.5
}
```
 
**Talking Points**:
- ✅ Parse code structure without execution (safe for untrusted code)
- ✅ Get complexity metrics instantly
- ✅ Perfect for code review and understanding
 
---
 
## 🎤 Presentation Tips
 
### For Live Demos:
1. **Pre-install** Code Scalpel to save time
2. **Have config ready** in a text file to paste
3. **Use large demo file** (500+ lines) to show token savings
4. **Show the MCP icon** in Claude Desktop for visual proof
 
### For Recorded Videos:
1. **Screen recording**: Show full installation process
2. **Zoom in** on configuration file for clarity
3. **Use screen annotations** to highlight token savings
4. **Picture-in-picture**: Show your face explaining while demo runs
 
### For Conference Talks:
1. **Start with problem**: "AI code tools read entire files - wasteful"
2. **Show installation**: "One command to solve this"
3. **Live demo**: Extract code in real-time
4. **Reveal savings**: Show token/cost comparison
 
---
 
## ❓ Anticipated Questions & Answers
 
**Q: Does this work with my programming language?**
A: Code Scalpel supports Python, JavaScript, TypeScript, Java, JSX, and TSX out of the box. More languages coming soon.
 
**Q: Do I need to modify my codebase?**
A: No! Code Scalpel works with your existing code. No annotations, no special comments, no changes required.
 
**Q: Can I use this with GitHub Copilot / Cursor / VS Code?**
A: Yes! Code Scalpel implements the MCP protocol, so it works with any MCP-compatible client. Configuration is similar to Claude Desktop.
 
**Q: Is the free tier limited?**
A: The Community (free) tier includes all 19 tools with some limits (50 findings per scan, 1MB file size). Perfect for individual developers and small projects.
 
**Q: What happens if I exceed the limits?**
A: The tool will return results up to the limit and show an "upgrade hint" suggesting the Pro tier. No data loss, just a cap on results.
 
**Q: How do I upgrade to Pro or Enterprise?**
A: Visit https://code-scalpel.dev/pricing to get a license JWT. Add it to your config, and you're upgraded instantly - no reinstall needed.
 
---
 
## 🎁 Demo Files Included
 
- `demo_app.py` - Sample Python application for extraction demo
- `sample_config.json` - Pre-configured MCP server config
- `installation_checklist.md` - Step-by-step setup guide
- `troubleshooting.md` - Common issues and solutions
 
---
 
## 🎯 Success Criteria
 
After this demo, viewers should be able to:
- ✅ Install Code Scalpel in under 2 minutes
- ✅ Configure MCP server in Claude Desktop
- ✅ Make their first tool call successfully
- ✅ Understand the value proposition (token efficiency)
- ✅ Know where to go next (Community features demo)
 
---
 
## 📊 Demo Metrics
 
Track effectiveness:
- Installation success rate (goal: >95%)
- Time to first tool call (goal: <5 minutes)
- Viewer engagement (YouTube retention goal: >70%)
- Click-through to next demo (goal: >40%)
 
---
 
## 🔗 Next Steps
 
After completing this demo, viewers should:
1. ✅ Successfully have Code Scalpel running
2. 🎯 Watch **Demo 2: Community Features** to see all free tier tools
3. 📚 Read the [Full Documentation](https://github.com/3D-Tech-Solutions/code-scalpel)
4. 💬 Join the community (Discord/GitHub Discussions)
 
---
 
**End of Demo 1**
 
*Total time: 5 minutes | Difficulty: Beginner | Setup: Minimal*