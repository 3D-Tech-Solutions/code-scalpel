# Security

Code Scalpel takes security seriously, both in detecting vulnerabilities in your code and in securing its own operations.

## Reporting Security Vulnerabilities

### Contact Information

**Primary Contact:** time@3dtechsolutions.us  
**Secondary Contact:** aescolopio@3dtechsolutions.us

### What to Report

- Security vulnerabilities in Code Scalpel itself
- False negatives in security scanning
- Bypass techniques for policy enforcement
- Crypto/signature verification issues
- Any security concerns with MCP integration

### How to Report

1. **Email** primary contact with:
   - Affected version(s)
   - Reproduction steps
   - Impact assessment
   - Proof of concept (if applicable)

2. **Do NOT** include:
   - Customer data or secrets
   - Excessive payloads
   - Public disclosure before coordination

### Response Timeline

- **Acknowledgement:** ≤1 business day
- **Triage:** ≤3 business days (priority assigned)
- **Resolution:**
  - High/Critical: ≤7 business days
  - Medium: ≤15 business days
  - Low: ≤30 business days

### Disclosure Policy

We prefer **coordinated disclosure**:
1. Report privately via email
2. We triage and develop fix
3. We propose publication date after users have upgrade path
4. **Do NOT** post details publicly until we confirm remediation

## Security Features

### 1. Policy Integrity Verification

Code Scalpel uses **cryptographic signatures** to ensure policy files haven't been tampered with.

#### How It Works

1. **Policy Files** contain security rules and compliance standards
2. **Manifest File** stores HMAC-SHA256 hashes of all policies
3. **Secret Key** (SCALPEL_MANIFEST_SECRET) used to sign manifest
4. **Verification** checks signatures before policy enforcement

#### Setup

```bash
# Initialize with secure secret
python -m code_scalpel init

# This creates .env with:
SCALPEL_MANIFEST_SECRET={random-256-bit-secret}

# Generate policy manifest
code-scalpel regenerate-manifest
```

#### Usage

```python
# Verify policies before enforcement
result = verify_policy_integrity(
    policy_dir="./policies",
    manifest_path="policy_manifest.json"
)

if not result.verified:
    # FAIL CLOSED: Deny operations
    raise SecurityError("Policy integrity check failed")
```

#### Security Model: FAIL CLOSED

| Condition | Action |
|-----------|--------|
| Missing `SCALPEL_MANIFEST_SECRET` | DENY ALL operations |
| Invalid manifest signature | DENY ALL operations |
| Policy file hash mismatch | DENY ALL operations |
| Missing manifest file | DENY ALL operations |

#### Production Deployment

**DO:**
- ✅ Store secret in CI/CD secrets manager (GitHub Secrets, AWS Secrets Manager, Azure Key Vault)
- ✅ Rotate secret if compromised
- ✅ Regenerate manifest after rotation
- ✅ Add `.env` to `.gitignore`

**DON'T:**
- ❌ Commit `.env` to git
- ❌ Share secret in plain text
- ❌ Use same secret across environments
- ❌ Hard-code secret in config files

### 2. Path Validation & Traversal Protection

Prevents path traversal attacks and unauthorized file access.

```python
# Validate paths before file operations
result = validate_paths(
    paths=[user_provided_path],
    base_path="/project",
    allow_symlinks=False
)

if not result.results[0].valid:
    raise SecurityError("Invalid path")
```

**Protections:**
- ✅ Path traversal detection (`../../../etc/passwd`)
- ✅ Absolute path enforcement
- ✅ Symlink restriction (optional)
- ✅ Docker volume boundary enforcement

### 3. Sandbox Execution

Isolate code operations in restricted environments.

```bash
# Enable sandbox mode
SCALPEL_SANDBOX_ENABLED=true
```

**Sandbox Features:**
- Limited filesystem access
- No network access
- Resource limits (memory, CPU, time)
- Process isolation

### 4. Code Policy Enforcement

Automated compliance and security checking.

