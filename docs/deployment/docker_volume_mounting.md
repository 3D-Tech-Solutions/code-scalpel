# Docker Volume Mounting Guide

**Version:** v1.5.3  
**Feature:** PathSmart - Intelligent Path Resolution  
**Last Updated:** December 14, 2025

---

## Overview

Code Scalpel v1.5.3 introduces intelligent path resolution that automatically detects Docker environments and provides actionable guidance when files cannot be accessed. This guide explains how to configure Docker volume mounts for seamless file-based operations.

### Why Volume Mounts Matter

When the MCP server runs in a Docker container, it can only access files that are:
1. Built into the container image
2. Mounted via Docker volumes
3. Created inside the container

**Without proper volume mounts, file-based MCP tools will fail with "File not found" errors.**

---

## Quick Start

### Basic Volume Mount

Mount your project directory to `/workspace`:

```bash
docker run -v /path/to/your/project:/workspace code-scalpel:latest
```

**Example:**
```bash
# Mount current directory
docker run -v $(pwd):/workspace ghcr.io/3dtech-solutions/code-scalpel:latest

# Mount specific project
docker run -v /home/user/myapp:/workspace ghcr.io/3dtech-solutions/code-scalpel:latest
```

### Verify Mount

Use the `validate_paths` MCP tool to check accessibility:

```python
# MCP tool call
result = validate_paths([
    "/workspace/main.py",
    "/workspace/src/utils.py"
])

if result.success:
    print("All paths accessible!")
else:
    print("Inaccessible paths:", result.inaccessible)
    print("Suggestions:", result.suggestions)
```

---

## Docker Compose Configuration

### Basic Setup

```yaml
version: '3.8'

services:
  code-scalpel:
    image: ghcr.io/3dtech-solutions/code-scalpel:latest
    volumes:
      - ./:/workspace  # Mount current directory
    environment:
      - WORKSPACE_ROOT=/workspace
    stdin_open: true
    tty: true
```

### Multi-Project Setup

```yaml
version: '3.8'

services:
  code-scalpel:
    image: ghcr.io/3dtech-solutions/code-scalpel:latest
    volumes:
      - ./project1:/workspace/project1
      - ./project2:/workspace/project2
      - ./shared:/workspace/shared
    environment:
      - WORKSPACE_ROOT=/workspace
```

---

## Common Scenarios

### Scenario 1: Local Development

**Goal:** Analyze code on your local machine using containerized Code Scalpel.

**Solution:**
```bash
# Navigate to your project
cd /home/user/myproject

# Run with current directory mounted
docker run -it \
  -v $(pwd):/workspace \
  -e WORKSPACE_ROOT=/workspace \
  ghcr.io/3dtech-solutions/code-scalpel:latest
```

**Verify:**
```bash
# Inside container, run MCP tool
python -c "
from code_scalpel.mcp.path_resolver import resolve_path
print(resolve_path('main.py', '/workspace'))
"
```

### Scenario 2: CI/CD Pipeline

**Goal:** Run Code Scalpel in GitHub Actions or GitLab CI.

**GitHub Actions Example:**
```yaml
name: Code Analysis
on: [push]

jobs:
  analyze:
    runs-on: ubuntu-latest
    container:
      image: ghcr.io/3dtech-solutions/code-scalpel:latest
      options: -v ${{ github.workspace }}:/workspace
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Analyze Code
        run: |
          python -m code_scalpel.mcp.server --transport stdio
```

**GitLab CI Example:**
```yaml
analyze:
  image: ghcr.io/3dtech-solutions/code-scalpel:latest
  script:
    - cd /workspace
    - python -m code_scalpel.mcp.server --transport stdio
  volumes:
    - $CI_PROJECT_DIR:/workspace
```

### Scenario 3: Remote Development

**Goal:** Run Code Scalpel on a remote server, analyze code via HTTP.

**Solution:**
```bash
# On remote server
docker run -d \
  -v /data/projects:/workspace \
  -p 8080:8080 \
  --name code-scalpel \
  ghcr.io/3dtech-solutions/code-scalpel:latest \
  python -m code_scalpel.mcp.server \
    --transport streamable-http \
    --host 0.0.0.0 \
    --port 8080 \
    --allow-lan
```

**Security Note:** Only use `--allow-lan` on trusted networks!

### Scenario 4: Multiple Projects

**Goal:** Analyze multiple projects without changing mounts.

**Solution:**
```bash
# Mount parent directory containing all projects
docker run -it \
  -v /home/user/projects:/workspace \
  ghcr.io/3dtech-solutions/code-scalpel:latest

# Inside container, projects are accessible:
# /workspace/project1/
# /workspace/project2/
# /workspace/project3/
```

