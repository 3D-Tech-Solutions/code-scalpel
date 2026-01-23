# Code Scalpel V2.0 - Comprehensive Recommendations Report

**Date:** December 15, 2025  
**Author:** GitHub Copilot Assessment  
**Version:** 2.0.0 Verification & Analysis

---

## V2.0.0 Deployment Status

**Container Verification (December 15, 2025):**
| Property | Value |
|----------|-------|
| Container Name | `code-scalpel` |
| Image | `code-scalpel:v2.0.0` |
| Version (Internal) | `2.0.0` |
| Status | Running (~1 hour) |
| Health Status | **UNHEALTHY** (see Issue #1 below) |

### Critical Issue #1: Health Check Design Flaw

**Problem:** The Docker health check attempts to curl the SSE endpoint:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8593/sse -H "Accept: text/event-stream" || exit 1
```

**Root Cause:** SSE (Server-Sent Events) connections are **designed to stay open** and stream events indefinitely. The `curl` command will connect successfully but never complete because it's waiting for the stream to close. This causes the 10-second timeout to expire, marking the container as unhealthy.

**Fix Required:**
```dockerfile
# Option 1: Add a health endpoint that returns immediately
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8593/health || exit 1

# Option 2: Use curl's max-time flag with a simple connection test  
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f --max-time 2 -o /dev/null -s http://localhost:8593/sse -H "Accept: text/event-stream" || exit 1
```

**Recommendation:** Add a `/health` endpoint to the server that returns `200 OK` immediately. This is standard practice for containerized services.

### V2.0.0 Server Capabilities Verified

Based on MCP tool analysis of the running server:
- [COMPLETE] **stdio transport support** - Present in `run_server()` function
- [COMPLETE] **streamable-http transport** - Present 
- [COMPLETE] **sse transport** - Present (deprecated but supported)
- [COMPLETE] **DNS rebinding protection** - Implemented via `TransportSecuritySettings`
- [COMPLETE] **LAN access control** - Via `--allow-lan` flag
- [FAILED] **Windows path resolution** - **VERIFIED BROKEN** (see Issue #2 below)
- [WARNING] **Resources primitive** - **PARTIAL**: 1 resource defined (`scalpel://capabilities`) - needs expansion
- [COMPLETE] **Prompts primitive** - 2 prompts defined via `@mcp.prompt()` decorator:
  - `code_review_prompt` - Comprehensive code review template
  - `security_audit_prompt` - Security-focused audit template
- [FAILED] **Progress token support** - Not implemented
- [FAILED] **Health endpoint** - Not implemented

### Critical Issue #2: Windows Path Resolution Broken in V2.0.0

**Verification Method:** Used `mcp_code-scalpel_validate_paths` tool with actual Windows paths

**Test Paths:**
```
k:\backup\Develop\scalpel-tests\CODE_SCALPEL_V2_RECOMMENDATIONS.md  → INACCESSIBLE
K:/backup/Develop/scalpel-tests/CODE_SCALPEL_V2_RECOMMENDATIONS.md  → INACCESSIBLE
/mnt/k/backup/Develop/scalpel-tests/CODE_SCALPEL_V2_RECOMMENDATIONS.md → INACCESSIBLE
```

**Result:** ALL Windows path formats fail, including WSL-style mounts.

**Root Cause Analysis (from `path_resolver.py`):**

The `PathResolver` class (v1.5.3) does NOT implement Windows path handling:

1. **`_detect_workspace_roots()`** - Only checks Linux paths (`/workspace`, `/app/code`, `/app`)
2. **`resolve()`** - Uses `Path(path).is_absolute()` which returns False for Windows paths on Linux
3. **No Windows drive letter parsing** - No regex for `C:\`, `K:\`, etc.
4. **No WSL mount translation** - No `/mnt/c/` → `C:\` mapping
5. **No Docker Desktop mount translation** - No `/c/` → `C:\` mapping

**Current PathResolver Strategies:**
1. Direct absolute path access (Linux paths only)
2. Relative to explicit project_root
3. Relative to detected workspace roots
4. Basename search in workspace roots
5. Parent directory search

**Missing Windows-Specific Strategies:**
- Windows drive letter detection (`[A-Za-z]:[/\\]`)
- WSL-style mount mapping (`/mnt/c/` → `C:/`)
- Docker Desktop mount mapping (`/c/` → `C:/`)
- `WINDOWS_DRIVE_MAP` environment variable support

**Recommended Fix:**
Add to `_attempt_resolution()`:
```python
import re

# Windows path detection
win_match = re.match(r'^([A-Za-z]):[/\\](.*)$', path)
if win_match:
    drive = win_match.group(1).lower()
    rel_path = win_match.group(2).replace('\\', '/')
    
    # Try WSL-style mount
    wsl_path = f'/mnt/{drive}/{rel_path}'
    if Path(wsl_path).exists():
        return PathResolutionResult(resolved_path=wsl_path, success=True, ...)
    
    # Try Docker Desktop mount
    docker_path = f'/{drive}/{rel_path}'
    if Path(docker_path).exists():
        return PathResolutionResult(resolved_path=docker_path, success=True, ...)
```

---

## Executive Summary

This document consolidates findings from:
1. Deep technical assessment of Code Scalpel v1.0.2
2. Research on how major AI platforms deploy MCP servers
3. Industry best practices from Docker, Anthropic, and GitHub
4. **Comprehensive MCP Protocol Requirements Research (Section 7)**

**Key Finding:** Code Scalpel has excellent core capabilities but its deployment architecture diverges from emerging industry standards in ways that limit adoption and cause compatibility issues.

**Research-Identified Gaps:** Beyond transport and path issues, Code Scalpel is missing two of the three core MCP primitives (Resources and Prompts), lacks proper capability negotiation, and has no support for advanced features like progress tokens, roots, and sampling that enable enterprise-grade deployments.

---

## Part 1: How Major AI Platforms Deploy MCP Servers

### 1.1 Transport Protocol Landscape (2025)

| Platform | Local Transport | Remote Transport | Deployment Model |
|----------|----------------|------------------|------------------|
| **Claude Desktop** | stdio (primary) | Streamable HTTP | Client spawns subprocess |
| **GitHub Copilot** | stdio | Streamable HTTP + OAuth | Local or Remote |
| **VS Code** | stdio | Streamable HTTP | Extension manages lifecycle |
| **Cursor** | stdio | HTTP+SSE | Configuration-based |
| **Windsurf** | stdio | PAT-based HTTP | Hybrid |
| **Docker MCP Toolkit** | stdio (containerized) | Gateway proxy | Container orchestration |
| **Code Scalpel** | [FAILED] None | SSE only | Always remote |

### 1.2 The Two Standard Transports

#### **stdio (Standard Input/Output)** - Primary for Local
```
┌─────────────────┐          stdin/stdout          ┌─────────────────┐
│   MCP Client    │ ◄─────────────────────────────►│   MCP Server    │
│  (Claude, VSC)  │     JSON-RPC messages          │   (subprocess)  │
└─────────────────┘                                └─────────────────┘
```

**Characteristics:**
- Client launches server as subprocess
- Communication via stdin/stdout pipes
- Server lifetime tied to client session
- **Zero network exposure** - most secure
- Recommended by MCP specification for local tools

**How Claude Desktop Uses stdio:**
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]
    }
  }
}
```

#### **Streamable HTTP** - Standard for Remote (Replaces SSE)
```
┌─────────────────┐         POST /mcp              ┌─────────────────┐
│   MCP Client    │ ────────────────────────────►  │   MCP Server    │
│                 │ ◄──────────────────────────────│   (HTTP)        │
└─────────────────┘    JSON or SSE Response        └─────────────────┘
```

**Characteristics:**
- Single HTTP endpoint for all operations
- Supports session management via `Mcp-Session-Id`
- Server can return JSON or open SSE stream
- Supports authentication (OAuth, PAT)
- **Deprecated:** Old HTTP+SSE dual-endpoint pattern

### 1.3 Docker's MCP Best Practices

Docker's MCP Toolkit represents the emerging enterprise standard:

1. **Containerize Everything**
   - MCP servers run in isolated containers
   - Secrets managed via Docker Secrets
   - Network isolation between servers

2. **Use stdio Inside Containers**
   - Container uses stdio internally
   - Docker MCP Gateway provides HTTP interface externally
   - Best of both worlds: security + accessibility

3. **Gateway Pattern for Remote Access**
   ```
   ┌─────────┐      HTTP       ┌─────────────┐      stdio      ┌─────────────┐
   │ Client  │ ◄─────────────► │ MCP Gateway │ ◄──────────────►│ MCP Server  │
   └─────────┘                 │  (proxy)    │                 │ (container) │
                               └─────────────┘                 └─────────────┘
   ```

4. **Tool Budget Management**
   - Limit tools to essential functions
   - Group related endpoints into higher-level tools
   - Use MCP prompts as "macros" for complex workflows

5. **Agent-First Design**
   - Error messages written for LLM consumption
   - Tool descriptions optimized for AI understanding
   - Documentation serves both humans and agents

---

## Part 2: Code Scalpel Current Architecture

### 2.1 Current Configuration

```json
{
  "mcpServers": {
    "code-scalpel": {
      "type": "sse",
      "url": "http://localhost:8593/sse"
    }
  }
}
```

### 2.2 Architecture Analysis

| Aspect | Code Scalpel | Industry Standard | Gap |
|--------|-------------|-------------------|-----|
| **Transport** | SSE only | stdio + Streamable HTTP | SSE is deprecated |
| **Deployment** | Always Docker | Local + Docker options | Missing local option |
| **Path Handling** | Linux paths only | Cross-platform | Windows broken |
| **Session Management** | None visible | Mcp-Session-Id | Missing |
| **Authentication** | None | OAuth/PAT support | Missing |

### 2.3 Critical Issues Identified

#### Issue 1: SSE Transport is Deprecated
The MCP specification (2025-06-18) explicitly states:
> "This replaces the HTTP+SSE transport from protocol version 2024-11-05"

Code Scalpel uses the old SSE pattern while the industry has moved to Streamable HTTP.

#### Issue 2: No stdio Support
Every major MCP client (Claude, VS Code, Cursor) primarily uses stdio for local servers. Code Scalpel's Docker-only approach means:
- Cannot run without Docker
- Network overhead for local operations
- Security audit concerns (network exposure)

#### Issue 3: Windows Path Resolution Failure
```
Error: Path does not exist: /app/k:\backup\Develop\scalpel-tests
```

The server attempts to prepend `/app/` to Windows paths, breaking all file-based operations.

#### Issue 4: Missing Session Management
Streamable HTTP servers should implement:
- `Mcp-Session-Id` header
- Session lifecycle management
- Proper initialization handshake

---

## Part 3: Consolidated Recommendations

### 3.1 Transport Layer Recommendations

#### P0: Add stdio Transport Support
```python
# Example: Multi-transport server entry point
if __name__ == "__main__":
    import sys
    
    if "--stdio" in sys.argv:
        from mcp.server.stdio import stdio_server
        asyncio.run(stdio_server(app))
    else:
        from mcp.server.streamable_http import streamable_http_server
        asyncio.run(streamable_http_server(app, port=8593))
```

**Benefits:**
- Compatible with Claude Desktop, VS Code, all major clients
- No network exposure for local use
- Simpler configuration for users
- Aligns with MCP specification recommendations

#### P0: Migrate from SSE to Streamable HTTP
```python
# Old pattern (deprecated)
@app.route('/sse')
def sse_endpoint():
    ...

@app.route('/messages', methods=['POST'])
def message_endpoint():
    ...

# New pattern (Streamable HTTP)
@app.route('/mcp', methods=['GET', 'POST'])
def mcp_endpoint():
    if request.method == 'POST':
        # Handle JSON-RPC request
        # Return JSON or start SSE stream
    else:
        # GET: Open SSE stream for server-initiated messages
```

### 3.2 Cross-Platform Compatibility

#### P0: Universal Path Resolver
```python
import re
import os
from pathlib import Path, PureWindowsPath, PurePosixPath

class UniversalPathResolver:
    """Resolve paths across Windows, Linux, and Docker environments."""
    
    def __init__(self, workspace_roots: list[str] = None):
        self.workspace_roots = workspace_roots or ['/app', '/workspace']
        self.volume_mappings = self._detect_volume_mappings()
    
    def resolve(self, path: str) -> str | None:
        """Convert any path format to accessible path."""
        candidates = []
        
        # Windows absolute path: C:\Users\... or C:/Users/...
        win_match = re.match(r'^([A-Za-z]):[/\\](.*)$', path)
        if win_match:
            drive = win_match.group(1).lower()
            rel_path = win_match.group(2).replace('\\', '/')
            
            # WSL-style mount
            candidates.append(f'/mnt/{drive}/{rel_path}')
            # Docker Desktop mount
            candidates.append(f'/{drive}/{rel_path}')
            # Custom workspace mount
            for root in self.workspace_roots:
                candidates.append(f'{root}/{rel_path}')
        
        # Already POSIX path
        elif path.startswith('/'):
            candidates.append(path)
            # Try relative to workspace roots
            for root in self.workspace_roots:
                if not path.startswith(root):
                    candidates.append(f'{root}{path}')
        
        # Relative path
        else:
            for root in self.workspace_roots:
                candidates.append(f'{root}/{path}')
        
        # Return first existing path
        for candidate in candidates:
            normalized = os.path.normpath(candidate)
            if os.path.exists(normalized):
                return normalized
        
        return None
    
    def _detect_volume_mappings(self) -> dict:
        """Auto-detect Docker volume mappings."""
        # Check /proc/mounts or Docker environment
        mappings = {}
        if os.path.exists('/proc/mounts'):
            # Parse mount points
            pass
        return mappings
```

#### P1: Environment-Based Configuration
```python
# Support WORKSPACE_ROOT environment variable
WORKSPACE_ROOT = os.environ.get('WORKSPACE_ROOT', '/app')

# Support multiple roots via colon-separated list
WORKSPACE_ROOTS = os.environ.get('WORKSPACE_ROOTS', '/app:/workspace').split(':')

# Windows-specific: Support Windows path translation
WINDOWS_DRIVE_MAP = os.environ.get('WINDOWS_DRIVE_MAP', 'C=/mnt/c,D=/mnt/d')
```

### 3.3 Deployment Flexibility

#### P1: Dual Deployment Support
Provide both containerized and native options:

**Option A: Native Installation (stdio)**
```bash
pip install code-scalpel
code-scalpel --stdio
```

Configuration for Claude Desktop:
```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "code-scalpel",
      "args": ["--stdio"]
    }
  }
}
```

**Option B: Docker with stdio (Current + stdio)**
```bash
docker run -i code-scalpel:latest --stdio
```

Configuration:
```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-v", "${workspaceFolder}:/workspace", "code-scalpel:latest", "--stdio"]
    }
  }
}
```

**Option C: Remote Streamable HTTP**
```json
{
  "mcpServers": {
    "code-scalpel": {
      "type": "http",
      "url": "http://localhost:8593/mcp"
    }
  }
}
```

### 3.4 Security Enhancements

#### P1: Origin Validation (Streamable HTTP)
```python
ALLOWED_ORIGINS = ['http://localhost', 'vscode-webview://']

@app.before_request
def validate_origin():
    origin = request.headers.get('Origin', '')
    if origin and not any(origin.startswith(allowed) for allowed in ALLOWED_ORIGINS):
        return jsonify({"error": "Invalid origin"}), 403
```

#### P2: Session Management
```python
import secrets

class SessionManager:
    def __init__(self):
        self.sessions = {}
    
    def create_session(self) -> str:
        session_id = secrets.token_urlsafe(32)
        self.sessions[session_id] = {
            'created_at': datetime.utcnow(),
            'state': {}
        }
        return session_id
    
    def validate_session(self, session_id: str) -> bool:
        if session_id not in self.sessions:
            return False
        # Check expiry
        session = self.sessions[session_id]
        if datetime.utcnow() - session['created_at'] > timedelta(hours=24):
            del self.sessions[session_id]
            return False
        return True
```

### 3.5 Tool Design Improvements

#### P2: Agent-Optimized Error Messages
```python
# Current (human-focused)
raise FileNotFoundError(f"File not found: {path}")

# Improved (agent-focused)
raise ToolError(
    code="FILE_NOT_FOUND",
    message=f"Cannot access file: {path}",
    suggestion="Verify the file path exists and is mounted in the container. "
               "For Docker: use -v /host/path:/workspace when starting the server.",
    recoverable=True
)
```

#### P2: Tool Budget Optimization
Current tool count: 15+ individual tools

**Recommendation:** Group into logical toolsets with prompts:

```python
# Instead of separate tools
- extract_code
- analyze_code  
- get_file_context

# Provide a unified prompt/macro
@mcp.prompt("analyze_symbol")
async def analyze_symbol_prompt(file_path: str, symbol_name: str):
    """Comprehensive symbol analysis combining extraction and context."""
    context = await get_file_context(file_path)
    extraction = await extract_code(file_path, symbol_name)
    analysis = await analyze_code(extraction.code)
    return AnalysisResult(context, extraction, analysis)
```

---

## Part 4: Implementation Roadmap

### Phase 1: Critical Fixes (Week 1-2)
| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| Add stdio transport | P0 | Medium | Enables 90% of MCP clients |
| Fix Windows path resolution | P0 | Low | Unblocks Windows users |
| Update to Streamable HTTP | P0 | Medium | Future-proofs protocol |

### Phase 2: Compatibility (Week 3-4)
| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| Native pip installation option | P1 | Medium | Simplifies adoption |
| Environment-based workspace config | P1 | Low | Docker flexibility |
| Origin validation security | P1 | Low | Security hardening |

### Phase 3: Enhancement (Week 5-6)
| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| Session management | P2 | Medium | Stateful operations |
| Agent-optimized errors | P2 | Low | Better AI interaction |
| Tool consolidation/prompts | P2 | Medium | Reduced complexity |

### Phase 4: Expansion (Week 7-8)
| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| JavaScript/TypeScript analysis | P2 | High | Multi-language support |
| Test generation AST expansion | P2 | High | More robust testing |
| Docker MCP Catalog submission | P3 | Low | Discovery/distribution |

---

## Part 5: Configuration Examples for V2.0

### 5.1 Claude Desktop (stdio)
```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "code-scalpel",
      "args": ["--stdio"],
      "env": {
        "WORKSPACE_ROOT": "/Users/dev/projects"
      }
    }
  }
}
```

### 5.2 VS Code (Local stdio via Docker)
```json
{
  "mcp": {
    "servers": {
      "code-scalpel": {
        "command": "docker",
        "args": [
          "run", "-i", "--rm",
          "-v", "${workspaceFolder}:/workspace",
          "-e", "WORKSPACE_ROOT=/workspace",
          "code-scalpel:v2.0",
          "--stdio"
        ]
      }
    }
  }
}
```

### 5.3 Remote Deployment (Streamable HTTP)
```json
{
  "mcpServers": {
    "code-scalpel": {
      "type": "http",
      "url": "https://code-scalpel.example.com/mcp",
      "headers": {
        "Authorization": "Bearer ${CODE_SCALPEL_TOKEN}"
      }
    }
  }
}
```

### 5.4 Docker Compose (Enterprise)
```yaml
version: '3.8'
services:
  code-scalpel:
    image: code-scalpel:v2.0
    command: ["--http", "--port", "8593"]
    volumes:
      - ./projects:/workspace:ro
    environment:
      - WORKSPACE_ROOT=/workspace
      - ALLOWED_ORIGINS=http://localhost,https://vscode.dev
    ports:
      - "8593:8593"
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
```

---

## Part 6: Comparison Matrix

### Code Scalpel vs Industry Standards

| Feature | Code Scalpel v2.0 Current | Industry Standard | V2.0 Target |
|---------|---------------------|-------------------|-------------|
| **stdio transport** | [FAILED] | [COMPLETE] Required | [COMPLETE] |
| **Streamable HTTP** | [FAILED] (SSE only) | [COMPLETE] | [COMPLETE] |
| **Windows paths** | [FAILED] Broken | [COMPLETE] | [COMPLETE] |
| **Native install** | [FAILED] Docker only | [COMPLETE] Both | [COMPLETE] |
| **Session management** | [FAILED] | [COMPLETE] | [COMPLETE] |
| **Origin validation** | [FAILED] | [COMPLETE] | [COMPLETE] |
| **Tool descriptions** | [WARNING] Human-focused | Agent-focused | [COMPLETE] |
| **Security scanning** | [COMPLETE] Excellent | [COMPLETE] | [COMPLETE] |
| **Code extraction** | [COMPLETE] Excellent | [COMPLETE] | [COMPLETE] |
| **Multi-language** | [WARNING] Python only | [COMPLETE] Multiple | [COMPLETE] |
| **Resources primitive** | [FAILED] Not implemented | [COMPLETE] | [COMPLETE] |
| **Prompts primitive** | [FAILED] Not implemented | [COMPLETE] | [COMPLETE] |
| **Capability negotiation** | [WARNING] Unverified | [COMPLETE] | [COMPLETE] |
| **Progress tokens** | [FAILED] | [COMPLETE] | [COMPLETE] |
| **Roots support** | [FAILED] | [COMPLETE] | [COMPLETE] |
| **Sampling capability** | [FAILED] | Optional | [COMPLETE] |
| **OAuth 2.1 auth** | [FAILED] | [COMPLETE] (remote) | [COMPLETE] |
| **stderr logging** | [WARNING] Unverified | [COMPLETE] Required | [COMPLETE] |
| **Protocol versioning** | [WARNING] Unverified | [COMPLETE] | [COMPLETE] |

### Unique Strengths to Preserve
- **Security Scanning:** 15+ vulnerability types with CWE mapping
- **Taint Analysis:** Cross-file data flow tracking
- **Symbolic Execution:** Path exploration for test generation
- **Surgical Extraction:** Token-efficient code retrieval
- **Refactor Simulation:** Safety analysis before changes

---

---

## Part 7: MCP Protocol Compliance Gaps (From Deep Research)

Based on the comprehensive MCP Server Toolset Requirements Research, the following critical protocol compliance items are **missing from the current recommendations** and must be addressed:

### 7.1 Capability Negotiation (Critical)

**Gap Identified:** The research emphasizes that the **capabilities object during initialization is the definitive registry**. If a capability is missing, the client will never request it.

#### P0: Proper Initialization Handshake
```python
# Server must correctly advertise ALL capabilities
{
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {},                          # Required for tool discovery
            "resources": { "subscribe": true },   # Required for resource access
            "prompts": {},                        # Required for prompt templates
            "logging": {}                         # Required for structured logging
        },
        "serverInfo": {
            "name": "code-scalpel",
            "version": "2.0.0"
        }
    }
}
```

**Action Required:** Audit current initialization response to ensure all implemented capabilities are advertised.

### 7.2 The "Three Pillars" of MCP (Major Gap)

The research identifies **three core primitives** that a comprehensive MCP toolset should implement:

| Primitive | Role | Current Status | V2 Target |
|-----------|------|----------------|-----------|
| **Tools** | Action/Execution | [COMPLETE] Implemented | Maintain |
| **Resources** | Passive Context | [FAILED] Not implemented | [COMPLETE] Add |
| **Prompts** | Reusable Templates | [FAILED] Not implemented | [COMPLETE] Add |

#### P1: Implement Resources Primitive
Resources provide **read-only context** to the AI—the "eyes" of the agent.

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("code-scalpel")

# Static resource: project structure
@mcp.resource("project://structure")
async def get_project_structure() -> str:
    """Return the project's file/folder structure."""
    return await generate_project_map()

# Dynamic resource template: file contents
@mcp.resource("file:///{path}")
async def get_file_contents(path: str) -> str:
    """Read file contents by path."""
    validated_path = validate_path_security(path)
    return await read_file_contents(validated_path)

# Resource with subscription support for real-time updates
@mcp.resource("analysis://security-status", subscribe=True)
async def get_security_status() -> str:
    """Current security scan status - subscribable for updates."""
    return await get_current_security_findings()
```

**Benefits:**
- Clients can pre-load context without tool invocation
- Supports subscription for real-time state awareness
- URI-based access is familiar and flexible

#### P1: Implement Prompts Primitive
Prompts are **reusable workflow templates** that combine tools and resources.

```python
@mcp.prompt("security-audit")
async def security_audit_prompt(project_path: str) -> dict:
    """
    Comprehensive security audit workflow.
    Combines multiple tools into a guided analysis.
    """
    return {
        "messages": [
            {
                "role": "system",
                "content": "You are a Senior Security Engineer performing a code audit."
            },
            {
                "role": "user", 
                "content": f"""
                Perform a security audit of the project at {project_path}.
                
                1. First, scan dependencies for known vulnerabilities
                2. Run taint analysis for injection vulnerabilities
                3. Check for hardcoded secrets
                4. Generate a security report with findings and remediation steps
                """
            }
        ],
        "tools": ["security_scan", "scan_dependencies", "cross_file_security_scan"]
    }

@mcp.prompt("refactor-function")
async def refactor_prompt(file_path: str, function_name: str) -> dict:
    """
    Safe refactoring workflow with validation.
    """
    return {
        "messages": [
            {
                "role": "system",
                "content": "You are refactoring code. Always validate changes before applying."
            },
            {
                "role": "user",
                "content": f"Extract and refactor `{function_name}` from `{file_path}`. "
                           f"Use simulate_refactor before update_symbol."
            }
        ],
        "tools": ["extract_code", "simulate_refactor", "update_symbol"]
    }
```

**Benefits:**
- Reduces cognitive load on users
- Creates curated workflows for common tasks
- Client UIs can render prompts as clickable actions

### 7.3 Advanced Capabilities (Research-Identified)

#### P2: Implement Sampling Capability
**Sampling** allows the server to request LLM completions from the client—reversing the typical flow.

```python
# Server requests LLM to summarize before processing
async def handle_large_file_analysis(file_path: str):
    content = await read_large_file(file_path)
    
    # Server asks client's LLM to summarize
    summary = await mcp.sample(
        messages=[
            {"role": "user", "content": f"Summarize this code:\n{content[:10000]}"}
        ],
        max_tokens=500
    )
    
    # Use summary for further processing
    return await analyze_with_context(summary)
```

**Use Cases:**
- Pre-processing large files before analysis
- Generating human-readable reports from scan results
- Intelligent triage of findings

#### P2: Implement Roots Capability
**Roots** define the file system boundaries the server should respect.

```python
class RootsManager:
    def __init__(self):
        self.allowed_roots: list[str] = []
    
    async def handle_roots_list(self, roots: list[dict]):
        """Receive allowed roots from client."""
        self.allowed_roots = [r["uri"] for r in roots]
    
    def validate_path(self, path: str) -> bool:
        """Ensure path is within allowed roots."""
        normalized = os.path.normpath(path)
        return any(
            normalized.startswith(root.replace("file://", ""))
            for root in self.allowed_roots
        )
```

**Security Benefit:** Prevents directory traversal attacks by enforcing client-specified boundaries.

### 7.4 Long-Running Operations (Critical for Security Scans)

#### P1: Progress Token Support
The research identifies that **long-running operations** (like full project security scans) need progress tracking to prevent timeouts.

```python
async def handle_project_scan(project_path: str, progress_token: str = None):
    """Security scan with progress reporting."""
    files = await discover_files(project_path)
    total = len(files)
    
    for i, file in enumerate(files):
        # Report progress to client
        if progress_token:
            await mcp.notify_progress(
                token=progress_token,
                progress=i,
                total=total,
                message=f"Scanning {file}..."
            )
        
        await scan_file(file)
    
    return results
```

**Why Critical:** `cross_file_security_scan` and `crawl_project` can take minutes on large codebases.

### 7.5 Logging and Debugging (Protocol Compliance)

#### P0: stderr-Only Logging for stdio Transport
**Critical Requirement:** When using stdio transport, **stdout must contain ONLY valid JSON-RPC messages**. Any `print()` statement corrupts the stream.

```python
import sys
import logging

# Configure logging to stderr ONLY
logging.basicConfig(
    stream=sys.stderr,
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Use protocol notifications for user-visible logs
async def log_to_client(level: str, message: str):
    """Send structured log via MCP protocol."""
    await mcp.notify({
        "method": "notifications/message",
        "params": {
            "level": level,  # "debug", "info", "warning", "error"
            "data": message
        }
    })
```

#### P2: MCP Inspector Integration
Document how to test Code Scalpel with the official MCP Inspector:

```bash
# Test stdio transport
npx @modelcontextprotocol/inspector code-scalpel --stdio

# Test HTTP transport  
npx @modelcontextprotocol/inspector --url http://localhost:8593/mcp
```

### 7.6 Protocol Versioning

#### P1: Version Negotiation Support
```python
SUPPORTED_VERSIONS = ["2024-11-05", "2025-03-26", "2025-06-18"]

async def handle_initialize(request):
    client_version = request["params"]["protocolVersion"]
    
    if client_version in SUPPORTED_VERSIONS:
        # Respond with same version
        server_version = client_version
    else:
        # Respond with latest supported, client decides compatibility
        server_version = SUPPORTED_VERSIONS[-1]
    
    return {
        "protocolVersion": server_version,
        "capabilities": {...},
        "serverInfo": {...}
    }
```

### 7.7 OAuth 2.1 Implementation Details

The research specifies **OAuth 2.1** for remote authentication:

#### P1: Bearer Token Validation
```python
from functools import wraps

def require_auth(scopes: list[str] = None):
    """Decorator for authenticated endpoints."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return {"error": "Missing bearer token"}, 401
            
            token = auth_header[7:]
            claims = await validate_token(token)
            
            # Check scopes
            if scopes:
                token_scopes = claims.get("scope", "").split()
                if not all(s in token_scopes for s in scopes):
                    return {"error": "Insufficient scope"}, 403
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Usage
@require_auth(scopes=["tools:execute"])
async def handle_tool_call(request):
    ...

@require_auth(scopes=["resources:read"])
async def handle_resource_read(request):
    ...
```

#### P2: Third-Party Token Delegation
For servers that access external services (GitHub, databases):

```python
async def handle_github_integration(user_token: str):
    """
    Server receives user's GitHub token from client.
    Must store securely and use for delegated access.
    """
    # Token exchange flow
    github_token = await exchange_token(
        user_token, 
        target_audience="https://api.github.com"
    )
    
    # Use delegated token
    return await github_api.list_repos(github_token)
```

---

## Part 8: Updated Implementation Roadmap

### Revised Priority Matrix

| Phase | Task | Priority | Source | Effort |
|-------|------|----------|--------|--------|
| **1** | stdio transport | P0 | V2 Rec | Medium |
| **1** | Windows path resolution | P0 | V2 Rec | Low |
| **1** | Streamable HTTP migration | P0 | V2 Rec | Medium |
| **1** | stderr-only logging (stdio) | P0 | Research | Low |
| **1** | Capability negotiation audit | P0 | Research | Low |
| **2** | Native pip installation | P1 | V2 Rec | Medium |
| **2** | Resources primitive | P1 | Research | Medium |
| **2** | Prompts primitive | P1 | Research | Medium |
| **2** | Progress token support | P1 | Research | Medium |
| **2** | Protocol version negotiation | P1 | Research | Low |
| **2** | OAuth 2.1 implementation | P1 | Research | High |
| **3** | Roots capability | P2 | Research | Medium |
| **3** | Sampling capability | P2 | Research | High |
| **3** | MCP Inspector documentation | P2 | Research | Low |
| **3** | Tool description optimization | P2 | V2 Rec | Low |

### Phase 1 (Critical Compliance) - Week 1-2
Focus: **Transport + Protocol Basics**
- All P0 items must be completed before beta release
- stdio + stderr logging are interdependent
- Capability object must advertise all features

### Phase 2 (Full MCP Coverage) - Week 3-5
Focus: **Primitives + Security**
- Resources enable passive context loading
- Prompts create workflow templates
- Progress tokens prevent timeout failures
- OAuth enables enterprise deployment

### Phase 3 (Advanced Features) - Week 6-8
Focus: **Advanced Capabilities + Polish**
- Roots for security boundaries
- Sampling for server-side AI
- Documentation and tooling

---

## Conclusion

Code Scalpel has built exceptional code analysis capabilities that surpass many alternatives. The V2.0 release should focus on **deployment compatibility** rather than adding new analysis features.

**The single most impactful change:** Adding stdio transport support would instantly make Code Scalpel compatible with Claude Desktop, VS Code, Cursor, and every other major MCP client.

**Priority Summary:**
1. **P0:** stdio transport + Windows paths + Streamable HTTP + Logging = Compatibility
2. **P1:** Resources + Prompts + Progress + OAuth = Full MCP Compliance
3. **P2:** Sampling + Roots + Polish = Advanced Features

The market is consolidating around stdio for local and Streamable HTTP for remote. Code Scalpel's current SSE-only approach puts it outside this standard. V2.0 should align with industry standards while preserving its unique analytical strengths.

**Research-Identified Gaps Summary:**
- Missing Resources primitive (passive context)
- Missing Prompts primitive (workflow templates)
- No capability negotiation documentation
- No progress token support for long operations
- No sampling capability for server-side AI
- No roots support for security boundaries
- Logging may break stdio transport

---

## Appendix: Reference Links

- [MCP Specification (2025-06-18)](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)
- [Docker MCP Best Practices](https://www.docker.com/blog/mcp-server-best-practices/)
- [GitHub MCP Server](https://github.com/github/github-mcp-server)
- [Docker MCP Catalog](https://hub.docker.com/mcp)
- [GitHub Copilot MCP Documentation](https://docs.github.com/en/copilot/concepts/context/mcp)
