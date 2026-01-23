# Code Scalpel Licensing System - Quick Reference

**Status**: Understanding document for feature extraction planning
**Created**: January 8, 2026
**Purpose**: Explain how the current licensing system works in v3.3.0

---

## 1. Current Licensing Architecture (v3.3.0)

The licensing system in Code Scalpel v3.3.0 uses **JWT tokens** with two-stage validation:

### Components

| Component | File | Purpose | Tier Support |
|-----------|------|---------|--------------|
| **JWTLicenseValidator** | `licensing/jwt_validator.py` | Parse and validate JWT tokens | Pro/Enterprise |
| **TierDetector** | `licensing/tier_detector.py` | Detect tier from environment/files | All |
| **LicenseManager** | `licensing/license_manager.py` | Central license state management | All |
| **FeatureRegistry** | `tiers/feature_registry.py` | Map features to required tiers | All |
| **LicenseValidator** | `licensing/validator.py` | Legacy HMAC validation (deprecated) | Pro/Enterprise |

---

## 2. How Tier Detection Works

**Priority Order** (first match wins):

```
1. CODE_SCALPEL_TIER env var
   └─> Returns immediately if set

2. License JWT file (path discovery)
   ├─> CODE_SCALPEL_LICENSE_PATH (explicit override)
   ├─> .code-scalpel/license/license.jwt
   ├─> ~/.config/code-scalpel/license.jwt
   ├─> ~/.code-scalpel/license.jwt
   └─> .scalpel-license (legacy)

3. Config file
   ├─> .code-scalpel/license.json
   ├─> ~/.code-scalpel/license.json
   └─> /etc/code-scalpel/license.json

4. Organization-based detection
   └─> CODE_SCALPEL_ORGANIZATION env var

5. Default: COMMUNITY tier
```

**Example Usage**:
```python
from code_scalpel.licensing import get_current_tier

tier = get_current_tier()  # Returns: "community", "pro", or "enterprise"
# → Checks env var first, then license file, then config, then defaults
```

---

## 3. JWT License Structure

### Token Format
```
JWT Header:
{
  "typ": "JWT",
  "alg": "RS256"  # RSA with SHA-256 (recommended)
}

JWT Payload (Claims):
{
  "iss": "code-scalpel-licensing",        # Issuer
  "sub": "customer_id_12345",             # Subject (customer ID)
  "aud": "code-scalpel-users",            # Audience
  "tier": "pro" | "enterprise",           # License tier
  "exp": 1735689600,                      # Expiration (Unix timestamp)
  "iat": 1704153600,                      # Issued at
  "jti": "unique-token-id",               # JWT ID (for revocation)
  "nbf": 1767287075,                      # Not before
  "org": "Acme Corporation",              # Organization name
  "seats": 10,                            # Number of seats
  "features": [                           # Available features
    "advanced_analysis",
    "enterprise_integration"
  ]
}

JWT Signature:
HMACSHA256(base64(header) + "." + base64(payload), secret)
```

### Real Examples (Test Licenses)

Located in `/tests/licenses/`:

```
code_scalpel_license_pro_20260101_190345.jwt
  ↓ Decodes to:
{
  "tier": "pro",
  "sub": "test-pro-001",
  "iss": "code-scalpel",
  "aud": "code-scalpel-users",
  "exp": 1798823075,
  "iat": 1767287075,
  "jti": "unique-pro-token",
  "org": "Test Pro Organization",
  "seats": 1
}

code_scalpel_license_enterprise_20260101_190754.jwt
  ↓ Decodes to:
{
  "tier": "enterprise",
  "sub": "test-enterprise-001",
  "iss": "code-scalpel",
  "aud": "code-scalpel-users",
  "exp": 1798823075,
  "iat": 1767287075,
  "jti": "unique-enterprise-token",
  "org": "Test Enterprise Organization",
  "seats": 100
}
```

---

## 4. Two-Stage Validation Process

### Stage 1: Offline Validation (Always Happens)

```python
validator = JWTLicenseValidator()
license_data = validator.validate_offline(license_jwt)
# Returns: JWTLicenseData with:
# - tier: str
# - customer_id: str
# - is_valid: bool
# - error_message: str (if invalid)
# - is_expired: bool
```