```python
# Check code against security policies
result = code_policy_check(
    paths=["src/"],
    rules=["SEC001", "SEC002", "SEC003"]  # Security rules
)

# Community tier: Basic security patterns
# Pro tier: Advanced patterns + custom rules
# Enterprise tier: Compliance standards (HIPAA, SOC2, GDPR, PCI-DSS)
```

**Detected Patterns:**

#### Community Tier (Basic Security)
- `SEC001`: Hardcoded passwords
- `SEC002`: SQL string concatenation
- `SEC003`: `os.system()` usage
- `SEC004`: `subprocess` with `shell=True`
- `SEC005`: `pickle` usage (insecure deserialization)
- `SEC006`: `yaml.load` without safe Loader
- `SEC007`: Hardcoded IP addresses
- `SEC008`: Insecure SSL/TLS settings
- `SEC009`: Debug mode enabled in production
- `SEC010`: Weak hashing (MD5/SHA1)

#### Pro Tier (Advanced Security)
- All Community patterns
- Async/await vulnerabilities
- Type hint enforcement
- Custom security rules

#### Enterprise Tier (Compliance)
- All Pro patterns
- HIPAA PHI handling rules
- SOC2 security controls
- GDPR data protection rules
- PCI-DSS payment data rules

## Security Scanning Capabilities

### Taint Analysis

Code Scalpel tracks data flow from **sources** (user input) to **sinks** (dangerous functions).

**Detected Vulnerabilities:**

| CWE | Vulnerability | Severity |
|-----|---------------|----------|
| CWE-89 | SQL Injection | Critical |
| CWE-78 | Command Injection | Critical |
| CWE-79 | Cross-Site Scripting (XSS) | High |
| CWE-22 | Path Traversal | High |
| CWE-94 | Code Injection | Critical |
| CWE-90 | LDAP Injection | High |
| CWE-611 | XML External Entity (XXE) | High |
| CWE-918 | Server-Side Request Forgery (SSRF) | High |
| CWE-601 | Open Redirect | Medium |
| CWE-502 | Insecure Deserialization | Critical |
| CWE-798 | Hardcoded Credentials | High |
| CWE-327 | Weak Cryptography | High |

**Example:**

```python
security_scan(
    code=source_code,
    entry_points=["handle_request"],
    min_confidence=0.8
)
```

**Returns:**
- Vulnerability type (CWE code)
- Severity level
- Source location (where tainted data enters)
- Sink location (where tainted data reaches danger)
- **Taint flow trace** (shows path data takes)
- Confidence score (0-1)
- Remediation recommendations

### Cross-File Security Analysis

Tracks taint flow **across module boundaries**—catches vulnerabilities missed by single-file analysis.

```python
cross_file_security_scan(
    entry_file="api/handlers.py",
    entry_points=["handle_request"],
    max_depth=5
)
```

**Example Scenario:**

```python
# File: api/handlers.py
def handle_request(request):
    user_id = request.GET['id']  # Source: user input
    return process_user(user_id)

# File: services/user.py
def process_user(user_id):
    return database.query(user_id)  # Sink: SQL injection

# Single-file scan: MISS (data flows between files)
# Cross-file scan: DETECT (tracks data across boundary)
```

### Type Evaporation Detection

Identifies where **TypeScript types evaporate** at serialization boundaries.

```python
type_evaporation_scan(
    frontend_code=typescript_code,
    backend_code=python_code
)
```

**Example Vulnerability:**

```typescript
// Frontend: Compile-time type (NO runtime enforcement)
type Role = 'admin' | 'user';
const role = input.value as Role;  // ⚠️ Type assertion, no validation

fetch('/api/users', {
  method: 'POST',
  body: JSON.stringify({ role })  // Type evaporates here!
});
```

```python
# Backend: No type checking!
@app.route('/api/users', methods=['POST'])
def create_user():
    role = request.get_json()['role']  # ⚠️ Accepts ANY value
    # Attacker can send: role="superadmin"
```

**Detection:** Cross-references TypeScript union types with backend validation logic.

## Best Practices

### 1. Initialize Security Configuration

```bash
# Create .env with secure defaults
python -m code_scalpel init

# This generates:
# - Random SCALPEL_MANIFEST_SECRET
# - Policy directory structure
# - Initial manifest
```

