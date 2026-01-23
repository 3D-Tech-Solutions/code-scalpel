# Code Scalpel: Complete Beginner's Guide for AI Agents

**For people with NO software development experience who want to use Code Scalpel with their AI assistants (Claude, GitHub Copilot, Cursor).**

---

## What is Code Scalpel?

Code Scalpel is a **bridge between you and your AI assistant**. 

Think of it like this:
- **Without Code Scalpel:** You ask Claude "scan my code for bugs," Claude reads all your files, gets confused, makes mistakes.
- **With Code Scalpel:** You ask Claude "scan my code," Claude uses Code Scalpel's tools to precisely understand your code, finds real bugs.

It's like the difference between asking someone to find a specific book in a library by handing them every book vs. giving them a catalog with exact locations.

---

## Step 1: Start the MCP Server

The "MCP Server" is like a tiny service on your computer that your AI assistant talks to.

### Option A: If you're using VS Code + GitHub Copilot

This is the easiest option. Follow these exact steps:

#### 1a. Open VS Code

Open your project folder in VS Code.

#### 1b. Create the config file

1. In the file explorer on the left, create a new folder: `.vscode` (note the dot at the start)
2. Right-click inside `.vscode` → New File → name it `mcp.json`
3. Paste this exactly (replacing `PATH_TO_YOUR_PROJECT`):

```json
{
  "servers": {
    "code-scalpel": {
      "type": "stdio",
      "command": "python",
      "args": [
        "-m",
        "code_scalpel.mcp.server",
        "--transport",
        "stdio",
        "--root",
        "PATH_TO_YOUR_PROJECT"
      ],
      "env": {
        "PYTHONPATH": "PATH_TO_YOUR_PROJECT/src",
        "CODE_SCALPEL_LICENSE_PATH": "PATH_TO_YOUR_PROJECT/.code-scalpel/license/license.jwt"
      }
    }
  }
}
```

**Example:** If your project is at `/Users/alice/myproject`, change `PATH_TO_YOUR_PROJECT` to `/Users/alice/myproject` (or `C:\Users\alice\myproject` on Windows).

#### 1c. The server starts automatically

That's it! VS Code will automatically start Code Scalpel when you use Copilot.

---

### Option B: If you're using Claude Desktop

#### 2a. Find the config file

- **Windows:** Open `C:\Users\YourUsername\AppData\Roaming\Claude\claude_desktop_config.json`
- **Mac:** Open `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux:** Open `~/.config/Claude/claude_desktop_config.json`

(If the file doesn't exist, create it)

#### 2b. Add Code Scalpel

Paste this into the file:

```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "python",
      "args": [
        "-m",
        "code_scalpel.mcp.server",
        "--transport",
        "stdio",
        "--root",
        "/path/to/your/project"
      ],
      "env": {
        "PYTHONPATH": "/path/to/your/project/src",
        "CODE_SCALPEL_LICENSE_PATH": "/path/to/your/project/.code-scalpel/license/license.jwt"
      }
    }
  }
}
```

Replace `/path/to/your/project` with your actual project path.

#### 2c. Restart Claude Desktop

Close and reopen Claude Desktop. The server will start automatically.

---

### Option C: If you're using Cursor IDE

Same as Option B, but the file is at `~/.cursor/mcp.json` instead.

---

## Step 2: Install Code Scalpel

You only need to do this ONCE.

### If you have Python installed:

Open a terminal and run:

```bash
pip install code-scalpel
```

Done! No restart needed.

**Don't have Python?** 
- Windows: Download from [python.org](https://www.python.org/downloads/)
- Mac: Run `brew install python3` (requires Homebrew)
- Linux: Run `sudo apt-get install python3`

---

## Step 3: Add Your License

Code Scalpel comes with a free **Community Edition** license. If you purchased Pro or Enterprise, you'll get a license file.

### If you have a license file:

1. In your project folder, create a folder: `.code-scalpel` (note the dot at the start)
2. Create a subfolder: `license`
3. Put your license file in `.code-scalpel/license/` and rename it to `license.jwt`

**What it looks like:**
```
your-project/
  .code-scalpel/
    license/
      license.jwt
```

### If you don't have a license file (using Community Edition):

Don't do anything. Code Scalpel automatically runs in Community mode.

---

## Step 4: Use It with Your AI Agent

Now your AI agent can access Code Scalpel's tools.

### In VS Code with Copilot:

1. Open the Chat panel (`Ctrl+L` or `Cmd+L`)
2. Ask questions about your code:

**Examples you can ask:**
- "Scan this file for security vulnerabilities"
- "Extract the `processPayment` function from my code"
- "Show me all places where this variable is used"
- "Generate tests for this function"
- "Is my refactoring safe?"
- "What does my project structure look like?"

### In Claude Desktop:

1. Start a new conversation
2. Attach your project folder (📎 icon)
3. Ask your questions

**Examples:**
- "Use Code Scalpel to scan src/api.py for SQL injection"
- "Extract the login function from my code and explain it"
- "Generate unit tests for my payment processing"

### In Cursor:

Use the Cursor Agent the same way as VS Code Copilot.

---

## Troubleshooting

### "Code Scalpel not found" / "module not found"

**Solution:** Make sure Python and Code Scalpel are installed:
```bash
python --version          # Should show Python 3.10+
python -m pip install code-scalpel
```

### "License not found"

**Solution:** Make sure your license file is at:
```
your-project/.code-scalpel/license/license.jwt
```

Or set the path manually in your MCP config in step 1.

### The server crashes / won't start

**Solution:** Check that the path in your MCP config is correct. It should point to your actual project folder.

### "Code Scalpel tools not available" in Claude/Copilot

**Solution:**
1. Restart your AI assistant (close and reopen)
2. Check that the MCP config file is in the right place
3. Open a terminal and run: `python -m code_scalpel.mcp.server --help` — it should print help text

---

## What Can Code Scalpel Do?

Your AI agent can now ask Code Scalpel to:

### 🔍 Understand Your Code
- Analyze code structure (functions, classes, complexity)
- Extract specific functions without reading the whole file
- Find where a variable is used
- Understand cross-file dependencies

### 🔒 Find Security Issues
- Detect SQL injection vulnerabilities
- Find XSS (cross-site scripting) bugs
- Detect command injection risks
- Check dependencies for known CVEs
- Track how user input flows through your code

### ✏️ Safely Modify Code
- Rename a function across your entire project
- Extract code into a new function
- Verify that refactoring doesn't break anything

### 🧪 Generate Tests
- Automatically create unit tests
- Explore edge cases your code might miss

### 📊 Understand Your Project
- Generate a project map showing structure
- Find circular dependencies
- Measure code complexity

---

## Next Steps

- **Learn the tools:** Read [Tool Reference](../../docs/reference/mcp_tools_current.md)
- **Advanced setup:** [MCP Server Configuration](../../docs/deployment/mcp_server_setup.md)
- **Developers:** [Contributing Guide](../../CONTRIBUTING.md)

---

## Getting Help

- **Stuck?** Check the [FAQ](../../docs/getting_started/faq.md)
- **Found a bug?** [Report it on GitHub](https://github.com/3D-Tech-Solutions/code-scalpel/issues)
- **Have a question?** [Start a discussion](https://github.com/3D-Tech-Solutions/code-scalpel/discussions)
