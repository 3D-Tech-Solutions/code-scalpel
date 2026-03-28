# Code Scalpel Pre-Release Pipeline – Quick Reference Guide

**Last Updated:** January 27, 2026  
**Audience:** Developers, DevOps, QA  
**Length:** 2-3 minutes to read

---

## TL;DR - What You Need to Know

We're implementing a **pre-release validation system** that tests all 23 tools across 3 tiers (COMMUNITY, PRO, ENTERPRISE) on 3 transports (stdio, HTTP, Docker) before every release.

**Why?** To ensure pricing is enforced correctly and tools don't accidentally get exposed at the wrong tier.

---

## Key Changes You'll See

### 1. New Files/Directories

```
docs/
  ├── PRE_RELEASE_PIPELINE.md        ← Full specification (this doc)
  └── QUICK_REFERENCE.md              ← You are here

src/code_scalpel/capabilities/
  ├── resolver.py                     ← NEW: Get capabilities by tier
  ├── limits.toml                     ← UPDATED: Central limit config
  └── schema.json                     ← NEW: Capability schema

capabilities/
  ├── community.json                       ← NEW: Golden file, COMMUNITY tier
  ├── pro.json                        ← NEW: Golden file, PRO tier
  ├── enterprise.json                 ← NEW: Golden file, ENTERPRISE tier
  └── README.md                       ← How to update

tests/
  ├── transports/
  │   ├── adapter.py                  ← NEW: Unified test interface
  │   ├── stdio_adapter.py            ← NEW: Subprocess tests
  │   ├── http_adapter.py             ← NEW: HTTP tests
  │   └── docker_adapter.py           ← NEW: Docker tests
  │
  ├── tier_enforcement/
  │   ├── test_tool_availability.py   ← NEW: 22 tools × 3 tiers
  │   ├── test_tool_limits.py         ← NEW: Limit enforcement
  │   └── test_feature_gating.py      ← NEW: Feature availability
  │
  └── capabilities/
      ├── test_capability_snapshot.py ← NEW: Golden file comparison
      └── test_capability_schema.py   ← NEW: Schema validation

.github/workflows/
  └── ci-tier-validation.yml          ← NEW: 8-stage CI pipeline
```

### 2. New Tools/Commands (For Users)

```bash
# Check what features are available at your tier
$ codescalpel capabilities
Tier: pro
Available tools: 14 (9 COMMUNITY + 5 PRO)

# Get detailed capabilities as JSON
$ codescalpel capabilities --json
{
  "tier": "pro",
  "tools": {...}
}

# MCP method for agents
[MCP] capabilities/get
→ Returns capability envelope for current tier
```

### 3. New GitHub Actions Pipeline

```
Stage 1: Syntax Check (2 min)
  ↓
Stage 2: Unit Tests (3 min)
  ↓
Stage 3: Build (2 min)
  ↓
Stage 4-6: Tier Tests (COMMUNITY/PRO/ENTERPRISE, each on stdio/HTTP/Docker)
  ↓
Stage 7: Capability Snapshots (compare against golden files)
  ↓
Stage 8: Release (if all pass)
```

**Total runtime: ~15 minutes per PR**

---

## For Tool Developers: New Pattern Required

### Old Pattern (❌ Don't Do This Anymore)

```python
@mcp.tool()
def analyze_code(files):
    if get_current_tier() == "pro":
        max_files = 5000  # ← Hardcoded, unclear
    else:
        max_files = 1000
    return analyze(files[:max_files])
```

### New Pattern (✅ Do This)

```python
from code_scalpel.capabilities import get_tool_capabilities

@mcp.tool()
def analyze_code(files):
    caps = get_tool_capabilities("analyze_code")  # ← One lookup
    max_files = caps["capabilities"]["max_files"]  # ← From config
    return analyze(files[:max_files])
```

**Benefit:** Limits are in `limits.toml`, tested in CI, reviewable in PRs.

---

## For DevOps: New Secrets Required

Add to GitHub repository Settings → Secrets and Variables:

| Secret Name | Value | Format |
|-------------|-------|--------|
| `CODESCALPEL_LICENSE_PRO` | JWT token | `eyJ...` (RS256 signed) |
| `CODESCALPEL_LICENSE_ENTERPRISE` | JWT token | `eyJ...` (RS256 signed) |

Both should be:
- ✅ Valid (not corrupted)
- ✅ Non-expired
- ✅ Full feature set
- ⚠️ Renew 30 days before expiry

---

## For QA: New Test Coverage

### What Gets Tested

- **22 tools** × **3 tiers** × **3 transports** = **198 tier enforcement tests**
- **24 features** × **3 tiers** = **72 feature gating tests**
- **3 capability snapshots** (compare against golden files)
- **License validation** tests (injection, validation, expiry)

**Total: ~300 tests, ~15 minutes runtime**

### What Blockers Are Enforced

❌ **BLOCKER** if:
- Tool count changes (must be 22)
- Tool schema changes
- Capability limits don't match golden file
- License not injected correctly
- Tier limits not enforced in practice
- Any test fails

