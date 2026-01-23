# Docker Connection Troubleshooting Guide - Code Scalpel v1.5.3

This guide helps diagnose and resolve connection issues when using Code Scalpel MCP server in Docker containers.

**NEW:** For LAN/remote device connection issues, see [LAN_CONNECTION_TROUBLESHOOTING.md](LAN_CONNECTION_TROUBLESHOOTING.md)

## Quick Diagnostics

### Check if container is running
```bash
docker ps -a | grep code-scalpel
```

Expected output: Container with status "Up" and port 8593 exposed.

### Check container logs
```bash
docker logs code-scalpel-mcp
```

Look for:
- "Uvicorn running on" message (success)
- Exception tracebacks (failure)
- Connection refused errors (port issue)

### Test port accessibility
```bash
# From host machine
curl -v http://localhost:8593/sse

# Expected response: HTTP/1.1 200 OK with event-stream content
```

### Verify PathResolver Docker detection
```bash
docker exec code-scalpel-mcp python3 -c "
from code_scalpel.mcp.path_resolver import PathResolver
pr = PathResolver()
print(f'Docker Detected: {pr.is_docker}')
print(f'Workspace Root: {pr.workspace_root}')
"
```

Expected output:
```
Docker Detected: True
Workspace Root: /workspace
```

## Common Connection Issues

### Issue 1: Port 8593 Already in Use

**Symptom:**
```
Error response from daemon: Bind for 0.0.0.0:8593 failed: port is already allocated
```

**Solution:**

Find and stop the existing container:
```bash
# Find process using port 8593
lsof -i :8593

# Or use fuser
fuser 8593/tcp

# Kill the container
docker kill $(docker ps -q --filter ancestor=code-scalpel)

# Or directly stop by name
docker stop code-scalpel-mcp
docker rm code-scalpel-mcp
```

Then start fresh:
```bash
docker run -d --name code-scalpel-mcp -p 8593:8593 code-scalpel:1.5.3
```

Alternatively, use a different port on the host:
```bash
docker run -d --name code-scalpel-mcp -p 9999:8593 code-scalpel:1.5.3

# Test on different port
curl http://localhost:9999/sse
```

### Issue 2: File Not Found or Path Resolution Failures

**Symptom:**
```
FileNotFoundError: Could not resolve path 'src/utils.py'
Attempted 5 strategies:
  1. Absolute path: /workspace/src/utils.py (FAILED)
  2. Relative to workspace: /workspace/src/utils.py (FAILED)
  3. Search in project_root: /workspace/src/utils.py (FAILED)
  4. Search entire tree: (FAILED)
  5. Parent dir hints: (FAILED)

Suggestion: Mount your project root:
  docker run -v /path/to/project:/workspace code-scalpel:1.5.3
```

**Root Causes:**

1. **Missing volume mount** - Container can't see host files
   ```bash
   # Current (WRONG)
   docker run -d code-scalpel:1.5.3
   
   # Fixed - mount project directory
   docker run -d -v $(pwd):/workspace code-scalpel:1.5.3
   ```

2. **Wrong mount path** - Files mounted to wrong location
   ```bash
   # Wrong - mounted to /code instead of /workspace
   docker run -d -v $(pwd):/code code-scalpel:1.5.3
   
   # Correct - use /workspace (container's expected path)
   docker run -d -v $(pwd):/workspace code-scalpel:1.5.3
   ```

3. **Absolute path without mount** - Using absolute paths without volume mount
   ```bash
   # Wrong - /home/user/project not in container
   docker run -d code-scalpel:1.5.3
   # Then trying to analyze /home/user/project/file.py
   
   # Correct - mount the directory
   docker run -d -v /home/user/project:/workspace code-scalpel:1.5.3
   ```

**Solution:**

Mount your project to `/workspace`:
```bash
# Single project
docker run -d \
  --name code-scalpel-mcp \
  -p 8593:8593 \
  -v $(pwd):/workspace \
  code-scalpel:1.5.3

# Specific directory
docker run -d \
  --name code-scalpel-mcp \
  -p 8593:8593 \
  -v /path/to/project:/workspace \
  code-scalpel:1.5.3
```

Verify mount:
```bash
docker exec code-scalpel-mcp ls -la /workspace
# Should show your project files
```