**Use `project_root` parameter:**
```python
# Extract code from project1
extract_code(
    file_path="main.py",
    target_type="function",
    target_name="process_data",
    project_root="/workspace/project1"
)

# Extract code from project2
extract_code(
    file_path="app.py",
    target_type="class",
    target_name="Server",
    project_root="/workspace/project2"
)
```

---

## Troubleshooting

### Error: "File not found: /host/path/to/file.py"

**Cause:** The file path references your host filesystem, but the Docker container cannot access it.

**Solution 1: Mount the directory**
```bash
docker run -v /host/path:/workspace code-scalpel:latest
```

**Solution 2: Use relative paths**
```python
# Instead of absolute host paths
extract_code(file_path="/home/user/project/main.py", ...)  # INCORRECT: Won't work

# Use paths relative to mounted workspace
extract_code(file_path="main.py", ...)  # CORRECT: Works with volume mount
```

### Error: "Attempted locations: /workspace, /app/code, /app"

**Cause:** PathResolver searched all workspace roots but couldn't find the file.

**Check mount configuration:**
```bash
# Inspect container mounts
docker inspect <container_id> | grep -A10 Mounts

# Verify files inside container
docker exec <container_id> ls -la /workspace
```

**Set explicit workspace root:**
```bash
docker run \
  -v $(pwd):/mycode \
  -e WORKSPACE_ROOT=/mycode \
  code-scalpel:latest
```

### Suggestion: "Mount your project with -v"

**Cause:** PathResolver detected Docker environment and knows the file isn't accessible.

**Follow the suggestion:**
```bash
# PathResolver might suggest:
# docker run -v /home/user/project:/workspace ... <image>

# Execute that command
docker run -v /home/user/project:/workspace ghcr.io/3dtech-solutions/code-scalpel:latest
```

### Permission Denied Errors

**Cause:** Container user doesn't have permission to read mounted files.

**Solution 1: Run as current user**
```bash
docker run \
  --user $(id -u):$(id -g) \
  -v $(pwd):/workspace \
  code-scalpel:latest
```

**Solution 2: Fix file permissions**
```bash
# On host
chmod -R a+r /path/to/project

# Or grant write access if needed
chmod -R a+rw /path/to/project
```

### Read-Only Mounts

**For safety, mount read-only:**
```bash
docker run \
  -v $(pwd):/workspace:ro \
  code-scalpel:latest
```

**Note:** Code Scalpel only reads files for analysis, never writes, so `:ro` is safe and recommended.

---

## Environment Variables

### WORKSPACE_ROOT

Override default workspace root detection:

```bash
docker run \
  -v /custom/path:/mycode \
  -e WORKSPACE_ROOT=/mycode \
  code-scalpel:latest
```

**Effect:** PathResolver will search `/mycode` first.

### PROJECT_ROOT

Alternative to WORKSPACE_ROOT (lower priority):

```bash
docker run \
  -v /project:/code \
  -e PROJECT_ROOT=/code \
  code-scalpel:latest
```

### Multiple Roots

PathResolver checks (in order):
1. `WORKSPACE_ROOT` (if set)
2. `PROJECT_ROOT` (if set)
3. Current working directory
4. `/workspace`
5. `/app/code`
6. `/app`

**Custom multi-root setup:**
```bash
docker run \
  -v /project1:/p1 \
  -v /project2:/p2 \
  -e WORKSPACE_ROOT=/p1:/p2 \
  code-scalpel:latest
```

---

## Best Practices

### 1. Always Mount to `/workspace`

**Recommended:**
```bash
docker run -v $(pwd):/workspace code-scalpel:latest
```

**Why:** PathResolver detects `/workspace` as a standard mount point.

### 2. Use Absolute Paths for Mounts

**Good:**
```bash
docker run -v /home/user/project:/workspace code-scalpel:latest
```

**Better:**
```bash
docker run -v $(pwd):/workspace code-scalpel:latest
```

**Avoid:**
```bash
docker run -v ./project:/workspace code-scalpel:latest  # Might fail
```

### 3. Test Paths Before Analysis

```python
# Always validate first
result = validate_paths([
    "main.py",
    "src/utils.py",
    "tests/test_main.py"
])

if not result.success:
    print("Fix these paths:", result.inaccessible)
    exit(1)

# Proceed with analysis
extract_code(file_path="main.py", ...)
```

### 4. Use `project_root` Parameter

**When analyzing specific project:**
```python
extract_code(
    file_path="main.py",
    project_root="/workspace/myproject",
    ...
)
```

**Why:** Speeds up path resolution and avoids ambiguity.

### 5. Read-Only Mounts for Safety

```bash
docker run -v $(pwd):/workspace:ro code-scalpel:latest
```

**Why:** Code Scalpel only needs read access for analysis.

---

## Docker Compose Complete Example

