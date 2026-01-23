# Policy Integrity Verification - Pro & Enterprise Features

## Overview

The `verify_policy_integrity` MCP tool provides cryptographic verification of policy files to prevent unauthorized modifications. This is essential for tamper-resistant governance in multi-agent environments.

**Security Model: FAIL CLOSED**
- Missing manifest → DENY ALL operations
- Invalid signature → DENY ALL operations  
- Hash mismatch → DENY ALL operations
- Any error → DENY ALL operations

## Tier-Based Features

### Community Tier
**Capabilities:**
- `basic_verification`: Format validation of policy files
- Checks for file existence
- Validates YAML/JSON syntax
- No cryptographic verification

**Use Case:** Development and testing environments

### Pro Tier  
**Capabilities:**
- All Community features
- `signature_validation`: HMAC-SHA256 cryptographic verification
- `tamper_detection`: SHA-256 file hash checking
- Manifest signature validation
- File integrity verification

**Use Case:** Production deployments with security requirements

### Enterprise Tier
**Capabilities:**
- All Pro features
- `full_integrity_check`: Comprehensive verification workflow
- `audit_logging`: Detailed audit trail of all verification attempts
- Compliance reporting
- Forensic analysis on failures

**Use Case:** Regulated industries (healthcare, finance, government)

## How It Works

### 1. Administrator Workflow

Administrators create a cryptographically signed manifest of policy files:

```python
from code_scalpel.policy_engine.crypto_verify import CryptographicPolicyVerifier

# Create manifest
manifest = CryptographicPolicyVerifier.create_manifest(
    policy_files=["policy.yaml", "budget.yaml", "rules.yaml"],
    secret_key=os.environ["SCALPEL_MANIFEST_SECRET"],  # From secure storage
    signed_by="admin@company.com",
    policy_dir=".code-scalpel",
)

# Save to file
manifest_path = CryptographicPolicyVerifier.save_manifest(
    manifest,
    ".code-scalpel",
)

# Commit to git (recommended for git source)
# git add .code-scalpel/policy.manifest.json
# git commit -m "Add signed policy manifest"
```

### 2. Agent Workflow

Before performing operations, agents verify policy integrity:

```python
from code_scalpel.mcp import verify_policy_integrity

# Verify policies
result = await verify_policy_integrity(
    policy_dir=".code-scalpel",
    manifest_source="git",  # or "env" or "file"
)

if not result.success:
    print(f"SECURITY: {result.error}")
    # Fail closed - deny all operations
    sys.exit(1)
else:
    print(f"✓ Verified {result.files_verified} policy files")
    # Proceed with operations
```

### 3. Manifest Sources

#### Git (Most Secure)
Loads manifest from committed version in git history. Agent cannot modify without creating a visible commit.

```python
result = await verify_policy_integrity(
    policy_dir=".code-scalpel",
    manifest_source="git",
)
```

**Advantages:**
- Immutable (part of git history)
- Auditable (git log shows any changes)
- Agent cannot tamper without detection

**Requirements:**
- Policy directory must be in a git repository
- Manifest must be committed to git

#### Environment Variable (CI/CD)
Loads manifest from `SCALPEL_POLICY_MANIFEST` environment variable. Useful for CI/CD pipelines.

```python
result = await verify_policy_integrity(
    policy_dir=".code-scalpel",
    manifest_source="env",
)
```

**Advantages:**
- Centrally managed (CI/CD secrets)
- No local files to tamper with
- Easy to rotate

**Requirements:**
- Set `SCALPEL_POLICY_MANIFEST` with JSON manifest
- Typically injected by CI/CD system

#### File (Development)
Loads manifest from local file. Less secure but convenient for development.

```python
result = await verify_policy_integrity(
    policy_dir=".code-scalpel",
    manifest_source="file",
)
```

**Advantages:**
- Simple to set up
- Works without git or CI/CD

**Disadvantages:**
- Agent could potentially modify manifest file
- Not recommended for production

## Manifest Format

The manifest is a JSON file containing:

```json
{
  "version": "1.0",
  "created_at": "2025-01-08T14:30:00.000Z",
  "signed_by": "admin@company.com",
  "files": {
    "policy.yaml": "sha256:a1b2c3d4e5f6...",
    "budget.yaml": "sha256:f6e5d4c3b2a1..."
  },
  "signature": "hmac-sha256:abcdef123456..."
}
```

**Fields:**
- `version`: Manifest format version (currently "1.0")
- `created_at`: ISO 8601 timestamp of manifest creation
- `signed_by`: Identity of the administrator who signed it
- `files`: Dictionary mapping filename to SHA-256 hash
- `signature`: HMAC-SHA256 signature of the manifest

## Cryptographic Details

### File Hashing (SHA-256)
Each policy file is hashed using SHA-256:

```python
import hashlib

def hash_file(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return "sha256:" + hasher.hexdigest()
```

### Manifest Signing (HMAC-SHA256)
The manifest is signed using HMAC-SHA256:

```python
import hmac
import hashlib
import json

def sign_manifest(manifest_data, secret_key):
    # Create canonical JSON representation
    message = json.dumps(
        {
            "version": manifest_data["version"],
            "files": manifest_data["files"],
            "created_at": manifest_data["created_at"],
            "signed_by": manifest_data["signed_by"],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    
    # Generate HMAC signature
    signature = hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()
    
    return signature
```

### Signature Verification
Uses constant-time comparison to prevent timing attacks:

```python
import hmac

def verify_signature(expected, actual):
    # Constant-time comparison
    return hmac.compare_digest(expected, actual)
```