**What it checks**:
- ✅ JWT signature is valid (cryptographic verification)
- ✅ Claims are present (iss, aud, tier, sub, exp, etc.)
- ✅ Token expiration time
- ✅ Token "not before" time
- ✅ Signature algorithm is RS256 or HS256

**Location**: RSA public key embedded in:
```
src/code_scalpel/licensing/public_key/vault-prod-2026-01.pem
```

**No network required**: Pure cryptographic verification.

### Stage 2: Online Validation (Every 24 Hours)

```python
validator = JWTLicenseValidator()
license_data = validator.validate_online(license_jwt)
# Returns: JWTLicenseData with:
# - is_valid: bool
# - is_revoked: bool
# - grace_period_remaining: int (days)
```

**What it checks**:
- ✅ License is not revoked (checked against CRL)
- ✅ License hasn't been transferred to another user
- ✅ Organization status is active
- ✅ Seat limits not exceeded

**When it happens**:
- First validation of a license
- Every 24 hours (cached)
- Can be triggered manually with `force_refresh=True`

**Grace period**:
- If verifier is offline: 24h grace period
- If offline for too long: Requires manual refresh every 48h
- After 48h without valid online check: License becomes invalid

**Fallback behavior**:
```python
# If CODE_SCALPEL_LICENSE_VERIFIER_URL is unreachable:
# 1. First 24h: License still valid (grace period)
# 2. 24-48h: License still valid but warning logged
# 3. After 48h: License invalid (must refresh online)
```

---

## 5. License Validation in Practice

### Scenario 1: User has Pro license

```bash
# License in ~/.code-scalpel/license.jwt
export CODE_SCALPEL_TIER=""  # Not set, will auto-detect

# In Python:
from code_scalpel.licensing import get_current_tier, get_license_info

tier = get_current_tier()  # → Detects "pro" from JWT file
# Process:
# 1. Check CODE_SCALPEL_TIER env var (not set)
# 2. Find license file at ~/.code-scalpel/license.jwt
# 3. Parse JWT, validate signature
# 4. Check expiration, validate online
# 5. Return "pro"

info = get_license_info()
# Returns:
# {
#   "tier": "pro",
#   "customer_id": "customer_12345",
#   "organization": "Acme Corp",
#   "is_valid": True,
#   "is_expired": False,
#   "days_until_expiration": 365,
#   "seats": 10,
#   "features": ["advanced_analysis", ...]
# }
```

### Scenario 2: User has Community tier (no license)

```bash
# No license file, no env var
from code_scalpel.licensing import get_current_tier

tier = get_current_tier()  # → "community"
# Process:
# 1. Check CODE_SCALPEL_TIER env var (not set)
# 2. No license file found
# 3. No config file found
# 4. No organization env var
# 5. Default to "community"

# IMPORTANT: Community tier requires NO license
# Features are available based on tier level only
```

### Scenario 3: License expired but within grace period

```python
from code_scalpel.licensing import get_license_info, get_current_tier

tier = get_current_tier()  # Still returns "pro"
info = get_license_info()

if info["is_expired"] and not info["is_revoked"]:
    if info["grace_period_remaining"] > 0:
        print(f"Grace period: {info['grace_period_remaining']} days")
        # License still works but user should renew
    else:
        # Grace period expired, license invalid
        tier = "community"  # Falls back to Community tier
```

---

## 6. Feature Gating Based on Tier

### Current Implementation (v3.3.0)

```python
# In FeatureRegistry
class FeatureRegistry:
    def is_enabled(self, feature_name: str) -> bool:
        """Check if feature is available at current tier."""
        feature = self._features.get(feature_name)
        current_tier = get_current_tier()
        current_level = TIER_LEVELS.get(current_tier, 0)
        required_level = TIER_LEVELS.get(feature.tier, 0)
        return current_level >= required_level

# Tier hierarchy
TIER_LEVELS = {
    "community": 0,
    "pro": 1,
    "enterprise": 2
}

# Example: Checking if advanced analysis is available
registry = FeatureRegistry()
if registry.is_enabled("advanced_analysis"):
    # Available (requires Pro tier)
    # User has Pro or Enterprise
else:
    # Not available (requires upgrade)
    # User has only Community
```

### Feature Definitions

