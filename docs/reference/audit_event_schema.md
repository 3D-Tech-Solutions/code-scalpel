# Audit Event Schema

**Status:** Production  
**Version:** v1.0.0  
**Applies to:** All tiers (Community, Pro, Enterprise)

---

## Overview

Code Scalpel provides comprehensive audit trails for all MCP tool invocations through the **Universal Response Envelope**. Every tool response includes audit-relevant metadata that enables compliance tracking, usage analysis, and security monitoring.

This document describes the audit event schema embedded in every tool response.

---

## Audit Fields in Response Envelope

Every MCP tool response includes the following audit-relevant fields:

### Core Audit Metadata

```typescript
interface AuditMetadata {
  // Tier identification
  tier: "community" | "pro" | "enterprise";
  
  // Tool identification
  tool_id: string;           // Canonical MCP tool name (e.g., "security_scan")
  tool_version: string;      // Semantic version (e.g., "3.2.8")
  
  // Request correlation
  request_id: string;        // UUID hex for request tracking
  
  // Capabilities used
  capabilities: string[];    // e.g., ["envelope-v1"]
  
  // Performance tracking
  duration_ms: number | null;  // End-to-end runtime in milliseconds
  
  // Error tracking
  error: ToolError | null;   // Structured error (see error_codes.md)
  
  // Tier compliance
  upgrade_hints: UpgradeHint[];  // Features unavailable at current tier
}
```

### Structured Error Model

When a tool invocation fails, the `error` field contains:

```typescript
interface ToolError {
  error: string;              // Human-readable error message
  error_code: ErrorCode;      // Machine-parseable error code
  error_details: Record<string, any> | null;  // Optional structured details
}

type ErrorCode = 
  | "invalid_argument"
  | "invalid_path"
  | "forbidden"
  | "not_found"
  | "timeout"
  | "too_large"
  | "resource_exhausted"
  | "not_implemented"
  | "upgrade_required"
  | "dependency_unavailable"
  | "internal_error";
```

### Upgrade Hints (Tier Compliance)

When a feature is restricted by tier, `upgrade_hints` contains:

```typescript
interface UpgradeHint {
  feature: string;  // What capability is restricted (e.g., "project-wide search")
  tier: string;     // Tier required to unlock (e.g., "pro")
  reason: string;   // Why restricted (e.g., "Community tier limited to 10 files")
}
```

---

## Audit Use Cases

### 1. Request Correlation

Track individual requests across distributed systems:

```python
response = await security_scan(code=code)
print(f"Request ID: {response['request_id']}")  # "a3f9c8e2d1b4..."
```

### 2. Tier Compliance Monitoring

Verify users are operating within their tier limits:

```python
response = await get_symbol_references(symbol="UserClass")

# Check if tier restrictions applied
if response['upgrade_hints']:
    for hint in response['upgrade_hints']:
        log_tier_limitation(
            user_tier=response['tier'],
            feature=hint['feature'],
            required_tier=hint['tier']
        )
```

### 3. Performance Analysis

Track tool performance and identify bottlenecks:

```python
response = await crawl_project(path="/large/project")

if response['duration_ms']:
    if response['duration_ms'] > 30000:  # 30 seconds
        alert_slow_operation(
            tool=response['tool_id'],
            duration=response['duration_ms'],
            tier=response['tier']
        )
```

### 4. Error Classification

Aggregate errors by type for monitoring:

```python
response = await security_scan(file_path="/nonexistent.py")

if response['error']:
    error_code = response['error']['error_code']
    if error_code == "not_found":
        # Handle file not found
        pass
    elif error_code == "upgrade_required":
        # Prompt user to upgrade tier
        pass
```

### 5. Security Audit Trail

Maintain compliance logs for enterprise customers:

```json
{
  "timestamp": "2025-12-23T10:30:45Z",
  "user_id": "user@example.com",
  "tier": "enterprise",
  "tool_id": "security_scan",
  "tool_version": "3.2.8",
  "request_id": "f3e9a2c1b8d7...",
  "duration_ms": 1234,
  "success": true,
  "capabilities": ["envelope-v1"],
  "upgrade_hints": []
}
```

---

## Audit Log Implementation Guidance

### Recommended Fields for Enterprise Logging

