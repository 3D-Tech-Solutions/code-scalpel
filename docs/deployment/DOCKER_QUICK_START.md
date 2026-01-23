# Code Scalpel v3.0.0 - Docker Deployment Quick Start

**Release Date:** December 18, 2025  
**Version:** 3.0.0  
**Docker Image:** code-scalpel:3.0.0  
**Status:** FULLY DEPLOYED AND TESTED

## One-Command Quick Start

```bash
# Single command to get Code Scalpel running (HTTP)
docker run -d \
  --name code-scalpel-mcp \
  -p 8593:8593 \
  -v $(pwd):/workspace \
  code-scalpel:3.0.0

# Verify it's running
curl http://localhost:8593/sse

# Connect your MCP client to: http://localhost:8593
```

## HTTPS Quick Start (For Claude API / Production)

```bash
# Generate self-signed certificates (or use your own)
mkdir -p certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout certs/key.pem -out certs/cert.pem \
  -subj "/CN=localhost"

# Run with HTTPS enabled
docker run -d \
  --name code-scalpel-mcp-https \
  -p 8443:8593 \
  -v $(pwd):/workspace \
  -v $(pwd)/certs:/certs:ro \
  -e SSL_CERT=/certs/cert.pem \
  -e SSL_KEY=/certs/key.pem \
  code-scalpel:3.0.0

# Verify HTTPS is working
curl -k https://localhost:8443/sse

# Connect Claude API to: https://localhost:8443
```

## What's New in v3.0.0

### Key Features

1. **22 MCP Tools** - Full tool suite with policy and governance:
   - All tools from v2.0.0 plus new policy/governance tools
   - `unified_sink_detect`, `get_graph_neighborhood`, `verify_policy_integrity`
   - Complete test coverage (4,033 tests, 94.86% coverage)

2. **HTTPS/SSL Support** - Production-ready secure connections:
   - Mount SSL certificates to enable HTTPS
   - Required for Claude API integration
   - Self-signed or CA-signed certificates supported

2. **Full Float Support** - Symbolic execution now handles floats:
   - Float constants (3.14159)
   - Float function parameters
   - Mixed int/float arithmetic

3. **Intelligent Path Resolution** - PathResolver module handles paths across:
   - Local development environments
   - Docker containers (auto-detected)
   - Remote systems
   - Multi-project workspaces

4. **Docker-Aware Error Messages** - When files aren't found, get helpful suggestions:
   ```
   Suggestion: Mount your project root:
     docker run -v /path/to/project:/workspace code-scalpel:3.0.0
   ```

5. **validate_paths MCP Tool** - Check path accessibility before analysis:
   ```python
   # Check multiple paths at once
   result = validate_paths(["/workspace/main.py", "/workspace/utils.py"])
   if not result.success:
       print(f"Inaccessible: {result.inaccessible}")
   ```

## Deployment Options

### Option 1: Simple Docker Run (HTTP - Local Development)

```bash
docker run -d \
  --name code-scalpel-mcp \
  -p 8593:8593 \
  -v $(pwd):/workspace \
  code-scalpel:3.0.0
```

### Option 2: HTTPS with Docker Run (Production / Claude API)

```bash
# Step 1: Create certificates directory and generate certs
mkdir -p certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout certs/key.pem -out certs/cert.pem \
  -subj "/CN=your-domain.com"

# Step 2: Run with HTTPS
docker run -d \
  --name code-scalpel-mcp-https \
  -p 8443:8593 \
  -p 8444:8594 \
  -v $(pwd):/workspace \
  -v $(pwd)/certs:/certs:ro \
  -e SSL_CERT=/certs/cert.pem \
  -e SSL_KEY=/certs/key.pem \
  code-scalpel:3.0.0

# Connect Claude to: https://your-domain.com:8443
```

### Option 3: Docker Compose (HTTP)

```bash
# Using included docker-compose.yml
docker compose up -d mcp-server

# Or specify workspace directory
CODE_SCALPEL_WORKSPACE=/path/to/project docker compose up -d mcp-server

# View logs
docker compose logs -f mcp-server

# Stop services
docker compose down
```

### Option 4: Docker Compose (HTTPS)