```python
DEFAULT_FEATURES = {
    # COMMUNITY features
    "analyze_code": Feature(
        name="analyze_code",
        tier="community",
        category="analysis"
    ),
    
    # PRO features
    "advanced_analysis": Feature(
        name="advanced_analysis",
        tier="pro",
        category="analysis"
    ),
    
    # ENTERPRISE features
    "formal_verification": Feature(
        name="formal_verification",
        tier="enterprise",
        category="analysis"
    ),
}
```

---

## 7. Environment Variables for License Control

### Key Environment Variables

| Variable | Example | Purpose |
|----------|---------|---------|
| `CODE_SCALPEL_TIER` | `pro` | Override detected tier |
| `CODE_SCALPEL_LICENSE_PATH` | `/path/to/license.jwt` | Explicit license file path |
| `CODE_SCALPEL_LICENSE_VERIFIER_URL` | `https://license.code-scalpel.dev/verify` | Online validation endpoint |
| `CODE_SCALPEL_ORGANIZATION` | `my-org` | Organization-based tier |
| `CODE_SCALPEL_ALLOW_HS256` | `1` | Allow HMAC-SHA256 (dev only) |
| `CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY` | `1` | Don't search for license files |

### Example: Override Detection

```bash
# Force Pro tier (useful for testing)
export CODE_SCALPEL_TIER=pro
python -c "from code_scalpel.licensing import get_current_tier; print(get_current_tier())"
# Output: pro

# Explicit license path
export CODE_SCALPEL_LICENSE_PATH=/home/user/my-license.jwt
python -c "from code_scalpel.licensing import get_license_info; print(get_license_info())"
# Output: Validates license from specified path
```

---

## 8. Caching and Performance

### Validation Cache (In-Memory)

```python
# Cached for 24 hours (per JWT spec)
_LICENSE_VALIDATION_CACHE: _LicenseValidationCacheEntry | None = None

# Cache stores:
_LicenseValidationCacheEntry(
    checked_at_epoch=1704153600,        # When last checked
    license_path="/home/user/.code-scalpel/license.jwt",
    license_mtime_ns=1704153600000000,  # File modification time
    license_size=4096,                  # File size
    crl_path="/path/to/crl.json",       # Certificate Revocation List
    result=JWTLicenseData(...)          # Parsed and validated data
)
```

### When Cache is Invalidated

```python
# Cache is checked/refreshed:
1. On first license validation
2. Every 24 hours (TTL)
3. When license file modification time changes
4. When file size changes
5. When force_refresh=True is passed
```

### Performance Impact

```
First validation (cold cache):
  - Parse JWT: ~1ms
  - Verify signature: ~10ms
  - Online validation (network): ~100-500ms
  Total: ~100-500ms

Subsequent validations (hot cache):
  - In-memory lookup: ~0.1ms
  Total: ~0.1ms

Validation expires after:
  - 24 hours in-memory cache
  - Re-validation then required
  - If online verifier unreachable: 48h grace period
```

---

## 9. Testing with Licenses

### Using Test Licenses

```python
# Test with Pro license
import os
os.environ["CODE_SCALPEL_LICENSE_PATH"] = "tests/licenses/code_scalpel_license_pro_20260101_190345.jwt"

from code_scalpel.licensing import get_current_tier
tier = get_current_tier()  # Returns: "pro"

# Test with no license (Community)
os.environ.pop("CODE_SCALPEL_LICENSE_PATH", None)
tier = get_current_tier()  # Returns: "community"
```

### Broken Test Licenses

Located in `/tests/licenses/`:
- `code_scalpel_license_pro_test_broken.jwt` - Missing `sub` claim
- `code_scalpel_license_enterprise_test_broken.jwt` - Missing `sub` claim

**Purpose**: Verify validator rejects malformed licenses

```python
# This should fail validation
result = validator.validate("code_scalpel_license_pro_test_broken.jwt")
assert not result.is_valid
assert "Missing 'sub' claim" in result.error_message
```

---

## 10. Security Properties

### What the JWT Token Provides

| Property | Mechanism | Strength |
|----------|-----------|----------|
| **Non-repudiation** | RSA signature (Code Scalpel private key only) | 🔴 Critical |
| **Integrity** | Any modification invalidates signature | 🔴 Critical |
| **Authenticity** | Public key verification | 🔴 Critical |
| **Expiration** | `exp` claim + online revocation check | 🟡 High |
| **Revocation** | CRL from verifier, jti (token ID) | 🟡 High |
| **Tampering detection** | Cryptographic signature fails | 🔴 Critical |

