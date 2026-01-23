# Architectural Decisions for v1.0.0 Feature-Tier Gating

[20251225_DOCS] Key architectural decisions for implementing all-tools-available with parameter-level feature gating

---

## Executive Summary

Three critical architectural decisions were made on December 25, 2025, to finalize the v1.0.0 feature-tier gating implementation:

1. **Manual Capability Checks** - Tools explicitly call `get_tool_capabilities()` for flexibility
2. **JWT Industry Standard** - License keys use standard JWT tokens with signature verification
3. **Documentation-Driven UX** - No upgrade hints in responses; users consult comprehensive tier docs

These decisions prioritize maintainability, industry best practices, and efficient use of context windows.

---

## Decision 1: Manual Capability Checks (Option B)

**Status:** ✅ APPROVED

### Context

Two implementation patterns were considered:

**Option A: Decorator-Based**
```python
@require_capability("advanced_taint_flow")
def security_scan_handler(code: str):
    # Implementation
```

**Option B: Manual Checks**
```python
def security_scan_handler(code: str):
    tier = get_current_tier()
    caps = get_tool_capabilities("security_scan", tier)
    
    if "advanced_taint_flow" in caps.capabilities:
        return advanced_analysis(code)
    return basic_analysis(code)
```

### Decision

**Choose Option B: Manual Checks**

### Rationale

1. **Maintainability**
   - Explicit is better than implicit (Python Zen)
   - Easier to understand control flow by reading the function
   - No "magic" behavior from decorators

2. **Flexibility**
   - Fine-grained control over feature gating within function logic
   - Can gate at any point in the execution, not just at function entry
   - Enables hybrid approaches (basic + advanced in same function)

3. **Testability**
   - Easier to mock tier and capabilities in unit tests
   - No decorator stack to navigate when debugging
   - Clear test setup: `@mock_tier("community")`

4. **Gradual Migration**
   - Can refactor tools one at a time without breaking others
   - No need for global decorator registration system
   - Backwards compatible with existing tools

### Implementation Pattern

```python
def {tool}_handler(params):
    # 1. Get current tier from JWT license validator
    tier = get_current_tier()
    
    # 2. Get capabilities for this tool at this tier
    caps = get_tool_capabilities("{tool}", tier)
    
    # 3. Apply tier-specific limits
    if caps.limits.{limit_name}:
        params = apply_limit(params, caps.limits.{limit_name})
    
    # 4. Use basic or advanced features based on capabilities
    if "{advanced_feature}" in caps.capabilities:
        result = advanced_function(params)
    else:
        result = basic_function(params)
    
    # 5. Apply result limits and return
    return apply_tier_limits("{tool}", result, tier)
```

### Migration Plan

**Phase 1: Proof of Concept (Week 1)**
- Refactor 4 tools: `security_scan`, `crawl_project`, `extract_code`, `symbolic_execute`
- Validate pattern works across different tool types
- Document lessons learned

**Phase 2: Core Tools (Week 2)**
- Refactor 8 more tools with highest usage
- Update tests to use manual check pattern
- Create helper functions for common patterns

**Phase 3: Remaining Tools (Week 3)**
- Complete remaining 8 tools
- Remove any decorator-based approaches
- Finalize documentation

---

## Decision 2: JWT Industry Standard for Licenses

**Status:** ✅ APPROVED

### Context

License key format options considered:
- Custom encrypted format (proprietary)
- JWT tokens (industry standard)
- Signed JSON (partial standard)

### Decision

**Use JWT (JSON Web Token) with RS256 or HS256 signing**

### Rationale

1. **Industry Best Practice**
   - Standard format used by Auth0, Okta, Firebase, etc.
   - Well-documented security properties
   - Battle-tested in production environments

2. **Tamper-Proof**
   - Cryptographic signature prevents modification
   - Public key verification (RS256) or secret key (HS256)
   - Standard algorithms with known security guarantees

3. **Standard Libraries**
   - PyJWT for Python backend
   - jsonwebtoken for Node.js integrations
   - jwt-decode for client-side parsing
   - No need to implement custom crypto

4. **Self-Contained**
   - All claims embedded in token
   - No database lookup required for validation
   - Offline verification possible (file-based mode); hosted deployments may prefer a remote verifier

5. **Debuggable**
   - Can decode JWT at jwt.io for inspection
   - Human-readable JSON payload
   - Standard expiration handling

### JWT Structure

**Header:**
```json
{
  "alg": "RS256",
  "typ": "JWT"
}
```

**Payload (Claims):**
```json
{
  "iss": "code-scalpel-licensing",
  "sub": "customer_id_12345",
  "tier": "pro",
  "features": [
    "cognitive_complexity",
    "context_aware_scanning",
    "remediation_suggestions"
  ],
  "exp": 1735689600,
  "iat": 1704153600
}
```

**Signature:**
```
RSASHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  private_key
)
```

### Implementation