```typescript
interface AuditLogEntry {
  // Standard audit metadata (from response envelope)
  timestamp: string;          // ISO 8601
  tier: string;               // community | pro | enterprise
  tool_id: string;            // MCP tool name
  tool_version: string;       // e.g., "3.2.8"
  request_id: string;         // UUID hex
  duration_ms: number | null; // Performance metric
  
  // Success/failure tracking
  success: boolean;           // Derived from error field
  error_code: string | null;  // Error code if failed
  
  // Tier compliance
  upgrade_hints_count: number;  // Number of tier restrictions hit
  
  // Organization metadata (enterprise-specific)
  user_id?: string;           // User identifier
  organization_id?: string;   // Organization identifier
  session_id?: string;        // Session identifier
  
  // Context (sanitized - never include code content)
  input_size_bytes?: number;  // Input payload size
  output_size_bytes?: number; // Output payload size
}
```

### Security Considerations

**DO NOT LOG:**
- Source code content
- Secrets, tokens, or credentials
- PII (personally identifiable information) unless required for compliance
- File contents or code snippets

**DO LOG:**
- Metadata only (tier, tool_id, request_id, duration, error codes)
- Aggregated metrics (counts, sizes, durations)
- Tier compliance events (upgrade_hints)

---

## Example: End-to-End Audit Flow

### 1. Tool Invocation

```python
response = await get_symbol_references(
    symbol_name="process_payment",
    project_root="/app/backend"
)
```

### 2. Response Envelope

```json
{
  "tier": "community",
  "tool_version": "3.2.8",
  "tool_id": "get_symbol_references",
  "request_id": "9f8e7d6c5b4a3210",
  "capabilities": ["envelope-v1"],
  "duration_ms": 2341,
  "error": null,
  "upgrade_hints": [
    {
      "feature": "project-wide symbol search",
      "tier": "pro",
      "reason": "Community tier limited to 10 files; found 10 references (more may exist)"
    }
  ],
  "data": {
    "symbol_name": "process_payment",
    "total_references": 10,
    "references": [...]
  }
}
```

### 3. Audit Log Entry

```json
{
  "timestamp": "2025-12-23T10:30:45.123Z",
  "tier": "community",
  "tool_id": "get_symbol_references",
  "tool_version": "3.2.8",
  "request_id": "9f8e7d6c5b4a3210",
  "duration_ms": 2341,
  "success": true,
  "error_code": null,
  "upgrade_hints_count": 1,
  "user_id": "user@example.com",
  "organization_id": "acme-corp",
  "session_id": "session_abc123"
}
```

---

## Tier-Specific Audit Requirements

### Community Tier

- **Audit logging:** Optional (users can implement their own)
- **Retention:** Not specified
- **Compliance:** Not required

### Pro Tier

- **Audit logging:** Recommended for production use
- **Retention:** 90 days minimum recommended
- **Compliance:** Customer-managed

### Enterprise Tier

- **Audit logging:** **Required** for compliance
- **Retention:** 1 year minimum (or per compliance requirements)
- **Compliance:** SOC 2, GDPR, HIPAA-ready (customer-managed)
- **Export:** JSON/CSV export for SIEM integration

---

## SIEM Integration

The audit event schema is designed for easy integration with Security Information and Event Management (SIEM) systems:

- **Splunk:** Ingest JSON logs via HEC (HTTP Event Collector)
- **Datadog:** Use structured logging with DD_TRACE_ENABLED
- **Elastic Stack:** Index as JSON documents
- **Custom:** Parse JSON and store in time-series database

---

## Compliance Standards

This audit schema supports compliance with:

- **SOC 2 Type II** (Control Activity Monitoring)
- **GDPR** (Data Processing Records)
- **HIPAA** (Access Audit Logs) - when handling PHI
- **PCI DSS** (Access Control Monitoring) - when processing payment data
- **ISO 27001** (Information Security Audit Trail)

**Note:** Code Scalpel provides audit-ready metadata; customers are responsible for implementing logging infrastructure and retention policies per their compliance requirements.

---

## API Reference

See also:
- [MCP Response Envelope](mcp_response_envelope.md) - Full envelope specification
- [Error Codes](error_codes.md) - Complete error code reference
- [Tier Configuration](../TIER_CONFIGURATION.md) - Tier setup and behavior

---

## Version History

| Version | Date       | Changes |
|---------|------------|---------|
| v1.0.0  | 2025-12-23 | Initial audit event schema documentation |

---

**Next Steps:**
- Implement audit logging in your application layer
- Configure log retention per compliance requirements
- Integrate with your SIEM/monitoring platform
- Set up alerts for tier compliance violations