### Issue 3: Connection Refused on Client Side

**Symptom:**
```
Error: Connection refused to http://localhost:8593
```

**Root Causes:**

1. **Container not running**
   ```bash
   docker ps | grep code-scalpel
   # If empty, container is stopped
   ```

2. **Wrong port mapping**
   ```bash
   # Check what port is actually mapped
   docker port code-scalpel-mcp
   # Output: 8593/tcp -> 0.0.0.0:8593
   ```

3. **Firewall blocking port**
   ```bash
   # Linux - check firewall rules
   sudo ufw status
   sudo ufw allow 8593
   
   # macOS - built-in firewall usually not blocking localhost
   # Windows - check Windows Defender Firewall
   ```

4. **Using wrong IP address**
   - Use `localhost` or `127.0.0.1` from host machine
   - Use `0.0.0.0` or service name from Docker Compose
   - For remote access, use the actual server IP

**Solution:**

Step-by-step verification:

```bash
# 1. Verify container is running
docker ps | grep code-scalpel

# 2. Verify port is mapped
docker port code-scalpel-mcp

# 3. Check if process is listening
netstat -tlnp | grep 8593

# 4. Test from inside container
docker exec code-scalpel-mcp curl -v http://localhost:8593/sse

# 5. Test from host
curl -v http://localhost:8593/sse

# 6. If using remote server, verify IP
curl -v http://<server-ip>:8593/sse
```

### Issue 4: Volume Mount Permission Denied

**Symptom:**
```
PermissionError: [Errno 13] Permission denied when accessing files in /workspace
```

**Root Causes:**

1. **Files not readable by container user**
   ```bash
   # Check file permissions
   ls -la /path/to/file
   
   # Container runs as root by default, so permission should be OK
   # But if you have custom user, check permissions
   ```

2. **Mounted volume is read-only**
   ```bash
   # Wrong - read-only mount
   docker run -d -v $(pwd):/workspace:ro code-scalpel:1.5.3
   
   # Correct - read-write mount (default)
   docker run -d -v $(pwd):/workspace code-scalpel:1.5.3
   ```

**Solution:**

```bash
# Make files readable
chmod -R 644 /path/to/project/files
chmod -R 755 /path/to/project/directories

# Or mount with explicit read-write permission
docker run -d \
  -v $(pwd):/workspace:rw \
  code-scalpel:1.5.3

# Check from inside container
docker exec code-scalpel-mcp ls -la /workspace
```

### Issue 5: Docker Compose Service Won't Start

**Symptom:**
```
ERROR: for mcp-server Cannot start service mcp-server: error during connect:
this error may indicate the network docker-compose is not available
```

**Root Causes:**

1. **Docker daemon not running**
   ```bash
   docker ps
   # If "Cannot connect to Docker daemon", Docker isn't running
   ```

2. **docker-compose version mismatch**
   ```bash
   docker-compose --version
   # Should be 1.25+, better 2.0+
   ```

3. **Network doesn't exist**
   ```bash
   docker network ls | grep nginx-proxy-manager
   # If not present, create it
   docker network create nginx-proxy-manager_default
   ```

4. **Service name conflicts**
   ```bash
   docker ps -a | grep code-scalpel-mcp
   # Remove existing container
   docker rm -f code-scalpel-mcp
   ```

**Solution:**

```bash
# 1. Ensure Docker is running
docker --version

# 2. Create required network if needed
docker network create nginx-proxy-manager_default

# 3. Clean up old services
docker-compose down
docker-compose rm -f

# 4. Start fresh
docker-compose up -d

# 5. Verify services
docker-compose ps
docker-compose logs mcp-server
```

### Issue 6: Client Connection Timeout

**Symptom:**
```
Timeout waiting for response
Connection timeout after 30 seconds
Request to http://localhost:8593 took too long
```

**Root Causes:**

1. **Container overloaded**
   ```bash
   # Check container resource usage
   docker stats code-scalpel-mcp
   ```

2. **Large project analysis causing slow response**
   - Some operations can take time with large codebases

3. **Network latency or firewall delays**

**Solution:**

