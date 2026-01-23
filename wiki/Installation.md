# Installation

Code Scalpel can be installed via pip or run in Docker. Choose the method that best fits your workflow.

## Prerequisites

- **Python 3.10+** (3.11+ recommended for native `tomllib` support)
- **pip** or **uv** package manager
- **Git** (for development installation)

## Quick Install (PyPI)

```bash
# Install from PyPI (when released)
pip install code-scalpel

# Or using uv (faster)
uv pip install code-scalpel
```

## Development Installation

For the latest features or contributions:

```bash
# Clone the repository
git clone https://github.com/3D-Tech-Solutions/code-scalpel.git
cd code-scalpel

# Install in editable mode with dependencies
pip install -e ".[dev]"

# Or using uv
uv pip install -e ".[dev]"
```

## Docker Installation

Run Code Scalpel in an isolated container:

```bash
# Pull the official image
docker pull 3dtechsolutions/code-scalpel:latest

# Run the MCP server (stdio mode)
docker run -i 3dtechsolutions/code-scalpel:latest

# Or use docker-compose
docker-compose up
```

**Custom Docker build:**
```bash
# Build from source
docker build -t code-scalpel:local .

# Run with volume mount for your code
docker run -i -v $(pwd):/workspace code-scalpel:local
```

## Verification

Test that Code Scalpel is installed correctly:

```bash
# Check version
python -m code_scalpel --version

# Run smoke test
python -m pytest tests/ -k "smoke" -v
```

## MCP Configuration

### VS Code / GitHub Copilot

Add to your MCP settings (`.vscode/mcp.json` or global settings):

```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "python",
      "args": ["-m", "code_scalpel.mcp.server"],
      "env": {
        "SCALPEL_PROJECT_ROOT": "${workspaceFolder}"
      }
    }
  }
}
```

### Claude Desktop

Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "python",
      "args": ["-m", "code_scalpel.mcp.server"],
      "env": {
        "SCALPEL_PROJECT_ROOT": "/path/to/your/project"
      }
    }
  }
}
```

### Cursor

Add to Cursor's MCP configuration:

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

## Docker MCP Configuration

For Docker-based deployments:

```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "${workspaceFolder}:/workspace",
        "3dtechsolutions/code-scalpel:latest"
      ],
      "env": {
        "SCALPEL_PROJECT_ROOT": "/workspace"
      }
    }
  }
}
```

## HTTP Server Mode

Run as a standalone HTTP server:

```bash
# Start HTTP server on port 8000
python -m code_scalpel.mcp.server --transport http --port 8000

# Or with Docker
docker run -p 8000:8000 3dtechsolutions/code-scalpel:latest \
  python -m code_scalpel.mcp.server --transport http --port 8000
```

Configure clients to connect to `http://localhost:8000`.

## Dependencies

Code Scalpel requires these core dependencies (automatically installed):

- **tree-sitter** - Multi-language AST parsing
- **esprima** - JavaScript/TypeScript parsing
- **z3-solver** - Symbolic execution (optional, for test generation)
- **fastmcp** - MCP protocol implementation
- **defusedxml** - Safe XML parsing for Maven/Gradle

### Optional Dependencies

```bash
# Install with all optional features
pip install code-scalpel[all]

# Or specific features
pip install code-scalpel[security]  # Enhanced security scanning
pip install code-scalpel[symbolic]  # Symbolic execution & test generation
pip install code-scalpel[dev]       # Development tools
```

## Environment Setup

Create a `.env` file in your project root (see [Configuration](Configuration) for details):

```bash
# Initialize with secure defaults
python -m code_scalpel init

# This creates .env with:
# - SCALPEL_MANIFEST_SECRET (for policy integrity)
# - SCALPEL_PROJECT_ROOT (your project path)
# - Default tier settings
```

## Updating

```bash
# PyPI installation
pip install --upgrade code-scalpel

# Development installation
cd code-scalpel
git pull
pip install -e ".[dev]"

# Docker
docker pull 3dtechsolutions/code-scalpel:latest
```

## Uninstalling

```bash
# Remove package
pip uninstall code-scalpel

# Clean Docker images
docker rmi 3dtechsolutions/code-scalpel:latest
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'code_scalpel'`:

```bash
# Verify installation
pip list | grep code-scalpel

# Reinstall
pip install --force-reinstall code-scalpel
```

### Z3 Solver Issues

Symbolic execution requires Z3. If not installed:

```bash
# Install Z3
pip install z3-solver

# Or skip symbolic features
pip install code-scalpel  # Minimal install
```

### Docker Permission Errors

If you encounter permission issues with mounted volumes:

```bash
# Run with current user
docker run -i --rm \
  -v $(pwd):/workspace \
  -u $(id -u):$(id -g) \
  3dtechsolutions/code-scalpel:latest
```

### Path Issues on Windows

Windows users should use forward slashes in paths:

```json
{
  "env": {
    "SCALPEL_PROJECT_ROOT": "C:/Users/YourName/project"
  }
}
```

---

**Next:** [Getting Started Guide](Getting-Started) →
