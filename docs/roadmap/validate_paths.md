# validate_paths Tool Roadmap

**Tool Name:** `validate_paths`  
**Tool Version:** v1.0  
**Code Scalpel Version:** v3.3.1  
**Current Status:** Stable  
**Primary Module:** `src/code_scalpel/mcp/server.py` (lines ~20368-20770)  
**Tier Availability:** All tiers (Community, Pro, Enterprise)

---

## Configuration Files

| File | Purpose |
|------|---------|
| `src/code_scalpel/licensing/features.py` | Tier capability definitions |
| `.code-scalpel/limits.toml` | Numeric limits (max_paths) |
| `.code-scalpel/response_config.json` | Output filtering (exclude validation_metadata, stat_results) |

---

## Overview

The `validate_paths` tool checks if file paths are accessible before running operations. Essential for Docker deployments where volume mounts must be configured correctly.

**Why AI Agents Need This:**
- **Pre-flight validation:** Verify paths before expensive operations
- **Docker awareness:** Detect container vs host path issues automatically
- **Clear guidance:** Actionable error messages with mount suggestions
- **Batch efficiency:** Validate multiple paths in one call
- **Deployment debugging:** Essential for containerized AI agent deployments

---

## Research Queries for Future Development

### Foundational Research
| Topic | Query | Purpose |
|-------|-------|---------|
| Path Resolution | "cross-platform path resolution algorithms" | Better OS support |
| Docker Volumes | "docker volume mount best practices troubleshooting" | Improve suggestions |
| Filesystem | "filesystem permission checking techniques" | Permission detection |
| Network Storage | "network filesystem latency detection timeout" | Network drive support |

### Platform-Specific Research
| Topic | Query | Purpose |
|-------|-------|---------|
| Windows | "windows UNC path handling best practices" | Windows support |
| Linux | "linux symbolic link resolution security" | Symlink handling |
| macOS | "macos file system case sensitivity handling" | macOS quirks |
| Container | "container filesystem overlay mount detection" | Container detection |

### Advanced Techniques
| Topic | Query | Purpose |
|-------|-------|---------|
| Auto-Mount | "automated docker volume mount configuration" | Smart mounting |
| Cloud Storage | "cloud storage path validation S3 Azure GCS" | Cloud support |
| Kubernetes | "kubernetes persistent volume path validation" | K8s integration |
| Performance | "filesystem operation caching strategies" | Fast validation |

---

## Current Capabilities (v1.0)

### All Tiers
| Capability | Config Name |
|------------|-------------|
| ✅ Path accessibility checking | `path_accessibility_checking` |
| ✅ Docker environment detection | `docker_environment_detection` |
| ✅ Workspace root detection | `workspace_root_detection` |
| ✅ Actionable error messages | `actionable_error_messages` |
| ✅ Docker volume mount suggestions | `docker_volume_mount_suggestions` |
| ✅ Batch path validation | `batch_path_validation` |

### Community Tier Limits
- `max_paths`: 100 (from limits.toml)

### Pro/Enterprise Tier Limits
- `max_paths`: unlimited

---

## Return Model: PathValidationResult

```python
class PathValidationResult(BaseModel):
  # Core fields (All Tiers)
  success: bool                              # Whether all paths were accessible
  error: str | None                          # Error message when failed
  error_code: str | None                     # Machine-readable error code (when failed)

  # Tier limit signaling (Community only)
  truncated: bool | None                     # True when input exceeded max_paths
  paths_received: int | None                 # Original number of input paths
  paths_checked: int | None                  # Number of paths actually validated
  max_paths_applied: int | None              # Applied max_paths value

  # Core results (All Tiers)
  accessible: list[str]                      # Resolved/accessible paths
  inaccessible: list[str]                    # Paths that could not be resolved
  suggestions: list[str]                     # Actionable guidance (mounts, batching, roots)
  workspace_roots: list[str]                 # Detected workspace root directories
  is_docker: bool                            # Whether running in a Docker container

  # Pro Tier (v1.0: preview features now implemented)
  alias_resolutions: list[dict]              # tsconfig/webpack alias mappings
  dynamic_imports: list[dict]                # Detected dynamic import patterns

  # Enterprise Tier (v1.0: preview features now implemented)
  traversal_vulnerabilities: list[dict]      # Traversal sequence detection (..)
  boundary_violations: list[dict]            # Workspace boundary escape warnings
  security_score: float | None               # 0.0-10.0 score derived from findings
```

Notes:
- Community-tier limit behavior is truncation, not hard failure: when `max_paths=100` is exceeded, the tool validates the first 100 and sets `truncated`, `paths_received`, `paths_checked`, and `max_paths_applied`, plus batching suggestions.
- Output verbosity is controlled by `.code-scalpel/response_config.json` and may exclude empty/default fields.

---

## Usage Examples

### Community Tier
```python
result = await validate_paths(
    paths=["/app/src/main.py", "/app/data/config.json"]
)
# Returns: accessible/inaccessible lists, workspace_roots, is_docker, suggestions
# Max 100 paths; when exceeded, truncation fields are set
```

### Pro Tier
```python
result = await validate_paths(
  paths=["/app/src", "/app/data"],
  project_root="/workspace/project"
)
# Additional (tier-gated): alias_resolutions, dynamic_imports
# Unlimited paths
```

### Enterprise Tier
```python
result = await validate_paths(
  paths=["../secrets", "/app/logs"],
  project_root="/workspace/project"
)
# Additional (tier-gated): traversal_vulnerabilities, boundary_violations, security_score
```

---

## Integration Points

### Related Tools
| Tool | Relationship |
|------|--------------|
| `crawl_project` | Validate project root before crawling |
| `extract_code` | Validate file paths before extraction |
| `update_symbol` | Ensure file accessible before update |
| `security_scan` | Validate file paths before scanning |