⚠️ **WARNING** (doesn't block) if:
- Feature improved (needs doc update)
- Deprecated feature used
- License expiring soon

---

## For Product: What Changes

### Pricing Enforcement (Automated)

Every release will verify:
- ✅ COMMUNITY scanner/crawl tier limited to 500 files (not 5000)
- ✅ PRO tier can cross-file scan (COMMUNITY can't)
- ✅ PRO and ENTERPRISE both support symbolic execution; ENTERPRISE adds deeper/formal capabilities
- ✅ 22 tools always available (none hidden per tier)

### Capability Documentation (Executable)

Capabilities are now:
- **Discoverable** - Agents can call `get_capabilities()`
- **Tested** - Each limit tested in CI
- **Auditable** - Changes in golden files are reviewed
- **Versioned** - Changelog shows what changed and when

---

## Adding a New Tier-Gated Feature

1. **Update Configuration**
   ```toml
   # src/code_scalpel/capabilities/limits.toml
   [my_tool.free]
   max_files = 100
   
   [my_tool.pro]
   max_files = 1000
   
   [my_tool.enterprise]
   max_files = 10000
   ```

2. **Update Tool Code**
   ```python
   # src/code_scalpel/mcp/tools/my_tool.py
   @mcp.tool()
   async def my_tool(files):
       caps = get_tool_capabilities("my_tool")
       max_files = caps["capabilities"]["max_files"]
       return process(files[:max_files])
   ```

3. **Add Tests**
   ```python
   # tests/tier_enforcement/test_my_tool_limits.py
   def test_my_tool_free_limit():
       with tier_context("free"):
           result = my_tool(["file"] * 500)
           assert len(result) == 100
   
   def test_my_tool_pro_limit():
       with tier_context("pro"):
           result = my_tool(["file"] * 2000)
           assert len(result) == 1000
   ```

4. **Merge**
   - CI auto-generates golden files
   - PR shows capability diff
   - Requires approval to merge
   - Golden files auto-update on merge

---

## Capability Snapshot Approval Workflow

**Scenario:** You add a new feature to PRO tier

1. **Make changes** → Commit code
2. **Push to PR** → CI runs tests
3. **Snapshot test fails** → Shows diff in CI
4. **Review diff** → Verify change is intentional
5. **Approve with label** → Add "regenerate-capabilities" label to PR
6. **Merge** → Golden files auto-regenerate
7. **Done** → New capabilities in production

**Example diff:**
```diff
- "max_files": 2000
+ "max_files": 5000

- "semantic_mode": false
+ "semantic_mode": true
```

---

## Troubleshooting

### CI Test Fails: "Tool count != 22"

**Cause:** Tool was hidden or removed per tier

**Fix:**
- ✅ All 22 tools must always be registered
- ✅ Hide features/limits, not tools
- ✅ Tool schemas immutable

### CI Test Fails: "Capability mismatch"

**Cause:** Generated capabilities don't match golden file

**Action:**
1. Review diff in CI artifacts
2. If intentional, add "regenerate-capabilities" label
3. If not intentional, revert changes
4. Merge → golden file auto-updates

### License Secret Not Found

**Cause:** GitHub secret not configured

**Fix:**
1. Go to repo Settings → Secrets
2. Add `CODESCALPEL_LICENSE_PRO` (from value in 1Password/vault)
3. Add `CODESCALPEL_LICENSE_ENTERPRISE`
4. Rerun CI

### Tests Pass Locally But Fail in CI

**Cause:** License secrets not set locally

**Fix:**
```bash
# Set license from environment variable
export CODE_SCALPEL_LICENSE="<jwt_token_from_1password>"
pytest tests/tier_enforcement/ -v
```

---

## Key Files to Know

| File | Purpose |
|------|---------|
| `docs/PRE_RELEASE_PIPELINE.md` | Full specification (read this for details) |
| `src/code_scalpel/capabilities/resolver.py` | Get capabilities by tier |
| `src/code_scalpel/capabilities/limits.toml` | Central config for all tier limits |
| `capabilities/community.json` | Golden file for COMMUNITY tier (auto-generated) |
| `capabilities/pro.json` | Golden file for PRO tier (auto-generated) |
| `capabilities/enterprise.json` | Golden file for ENTERPRISE tier (auto-generated) |
| `tests/transports/adapter.py` | Unified test interface for all transports |
| `.github/workflows/ci-tier-validation.yml` | 8-stage CI pipeline |

---

## One-Minute Recap

| What | Old Way | New Way |
|------|---------|---------|
| **Limits** | Hardcoded in tool | `limits.toml` |
| **Discovery** | No way for agents | `get_capabilities()` MPC method |
| **Testing** | Some tier tests | 300+ tier tests, all transports |
| **Pricing Safety** | Manual review | Automated CI with blockers |
| **Documentation** | Outdated docs | Executable capabilities |

---

## Questions?

See full specification: `docs/PRE_RELEASE_PIPELINE.md`

---

**Created:** January 27, 2026  
**For:** Code Scalpel v1.3.0+ releases