## Security Considerations

### Secret Key Management

**Do:**
- ✅ Store secret in secure vault (HashiCorp Vault, AWS Secrets Manager)
- ✅ Use environment variables injected by CI/CD
- ✅ Rotate secrets periodically
- ✅ Use different secrets for dev/staging/production

**Don't:**
- ❌ Hardcode secret in source code
- ❌ Commit secret to git
- ❌ Share secret in chat/email
- ❌ Use weak secrets (use at least 32 random bytes)

### Attack Prevention

#### Tampering Detection
If an agent modifies a policy file, the hash mismatch is detected:

```
Original hash:  sha256:a1b2c3d4e5f6...
Current hash:   sha256:f6e5d4c3b2a1...  ❌ MISMATCH!
```

#### Signature Forgery Prevention
Even if an agent modifies both the policy and manifest, it cannot forge the HMAC signature without the secret key.

#### Bypass Prevention
File permissions (`chmod 0444`) can be bypassed, but hash verification detects any modification regardless of how it was made.

## Troubleshooting

### "SCALPEL_MANIFEST_SECRET environment variable not set"

**Cause:** The signing secret is not available to the verification process.

**Solution:**
```bash
export SCALPEL_MANIFEST_SECRET='your-secret-key-here'
```

### "Policy manifest not found in git history"

**Cause:** Manifest file not committed to git when using `manifest_source="git"`.

**Solution:**
```bash
git add .code-scalpel/policy.manifest.json
git commit -m "Add signed policy manifest"
```

### "Policy manifest signature INVALID"

**Cause:** Manifest has been tampered with, or wrong secret key is being used.

**Solutions:**
1. Verify correct secret key is set
2. Regenerate manifest with correct secret
3. Check for unauthorized modifications

### "Policy files tampered or missing"

**Cause:** Policy file contents don't match the hash in the manifest.

**Solutions:**
1. If intentional change: Regenerate manifest
2. If unintentional: Restore from git/backup
3. If attack: Investigate security incident

## Integration Examples

### VS Code MCP Client

Configure in `.vscode/mcp.json`:

```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "uv",
      "args": ["--directory", "/path/to/code-scalpel", "run", "code-scalpel"],
      "env": {
        "CODE_SCALPEL_TIER": "enterprise",
        "SCALPEL_MANIFEST_SECRET": "${env:SCALPEL_MANIFEST_SECRET}"
      }
    }
  }
}
```

Set secret in your shell:
```bash
export SCALPEL_MANIFEST_SECRET='your-secret-key'
code .  # Launch VS Code
```

### Claude Desktop

Configure in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "code-scalpel": {
      "command": "uv",
      "args": ["--directory", "/path/to/code-scalpel", "run", "code-scalpel"],
      "env": {
        "CODE_SCALPEL_TIER": "pro",
        "SCALPEL_MANIFEST_SECRET": "your-secret-key"
      }
    }
  }
}
```

### CI/CD Pipeline

GitHub Actions example:

```yaml
name: Agent Operations

on: [push]

jobs:
  agent-task:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install Code Scalpel
        run: pip install code-scalpel
      
      - name: Run agent with policy verification
        env:
          SCALPEL_MANIFEST_SECRET: ${{ secrets.SCALPEL_MANIFEST_SECRET }}
          CODE_SCALPEL_TIER: enterprise
        run: |
          python agent_script.py
```

## API Reference

### MCP Tool

```python
async def verify_policy_integrity(
    policy_dir: str | None = None,
    manifest_source: str = "file",
) -> PolicyVerificationResult
```

**Parameters:**
- `policy_dir`: Directory containing policy files (default: ".code-scalpel")
- `manifest_source`: Where to load manifest from ("git", "env", or "file")

**Returns:** `PolicyVerificationResult` with:
- `success`: `bool` - True if verification passed
- `manifest_valid`: `bool` - True if signature is valid
- `files_verified`: `int` - Number of files successfully verified
- `files_failed`: `List[str]` - List of files that failed verification
- `signature_validated`: `bool` - True if HMAC signature was checked
- `tamper_detection_enabled`: `bool` - True if hash checking was enabled
- `audit_log_entry`: `Dict` - Audit log entry (Enterprise tier only)
- `error`: `str | None` - Error message if verification failed

### Python API

```python
from code_scalpel.policy_engine.crypto_verify import (
    CryptographicPolicyVerifier,
    PolicyManifest,
    SecurityError,
)

# Create verifier
verifier = CryptographicPolicyVerifier(
    manifest_source="git",  # or "env" or "file"
    policy_dir=".code-scalpel",
)

# Verify all policies
try:
    result = verifier.verify_all_policies()
    print(f"Verified {result.files_verified} files")
except SecurityError as e:
    print(f"SECURITY ERROR: {e}")
    sys.exit(1)

# Verify single file
verifier.verify_single_file("policy.yaml")
```

## Best Practices

1. **Use git source in production** - Most secure, auditable, immutable
2. **Rotate secrets regularly** - Regenerate manifest with new secret periodically
3. **Monitor verification failures** - Set up alerts for tamper detection
4. **Separate dev/prod secrets** - Use different secrets for different environments
5. **Automate manifest generation** - Include in your deployment pipeline
6. **Test verification in CI** - Verify policies as part of CI/CD
7. **Document secret management** - Ensure team knows how to rotate secrets

## License

This feature is available under the Apache 2.0 license. See LICENSE file for details.

## Support

For issues or questions:
- GitHub Issues: https://github.com/3DTechSolutions/code-scalpel/issues
- Email: time@3dtechsolutions.us
