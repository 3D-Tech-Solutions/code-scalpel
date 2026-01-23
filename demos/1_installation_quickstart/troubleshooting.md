# Troubleshooting Guide
 
Common issues and solutions for Code Scalpel MCP server installation.
 
---
 
## 🔍 General Debugging
 
### Check Logs
 
**Claude Desktop Logs**:
- **macOS**: `~/.claude_desktop/logs/`
- **Windows**: `%APPDATA%\Claude\logs\`
- **Linux**: `~/.config/claude-desktop/logs/`
 
Look for errors mentioning "code-scalpel" or "MCP".
 
**Code Scalpel Logs**:
```bash
# Enable debug logging
export CODE_SCALPEL_LOG_LEVEL=DEBUG
python -m code_scalpel.mcp
```
 
---
 
## ❌ Problem: "MCP server not showing up in Claude Desktop"
 
### Solution 1: Check Configuration File
 
**Verify the config file exists**:
```bash
# macOS/Linux
cat ~/.claude_desktop_config.json
 
# Windows (PowerShell)
Get-Content "$env:APPDATA\Claude\claude_desktop_config.json"
```
 
**Validate JSON syntax**:
- Use https://jsonlint.com/ to check for syntax errors
- Common mistakes:
  - Missing comma between entries
  - Trailing comma after last entry
  - Unescaped backslashes in Windows paths
 
**Correct format**:
```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "python",
      "args": ["-m", "code_scalpel.mcp"],
      "env": {
        "SCALPEL_ROOT": "/absolute/path/to/project"
      }
    }
  }
}
```
 
### Solution 2: Restart Properly
 
**Full restart required**:
1. Completely quit Claude Desktop (not just close window)
2. On macOS: Cmd+Q
3. On Windows: Right-click taskbar icon → Exit
4. Wait 5 seconds
5. Reopen Claude Desktop
 
### Solution 3: Check Python Command
 
**Verify Python is accessible**:
```bash
# Try both python and python3
python --version
python3 --version
 
# Test if Code Scalpel module is found
python -m code_scalpel --version
python3 -m code_scalpel --version
```
 
**If python3 works but python doesn't**, update config:
```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "python3",  // Changed from "python"
      "args": ["-m", "code_scalpel.mcp"]
    }
  }
}
```
 
---
 
## ❌ Problem: "Code Scalpel installed but command not found"
 
### Solution: Check Python PATH
 
**Verify installation**:
```bash
pip show code-scalpel
```
 
**Expected output**:
```
Name: code-scalpel
Version: 1.0.0
Location: /path/to/site-packages
```
 
**If not installed**:
```bash
# Reinstall with explicit pip
python -m pip install code-scalpel
 
# Or use pip3
pip3 install code-scalpel
```
 
**If installed but not found**:
```bash
# Add to PATH (macOS/Linux)
export PATH="$HOME/.local/bin:$PATH"
 
# Or use full path in config
{
  "mcpServers": {
    "code-scalpel": {
      "command": "/usr/bin/python3",  // Full path
      "args": ["-m", "code_scalpel.mcp"]
    }
  }
}
```
 
---
 
## ❌ Problem: "Permission Denied" or "Access Denied"
 
### Solution 1: Install for User (not system-wide)
 
```bash
# Install in user directory (no sudo needed)
pip install --user code-scalpel
```
 
### Solution 2: Use Virtual Environment
 
```bash
# Create virtual environment
python -m venv code-scalpel-env
 
# Activate it
# macOS/Linux:
source code-scalpel-env/bin/activate
# Windows:
code-scalpel-env\Scripts\activate
 
# Install in virtual environment
pip install code-scalpel
 
# Update config with venv python path
{
  "mcpServers": {
    "code-scalpel": {
      "command": "/path/to/code-scalpel-env/bin/python",
      "args": ["-m", "code_scalpel.mcp"]
    }
  }
}
```
 
### Solution 3: Check File Permissions
 
```bash
# macOS/Linux: Fix config file permissions
chmod 644 ~/.claude_desktop_config.json
 