### What the JWT Token Does NOT Provide

| Limitation | Reason | Mitigation |
|-----------|--------|-----------|
| **Offline verification of revocation** | CRL requires online check | Grace period (48h) |
| **Protection from stolen token** | Token can be copied | MFA at issuer, rate limiting |
| **Binding to hardware** | JWT is portable | Hardware fingerprinting (Enterprise) |
| **Audit logging** | Token doesn't log usage | License server tracks usage |

---

## 11. Integration with Plugin System (Target Architecture)

In the target architecture, the licensing system will:

### 1. Load Community Package
```python
# Always works
from code_scalpel.licensing import get_current_tier, get_license_info
tier = get_current_tier()  # "community", "pro", or "enterprise"
```

### 2. Detect License Tier
```python
# If license found, parse JWT
license_data = validate_license()
# If tier == "pro", load Pro plugin
# If tier == "enterprise", load Pro + Enterprise plugins
```

### 3. Load Plugins Based on Tier
```python
# In MCP server initialization
if tier == "pro":
    load_plugin("code_scalpel_pro")  # Install Pro features
elif tier == "enterprise":
    load_plugin("code_scalpel_pro")
    load_plugin("code_scalpel_enterprise")
```

### 4. Feature Registry Reflects Available Features
```python
# After plugins loaded, registry contains:
# - Community features (always)
# - Pro features (if Pro tier + plugin loaded)
# - Enterprise features (if Enterprise tier + plugin loaded)

registry = FeatureRegistry()
available = registry.get_available_features()
# Returns only features for current tier
```

---

## 12. Key Files in Licensing System

```
src/code_scalpel/licensing/
├── __init__.py                    # Public API (get_current_tier, validate_license)
├── jwt_validator.py               # JWT parsing and validation
├── tier_detector.py               # Environment/file-based tier detection
├── license_manager.py             # Central state management
├── validator.py                   # Legacy HMAC validation (deprecated)
├── cache.py                       # Caching logic
├── public_key/
│   └── vault-prod-2026-01.pem    # RSA public key for signature verification
└── ... (other support files)

src/code_scalpel/tiers/
├── __init__.py                    # Tier constants
├── feature_registry.py            # Feature definitions and tier requirements
└── ... (tier-related utilities)

tests/licenses/
├── README.md                      # License testing guide
├── code_scalpel_license_pro_*.jwt # Test Pro licenses
└── code_scalpel_license_enterprise_*.jwt  # Test Enterprise licenses
```

---

## 13. Key Takeaways for Feature Extraction

### What Stays in Community Package
1. **JWTLicenseValidator** - License parsing
2. **TierDetector** - Tier detection
3. **LicenseManager** - License state
4. **FeatureRegistry** - Feature definitions
5. **Plugin system** - Infrastructure (NEW)

### What Goes in Pro Plugin
1. **Pro-tier tool implementations** - Advanced analysis, enhanced features
2. **Pro feature definitions** - Register as Features with tier="pro"
3. **Pro dependencies** - Advanced libraries (scikit-learn, etc.)

### What Goes in Enterprise Plugin
1. **Enterprise-tier implementations** - Formal verification, unlimited features
2. **Enterprise feature definitions** - Register as Features with tier="enterprise"
3. **Enterprise dependencies** - Enterprise libraries (Z3, HSM interfaces)

### Plugin Loading Sequence
1. Load Community package (always)
2. Detect tier from environment/license
3. Load plugins if tier >= "pro"
4. Validate plugin license requirements
5. Merge plugin tools with Community tools
6. Return combined tool set

---

## Summary

The Code Scalpel licensing system is **production-grade** and uses **industry-standard JWT tokens**. It provides:

- ✅ Cryptographic verification (RS256 signatures)
- ✅ Two-stage validation (offline + online)
- ✅ Flexible tier detection (environment, file, config)
- ✅ Graceful degradation (48h grace period)
- ✅ Comprehensive feature gating
- ✅ Extensible through plugins

For the feature extraction plan, this system enables:
- **Community package**: Free, MIT-licensed, no license required
- **Pro package**: Optional plugin with valid Pro license
- **Enterprise package**: Optional plugin with valid Enterprise license
- **Plugins only load if tier supports them**
- **No Pro/Enterprise code in public repo**

This is the foundation for the package separation architecture documented in FEATURE_EXTRACTION_PLAN.md.