```yaml
version: '3.8'

services:
  code-scalpel:
    image: ghcr.io/3dtech-solutions/code-scalpel:latest
    container_name: code-scalpel-server
    
    # Mount current directory
    volumes:
      - ./:/workspace:ro  # Read-only for safety
    
    # Environment configuration
    environment:
      - WORKSPACE_ROOT=/workspace
      - SCALPEL_CACHE_ENABLED=1
    
    # For stdio transport
    stdin_open: true
    tty: true
    
    # Or for HTTP transport
    # ports:
    #   - "8080:8080"
    # command: >
    #   python -m code_scalpel.mcp.server
    #   --transport streamable-http
    #   --host 0.0.0.0
    #   --port 8080
    
    # Resource limits
    mem_limit: 2g
    cpus: 2.0
    
    # Restart policy
    restart: unless-stopped
```

**Usage:**
```bash
# Start the service
docker-compose up -d

# Check logs
docker-compose logs -f

# Execute MCP operations
docker-compose exec code-scalpel python -m code_scalpel.cli analyze /workspace/main.py

# Stop the service
docker-compose down
```

---

## Integration with MCP Clients

### Claude Desktop

**Config:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v",
        "/path/to/your/project:/workspace",
        "ghcr.io/3dtech-solutions/code-scalpel:latest",
        "python",
        "-m",
        "code_scalpel.mcp.server"
      ]
    }
  }
}
```

### VS Code with Copilot

**.vscode/settings.json:**
```json
{
  "mcp.servers": {
    "code-scalpel": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v",
        "${workspaceFolder}:/workspace",
        "ghcr.io/3dtech-solutions/code-scalpel:latest",
        "python",
        "-m",
        "code_scalpel.mcp.server"
      ]
    }
  }
}
```

---

## Advanced: Custom Dockerfile

For projects with specific dependencies:

```dockerfile
FROM ghcr.io/3dtech-solutions/code-scalpel:latest

# Install additional tools
RUN pip install mypy black

# Set custom workspace
WORKDIR /workspace

# Copy project-specific config
COPY .code-scalpel.conf /etc/scalpel.conf

# Environment variables
ENV WORKSPACE_ROOT=/workspace
ENV PYTHONPATH=/workspace

# Entrypoint
ENTRYPOINT ["python", "-m", "code_scalpel.mcp.server"]
```

**Build and run:**
```bash
docker build -t my-code-scalpel .
docker run -v $(pwd):/workspace my-code-scalpel
```

---

## Security Considerations

### 1. Bind Mounts vs Volumes

**Bind Mounts (Recommended):**
```bash
docker run -v /host/path:/container/path code-scalpel:latest
```
- Direct access to host filesystem
- Good for development
- Read-only recommended: `-v $(pwd):/workspace:ro`

**Docker Volumes:**
```bash
docker volume create scalpel-data
docker run -v scalpel-data:/workspace code-scalpel:latest
```
- Managed by Docker
- Better for production
- Isolated from host

### 2. Network Security

**stdio transport (default):**
- No network exposure
- Most secure
- Use for local development

**HTTP transport:**
```bash
# Localhost only (secure)
docker run -p 127.0.0.1:8080:8080 code-scalpel:latest \
  python -m code_scalpel.mcp.server --transport streamable-http

# LAN access (use with caution!)
docker run -p 0.0.0.0:8080:8080 code-scalpel:latest \
  python -m code_scalpel.mcp.server \
    --transport streamable-http \
    --allow-lan
```

### 3. User Permissions

**Run as non-root:**
```bash
docker run \
  --user 1000:1000 \
  -v $(pwd):/workspace \
  code-scalpel:latest
```

---

## Summary

### Key Takeaways

1. **Always mount your project directory**
   - Recommended mount point: `/workspace`
   - Use absolute paths or `$(pwd)`

2. **Use `validate_paths` first**
   - Check accessibility before expensive operations
   - Get actionable error messages

3. **Set `WORKSPACE_ROOT` for clarity**
   - Helps PathResolver find files faster
   - Reduces ambiguity

4. **Use read-only mounts**
   - Code Scalpel only reads, never writes
   - Safer for production

5. **Test your configuration**
   - Verify mounts with `docker exec`
   - Use PathResolver's helpful error messages

### Getting Help

If you encounter path issues:
1. Check error message suggestions
2. Use `validate_paths` MCP tool
3. Inspect container mounts: `docker inspect <container>`
4. Review logs: `docker logs <container>`
5. Open issue: [github.com/3D-Tech-Solutions/code-scalpel/issues](https://github.com/3D-Tech-Solutions/code-scalpel/issues)

---

**v1.5.3 Feature:** Intelligent path resolution with Docker-aware error messages and automatic workspace detection.