# Fix directory permissions
chmod 755 ~/.config/claude-desktop/
```
 
---
 
## ❌ Problem: "SCALPEL_ROOT not found" or "Invalid path"
 
### Solution: Use Absolute Paths
 
**❌ Wrong** (relative paths):
```json
{
  "env": {
    "SCALPEL_ROOT": "./my-project"      // ❌ Doesn't work
  }
}
```
 
```json
{
  "env": {
    "SCALPEL_ROOT": "~/projects/my-app" // ❌ ~ not expanded
  }
}
```
 
**✅ Correct** (absolute paths):
```json
{
  "env": {
    "SCALPEL_ROOT": "/Users/yourname/projects/my-app"  // ✅ macOS/Linux
  }
}
```
 
```json
{
  "env": {
    "SCALPEL_ROOT": "C:\\Users\\yourname\\projects\\my-app"  // ✅ Windows
  }
}
```
 
**Get absolute path**:
```bash
# macOS/Linux
cd /path/to/your/project
pwd
# Copy the output
 
# Windows (PowerShell)
cd C:\path\to\your\project
Get-Location
# Copy the output
```
 
---
 
## ❌ Problem: "Tool call failed" or "No response from server"
 
### Solution 1: Check Server is Running
 
**Test server manually**:
```bash
cd /path/to/your/project
export SCALPEL_ROOT=$(pwd)
python -m code_scalpel.mcp
 
# Should show:
# MCP Server started
# Listening for connections...
```
 
**If it crashes immediately**, check error message:
- Python version too old? (need 3.10+)
- Missing dependencies? Run `pip install code-scalpel[all]`
- Port already in use? (if using HTTP transport)
 
### Solution 2: Increase Timeout
 
**Add timeout to config**:
```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "python",
      "args": ["-m", "code_scalpel.mcp"],
      "env": {
        "SCALPEL_ROOT": "/path/to/project"
      },
      "timeout": 30000  // 30 seconds (default is 10)
    }
  }
}
```
 
### Solution 3: Check File Sizes
 
**Community tier limits**:
- Max file size: 1MB
- Max findings: 50
 
**If your files are larger**:
- Upgrade to Pro tier (10MB limit)
- Or split analysis into smaller chunks
 
---
 
## ❌ Problem: "Invalid license" or "License expired"
 
### Solution 1: Check License File Location
 
**Valid locations** (checked in order):
1. `.code-scalpel/license.jwt` (project root)
2. `~/.config/code-scalpel/license.jwt` (user-wide)
3. `.scalpel-license` (legacy)
4. Path in `CODE_SCALPEL_LICENSE_PATH` env var
 
**Verify file exists**:
```bash
# Check project license
ls -la .code-scalpel/license.jwt
 
# Check user license
ls -la ~/.config/code-scalpel/license.jwt
```
 
### Solution 2: Validate License JWT
 
**Check license expiration**:
```bash
python -c "
import jwt
import json
 
with open('.code-scalpel/license.jwt', 'r') as f:
    token = f.read()
 