**License Validator:**
```python
import jwt
from cryptography.hazmat.primitives import serialization

def validate_license(token: str) -> dict:
    """Validate JWT license token and return claims."""
    try:
        # Load public key (stored securely)
        public_key = load_public_key()
        
        # Verify signature and decode
        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "require": ["tier", "exp", "iat"]
            }
        )
        
        return {
            "valid": True,
            "tier": claims["tier"],
            "features": claims.get("features", []),
            "customer_id": claims["sub"]
        }
        
    except jwt.ExpiredSignatureError:
        # License expired - downgrade to community
        return {"valid": False, "tier": "community", "reason": "expired"}
        
    except jwt.InvalidTokenError as e:
        # Invalid token - downgrade to community
        return {"valid": False, "tier": "community", "reason": str(e)}
```

**Tier Detection:**
```python
def get_current_tier() -> str:
   """Get current tier from a license file (file-only discovery)."""
   # 1. Explicit override (path to file)
   license_path = os.getenv("CODE_SCALPEL_LICENSE_PATH")

   # 2. Standard search paths
   candidate_paths = [
      ".code-scalpel/license.jwt",
      os.path.expanduser("~/.config/code-scalpel/license.jwt"),
      os.path.expanduser("~/.code-scalpel/license.jwt"),
      ".scalpel-license",
   ]

   paths_to_try = [license_path] if license_path else []
   paths_to_try.extend(candidate_paths)

   for path in paths_to_try:
      if path and os.path.exists(path):
         with open(path) as f:
            token = f.read().strip()
         return validate_license(token)["tier"]

   # Default to community
   return "community"
```

### Key Management

**Private Key (License Generation):**
- Kept secure by Code Scalpel organization
- Used to sign license tokens
- Never distributed to customers
- Rotate yearly for security

**Public Key (License Verification):**
- Embedded in Code Scalpel distribution
- Used by all installations to verify signatures
- Can be updated via package upgrades
- Public knowledge (not secret)

### Security Properties

1. **Non-Repudiation**: Only Code Scalpel can issue valid licenses
2. **Integrity**: Any modification invalidates the signature
3. **Expiration**: Built-in expiration with strict posture (expired licenses never grant paid tier; grace period is informational only)
4. **Revocation**: Can add revocation list check (optional)

---

## Decision 3: Documentation-Driven UX (No Upgrade Hints)

**Status:** ✅ APPROVED

### Context

Original plan included "upgrade hints" in tool responses:

```python
return {
    "vulnerabilities": vulnerabilities[:10],
    "upgrade_hint": "Upgrade to PRO to see all vulnerabilities and get remediation suggestions."
}
```

### Decision

**NO upgrade hints in tool responses. All tier limitations documented in comprehensive tier comparison guide.**

### Rationale

1. **Context Window Efficiency**
   - Upgrade hints waste 50-100 tokens per response
   - For agents making 100+ tool calls, this adds up to 5,000-10,000 wasted tokens
   - Tokens are expensive and count toward rate limits

2. **Cleaner Tool Output**
   - Tool responses focused on actual results, not marketing
   - Easier for agents to parse (no sales noise)
   - Better UX for programmatic consumption

3. **Documentation as Source of Truth**
   - `docs/TIER_CONFIGURATION.md` is comprehensive tier comparison
   - Users reference once when choosing tier
   - Documentation is more detailed than inline hints could ever be

4. **Reduces Maintenance Burden**
   - No need to maintain upgrade hint strings in 20 tools
   - No i18n concerns for upgrade messaging
   - No A/B testing of upgrade copy

5. **Professional Positioning**
   - B2B software doesn't nag in API responses
   - Users are developers who read docs, not consumers who need prompts
   - Trust users to make informed decisions

### User Experience

**When Community user hits a limit:**

1. Tool returns truncated results:
   ```json
   {
     "vulnerabilities": [...10 items...],
     "tier": "community"
   }
   ```

2. User notices only 10 vulnerabilities returned

3. User consults documentation:
   - `docs/TIER_CONFIGURATION.md` - Full tier comparison table
   - Shows Community: 10 findings, Pro: Unlimited + remediation
   - Clear upgrade path with pricing link

4. User makes informed decision to upgrade or continue with Community

### Documentation Structure

**`docs/TIER_CONFIGURATION.md`** should contain:

1. **Executive Summary Table**
   ```markdown
   | Tier | Price | Best For | Key Features |
   |------|-------|----------|--------------|
   | Community | Free | Individual devs | All 20 tools, AST/PDG analysis |
   | Pro | $X/mo | Teams | + Automation & deep context |
   | Enterprise | $Y/mo | Organizations | + Governance & scale |
   ```

2. **Tool-by-Tool Comparison**
   ```markdown
   ### security_scan
   
   | Feature | Community | Pro | Enterprise |
   |---------|-----------|-----|------------|
   | Max findings | 10 | Unlimited | Unlimited |
   | Taint analysis | ✅ Basic | ✅ Advanced | ✅ Advanced |
   | Remediation | ❌ | ✅ | ✅ |
   | Compliance mapping | ❌ | ❌ | ✅ |
   ```

3. **Feature Deep Dives**
   - What is "Cognitive Complexity"?
   - What is "Context-Aware Scanning"?
   - What is "Formal Verification"?

4. **Upgrade Decision Guide**
   - When to upgrade to Pro
   - When to upgrade to Enterprise
   - ROI calculator examples

