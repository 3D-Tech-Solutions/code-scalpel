# verify_policy_integrity - Deep Dive Documentation

> [20260112_DOCS] Comprehensive deep dive documentation for verify_policy_integrity MCP tool based on v2.5.0 implementation

**Document Type:** Tool Deep Dive Reference  
**Tool Version:** v2.5.0  
**Code Scalpel Version:** v1.0.0  
**Last Updated:** 2026-01-12  
**Status:** Stable  
**Tier Availability:** Enterprise Only (Core Governance Feature)

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

---

## Executive Summary

### Purpose Statement
The `verify_policy_integrity` tool is the cryptographic guardian of the Code Scalpel governance model. It ensures that critical policy definitions (allowlists, denylists, compliance rules) have not been tampered with by unauthorized actors, malicious insiders, or compromised processes. By enforcing a **FAIL-CLOSED** security model, it prevents the system from operating under a compromised configuration.

### Key Benefits
- **Immutable Governance:** Cryptographically guarantees that the running policy matches the approved/signed policy.
- **Fail-Closed Security:** Any anomaly (missing stamp, hash mismatch, invalid signature) causes an immediate denial of operations.
- **Bypass Resistance:** Defeats `chmod +w` attacks—even if file permissions are overridden, the cryptographic content verification will still fail.
- **Multi-Source Manifests:** Supports verification against local files, environment variables (CI/CD friendly), or git history constraints.

### Quick Stats
| Metric | Value |
|--------|-------|
| **Tool Version** | v2.5.0 |
| **Code Scalpel Version** | v1.0.0 |
| **Release Date** | 2025-12-20 |
| **Algorithm** | HMAC-SHA256 & SHA-256 |
| **Security Model** | Fail-Closed (Deny by default) |
| **Manifest Formats** | JSON, Signed JWT (Enterprise) |

### When to Use This Tool
- **Primary Use Case:** Pre-flight check before continuously running AI agents with modification capabilities (e.g., `update_symbol`).
- **Secondary Use Cases:**
  - Auditing production environments for "Policy Drift".
  - Verifying integrity of compliance artifacts in CI/CD pipelines.
  - Detecting unauthorized manual edits to `policy.yaml`.

---

## Technical Overview

### Core Functionality
The tool performs a 3-step verification process:
1.  **Manifest Retrieval:** Loads the "Source of Truth" (manifest) containing expected hashes and signatures.
2.  **Signature Verification:** Validates the digital signature of the manifest itself to ensure the *list* of expected hashes hasn't been tampered with.
3.  **Content Verification:** Computes the SHA-256 checksum of every policy file on disk and verifies it against the trusted manifest.

### Design Principles
1.  **Fail-Closed:** If even one byte is off, or one file is missing, the entire verification fails (`success=False`).
2.  **Permission Agnostic:** Does not rely on OS file permissions (which root/admin can bypass), relying instead on mathematical content verification.
3.  **Audit Ready:** Returns detailed error codes and lists specific failed files for forensic analysis.

### System Requirements
-   **Secret Key:** Requires `CODE_SCALPEL_POLICY_KEY` (or similar) to be present in the environment for signature validation.
-   **Policy Directory:** Read access to the configuration folder (default `.code-scalpel`).

---

## Features and Capabilities

### 1. Cryptographic Tamper Detection
**Description:** Detects single-bit changes in policy files using SHA-256 hashing.
**Capabilities:**
*   Detects content modification (edits).
*   Detects file truncation (empty files).
*   Detects file deletion (missing file).

### 2. Manifest Signature Validation
**Description:** Ensures the "reference list" (manifest) itself is authentic.
**Capabilities:**
*   Verifies HMAC-SHA256 signature of the manifest JSON.
*   Prevents "Split-View" attacks where an attacker replaces *both* the policy and the manifest.

### 3. Bypass-Resistant Architecture
**Description:** Designed to withstand privilege escalation on the host.
**Capabilities:**
*   Even if an attacker gains write access (`chmod 777`) and modifies a policy, they cannot generate a valid signature without the separate signing key (stored in a secure vault/env var).

---

## API Specification

The tool is exposed via `mcp_code_scalpel_verify_policy_integrity`.

### Request Schema
```python
class VerifyPolicyIntegrityRequest(BaseModel):
    policy_dir: str = ".code-scalpel"  # Directory containing policies
    manifest_source: str = "file"      # "file", "git", or "env"
```

### Response Schema
```python
class PolicyVerificationResult(BaseModel):
    success: bool            # Master switch: True only if EVERYTHING passes
    manifest_valid: bool     # True if manifest signature is correct
    files_verified: int      # Count of successfully checked files
    files_failed: List[str]  # List of filenames that failed check
    error: Optional[str]     # Human-readable error description
    error_code: Optional[str] # Machine-readable code (e.g. "HASH_MISMATCH")
    manifest_source: Optional[str]
```

---

## Usage Examples

### 1. Standard Pre-Flight Check
Agent verifies integrity before starting a refactoring task.

**Code:**
```python
result = await verify_policy_integrity(
    policy_dir=".code-scalpel",
    manifest_source="file"
)

if not result.success:
    # EMERGENCY STOP
    shutdown_agent(reason=f"Policy Tampering Detected: {result.error}")
```

**Response (Success):**
```json
{
  "success": true,
  "manifest_valid": true,
  "files_verified": 4,
  "files_failed": [],
  "error": null
}
```

**Response (Failure - Tampering):**
```json
{
  "success": false,
  "manifest_valid": true,
  "files_verified": 3,
  "files_failed": ["policy.yaml"],
  "error": "Hash mismatch for policy.yaml: expected a7f3... got b8c9...",
  "error_code": "HASH_MISMATCH"
}
```

---

## Architecture and Implementation

### Verification Logic Flow
1. Load `policy.lock` (the manifest) from `policy_dir`.
2. Retrieve `CODE_SCALPEL_POLICY_KEY` from environment.
3. **Primary Check:** Compute `HMAC(policy.lock.content, key)` vs `policy.lock.signature`.
    *   If fail -> `RETURN error("MANIFEST_INVALID")`
4. Parse `policy.lock` JSON to get map `{ filename: expected_hash }`.
5. **Secondary Check:** Iterate all files in map:
    *   Read file content -> Compute SHA-256.
    *   If `computed != expected` -> Add to `files_failed`.
6. Return Result.

### Key Components
*   `crypto_verify.py`: Core cryptographic primitives using `hashlib` and `hmac`.
*   `tamper_resistance.py`: High-level orchestrator dealing with file IO and error handling.

---

## Tier-Specific Behavior

| Feature | Community | Pro | Enterprise |
| :--- | :--- | :--- | :--- |
| **Availability** | ❌ Not available | ❌ Not available | ✅ Full Feature |
| **Enforcement** | N/A | N/A | Strict (Fail-Closed) |
| **Manifest Source** | N/A | N/A | File, Git, Env |

*Note: This is strictly an Enterprise governance feature designed for regulated environments.*

---

## Security Considerations
*   **Key Management:** The security of this entire system rests on the secrecy of the signing key. This key should be injected into the agent's environment at runtime (e.g., via Vault, AWS Secrets Manager) and never committed to repo.
*   **Race Conditions:** TOCTOU (Time-of-Check Time-of-Use) is minimized by verifying integrity *immediately* before loading policies into memory. Ideally, the `PolicyEngine` loads and verifies in a single atomic transaction.

---

## Roadmap and Future Plans
*   **v3.0:** Hardware Security Module (HSM) support for signature verification.
*   **v3.1:** "Rolling Integrity" - Periodic background re-verification for long-running agents.

---