```bash
# 1. Increase client timeout
# In your client code, increase timeout from default 30s to 60s+

# 2. Monitor container resources
docker stats code-scalpel-mcp

# 3. Check server logs for slow operations
docker logs code-scalpel-mcp -f

# 4. Test simple operation first
curl -X POST http://localhost:8593/analyze -d '{"code":"x = 1"}'

# 5. If container is resource-constrained, increase limits
docker run -d \
  --memory=2g \
  --cpus=2 \
  code-scalpel:1.5.3
```

## Health Check Verification

The container includes a health check that pings the SSE endpoint every 30 seconds.

### Check health status
```bash
docker ps -a | grep code-scalpel
# Look at STATUS column for "(healthy)" or "(unhealthy)"

# Detailed health info
docker inspect code-scalpel-mcp | grep -A 10 '"Health"'
```

### Manually verify health
```bash
# Should return event-stream content
curl -i http://localhost:8593/sse

# Expected response:
# HTTP/1.1 200 OK
# content-type: text/event-stream; charset=utf-8
```

## Docker Compose Troubleshooting

### Services won't connect to each other

**Issue:** mcp-server can't connect to rest-api service

**Solution:**
```bash
# Both services must be on the same network
# Check docker-compose.yml has correct network config

# Verify services are on same network
docker network inspect nginx-proxy-manager_default

# Test service-to-service connectivity
docker exec code-scalpel-mcp ping rest-api
# Should succeed with service name resolution

# Check service name matches docker-compose.yml
# service name in yml: rest-api
# hostname in container: rest-api
# DNS works automatically on docker-compose network
```

### Volume mount issues in docker-compose

**Ensure volume paths are correct:**
```yaml
services:
  mcp-server:
    volumes:
      # Absolute path on host
      - /path/to/project:/workspace
      
      # Or relative to docker-compose.yml location
      - ./src:/workspace/src
      
      # Named volume
      - code-volume:/workspace
      
volumes:
  code-volume:
    driver: local
```

### Check docker-compose environment variables

```bash
# View environment variables in running container
docker-compose exec mcp-server env | grep SCALPEL

# Or directly
docker exec code-scalpel-mcp env | grep SCALPEL
```

## PathResolver-Specific Issues

### Docker detection not working

**Symptom:**
```
Docker Detected: False
```

**Issue:** Container not properly detected as Docker environment.

**Solution:**
```bash
# Manually enable Docker detection
docker run -d \
  -e FORCE_DOCKER=1 \
  code-scalpel:1.5.3

# Or set in docker-compose.yml
environment:
  - FORCE_DOCKER=1

# Or initialize PathResolver with flag
from code_scalpel.mcp.path_resolver import PathResolver
pr = PathResolver(enable_docker_detection=True)
```

### Workspace root not being detected

**Symptom:**
```
Workspace Root: /app/code  # Unexpected path
```

**Solution:**
```bash
# Set explicitly
docker run -d \
  -e WORKSPACE_ROOT=/workspace \
  code-scalpel:1.5.3

# For docker-compose
environment:
  - WORKSPACE_ROOT=/workspace
  - PROJECT_ROOT=/workspace

# Verify
docker exec code-scalpel-mcp python3 -c "
import os
print(f'WORKSPACE_ROOT={os.getenv(\"WORKSPACE_ROOT\")}')
print(f'PROJECT_ROOT={os.getenv(\"PROJECT_ROOT\")}')
"
```

### Path caching causing stale results

**Issue:** Path resolution caches results, so deleted files still resolve.

**Solution:**
```bash
# Disable caching (for debugging only)
from code_scalpel.mcp.path_resolver import PathResolver
pr = PathResolver()
pr.clear_cache()

# Or recreate PathResolver instance
pr = PathResolver()  # New instance, fresh cache

# In docker-compose, restart service to clear in-memory caches
docker-compose restart mcp-server
```

## Performance and Optimization

### Container is slow

**Check resource allocation:**
```bash
# See actual usage
docker stats code-scalpel-mcp

# Increase limits
docker run -d \
  --memory=2g \
  --cpus=2 \
  --memory-swap=4g \
  code-scalpel:1.5.3
```

### Large project causing timeouts

**Solution:**
```bash
# 1. Use PROJECT_ROOT to limit search scope
docker run -d \
  -e PROJECT_ROOT=/workspace/specific-module \
  code-scalpel:1.5.3

# 2. Mount only needed directories
docker run -d \
  -v /path/to/src:/workspace/src \
  -v /path/to/tests:/workspace/tests \
  code-scalpel:1.5.3

# 3. Increase timeout in client (60 seconds)
```