### Exception: CLI Upgrade Command

The ONE place upgrade information appears is in the CLI:

```bash
$ scalpel upgrade info

Current Tier: Community

Your license is valid and active. To unlock additional features:

PRO ($X/month):
  - Unlimited results for all tools
  - Cognitive complexity analysis
  - Context-aware security scanning
  - Framework entry point detection
  
ENTERPRISE ($Y/month):
  - Formal verification
  - Compliance audit engine
  - Multi-repo architecture support
  - 24/7 priority support

Visit http://codescalpel.dev/pricing for details.
```

This is acceptable because:
- User explicitly requested upgrade info
- Not injected into tool responses
- Shown once, not repeatedly

---

## Implementation Timeline

### Week 1: Core Infrastructure
- [ ] Implement JWT license validator (RS256)
- [ ] Add `get_current_tier()` function
- [ ] Update `get_tool_capabilities()` to use JWT tier
- [ ] Create comprehensive tier comparison docs

### Week 2: Tool Handler Refactoring
- [ ] Refactor 4 proof-of-concept tools with manual checks
- [ ] Document migration pattern
- [ ] Create test fixtures (`@mock_tier`)
- [ ] Validate no upgrade hints in responses

### Week 3: Remaining Tools
- [ ] Refactor remaining 16 tools
- [ ] Remove any upgrade hint code
- [ ] Update all tool documentation
- [ ] Finalize migration guide

### Week 4: Testing & Documentation
- [ ] 60 unit tests (20 tools × 3 tiers)
- [ ] Integration tests for tier enforcement
- [ ] CLI upgrade info command
- [ ] Release v1.0.0

---

## Success Metrics

1. **Context Efficiency**
   - Average tool response: <500 tokens (currently ~600 with hints)
   - 100-tool session: <50K tokens (currently ~60K)

2. **Maintainability**
   - All 20 tools use consistent manual check pattern
   - Zero decorator magic in tool handlers
   - Single source of truth for capabilities

3. **User Satisfaction**
   - Documentation clarity: 90%+ satisfaction
   - Tier comparison guide rated "very clear"
   - No confusion about tier limitations

4. **Business Metrics**
   - Conversion rate Community → Pro: Target 5%
   - Conversion rate Pro → Enterprise: Target 10%
   - Documentation page views before upgrade decision

---

## Risks & Mitigations

### Risk 1: Users Don't Find Documentation

**Mitigation:**
- Prominent link in error messages: "See tier comparison: https://..."
- CLI command `scalpel tiers compare`
- In-app help command: `scalpel help tiers`

### Risk 2: Manual Checks Inconsistently Applied

**Mitigation:**
- Code review checklist for tool PRs
- Automated linting: Check that `get_tool_capabilities()` is called
- Test coverage requirement: Each tool has tier tests

### Risk 3: JWT Key Compromise

**Mitigation:**
- Annual key rotation
- Monitor for license validation failures (possible attack)
- Revocation list for compromised licenses

---

## Alternatives Considered & Rejected

### Alternative 1: Decorator-Based Capability Checks

**Rejected because:**
- Less flexible than manual checks
- Harder to test and debug
- "Magic" behavior not obvious from reading code

### Alternative 2: Custom License Format

**Rejected because:**
- JWT is industry standard with better tooling
- Custom format requires custom crypto implementation
- Harder to debug and validate

### Alternative 3: Upgrade Hints in Responses

**Rejected because:**
- Wastes context window tokens (50-100 per response)
- Clutters tool output with marketing copy
- Documentation is more comprehensive anyway

### Alternative 4: Server-Side License Validation

**Rejected because:**
- Requires network call on every MCP server start
- Breaks offline usage
- JWT with embedded claims is sufficient

---

## Open Questions

### Q1: Should we support license key in `.env` file?

**Answer:** Yes, add support for:
- `.code-scalpel/license.jwt` project-local file (recommended)
- `CODE_SCALPEL_LICENSE_PATH` environment variable (path to file)
- `~/.config/code-scalpel/license.jwt` global file
- `.scalpel-license` legacy filename

### Q2: Grace period for expired licenses?

**Answer:**

> [20251227_DOCS] Updated posture: grace period is informational only.

- A 7-day window can be used to display renewal reminders (`is_in_grace_period`).
- Expired licenses do **not** grant paid tier during this window.
- Effective tier remains `community` until a valid (unexpired) license is provided.

### Q3: Should we log tier enforcement events?

**Answer:** Yes, for debugging:
```python
logger.debug(f"Tool: {tool_id}, Tier: {tier}, Applied limit: {limit_name}={limit_value}")
```

But do NOT log to user-facing output.

---

## References

- [All-Tools-Available Implementation Summary](./all_tools_available_summary.md)
- [TIER_CONFIGURATION.md](../TIER_CONFIGURATION.md)
- [JWT RFC 7519](https://tools.ietf.org/html/rfc7519)
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)

---

**Document Status:** ✅ Final
**Last Updated:** December 25, 2025
**Approved By:** User (Architectural Decisions)
**Next Review:** After v1.0.0 release (planned Q1 2026)