```bash
# Set up certificates first
mkdir -p certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout certs/key.pem -out certs/cert.pem \
  -subj "/CN=localhost"

# Start HTTPS server
SSL_CERT_DIR=./certs docker compose up -d mcp-server-https

# Connect to: https://localhost:8443
```

### Option 5: Custom Port with HTTPS

```bash
docker run -d \
  -p 443:8593 \
  -v /path/to/project:/workspace \
  -v /etc/letsencrypt/live/yourdomain.com:/certs:ro \
  -e SSL_CERT=/certs/fullchain.pem \
  -e SSL_KEY=/certs/privkey.pem \
  code-scalpel:3.0.0

# Connect to: https://yourdomain.com
```

### Option 6: With Resource Limits

```bash
docker run -d \
  --name code-scalpel-mcp \
  -p 8593:8593 \
  --memory=2g \
  --cpus=2 \
  -v $(pwd):/workspace \
  code-scalpel:1.5.3
```

## Verify Deployment

### Quick Health Check

```bash
# Check container is running
docker ps | grep code-scalpel-mcp

# Should show: Up X seconds (health: starting/healthy)
```

### Test MCP Endpoint

```bash
# Test SSE endpoint
curl http://localhost:8593/sse

# Should return: 
# HTTP/1.1 200 OK
# content-type: text/event-stream
```

### Verify PathResolver

```bash
# Check Docker detection
docker exec code-scalpel-mcp python3 -c \
  "from code_scalpel.mcp.path_resolver import PathResolver; \
   pr = PathResolver(); \
   print(f'Docker: {pr.is_docker}, Workspace: {pr.workspace_root}')"

# Should show:
# Docker: True, Workspace: /workspace
```

### Test a Tool

```bash
# Test validate_paths tool
docker exec code-scalpel-mcp python3 << 'EOF'
from code_scalpel.mcp.path_resolver import PathResolver
pr = PathResolver()
result = pr.resolve_path("test.py", project_root="/workspace")
print(f"Path resolution available: True")
EOF
```

## Connecting Your MCP Client

### Claude Desktop

Add to `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "curl",
      "args": ["--http2-prior-knowledge", "http://localhost:8593"],
      "disabled": false
    }
  }
}
```

### VS Code Copilot / Cursor

Set MCP server configuration:
- **Host:** localhost
- **Port:** 8593
- **Protocol:** HTTP (streamable-http)

### Python Script

```python
import httpx

async def analyze_code(file_path):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8593",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "analyze_code",
                    "arguments": {"file_path": file_path}
                }
            }
        )
        return response.json()
```

## Common Tasks

### View Container Logs

```bash
# Real-time logs
docker logs -f code-scalpel-mcp

# Last 50 lines
docker logs --tail 50 code-scalpel-mcp

# Logs from last 5 minutes
docker logs --since 5m code-scalpel-mcp
```

### Check File Access

```bash
# List files the container can see
docker exec code-scalpel-mcp ls -la /workspace

# Check specific file
docker exec code-scalpel-mcp test -f /workspace/main.py && echo "Found" || echo "Not found"
```

### Stop and Remove Container

```bash
# Stop container
docker stop code-scalpel-mcp

# Remove container
docker rm code-scalpel-mcp

# Or with docker compose
docker compose down
```

### Update to Latest Build

```bash
# Rebuild image with latest code
docker build -t code-scalpel:1.5.3 .

# Remove old container
docker rm -f code-scalpel-mcp

# Start new container
docker run -d \
  --name code-scalpel-mcp \
  -p 8593:8593 \
  -v $(pwd):/workspace \
  code-scalpel:1.5.3
```

## Troubleshooting

### Port Already in Use

```bash
# Find what's using port 8593
lsof -i :8593

# Kill container
docker kill code-scalpel-mcp

# Or use different port
docker run -d -p 9999:8593 code-scalpel:1.5.3
```

### Files Not Found

```bash
# Ensure volume is mounted
docker run -d \
  -v $(pwd):/workspace \  # This line is important!
  code-scalpel:1.5.3

# Verify files are accessible
docker exec code-scalpel-mcp ls /workspace
```

### Container Exits Immediately

```bash
# Check logs
docker logs code-scalpel-mcp

# See last 20 lines with timestamp
docker logs --timestamps code-scalpel-mcp | tail -20
```