# Decode without verification to see claims
decoded = jwt.decode(token, options={'verify_signature': False})
print(json.dumps(decoded, indent=2))
"
```
 
**Look for**:
- `exp`: Expiration timestamp (Unix time)
- `tier`: Should be "pro" or "enterprise"
- `iat`: Issued at timestamp
 
### Solution 3: Re-download License
 
1. Log in to https://code-scalpel.dev/account
2. Download fresh license JWT
3. Save to one of the valid locations
4. Restart Claude Desktop
 
---
 
## ❌ Problem: "Windows path issues" or "Backslash errors"
 
### Solution: Escape Backslashes
 
**In JSON, backslashes must be doubled**:
 
**❌ Wrong**:
```json
{
  "env": {
    "SCALPEL_ROOT": "C:\Users\yourname\project"  // ❌ Invalid JSON
  }
}
```
 
**✅ Correct**:
```json
{
  "env": {
    "SCALPEL_ROOT": "C:\\Users\\yourname\\project"  // ✅ Escaped
  }
}
```
 
**Alternative: Use forward slashes** (works on Windows):
```json
{
  "env": {
    "SCALPEL_ROOT": "C:/Users/yourname/project"  // ✅ Also valid
  }
}
```
 
---
 
## ❌ Problem: "Python version too old"
 
### Solution: Upgrade Python
 
**Check current version**:
```bash
python --version
```
 
**Required**: Python 3.10 or higher
 
**Install newer Python**:
- **macOS**: `brew install python@3.11`
- **Windows**: Download from https://python.org
- **Linux**: `sudo apt install python3.11` (Ubuntu/Debian)
 
**Update config to use new Python**:
```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "/usr/local/bin/python3.11",  // Full path to new version
      "args": ["-m", "code_scalpel.mcp"]
    }
  }
}
```
 
---
 
## ❌ Problem: "Import Error: No module named 'code_scalpel'"
 
### Solution: Check Installation Location
 
**Issue**: Python in config is different from where you installed
 
**Debug**:
```bash
# Which Python was used for installation?
which python
which pip
 
# Where is code-scalpel installed?
pip show code-scalpel | grep Location
 
# Test if importable
python -c "import code_scalpel; print('OK')"
```
 
**Fix**: Use same Python for both install and config
 
```bash
# Install with specific Python
python3.11 -m pip install code-scalpel
 
# Update config to match
{
  "command": "python3.11",  // Same as install
  "args": ["-m", "code_scalpel.mcp"]
}
```
 
---
 
## ❌ Problem: "Connection timeout" or "Server not responding"
 
### Solution 1: Check Firewall
 
**Allow Python through firewall**:
- **macOS**: System Preferences → Security → Firewall → Allow Python
- **Windows**: Windows Defender Firewall → Allow an app → Add Python
 
### Solution 2: Disable Antivirus Temporarily
 
Some antivirus software blocks MCP connections.
 
**Test without antivirus**:
1. Temporarily disable antivirus
2. Restart Claude Desktop
3. Test if server connects
4. If it works, add exception for Python/Claude Desktop
 
### Solution 3: Use Stdio Transport (Default)
 
**MCP supports multiple transports**. Stdio is most reliable.
 
**Verify your config uses stdio** (default):
```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "python",
      "args": ["-m", "code_scalpel.mcp"]
      // No "transport" key = stdio (good!)
    }
  }
}
```
 
**If you're using HTTP and having issues**, switch to stdio:
```json
// Remove these if present:
"transport": "http",
"port": 8080
```
 
---
 
## 🆘 Still Having Issues?
 
### Get Help
 
1. **GitHub Issues**: https://github.com/3D-Tech-Solutions/code-scalpel/issues
   - Search existing issues first
   - Provide full error message
   - Include Python version, OS, config file
 
2. **Discord Community**: [Link to Discord]
   - Real-time help from community
   - Share screenshots
 
3. **Email Support**: support@code-scalpel.dev
   - For Pro/Enterprise customers
   - Include license ID
 
### Include This Info
 
When asking for help, provide:
 
```
1. Python version: `python --version`
2. Code Scalpel version: `pip show code-scalpel`
3. Operating System: macOS/Windows/Linux + version
4. Config file: (paste your .claude_desktop_config.json)
5. Error message: (full text from logs)
6. Steps to reproduce: What you did when error occurred
```
 
---
 
## 📚 Additional Resources
 
- 📖 [Full Documentation](https://github.com/3D-Tech-Solutions/code-scalpel)
- 🎥 [Video Tutorials](https://youtube.com/@code-scalpel)
- 💬 [Community Forum](https://github.com/3D-Tech-Solutions/code-scalpel/discussions)
- 🐛 [Report a Bug](https://github.com/3D-Tech-Solutions/code-scalpel/issues/new)
 
---
 
**Last Updated**: 2026-01-19
**Applies to**: Code Scalpel v1.0.0+