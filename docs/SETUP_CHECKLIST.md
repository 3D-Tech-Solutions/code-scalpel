# Code Scalpel Setup Checklist

**Follow these steps in order. Check off each box as you go.**

---

## ✅ Pre-Flight Checks

- [ ] I have Python 3.10 or higher installed
  - Check: Open terminal, run `python --version`
  - Not installed? Go to [python.org](https://www.python.org/downloads/)

- [ ] I have one of these AI editors installed:
  - [ ] VS Code + GitHub Copilot
  - [ ] Claude Desktop
  - [ ] Cursor IDE

---

## ✅ Step 1: Install Code Scalpel (Do This Once)

- [ ] Open a terminal (Command Prompt on Windows, Terminal on Mac/Linux)
- [ ] Run: `pip install code-scalpel`
- [ ] Wait for it to finish (you'll see ✓ Successfully installed)

---

## ✅ Step 2: Configure Your AI Editor

### If using VS Code + GitHub Copilot:

- [ ] Open your project in VS Code
- [ ] Create folder `.vscode` (with the dot at the beginning)
- [ ] Create file `.vscode/mcp.json`
- [ ] Copy this into it (replace `YOUR_PROJECT_PATH`):

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
        "YOUR_PROJECT_PATH"
      ],
      "env": {
        "PYTHONPATH": "YOUR_PROJECT_PATH/src",
        "CODE_SCALPEL_LICENSE_PATH": "YOUR_PROJECT_PATH/.code-scalpel/license/license.jwt"
      }
    }
  }
}
```

- [ ] Example: If your project is in `/Users/jane/myproject`, replace `YOUR_PROJECT_PATH` with `/Users/jane/myproject`
- [ ] Save the file

### If using Claude Desktop:

- [ ] Find your config file:
  - Windows: `C:\Users\YourName\AppData\Roaming\Claude\claude_desktop_config.json`
  - Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`
  - Linux: `~/.config/Claude/claude_desktop_config.json`
- [ ] Add this (replace `YOUR_PROJECT_PATH`):

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
        "YOUR_PROJECT_PATH"
      ],
      "env": {
        "PYTHONPATH": "YOUR_PROJECT_PATH/src",
        "CODE_SCALPEL_LICENSE_PATH": "YOUR_PROJECT_PATH/.code-scalpel/license/license.jwt"
      }
    }
  }
}
```

- [ ] Save and close
- [ ] Restart Claude Desktop completely

### If using Cursor:

- [ ] Same as Claude Desktop, but file is at `~/.cursor/mcp.json`

---

## ✅ Step 3: Set Up License (If You Have One)

- [ ] Do you have a license file (`.jwt` file)?
  - [ ] YES: Continue to next step
  - [ ] NO: Skip to Step 4 (Community Edition is free)

If yes:

- [ ] In your project folder, create folder `.code-scalpel` (with the dot)
- [ ] Inside `.code-scalpel`, create folder `license`
- [ ] Move your license file there and rename it to `license.jwt`
- [ ] Final structure should look like:
  ```
  your-project/
    .code-scalpel/
      license/
        license.jwt
  ```

---

## ✅ Step 4: Test It Out

### For VS Code + Copilot:

- [ ] Restart VS Code
- [ ] Open the Chat panel (Ctrl+L or Cmd+L)
- [ ] In a chat message, type: "What tools do you have available?"
- [ ] Copilot should list Code Scalpel tools

### For Claude Desktop:

- [ ] Restart Claude Desktop (close completely, then open again)
- [ ] Create a new conversation
- [ ] Type: "What MCP servers are available?"
- [ ] Claude should mention code-scalpel

### For Cursor:

- [ ] Restart Cursor
- [ ] Open Agent mode (Cmd+K or Ctrl+K)
- [ ] Type: "Use your tools to analyze my code"
- [ ] Cursor Agent should be able to access Code Scalpel

---

## ✅ Step 5: Use It

Ask your AI assistant to:

```
Scan src/api.py for security vulnerabilities using Code Scalpel
```

Or:

```
Extract the login() function from my code
```

Or:

```
Generate unit tests for my payment processing function
```

---

## ⚠️ Common Issues

### "Python not found"
- [ ] Install Python from [python.org](https://www.python.org)
- [ ] On Mac: `brew install python3`
- [ ] On Linux: `sudo apt-get install python3`

### "Code Scalpel not found"
- [ ] Run: `pip install code-scalpel`
- [ ] Wait for it to complete

### "License path not found"
- [ ] Check your license file is at: `your-project/.code-scalpel/license/license.jwt`
- [ ] Or update `CODE_SCALPEL_LICENSE_PATH` in your config file

### "Tools not available in Claude/Copilot"
- [ ] Restart your AI editor (close completely, then reopen)
- [ ] Check `.vscode/mcp.json` path is correct
- [ ] Make sure project path has NO special characters or spaces

### "Server crashes on startup"
- [ ] Check the path in your MCP config
- [ ] Make sure it points to your real project folder
- [ ] Try running: `python -m code_scalpel.mcp.server --help` to test

---

## ✅ You're Done!

Your AI assistant now has access to 22 Code Scalpel tools for analyzing and modifying your code safely.

**Next: Ask your AI assistant to help you!**
