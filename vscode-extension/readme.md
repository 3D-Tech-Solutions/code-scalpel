# Code Scalpel for VS Code

Code Scalpel is a 22-core-tool MCP server toolkit for AI agents, focused on surgical code analysis, security scanning, and intelligent refactoring.

The extension also works with a built-in capability-introspection surface so agents can inspect current tier/license limits without changing the 22-core-tool product count.

## Features

- **MCP Server Integration**: Start/stop the Code Scalpel MCP server directly from VS Code
- **Code Analysis**: Analyze Python, JavaScript, TypeScript, Java, and more
- **Security Scanning**: Detect vulnerabilities, taint flows, and security issues
- **AI-Powered Refactoring**: Works with Claude, GPT, and other LLM agents via MCP protocol

## Requirements

- Python 3.10 or higher
- Code Scalpel Python package (`pip install codescalpel`)

## Installation

1. Install from VS Code Marketplace
2. Install the Python package:
   ```bash
   pip install codescalpel
   ```

## Usage

### Commands

- **Code Scalpel: Start MCP Server** - Start the MCP server
- **Code Scalpel: Stop MCP Server** - Stop the MCP server
- **Code Scalpel: Analyze Current File** - Analyze the active file
- **Code Scalpel: Security Scan Project** - Scan the entire project for vulnerabilities
- **Code Scalpel: Show Server Status** - View server status and tier info

### Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| `codeScalpel.pythonPath` | Path to Python executable | `python` |
| `codeScalpel.serverPort` | MCP server port | `8765` |
| `codeScalpel.autoStart` | Auto-start server on VS Code open | `false` |
| `codeScalpel.tier` | License tier (community/pro/enterprise) | `community` |
| `codeScalpel.licensePath` | Path to license file | (empty) |

## License Tiers

- **Community**: Basic analysis, 50 file limit, standard security scanning
- **Pro**: Unlimited files, advanced refactoring, taint analysis
- **Enterprise**: All Pro features plus compliance, audit trails, approval workflows

## MCP Integration

This extension integrates with the Model Context Protocol (MCP) for AI agent communication. Configure your AI client (Claude Desktop, etc.) to connect to the MCP server:

```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "python",
      "args": ["-m", "code_scalpel.mcp.server"]
    }
  }
}
```

## Support

- [GitHub Issues](https://github.com/3D-Tech-Solutions/code-scalpel/issues)
- [Documentation](https://github.com/3D-Tech-Solutions/code-scalpel#readme)

## License

MIT License - see [LICENSE](https://github.com/3D-Tech-Solutions/code-scalpel/blob/HEAD/LICENSE) for details.
