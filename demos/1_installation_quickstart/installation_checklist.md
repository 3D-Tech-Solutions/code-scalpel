# Installation Checklist
 
Use this checklist to ensure successful Code Scalpel installation and configuration.
 
## ✅ Pre-Installation
 
- [ ] Python 3.10 or higher installed
  ```bash
  python --version  # Should show 3.10+
  ```
 
- [ ] pip is up to date
  ```bash
  pip install --upgrade pip
  ```
 
- [ ] Claude Desktop installed (or another MCP-compatible client)
  - Download from: https://claude.ai/desktop
 
## ✅ Installation
 
- [ ] Install Code Scalpel
  ```bash
  pip install code-scalpel
  ```
 
- [ ] Verify installation
  ```bash
  python -m code_scalpel --version
  # Expected: Code Scalpel v1.0.0
  ```
 
- [ ] Test MCP server starts
  ```bash
  python -m code_scalpel.mcp --version
  # Expected: MCP Server v1.0.0
  ```
 
## ✅ Configuration
 
- [ ] Locate Claude Desktop config file
  - **macOS**: `~/.claude_desktop_config.json`
  - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
  - **Linux**: `~/.config/claude-desktop/config.json`
 
- [ ] Create config file if it doesn't exist
  ```bash
  # macOS/Linux
  mkdir -p ~/.config/claude-desktop/
  touch ~/.config/claude-desktop/config.json
 
  # Windows (PowerShell)
  New-Item -ItemType File -Path "$env:APPDATA\Claude\claude_desktop_config.json" -Force
  ```
 
- [ ] Add Code Scalpel to config
  ```json
  {
    "mcpServers": {
      "code-scalpel": {
        "command": "python",
        "args": ["-m", "code_scalpel.mcp"],
        "env": {
          "SCALPEL_ROOT": "/absolute/path/to/your/project"
        }
      }
    }
  }
  ```
 
- [ ] Update `SCALPEL_ROOT` to point to your actual project directory
  - Use **absolute paths** (not relative paths like `./` or `~/`)
  - Example (macOS): `/Users/yourname/projects/my-app`
  - Example (Windows): `C:\Users\yourname\projects\my-app`
 
## ✅ First Run
 
- [ ] Restart Claude Desktop completely
  - Quit the application (don't just close the window)
  - Reopen Claude Desktop
 
- [ ] Verify MCP server is connected
  - Look for 🔌 icon in Claude Desktop
  - Check that "code-scalpel" appears in the servers list
  - Status should show "Connected" or "Active"
 
- [ ] Make first tool call
  ```
  Prompt: "List all the tools available in the code-scalpel MCP server"
  ```
 
- [ ] Expected response should include tools like:
  - `extract_code`
  - `analyze_code`
  - `security_scan`
  - `get_project_map`
  - And 15+ more tools
 
## ✅ Test Tool Functionality
 
- [ ] Test `extract_code` tool
  ```
  Prompt: "Extract the calculate_tax function from demo_app.py"
  ```
 
- [ ] Test `analyze_code` tool
  ```
  Prompt: "Analyze the structure of demo_app.py"
  ```
 
- [ ] Verify output looks correct (function code or analysis results)
 
## ✅ Optional: Set Up License (Pro/Enterprise)
 
If you have a Pro or Enterprise license:
 
- [ ] Download your license JWT file
  - From: https://code-scalpel.dev/account/license
 
- [ ] Save license to one of these locations:
  - `.code-scalpel/license.jwt` (in your project root)
  - `~/.config/code-scalpel/license.jwt` (user-wide)
  - `.scalpel-license` (legacy location)
 
- [ ] Or set environment variable in config:
  ```json
  {
    "mcpServers": {
      "code-scalpel": {
        "command": "python",
        "args": ["-m", "code_scalpel.mcp"],
        "env": {
          "SCALPEL_ROOT": "/path/to/project",
          "CODE_SCALPEL_LICENSE_PATH": "/path/to/license.jwt"
        }
      }
    }
  }
  ```
 
- [ ] Restart Claude Desktop
 
- [ ] Verify tier upgrade
  ```
  Prompt: "What tier am I currently using with Code Scalpel?"
  ```
  - Should show "pro" or "enterprise" instead of "community"
 
## ✅ Troubleshooting Quick Check
 
If something doesn't work, check:
 
- [ ] Python version is 3.10+
- [ ] Config file has valid JSON (use a JSON validator)
- [ ] `SCALPEL_ROOT` is an absolute path
- [ ] Claude Desktop was fully restarted
- [ ] No firewall blocking Python
- [ ] Check logs: `~/.claude_desktop/logs/`
 
See `troubleshooting.md` for detailed solutions.
 
## 🎉 Success!
 
If all items are checked, you have successfully installed Code Scalpel!
 
**Next Steps**:
1. 📚 Read the [Full Documentation](https://github.com/3D-Tech-Solutions/code-scalpel)
2. 🎓 Try [Demo 2: Community Features](../2_community_features/)
3. 💬 Join the community for help and tips
 
---
 
**Estimated Time**: 5-10 minutes
**Difficulty**: Beginner
**Support**: https://github.com/3D-Tech-Solutions/code-scalpel/issues