## Advanced Debugging

### Enable verbose logging

```bash
# View all server logs in real-time
docker logs -f code-scalpel-mcp

# Or from docker-compose
docker-compose logs -f mcp-server

# Check for PathResolver debug messages
docker logs code-scalpel-mcp | grep -i "path_resolver\|docker\|workspace"
```

### Interactive debugging

```bash
# Shell into container
docker exec -it code-scalpel-mcp /bin/bash

# Inside container, test PathResolver
python3 << 'EOF'
from code_scalpel.mcp.path_resolver import PathResolver
pr = PathResolver()
result = pr.resolve_path("test.py")
print(f"Resolved: {result}")
print(f"Docker: {pr.is_docker}")
print(f"Workspace: {pr.workspace_root}")
EOF
```

### Container inspection

```bash
# Full configuration
docker inspect code-scalpel-mcp

# Specific fields
docker inspect -f '{{.Mounts}}' code-scalpel-mcp
docker inspect -f '{{.NetworkSettings}}' code-scalpel-mcp
docker inspect -f '{{.State.Health}}' code-scalpel-mcp
```

## Testing MCP Tool Connectivity

### Quick test of validate_paths tool

```bash
# Using curl to test HTTP transport
curl -X POST http://localhost:8593/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "validate_paths",
      "arguments": {
        "paths": ["/workspace/main.py", "/workspace/utils/helpers.py"]
      }
    }
  }'
```

### Test extract_code tool

```bash
curl -X POST http://localhost:8593/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "extract_code",
      "arguments": {
        "file_path": "/workspace/main.py",
        "target_type": "function",
        "target_name": "main"
      }
    }
  }'
```

## Next Steps

1. **Verify basic connectivity** - Run quick diagnostic commands above
2. **Check container logs** - Look for error messages
3. **Inspect volume mounts** - Ensure files are accessible
4. **Test PathResolver** - Verify Docker detection works
5. **Enable verbose logging** - Diagnose specific failures
6. **Consult issue tracker** - Link to GitHub issues for known problems

## Docker Build Analysis

### Build Status
The Docker build for Code Scalpel MCP server is functional and completes successfully. The multi-stage build process installs all dependencies correctly and produces a working image.

### Test Results
- **Build Time**: Approximately 40-60 seconds  
- **Image Size**: ~1.39GB for tagged version 1.5.3
- **Dependencies**: All Python packages install without errors in the builder stage
- **Base Image**: python:3.10-slim

### Known Issues and Fixes

#### Import Error on Container Startup
**Symptom**: Container starts but MCP server fails with:
```
ModuleNotFoundError: No module named 'code_scalpel.mcp.archive.server'
```

**Root Cause**: The source file `src/code_scalpel/mcp/archive/server.py` was incorrectly named as `server.py.archive`.

**Fix**: Rename the file:
```bash
mv src/code_scalpel/mcp/archive/server.py.archive src/code_scalpel/mcp/archive/server.py
```

**Status**: Fixed in source code. Rebuild the Docker image after applying this fix.

### Security Notes
- Multi-stage build prevents development dependencies in final image
- Container runs as non-root user  
- Only necessary ports (8593/8594) are exposed
- SSL support available via environment variables

### Testing Recommendations
1. Build the image: `docker build -t code-scalpel:test .`
2. Run container: `docker run -d -p 8593:8593 code-scalpel:test`
3. Test health: `curl http://localhost:8593/sse`
4. Check logs: `docker logs <container_id>`

This analysis confirms the Docker build process works correctly when source code issues are resolved.

## Getting Help

If issues persist:

1. Collect diagnostic information:
   ```bash
   docker logs code-scalpel-mcp > logs.txt
   docker inspect code-scalpel-mcp > container-info.json
   docker ps -a > containers.txt
   ```

2. Check [Code Scalpel GitHub Issues](https://github.com/username/code-scalpel/issues)

3. Include in bug report:
   - Docker version: `docker --version`
   - Docker Compose version: `docker-compose --version`
   - Container logs (above)
   - Volume mount configuration
   - Error messages (full output)
   - Steps to reproduce
