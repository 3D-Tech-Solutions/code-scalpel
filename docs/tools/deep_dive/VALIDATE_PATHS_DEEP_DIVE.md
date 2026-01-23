# validate_paths - Deep Dive Documentation

**Document Type:** Tool Deep Dive Reference  
**Tool Name:** validate_paths  
**Tool Version:** v1.0  
**Code Scalpel Version:** v1.0.0  
**Last Updated:** 2026-01-12  
**Status:** Stable  
**Tier Availability:** All Tiers (Community, Pro, Enterprise)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Technical Overview](#technical-overview)
3. [Features and Capabilities](#features-and-capabilities)
4. [API Specification](#api-specification)
5. [Usage Examples](#usage-examples)
6. [Architecture and Implementation](#architecture-and-implementation)
7. [Testing Evidence](#testing-evidence)
8. [Performance Characteristics](#performance-characteristics)
9. [Security Considerations](#security-considerations)
10. [Integration Patterns](#integration-patterns)
11. [Tier-Specific Behavior](#tier-specific-behavior)
12. [Known Limitations](#known-limitations)
13. [Roadmap and Future Plans](#roadmap-and-future-plans)
14. [Troubleshooting](#troubleshooting)
15. [References and Related Tools](#references-and-related-tools)

## Executive Summary

### Purpose Statement
The `validate_paths` tool is the "Pre-Flight Checklist" for filesystem operations in the Code Scalpel ecosystem. It validates that file paths are accessible, exist, and are safe to access *before* more expensive or potentially destructive operations (like extraction or modification) are attempted.

Crucially, it is **Docker-Aware**. In containerized AI agent environments, path confusion (e.g., host path vs. container path) is a primary source of failure. `validate_paths` detects if it is running inside Docker and analyzes missing paths to suggest missing volume mounts, turning cryptic "File Not Found" errors into actionable DevOps guidance.

### Key Benefits
- **Fail Fast:** Prevents AI agents from burning tokens on operations destined to fail due to missing files.
- **Docker Intelligence:** Detects execution context and provides volume mount suggestions for inaccessible paths.
- **Security Enforcement:** Validates paths against workspace boundaries to prevent directory traversal attacks (Enterprise).
- **Batch Efficiency:** Validates hundreds of paths in a single tool call (vs. 100 calls to `ls` or `exists`).
- **Tier-Gated Safety:** Enforces limits appropriate for usage level (100 paths for Community vs. Unlimited for Pro).

### Quick Stats
| Metric | Value |
|--------|-------|
| **Tool Version** | v1.0 |
| **Release Date** | 2025-12-30 |
| **Test Coverage** | 100% (118/118 tests passed) |
| **Performance** | <10ms for 100 paths |
| **Limits** | 100 paths (Community), Unlimited (Pro/Ent) |
| **Token Efficiency** | Structured summary output avoids listing stat details for every file |

## Technical Overview

### Core Functionality
The tool accepts a list of absolute or relative paths and a `project_root`. It performs a multi-stage validation pipeline on every path:

1.  **Resolution:** Resolves absolute paths relative to the project root.
2.  **Existence Check:** Verifies if the path exists on the filesystem.
3.  **Type Check:** Identifies if the path is a file, directory, or symlink.
4.  **Boundary Check:** Ensures the path does not traverse outside the allowed `project_root` (critical for security).
5.  **Context Analysis:** If a path is missing, it checks global environment indicators (e.g., `/.dockerenv`) to hypothesize why (e.g., missing volume mount).

### Design Principles
1.  **Actionable Errors:** A missing file isn't just "false"; it's a "Missing Volume?" suggestion if likely.
2.  **Batch-First:** Designed for LLMs that extract many file references at once (e.g., "Analyze these 50 files").
3.  **Security-Aware:** Treats path traversal inputs (e.g., `../../etc/passwd`) as hostile events to be monitored (Enterprise).
4.  **Cross-Platform:** Handles Windows/Linux/macOS path separators and nuances transparently.

### System Requirements
-   **Python Version:** Python 3.9+
-   **Dependencies:** Standard library (`pathlib`, `os`) - No heavy external dependencies.
-   **Memory:** Negligible.


## Features and Capabilities

### 1. Batch Path Validation
**Description:** Validates multiple paths in a single tool call to reduce round-trip latency and token costs.
**Capabilities:**
*   Categorizes inputs into `valid`, `invalid`, `missing`, and `excluded`.
*   Ignores `code-scalpel` reserved directories (e.g., internal configs) to prevent accidental tampering.

### 2. Docker Awareness Engine
**Description:** Automatically detects if Code Scalpel is running inside a Docker container.
**Capabilities:**
*   **Environment Signature:** Checks for `/.dockerenv` and cgroup markers.
*   **Heuristic Suggestions:** If a path is missing but valid on the host (inferred by structure like `/Users/` or `C:`), it suggests: _"This path looks like a host path. Did you forget to mount a volume? Example: -v /Users/dev/project:/app"_.

### 3. Tier-Gated Security
**Description:** Applies different governance rules based on the active license.
*   **Community:** Enforces a hard limit of 100 paths per call.
*   **Pro/Enterprise:** Unlimited paths; Enterprise adds audit logging for boundary violations (e.g., attempts to access `/etc/passwd`).

## API Specification

The tool is exposed via `mcp_code_scalpel_validate_paths`.

### Request Schema
```python
class ValidatePathsRequest(BaseModel):
    paths: List[str]            # List of file paths to validate
    project_root: Optional[str] # The security boundary root. Defaults to current workspace.
```

### Response Schema
```python
class PathValidationResult(BaseModel):
    # Supported by All Tiers
    valid_paths: List[str]      # Paths that exist and are accessible
    missing_paths: List[str]    # Paths that do not exist
    invalid_paths: List[str]    # Paths that are malformed or outside permitted root
    
    # Context (All Tiers)
    is_docker: bool             # True if running inside container
    workspace_root: str         # The resolved project root used for checks
    
    # Suggestions (All Tiers)
    mount_suggestions: List[str] # Helpful hints for missing paths in Docker
    
    # Tier Information
    truncated: bool = False     # True if input exceeded 100 paths (Community)
    security_score: float       # Enterprise Only: Risk assessment of the path set
```

## Usage Examples

### 1. Basic Pre-Flight Check (Python Client)
Validating that source files exist before attempting extraction.

**Code:**
```python
await validate_paths(
    paths=["src/main.py", "src/utils.py", "missing_config.json"],
    project_root="/app"
)
```

**Response:**
```json
{
  "valid_paths": ["/app/src/main.py", "/app/src/utils.py"],
  "missing_paths": ["/app/missing_config.json"],
  "invalid_paths": [],
  "is_docker": true,
  "workspace_root": "/app",
  "mount_suggestions": []
}
```

### 2. Docker Host Path Confusion (Common Error)
Agent tries to access a host path while running in a container.

**Code:**
```python
await validate_paths(
    paths=["/Users/alice/dev/project/data.csv"],  # Host path on macOS
    project_root="/app"
)
```

**Response:**
```json
{
  "valid_paths": [],
  "missing_paths": ["/Users/alice/dev/project/data.csv"],
  "is_docker": true,
  "mount_suggestions": [
     "Path looks like a host absolute path. Ensure volume is mounted: -v /Users/alice/dev/project:/app"
  ]
}
```

## Architecture and Implementation

### Logic Flow
1.  **Input Normalization**: All paths are converted to `pathlib.Path` objects.
2.  **Safety Check**: `os.path.commonpath([project_root, target_path])` is used to verify the target is physically inside the root. This blocks `../` traversal attacks.
3.  **Existence Probe**: Lightweight `path.exists()` check.
4.  **Docker Heuristics**: If `path.exists()` fails, the path string is analyzed against regex patterns for Windows (`^[a-zA-Z]:`) and macOS (`^/Users/`) absolute paths. If matched inside a container context, a volume mount suggestion is generated.

### Container Detection
The `_is_docker()` helper checks for:
1.  Existence of `/.dockerenv`.
2.  Presence of "docker" or "kubepods" strings in `/proc/1/cgroup` (Linux specific).

## Testing Evidence
As of v1.0.0 (Dec 29, 2025), the tool is validated by a rigorous test suite:

*   **Total Tests**: 118 passing tests (100% pass rate).
*   **Categories**:
    *   ✅ **License Validation**: 15 tests covering valid, invalid, expired, and revoked licenses.
    *   ✅ **Tier Enforcement**: 28 tests verifying the 100-path limit for Community and unlimited for Pro.
    *   ✅ **Cross-Platform**: 28 tests verifying Windows/Linux path handling.
    *   ✅ **Global State**: 100% isolation achieved (no test pollution via env vars).

## Performance Characteristics
*   **Speed**: Path operations are purely filesystem metadata lookups. Latency is negligible (<1ms per path on local SSD).
*   **Scalability**: Linear O(N) complexity with the number of paths. Batching up to 1,000 paths is efficient; beyond that, pagination is recommended for network stability.

## Security Considerations
*   **Directory Traversal**: The tool enforces a strict "jail" mechanism. Any resolved path that does not start with the `project_root` prefix is classified as `invalid` and flagged as a security violation in Enterprise logs.
*   **Symlink Safety**: By default, symlinks are resolved to their real paths before the boundary check, preventing attacks where a symlink inside the root points to `/etc/passwd`.

## Integration Patterns
*   **Standard Workflow**: `validate_paths` -> `analyze_code`.
*   **Reasoning Loop**: An agent should call `validate_paths` immediately after parsing a user prompt containing file references. If paths are missing, the agent can pause and ask the user to fix volume mounts before crashing on a read operation.

## Tier-Specific Behavior

| Feature | Community | Pro | Enterprise |
| :--- | :--- | :--- | :--- |
| **Path Limit** | Max 100 | Unlimited | Unlimited |
| **Traversal Audit** | Blocked (Silent) | Blocked (Silent) | Blocked + Logged |
| **Custom Policies** | ❌ | ❌ | ✅ (Planned) |

## Known Limitations
*   **Network Shares**: Latency checks on NFS/SMB mounts are not currently performed (treated as local paths).
*   **Wildcards**: Does not support glob expansion (e.g., `*.py`). Use `file_search` for discovery, then `validate_paths` for verification.

## Roadmap and Future Plans
*   **v1.1**: Permission checking (read/write/execute bits) in the response model.
*   **v1.2**: Kubernetes Persistent Volume verification.
*   **v1.3**: Advanced Symlink Loop detection.

## Troubleshooting

### Issue: "Path looks like a host absolute path"
*   **Cause**: You are running in Docker but passed a path from your host machine (e.g., `C:\Users`).
*   **Fix**: Mount the directory into the container (e.g., `-v C:\Users\project:/app`) and use the container path (`/app`).

### Issue: "Invalid path: outside project root"
*   **Cause**: You tried to access `../config.json` which resolves to a parent directory outside the workspace.
*   **Fix**: Ensure all assets are inside the `project_root` or expand the root scope.

## References and Related Tools
*   **`os.path`**: Python documentation for path manipulation.
*   **`crawl_project`**: Discovery tool that naturally feeds into `validate_paths`.