### Export Formats
| Format | Status | Use Case |
|--------|--------|----------|
| **JSON** | ✅ v1.0 | Programmatic results |
| **Text** | ✅ v1.0 | Human-readable output |
| **Docker Compose** | 🔄 v1.2 | Volume mount YAML |

---

## Competitive Analysis

| Tool | Strengths | Weaknesses | Our Differentiation |
|------|-----------|------------|---------------------|
| **os.path.exists** | Built-in | No suggestions | Actionable guidance |
| **pathlib** | Modern API | No Docker awareness | Container detection |
| **Docker CLI** | Authoritative | Manual checking | Automated batch |
| **test -f/-d** | Simple | No cross-platform | Cross-platform |
| **fs.access (Node)** | JS native | Node only | Multi-language |

---

## MCP Request/Response Examples

### MCP Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "mcp_code-scalpel_validate_paths",
    "arguments": {
      "paths": ["/app/src/main.py", "/app/data/config.json"]
    }
  },
  "id": 1
}
```

### Community Tier Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": false,
    "accessible": ["/app/src/main.py"],
    "inaccessible": ["/app/data/config.json"],
    "suggestions": [
      "Running in Docker: Mount your project with -v /path/to/project:/workspace",
      "Example: docker run -v $(pwd):/workspace code-scalpel:latest"
    ],
    "workspace_roots": ["/app"],
    "is_docker": true
  },
  "id": 1
}
```

### Pro Tier Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "accessible": ["/workspace/project/src/index.ts"],
    "inaccessible": [],
    "suggestions": [],
    "workspace_roots": ["/workspace/project"],
    "is_docker": true,
    "alias_resolutions": [
      {
        "alias": "@app",
        "original_path": "src/*",
        "resolved_path": "/workspace/project/src",
        "source": "tsconfig.json"
      }
    ],
    "dynamic_imports": [
      {
        "source_file": "/workspace/project/src/index.ts",
        "import_pattern": "dynamic_import_detected",
        "resolved_paths": []
      }
    ]
  },
  "id": 1
}
```

### Enterprise Tier Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "accessible": ["/workspace/project/app.py"],
    "inaccessible": [],
    "suggestions": [],
    "workspace_roots": ["/workspace/project"],
    "is_docker": true,
    "traversal_vulnerabilities": [
      {
        "path": "../secrets",
        "escape_attempt": "Contains 1 parent directory references",
        "severity": "high",
        "recommendation": "Remove traversal sequences or validate against whitelist"
      }
    ],
    "boundary_violations": [
      {
        "path": "/secrets",
        "boundary": "/workspace/project",
        "violation_type": "workspace_escape",
        "risk": "high"
      }
    ],
    "security_score": 7.5
  },
  "id": 1
}
```

---

## Roadmap

### v1.1 (Q1 2026): Enhanced Validation

#### All Tiers
- [ ] Per-path detail results (exists/is_file/is_dir/reason) while keeping token-efficient defaults
- [ ] Permission checking (read/write/execute) surfaced as structured output (Enterprise)
- [ ] Symlink resolution + symlink loop detection
- [ ] Network path support (UNC/NFS) with smarter suggestions
- [ ] Better mount suggestions keyed to common layouts (/app, /workspace)

#### Pro Tier
- [ ] Deeper alias resolution (globs, multiple targets, monorepo workspaces)
- [ ] Dynamic import path enrichment (optional)

#### Enterprise Tier
- [ ] Custom allow/deny policy rules integrated with governance config
- [ ] Audit logging for path validation calls
- [ ] Boundary enforcement modes (warn vs deny)

### v1.2 (Q2 2026): Integration Features

#### Community Tier
- [ ] GitHub Actions integration
- [ ] GitLab CI helpers
- [ ] Docker Compose validation

#### Pro Tier
- [ ] Kubernetes volume validation
- [ ] Cloud storage path validation
- [ ] Remote filesystem support

#### Enterprise Tier
- [ ] Multi-cloud path validation
- [ ] VPN/VPC path checking
- [ ] Compliance-based path rules

### v1.3 (Q3 2026): Performance & Reliability

#### All Tiers
- [ ] Faster path validation (<10ms)
- [ ] Batch optimization
- [ ] Caching for repeated checks

#### Pro Tier
- [ ] Async path validation
- [ ] Parallel validation

#### Enterprise Tier
- [ ] Distributed path validation
- [ ] Real-time path monitoring

### v1.4 (Q4 2026): Advanced Features

#### Pro Tier
- [ ] Path recommendation engine
- [ ] Automated mount configuration
- [ ] Path migration helpers

#### Enterprise Tier
- [ ] Custom validation plugins
- [ ] Infrastructure-as-code generation
- [ ] Automated remediation

---

## Known Issues & Limitations

### Current Limitations
- **Windows paths:** Limited Windows UNC path support
- **Network drives:** Network drive latency may cause timeouts
- **Container paths:** Complex container path mapping not fully detected

### Planned Fixes
- v1.1: Full Windows path support
- v1.2: Network drive optimization
- v1.3: Better container detection

---

## Success Metrics

### Performance Targets
- **Validation time:** <50ms per path
- **Accuracy:** >99% correct accessibility detection
- **Docker detection:** 100% accurate

### Adoption Metrics
- **Usage:** 200K+ validations per month by Q4 2026
- **Error prevention:** 90% of path errors caught early

---

## Dependencies

### Internal Dependencies
- None

### External Dependencies
- Python `os` and `pathlib` modules

---

## Breaking Changes

None planned for v1.x series.

---

**Last Updated:** December 30, 2025  
**Next Review:** March 31, 2026