### Connection Refused

```bash
# Check container is actually running
docker ps | grep code-scalpel-mcp

# Wait longer for startup (health: starting)
sleep 5 && curl http://localhost:8593/sse

# Check if port is bound
netstat -tlnp | grep 8593
```

## Useful Commands Reference

```bash
# Image management
docker images | grep code-scalpel          # List images
docker rmi code-scalpel:1.5.3             # Remove image
docker tag code-scalpel:latest code-scalpel:1.5.3  # Tag image

# Container management
docker ps -a                               # List all containers
docker stats code-scalpel-mcp             # View resource usage
docker exec -it code-scalpel-mcp /bin/bash  # Shell into container
docker inspect code-scalpel-mcp           # Detailed info

# Network
docker network ls                          # List networks
docker network inspect code-scalpel-network  # Network details
curl -v http://localhost:8593/sse         # Test connectivity

# Cleanup
docker system prune                        # Remove unused images/containers
docker volume prune                        # Remove unused volumes
docker network prune                       # Remove unused networks
```

## Environment Variables

All optional. Container works fine with defaults.

```bash
# Workspace root for path resolution
-e WORKSPACE_ROOT=/workspace

# Project root for relative paths
-e PROJECT_ROOT=/workspace

# Force Docker detection (if auto-detection fails)
-e FORCE_DOCKER=1

# Enable verbose logging
-e DEBUG=1

# Python settings
-e PYTHONUNBUFFERED=1
-e PYTHONDONTWRITEBYTECODE=1
```

## Performance Tips

1. **Mount only necessary directories** - Reduces scan time
   ```bash
   docker run -v /path/to/src:/workspace/src code-scalpel:1.5.3
   ```

2. **Set PROJECT_ROOT** - Limits path search scope
   ```bash
   docker run -e PROJECT_ROOT=/workspace/backend code-scalpel:1.5.3
   ```

3. **Use resource limits** - Prevents OOM kills
   ```bash
   docker run --memory=2g --cpus=2 code-scalpel:1.5.3
   ```

4. **Cache mount for pip** - Speeds up multi-container rebuilds
   ```bash
   docker build --cache-from code-scalpel:1.5.3 .
   ```

## Production Considerations

1. **Use specific version tags** - Not `latest`
   ```bash
   docker run code-scalpel:1.5.3  # Good
   docker run code-scalpel:latest # Bad for production
   ```

2. **Enable logging** - docker-compose.yml has logging configured
   ```yaml
   logging:
     driver: "json-file"
     options:
       max-size: "10m"
       max-file: "3"
   ```

3. **Set resource limits** - Prevent runaway processes
   ```bash
   --memory=2g --cpus=2
   ```

4. **Use restart policies** - Keep container running
   ```bash
   --restart unless-stopped
   ```

5. **Monitor health** - Use health checks
   ```bash
   # Check status
   docker inspect code-scalpel-mcp | grep '"Health"'
   ```

## Getting Help

### Documentation

- [DOCKER_DEPLOYMENT_STATUS_v1.5.3.md](DOCKER_DEPLOYMENT_STATUS_v1.5.3.md) - Detailed deployment info
- [DOCKER_CONNECTION_TROUBLESHOOTING.md](DOCKER_CONNECTION_TROUBLESHOOTING.md) - Troubleshooting guide
- [docker_volume_mounting.md](docker_volume_mounting.md) - Volume mount examples

### Useful Commands

```bash
# Full diagnostic check
./scripts/docker_setup.sh

# View all logs
docker logs code-scalpel-mcp -f

# Container info
docker inspect code-scalpel-mcp

# Network diagnostics
docker network inspect code-scalpel-network
```

### GitHub Issues

If issues persist, open issue with:

```bash
# Collect diagnostic info
docker logs code-scalpel-mcp > logs.txt 2>&1
docker inspect code-scalpel-mcp > container-info.json
docker images code-scalpel:1.5.3
docker --version
```

Include this info in your issue report.

---

**Questions?** See [DOCKER_CONNECTION_TROUBLESHOOTING.md](DOCKER_CONNECTION_TROUBLESHOOTING.md) or open an issue on GitHub.