### 2. Store Secrets Securely

**GitHub Actions:**
```yaml
# .github/workflows/security.yml
env:
  SCALPEL_MANIFEST_SECRET: ${{ secrets.SCALPEL_SECRET }}
```

**Docker:**
```bash
# Use secrets management
docker run -e SCALPEL_MANIFEST_SECRET=$(cat /run/secrets/scalpel_secret) ...
```

**AWS Lambda:**
```python
import boto3

secrets = boto3.client('secretsmanager')
secret = secrets.get_secret_value(SecretId='scalpel-manifest-secret')
os.environ['SCALPEL_MANIFEST_SECRET'] = secret['SecretString']
```

### 3. Rotate Secrets Regularly

```bash
# Generate new secret
python -c "import secrets; print(secrets.token_hex(32))"

# Update .env
SCALPEL_MANIFEST_SECRET={new-secret}

# Regenerate manifest
code-scalpel regenerate-manifest

# Update CI/CD secrets
# Update production deployment
```

### 4. Validate All Paths

```python
# Before file operations
validate_result = validate_paths(
    paths=[user_input_path],
    base_path=PROJECT_ROOT,
    allow_symlinks=False
)

if not validate_result.results[0].valid:
    raise SecurityError("Path validation failed")

# Then proceed with file operation
extract_code(file_path=user_input_path, ...)
```

### 5. Run Security Scans in CI

```yaml
# .github/workflows/security.yml
- name: Code Scalpel Security Scan
  run: |
    python -c "
    from code_scalpel.mcp.helpers.security_helpers import security_scan
    import sys
    
    result = security_scan(
        code=open('src/app.py').read(),
        min_confidence=0.8
    )
    
    if result.vulnerabilities:
        print(f'Found {len(result.vulnerabilities)} vulnerabilities')
        for vuln in result.vulnerabilities:
            print(f'{vuln.cwe}: {vuln.description}')
        sys.exit(1)
    "
```

### 6. Enable Sandbox in Production

```bash
# Production deployment
SCALPEL_SANDBOX_ENABLED=true
SCALPEL_MAX_FILE_SIZE=10485760  # 10 MB limit
SCALPEL_MAX_COMPLEXITY=100
```

## Security Scope

### In Scope

- MCP server implementation
- Surgical code tools (extraction, modification)
- AST/PDG/symbolic/security analysis modules
- Policy enforcement and integrity verification
- Official documentation and release artifacts

### Out of Scope

- Third-party dependencies (report to upstream)
- Demo/example code (not production-grade)
- Forks not maintained by 3D Tech Solutions

## Safe Harbor

Research conducted under this policy will not be pursued legally if:
- ✅ Performed in good faith
- ✅ Reported privately via proper channels
- ✅ No exploitation in production
- ✅ No access to other users' data
- ✅ No denial-of-service attacks

## Release Security Checklist

Every Code Scalpel release must pass:

- ✅ **Tests:** `pytest` green, mutation smoke + fuzz tests
- ✅ **Coverage:** ≥90% combined (statement + branch)
- ✅ **Lint:** `ruff` and `black` clean
- ✅ **SBOM:** Generated and stored in `release_artifacts/`
- ✅ **Dependency Scan:** OSV/pip-audit with no high/critical vulns
- ✅ **Signing:** Sigstore/Cosign signatures for release artifacts
- ✅ **Evidence:** Credibility bundle with benchmarks and verification

## Governance & Roles

| Role | Responsibilities |
|------|------------------|
| **Maintainer** | Release authority, gate enforcement, artifact signing |
| **Security Lead** | CVE coordination, vulnerability triage, scan review |
| **Reviewer** | Test/lint/coverage enforcement on PRs |

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST Secure Software Development Framework](https://csrc.nist.gov/projects/ssdf)

---

**Related Pages:**
- [Configuration](Configuration) - Security environment variables
- [MCP Tools Reference](MCP-Tools-Reference) - Security scanning tools
- [Contributing](Contributing) - Security testing guidelines
