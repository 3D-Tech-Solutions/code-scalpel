# Code Scalpel Beginner's FAQ

**Answers to common questions from people new to Code Scalpel.**

---

## Installation & Setup

### Q: Do I need to be a programmer to use Code Scalpel?

**A:** No! You just need to know how to:
- Open a terminal (Command Prompt on Windows, Terminal on Mac/Linux)
- Copy and paste text into a file
- Edit your AI editor's config file

That's it. No programming knowledge required.

---

### Q: What does "MCP" mean?

**A:** It stands for "Model Context Protocol." Think of it as a standard way for AI assistants to access tools.

In plain English: It's how Claude, Copilot, and Cursor can talk to Code Scalpel.

---

### Q: Python is already installed on my computer. Do I need to do anything special?

**A:** Just run:
```bash
pip install code-scalpel
```

If that doesn't work, type:
```bash
python3 -m pip install code-scalpel
```

---

### Q: What if I don't have Python?

**A:** 
- **Windows:** Download from [python.org](https://www.python.org/downloads/) and run the installer
- **Mac:** Run `brew install python3` (you need Homebrew first)
- **Linux:** Run `sudo apt-get install python3` or `sudo yum install python3`

---

### Q: What does the `.vscode/mcp.json` file do?

**A:** It tells VS Code where Code Scalpel is and how to start it. Think of it as an instruction manual.

---

### Q: I'm on Mac. What does `~` mean in file paths?

**A:** It means "your home directory." So `~/Library/Application Support/Claude/` means:
- Start at your home folder
- Go to Library
- Then Application Support
- Then Claude

---

### Q: Do I need a license to use Code Scalpel?

**A:** No! Code Scalpel comes with a free **Community Edition** that includes:
- All 22 tools
- Unlimited use
- Works offline

If you purchase Pro or Enterprise, you get a license file to unlock extra features.

---

### Q: Where do I get my license file?

**A:** When you purchase Pro or Enterprise, you'll receive a `.jwt` file by email. Ask your account manager if you don't have it.

---

### Q: What if I lose my license file?

**A:** No problem! Code Scalpel still works in Community mode. You just don't get the Pro/Enterprise features.

---

## Troubleshooting

### Q: I get "command not found: python" or "Python is not recognized"

**A:** Python isn't in your system's PATH. Solutions:

**Windows:**
1. Go to [python.org](https://www.python.org/downloads/)
2. Download Python
3. When installing, **CHECK the box that says "Add Python to PATH"**
4. Restart your terminal after installing

**Mac:**
```bash
brew install python3
```

**Linux:**
```bash
sudo apt-get install python3
```

Then restart your terminal.

---

### Q: I get "No module named code_scalpel"

**A:** Code Scalpel isn't installed. Run:
```bash
pip install code-scalpel
```

Or if that doesn't work:
```bash
python3 -m pip install code-scalpel
```

---

### Q: Code Scalpel is installed but Claude/Copilot can't find it

**A:** 

1. **Check your config file exists:**
   - VS Code: Does `.vscode/mcp.json` exist in your project?
   - Claude: Does `claude_desktop_config.json` exist in the right place?

2. **Check the path is correct:**
   - Open `.vscode/mcp.json` or `claude_desktop_config.json`
   - Look for `"--root"` and the path after it
   - Is that path real? Does your project exist there?

3. **Restart your AI editor:**
   - Close it completely (not just the window)
   - Open it again

---

### Q: "License path not found"

**A:** Code Scalpel is looking for your license but can't find it.

**Solution:**

1. Check your project folder structure:
   ```
   your-project/
     .code-scalpel/
       license/
         license.jwt
   ```

2. If your license file is somewhere else, update the `CODE_SCALPEL_LICENSE_PATH` in your config:

   **In `.vscode/mcp.json` or `claude_desktop_config.json`:**
   ```json
   "CODE_SCALPEL_LICENSE_PATH": "/full/path/to/your/license.jwt"
   ```

---

### Q: "The MCP server crashed"

**A:** 

1. **Check your config file for typos:**
   - Open `.vscode/mcp.json` or `claude_desktop_config.json`
   - Look for any red squiggly lines (syntax errors)

2. **Check the path:**
   - Does `--root` point to your real project folder?
   - Is the path spelled correctly?

3. **Try testing from terminal:**
   ```bash
   python -m code_scalpel.mcp.server --help
   ```
   If this prints help text, Code Scalpel works. If you get an error, Code Scalpel isn't installed correctly.

---

### Q: How do I know if Code Scalpel is actually running?

**A:**

1. **In VS Code:** Look for a hammer icon in the bottom status bar (right side)
2. **In Claude Desktop:** Look for the hammer/tool icon next to server names
3. **From terminal:** Run:
   ```bash
   python -m code_scalpel.mcp.server --help
   ```
   You should see help text printed out.

---

### Q: What files should NOT be uploaded to GitHub?

**A:** These files contain sensitive info and should be in your `.gitignore`:

```
.code-scalpel/license/license.jwt
.code-scalpel/audit.log
```

The rest of `.code-scalpel/` is safe to upload.

---

## Using Code Scalpel

### Q: What should I ask my AI assistant to do?

**A:** Examples:

```
"Use Code Scalpel to scan src/payment.py for SQL injection"
"Extract the login() function from my code"
"Generate unit tests for my main function"
"Find everywhere the API_KEY variable is used"
"What does my project structure look like?"
"Is my refactoring safe?"
```

---

### Q: Can Code Scalpel modify my code?

**A:** Yes, but safely. Code Scalpel's tools include:
- `update_symbol` — safely replace a function
- `rename_symbol` — rename a function everywhere
- `simulate_refactor` — test changes before applying them

Your AI assistant can use these, but you always review changes before they're saved.

---

### Q: Is Code Scalpel secure?

**A:** Yes:
- Runs locally on your computer (nothing is sent to servers by default)
- All code analysis happens on your machine
- Your code never leaves your computer
- Open source — anyone can audit it

---

### Q: Why does Code Scalpel need a project root?

**A:** The project root tells Code Scalpel where your code starts. This allows it to:
- Understand all your files together
- Track imports across files
- Understand your project structure

---

### Q: Can I use Code Scalpel on multiple projects?

**A:** Yes! Set up Code Scalpel separately for each project:

1. In each project folder, create `.vscode/mcp.json` (or update `claude_desktop_config.json`)
2. Each config points to its own project root
3. Switch between projects in your AI editor

---

## Upgrading

### Q: How do I update Code Scalpel?

**A:** Run:
```bash
pip install --upgrade code-scalpel
```

---

### Q: Will upgrading break my code?

**A:** No. Code Scalpel only adds features or fixes bugs. It doesn't change how your code works.

---

## Getting Help

### Q: Where do I report a bug?

**A:** [GitHub Issues](https://github.com/3D-Tech-Solutions/code-scalpel/issues) — click "New Issue" and describe what went wrong.

---

### Q: Where can I ask questions?

**A:** [GitHub Discussions](https://github.com/3D-Tech-Solutions/code-scalpel/discussions) — click "New Discussion" and ask away.

---

### Q: How do I give feedback?

**A:** 
- Share feedback on [GitHub Discussions](https://github.com/3D-Tech-Solutions/code-scalpel/discussions)
- Or email: support@codescalpel.dev

---

## I'm Still Stuck

**Try this:**

1. Check you've followed [SETUP_CHECKLIST.md](SETUP_CHECKLIST.md) exactly
2. Search [GitHub Discussions](https://github.com/3D-Tech-Solutions/code-scalpel/discussions) for your question
3. Post a new discussion with:
   - What you're trying to do
   - What error you got
   - Your operating system (Windows/Mac/Linux)
   - Your AI editor (VS Code/Claude/Cursor)

We'll help you get it working!
