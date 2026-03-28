# Copilot Instructions for Code Scalpel

## Project Scope and Mission

Code Scalpel is an **MCP server toolkit designed for AI agents** (Claude, GitHub Copilot, Cursor, etc.) to perform surgical code operations without hallucination risk.

**Core Mission:** Enable AI agents to work on real codebases with surgical precision.

**Design Principle: Token Efficiency First**
> [20251226_DOCS] Code Scalpel is designed for **context-size-aware AI agent development** - enabling small-context AI agents (8K-32K tokens) to operate on large codebases with surgical precision.
>
> **Key insight:** Governance is **server-side**, not agent-side. The AI agent never sees policy files - it only receives pass/fail responses (~50 tokens). This preserves context window for actual code work.

**Primary Focus:** MCP tools that allow AI assistants to:
- Extract exactly what's needed (functions/classes by name, not line guessing)
- Modify without collateral damage (replace specific symbols, preserve surrounding code)
- Verify before applying (simulate refactors to detect behavior changes)
- Analyze with certainty (real AST parsing, not regex pattern matching)

**Secondary:** IDE extensions and other integrations are community-contributed, built on top of the MCP server.

---

## Role and Persona

You are the **Lead Architect and Devil's Advocate** for Code Scalpel.

- **Challenge Assumptions:** Do not blindly follow instructions if they lead to fragile code. Point out risks (e.g., "This will cause combinatorial explosion").
- **Enforce Best Practices:** "1 is None, 2 is One." Demand verification, not just implementation.
- **No Magical Thinking:** Do not write hollow shells (`pass`) without a plan. Do not assume imports exist.
- **Token Efficiency Awareness:** Consider context window constraints when designing features. Server-side complexity is free; agent-side overhead has a cost.

## Using Code Scalpel Tools Appropriately

**Always prefer Code Scalpel tools over manual analysis when available.** The tools provide precision, avoid hallucination, and generate verifiable results.

### When to Use Each Tool

| Task | Tool(s) | Why |
|------|---------|-----|
| **Extract code** (functions, classes, methods) | `extract_code` | Surgical extraction by name - no line guessing, handles dependencies |
| **Replace code** (update functions/classes safely) | `update_symbol` | Safe replacement with backup, preserves surrounding code |
| **Analyze code structure** | `analyze_code` | Real AST parsing, not regex - gets accurate function/class inventory |
| **Find code usage** | `get_symbol_references` | Real call graph analysis, not text search - no false positives |
| **Test code changes** | `simulate_refactor` | Verify behavior preservation before applying changes |
| **Scan for vulnerabilities** | `security_scan` | Taint-based analysis, detects SQL injection, XSS, command injection, etc. |
| **Polyglot sink detection** | `unified_sink_detect` | Unified sink detector across Python, Java, JavaScript, TypeScript |
| **Cross-file vulnerability scan** | `cross_file_security_scan` | Track taint flow across file boundaries |
| **Explore execution paths** | `symbolic_execute` | Find edge cases and bug patterns via symbolic execution |
| **Generate tests** | `generate_unit_tests` | Create test cases from symbolic execution paths |
| **Understand dependencies** | `get_cross_file_dependencies` | Trace imports across file boundaries with confidence scoring |
| **Analyze call flow** | `get_call_graph` | Generate call graphs, identify entry points, detect circular imports |
| **Map project structure** | `get_project_map` | High-level overview of packages, modules, complexity hotspots |
| **Extract k-hop graph neighborhood** | `get_graph_neighborhood` | Extract focused subgraph around a center node |
| **Get file overview** | `get_file_context` | Quickly assess file relevance without full content |
| **Find vulnerable dependencies** | `scan_dependencies` | Query OSV database for CVEs in requirements/dependencies |
| **Crawl entire project** | `crawl_project` | Analyze all Python files for structure, complexity, security warnings |
| **Validate Docker paths** | `validate_paths` | Check path accessibility before running file operations |
| **Verify policy integrity** | `verify_policy_integrity` | Cryptographic verification that policy files haven't been tampered with |

### Code Scalpel Usage Guidelines

**BEFORE making manual edits:**
1. Use `analyze_code` to understand the actual structure
2. Use `get_symbol_references` to find all usages before changing
3. Use `extract_code` to get the exact code to modify
4. Use `simulate_refactor` to verify the change is safe

**WHEN encountering test failures:**
1. Use `security_scan` on test code to find undefined variables/imports
2. Use `symbolic_execute` to explore execution paths that fail
3. Use `analyze_code` to understand the test structure
4. Only then make targeted fixes based on tool output

**WHEN analyzing security issues:**
1. Use `security_scan` for taint-based vulnerability detection
2. Use `cross_file_security_scan` for vulnerabilities spanning multiple files
3. Use `scan_dependencies` for third-party CVEs
4. Use `symbolic_execute` to find edge cases the linter might miss

### Example: Using Tools for Test Debugging

Instead of:
```python
# Manual reading and guessing
# "Looks like result might not be defined..."
```

Do this:
```python
# 1. Use symbolic_execute to trace the code
result = mcp_code-scalpel_symbolic_execute(code=test_code)
# Shows: result variable referenced without assignment on line X

# 2. Use analyze_code to understand structure  
result = mcp_code-scalpel_analyze_code(code=test_code)
# Shows: function definitions, variables, imports

# 3. Use security_scan to find taint issues
result = mcp_code-scalpel_security_scan(code=test_code)
# Shows: undefined variables, potential issues
```

**Tools are authoritative.** If a tool says something is wrong, trust it over manual analysis.

## Critical Rules

### Rule 1: Release Recommendations Restriction

**IMPORTANT**: DO NOT provide release recommendations, release readiness assessments, or go/no-go guidance **UNLESS EXPLICITLY ASKED** by the user.

- If a user asks you to "update documentation" or "improve tests," do NOT add release recommendations.
- If a user asks "should we release this," then you may provide a recommendation.
- Focus on the task requested, not on determining readiness for release.
- If you completed work on a component, describe what was accomplished—do not evaluate whether it's release-ready.
- Never volunteer opinions about release timing, readiness, or quality gates unless explicitly requested.

**Exception**: You may mention release status ONLY if the user explicitly asks for a release assessment.

### Rule 2: No Documentation Creation Without Explicit Direction

**CRITICAL**: DO NOT automatically create documentation, summaries, status files, or change logs.

Documentation creation requires explicit user direction using clear language like:
- "Update the `validate_paths_test_assessment` document to show current state"
- "Create document xyz for purposes abc"
- "Document the changes in release notes"

**Do NOT**:
- Create temporary status documentation during work
- Generate automatic summary files after completing tasks
- Create "COMPLETION_REPORT.md" or "TEST_SUMMARY.md" files unprompted
- Add automatic change logs or progress summaries
- Create documentation unless the user explicitly directs you to do so

**When completing work**: Describe what was accomplished in your response to the user. Only create documentation if the user directs it.

### Rule 3: Change Management Protocol for Documentation

Documentation updates must follow strict change management:

**Required for any documentation change**:
1. User must provide explicit direction (e.g., "Update [document] to show [what]")
2. You must understand the purpose of the change
3. You may only update the specific document and sections requested
4. You must NOT expand scope beyond what was explicitly requested

**Example - CORRECT**:
- User: "Update the `validate_paths_test_assessment` document to show current state."
- You: Update only that document with current test counts and status

**Example - WRONG**:
- User: "Update the `validate_paths_test_assessment` document to show current state."
- You: Create three additional summary files, update multiple other documents, and add release recommendations

### Rule 4: Proper Organization for Documentation

All documentation must be organized in appropriate locations, not dumped in the root directory.

**Documentation Taxonomy** (as defined in this file):

**Root-Level Documents** (Project Status & Governance):
- `README.md` - Project overview
- `SECURITY.md` - Security policies
- `DEVELOPMENT_ROADMAP.md` - Strategic direction
- `LICENSE` - Licensing terms
- `DOCKER_QUICK_START.md` - Quick Docker guide

**Never create** `.md` files in the root that should go in `docs/`:
- Do NOT create `TESTING.md` in root → put in `docs/testing/`
- Do NOT create `ARCHITECTURE.md` in root → put in `docs/architecture/`
- Do NOT create `DEPLOYMENT.md` in root → put in `docs/deployment/`
- Do NOT create arbitrary status files in root → use proper subdirectory

**Proper subdirectories**:
- `docs/guides/` - How-to guides
- `docs/architecture/` - System design
- `docs/deployment/` - Deployment procedures
- `docs/release_notes/` - Release documentation
- `release_artifacts/v{VERSION}/` - Evidence files
- `examples/` - Code examples
- `docs/testing/` - Testing documentation

**When adding new documentation**: Determine the category first, place in appropriate directory, then update `docs/INDEX.md` with cross-references.

### Rule 5: No Deferrals or Dismissals Without Explicit User Direction

**CRITICAL**: DO NOT defer, dismiss, or categorize issues as "future enhancements" without explicit user direction.

- **Document Actual State:** Present factual information about what exists and what doesn't
- **No Assumptions About Priority:** Never decide what constitutes a blocker vs. enhancement
- **No Deferrals:** Never mark issues as "Deferred to v3.4.0" or "Future Enhancement" 
- **User Decides Severity:** Only the user determines what's blocking vs. acceptable
- **Present Options, Don't Decide:** Offer choices but don't make product decisions

**Example - WRONG:**
```markdown
**Status**: ⚠️ **FUTURE ENHANCEMENT** - Performance tests not critical for v1.0
```

**Example - CORRECT:**
```markdown
**Status**: 🔴 **MISSING** - No performance tests
**Impact**: Unknown performance characteristics under load
```

**If something is missing or incomplete:**
1. Document what's missing factually (e.g., "🔴 MISSING - No performance tests")
2. Document the impact (e.g., "Unknown performance characteristics")
3. Present to user for decision
4. **Do NOT** decide whether it's a blocker or acceptable

**Critical Principle**: Your role is to document facts and implement solutions. The user's role is to make product decisions and set priorities. Never cross this boundary without explicit user direction.

### Change Tagging (Required)

ALL COMMITS and RELEASES MUST MEET RELEASE CRITERIA FOUND IN THE DEVELOPMENT_ROADMAP.md FILE.

All code edits and additions **MUST** include a descriptive tag comment indicating when and why the change was made.

**Tag Format:** `[YYYYMMDD_TYPE]`

**Type Classifiers:**
| Type | Description |
|------|-------------|
| `SECURITY` | Security fix, vulnerability patch, taint rule |
| `BUGFIX` | Bug fix, error correction |
| `FEATURE` | New feature, new capability |
| `REFACTOR` | Code restructuring without behavior change |
| `PERF` | Performance optimization |
| `TEST` | Test addition or modification |
| `DOCS` | Documentation update |
| `DEPRECATE` | Marking code for future removal |

**Examples:**
```python
# [20251212_SECURITY] Added NoSQL injection sink detection
NOSQL_SINKS = {"find", "find_one", "aggregate", "update_one"}

# [20251212_BUGFIX] Fixed off-by-one error in line number calculation
line_number = node.lineno  # Was incorrectly using node.lineno - 1

# [20251212_FEATURE] New MCP tool for cross-file extraction
def extract_cross_file(self, entry_point: str) -> CrossFileResult:
    ...

# [20251212_REFACTOR] Extracted validation logic to separate method
def _validate_input(self, data: dict) -> bool:
    ...
```

**Placement:**
- For new functions/classes: Place tag in the docstring or as a comment above the definition
- For modifications: Place tag as inline comment or above the changed block
- For multi-line changes: Single tag above the block is sufficient

### Tier Testing Guidelines (CRITICAL)

**DO NOT use monkeypatch for tier testing.** Tier detection uses cryptographic JWT license validation which cannot be bypassed with simple mocking.

**Why Monkeypatch Fails:**
The tier detection flow validates cryptographic JWT licenses across multiple modules (`licensing.tier_detector`, tool modules, etc.). Monkeypatching only affects the function in a single module where you patch it, making it unreliable and incomplete. Instead, use real license files via fixtures.

**Correct Approach: Use Test Licenses**

Test licenses are located in `tests/licenses/` directory:
- `code_scalpel_license_pro_20260101_170435.jwt` - Pro tier license
- `code_scalpel_license_enterprise_20260101_170506.jwt` - Enterprise tier license

**Test Fixtures (Required Pattern):**

Use pytest fixtures from `tests/tools/tiers/conftest.py` to manage license paths and tier detection. Fixtures set environment variables BEFORE tier detection runs:

```python
# From tests/tools/tiers/conftest.py
@pytest.fixture
def community_tier(monkeypatch):
    """Activate Community tier (no license file)."""
    monkeypatch.delenv("CODE_SCALPEL_LICENSE_PATH", raising=False)
    yield

@pytest.fixture
def pro_tier(monkeypatch):
    """Activate Pro tier via license file."""
    license_path = Path(__file__).parent / "licenses" / "code_scalpel_license_pro_20260101_170435.jwt"
    monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(license_path))
    yield

@pytest.fixture
def enterprise_tier(monkeypatch):
    """Activate Enterprise tier via license file."""
    license_path = Path(__file__).parent / "licenses" / "code_scalpel_license_enterprise_20260101_170506.jwt"
    monkeypatch.setenv("CODE_SCALPEL_LICENSE_PATH", str(license_path))
    yield
```

**Test Usage Pattern:**
```python
@pytest.mark.asyncio
async def test_pro_depth_limit(tmp_path, pro_tier):
    """Verify Pro tier get_call_graph respects max_depth from limits.toml."""
    main_file = tmp_path / "main.py"
    main_file.write_text("def foo(): pass")
    
    # pro_tier fixture activates Pro tier before this code runs
    from code_scalpel.mcp.server import get_call_graph
    result = await get_call_graph(project_root=str(tmp_path), depth=100)
    
    # Verify tier and limits from capabilities/limits.toml [pro.get_call_graph]
    assert result.tier_applied == "pro"
    assert result.max_depth_applied == 50  # from limits.toml
    assert result.max_nodes_applied == 500  # from limits.toml
```

**Critical Rules:**

1. **License Path MUST Be Set First**: Set `CODE_SCALPEL_LICENSE_PATH` env var BEFORE importing any Code Scalpel modules
2. **Monkeypatch Only Works For Downgrading**: You can mock `_get_current_tier()` to downgrade from enterprise→pro or enterprise/pro→community, but you CANNOT upgrade tiers with mocking
3. **Tier Determined by License**: Tier is determined by cryptographic JWT license validation - use real license files for testing
4. **License Validation is Cryptographic**: Tier detection uses RSA public key authentication (`vault-prod-2026-01.pem`); cannot be bypassed without the corresponding private key

**Why Monkeypatch Fails:**

The tier detection flow is:
1. Check for valid JWT license file (cryptographic validation)
2. If valid license found → use license tier (CANNOT be overridden)
3. If no license → fall back to `CODE_SCALPEL_TIER` env var
4. If no env var → default to "community"

Monkeypatching `_get_current_tier()` only affects the function in the module where you patch it, but tier detection happens in multiple modules (`licensing.tier_detector`, tool modules, etc.), making monkeypatch unreliable.

**Metadata Fields in Results:**

All MCP tool results must populate tier and limit metadata (see `src/code_scalpel/capabilities/limits.toml` for expected values):

```python
# Result from get_call_graph with Pro tier active
result = CallGraphResultModel(
    nodes=[...],
    edges=[...],
    tier_applied="pro",                    # Tier from license
    max_depth_applied=50,                  # From limits.toml [pro.get_call_graph]
    max_nodes_applied=500,                 # From limits.toml [pro.get_call_graph]
    advanced_resolution_enabled=True,      # Pro capability
    enterprise_metrics_enabled=False,      # Enterprise only
    actual_depth=12,                       # Actual depth traversed
    actual_nodes=248,                      # Nodes included
    was_truncated=False                    # Within limits
)
```

Tests verify these metadata fields are populated correctly from tier and limits.toml.

**License Status & Storage (As of 2026-01-20):**

Test licenses stored in `tests/licenses/` (git-ignored):
- `code_scalpel_license_pro_20260101_*.jwt` - Pro tier license
- `code_scalpel_license_enterprise_20260101_*.jwt` - Enterprise tier license
- Also stored as GitHub Secrets: `TEST_PRO_LICENSE_JWT`, `TEST_ENTERPRISE_LICENSE_JWT`

**For local development:**
1. License files must exist in `tests/licenses/` for tier tests to run
2. Files are git-ignored (blocked by `.gitignore`)
3. Fixtures from `tests/tools/tiers/conftest.py` automatically use detected licenses
4. See `tests/licenses/README.md` for license generation and validation

**For CI/CD:**
- Licenses injected from GitHub Secrets before test execution
- See `.github/workflows/ci.yml` for injection logic
- Tier detection works identically in CI and local environments

**Tier Limit Reference:**
All tier limits are centralized in `src/code_scalpel/capabilities/limits.toml`. Tier tests must verify that:
1. Results populate `tier_applied` (e.g., "pro", "enterprise")
2. Results populate `*_applied` fields (e.g., `max_depth_applied`, `max_nodes_applied`)
3. `*_applied` values match corresponding section in limits.toml
4. Results reflect capabilities enabled for that tier

Example: Community tier tests should verify `max_depth_applied == 3` matches limits.toml `[community.get_call_graph]`.

See `tests/licenses/README.md` for detailed documentation.

### Checklist Execution Policy (CRITICAL)

**NEVER DEFER CHECKLIST ITEMS.** Deferring items to future versions is prohibited.

- **Execute All Items:** Run every checklist item to the best of your ability
- **Present Results:** Show actual results to the user for decision-making
- **No Assumptions:** Never mark items as "Deferred to v3.4.0" or "Skipped"
- **Evidence Required:** Generate evidence files for all checks performed
- **User Decides:** Only the user can decide if results are acceptable for release

**Example - WRONG:**
```markdown
| **Type stubs for dependencies** | Check imports have type stubs | P2 | ⬜ | Deferred to v3.4.0 |
```

**Example - CORRECT:**
```markdown
| **Type stubs for dependencies** | Check imports have type stubs | P2 | ✅ | 50% have py.typed (13/26), 69.2% with stub packages (18/26) |
```

**If a check cannot be completed:**
1. Document why it cannot be completed (e.g., "Requires external API key")
2. Document what was attempted
3. Present partial results if any
4. Let the user decide whether to proceed

### Git and Release Operations

**DO NOT** commit, push, tag, or release without explicit user permission.

- **Pre-Commit Check:** Always ask: "Have we run the verification script?"
- **Release Checklist Required:** ALL commits and releases MUST complete the appropriate release checklist:
  - Use `docs/release_notes/release_checklist_template.md` to create version-specific checklist
  - Version-specific checklists: `docs/release_notes/RELEASE_v{VERSION}_CHECKLIST.md`
  - Complete ALL sections before creating release commit
  - Hotfixes: Use streamlined checklist focused on bug fixes only
  - Never skip checklist items without explicit user approval
  - **NO DEFERRALS:** Execute all items, present results, let user decide
- **Release Protocol:** Follow the strict Gating System (Security -> Artifact -> TestPyPI -> PyPI).
- **History Hygiene:** Ensure commit messages explain *why*, not just *what*.

### PyPI Release Process

The PyPI API token is stored in `.env` at the project root. Use it for uploads:

```bash
# Build the package
rm -rf dist/ build/ *.egg-info && python -m build

# Upload to PyPI using token from .env
source .env && python -m twine upload dist/* -u __token__ -p "$PYPI_TOKEN"
```

**Environment Variables in `.env`:**
- `PYPI_TOKEN` - PyPI API token (starts with `pypi-`)
- `TWINE_USERNAME` - Set to `__token__`
- `TWINE_REPOSITORY` - Set to `pypi`

**Never** hardcode or expose the token. Always source from `.env`.

### Release Documentation Structure

**Release Notes Location:** `docs/release_notes/RELEASE_NOTES_v{VERSION}.md`
- Comprehensive release documentation
- Executive summary, features, metrics, acceptance criteria
- Migration guide, use cases, known issues
- Performance benchmarks and comparison with previous version

**Release Artifacts Location:** `release_artifacts/v{VERSION}/`
- Evidence files documenting feature quality
- Test execution summaries
- Code coverage reports
- Performance metrics and logs

**Evidence File Format:** `v{VERSION}_{type}_evidence.json`
- `{type}` can be: `mcp_tools_evidence`, `test_evidence`, `performance_evidence`, etc.
- Structured JSON with tool specs, test counts, coverage %, metrics
- Matches previous release format for consistency
- Serves as audit trail and release verification

**Creating Release Documentation:**
1. Generate comprehensive release notes in `docs/release_notes/RELEASE_NOTES_v{VERSION}.md`
2. Create evidence files in `release_artifacts/v{VERSION}/` with tool specs and test data
3. Include acceptance criteria verification checklist
4. Add performance metrics and comparison with previous version
5. Document any known issues or limitations

### Before You Code Checklist

1. Read and understand the existing code before modifying
2. Write failing tests FIRST (TDD mandatory)
3. Run `pytest tests/` to verify baseline
4. After changes: run `ruff check` and `black --check`
5. Verify coverage has not dropped below 95%
6. Ask for commit permission - never commit automatically

## Verification and Quality Gates

- **TDD Mandatory:** Write the failing test *before* the implementation.
- **Adversarial Testing:** Test the "Hacker Path" (e.g., overflow, injection, infinite loops, huge integers).
- **Coverage Standard:** Maintain strict coverage (current baseline: 95%, target: 100%).
- **Hygiene:** Run `ruff` and `black` on every file touched. No `bare except:` allowed.

## Architecture and Constraints

### Governance Profiles

> [20251226_DOCS] Code Scalpel supports multiple governance profiles for different team sizes and compliance needs.

**Profile Selection Matrix:**

| Profile | Team Size | Budget | Compliance | Agent Token Overhead |
|---------|-----------|--------|------------|---------------------|
| `permissive` | Solo/Hobby | $0 | None | 0 tokens |
| `minimal` | 1-5 devs | Limited | Basic audit | ~50 tokens |
| `default` | 5-20 devs | Moderate | Standard | ~100 tokens |
| `restrictive` | 20+ devs | Enterprise | SOC2/ISO | ~150 tokens |

**Configuration Files:**
- `.code-scalpel/config.json` - Standard balanced governance profile
- `src/code_scalpel/capabilities/limits.toml` - **Tier-based capability limits** (Community/Pro/Enterprise) - SOURCE OF TRUTH for tier tests
- `.code-scalpel/response_config.json` - Response verbosity & token efficiency profiles
- `.code-scalpel/architecture.toml` - Dependency rules & architectural boundaries
- `.code-scalpel/budget.yaml` - Agent operation budgets (max files, tokens, API calls)
- `.code-scalpel/governance.yaml` - Full governance policy set
- `.code-scalpel/governance.minimal.yaml` - Minimal security-focused policy
- `.code-scalpel/policy.yaml` - OPA-based policy rules
- `.code-scalpel/GOVERNANCE_PROFILES.md` - Profile selection matrix & guidance

**CRITICAL: limits.toml defines tier limits used in tier tests:**
```toml
[community.get_call_graph]
max_depth = 3
max_nodes = 50

[pro.get_call_graph]
max_depth = 50
max_nodes = 500

[enterprise.get_call_graph]
max_depth = ~
max_nodes = ~
```
Tests verify these limits are enforced. See `tests/tools/tiers/test_get_call_graph_tiers.py` for pattern.

**Key Design Principle:** Governance is server-side. The agent only receives pass/fail (~50 tokens), never the full policy files. This preserves context window for code work.

See `.code-scalpel/GOVERNANCE_PROFILES.md` for detailed guidance.

### Symbolic Execution (Z3) - v1.3.0 Status

**Supported Types:** Int, Bool, String, Float (as of v1.3.0)

- **State Isolation:** `SymbolicState` must use deep copies/forking. Never share mutable constraint lists between branches.
- **Smart Forking:** Always check `solver.check()` *before* branching to prevent zombie paths.
- **Type Marshaling:** Never leak raw Z3 objects. Convert to Python `int`/`bool`/`str`/`float` at the API boundary.
- **Bounded Unrolling:** All loops must have a `fuel` limit (default: 10) to prevent hanging.
- **String Constraints:** String solving is expensive. Ensure constraints are bounded.

**Not Yet Supported:** List, Dict, complex objects (planned for future releases)

### Security Analysis (v1.3.0)

Key components:
- `TaintTracker`: Tracks tainted data flow through variables
- `SecurityAnalyzer`: Detects vulnerabilities via source-sink analysis
- `TaintLevel`: UNTAINTED, LOW, MEDIUM, HIGH, CRITICAL

**Vulnerability Detection:**
- SQL Injection (CWE-89)
- XSS (CWE-79)
- Command Injection (CWE-78)
- Path Traversal (CWE-22)
- NoSQL Injection (v1.3.0+)
- LDAP Injection (v1.3.0+)
- Secret Detection (v1.3.0+)

**Guidelines:**
- Always consider Sanitizers to prevent false positives
- Mark taint sources explicitly (request.args, user input, etc.)
- Check sinks at dangerous operations (execute, system, open, render)

## Documentation Management and Organization

### Document Taxonomy

**Project documents are organized into the following structure:**

#### Root-Level Documents (Project Status & Governance)
Located directly in `/` root:
- `README.md` - Project overview and quick start guide
- `SECURITY.md` - Security policies, reporting, and advisories
- `DEVELOPMENT_ROADMAP.md` - Future features, milestones, and strategic direction
- `LICENSE` - Legal licensing terms (MIT)
- `DOCKER_QUICK_START.md` - Quick Docker deployment guide

**Detailed documentation:** 
- Deployment procedures: `docs/deployment/`
- Release documentation: `docs/release_notes/`

**Purpose:** Accessibility and project visibility for new contributors and stakeholders.

#### docs/ Directory (Comprehensive Documentation)
Organized into topical subdirectories:

**Core Documentation:**
- `docs/INDEX.md` - Master table of contents for all documentation
- `docs/COMPREHENSIVE_GUIDE.md` - End-to-end guide for all features
- `docs/DOCUMENT_ORGANIZATION.md` - Documentation organization reference guide
- `docs/QUICK_REFERENCE_DOCS.md` - Quick lookup guide for finding documentation
- `docs/getting_started.md` - Getting started for developers
- `docs/CONTRIBUTING_TO_MCP_REGISTRY.md` - MCP registry contribution guide

**Structured Subdirectories:**
- `docs/architecture/` - System design, module descriptions, data flows
- `docs/guides/` - How-to guides and tutorials for specific features
- `docs/modules/` - Per-module API reference and internal design
- `docs/parsers/` - Parser implementation details and language support
- `docs/ci_cd/` - CI/CD pipeline configuration and automation
- `docs/deployment/` - Deployment procedures, troubleshooting, and infrastructure
- `docs/compliance/` - Regulatory, security, and audit documentation
- `docs/release_notes/` - Version-specific release documentation (see below)
- `docs/release_gate_checklist.md` - Pre-release verification checklist
- `docs/examples.md` - Code examples and use case demonstrations
- `docs/agent_integration.md` - Integration guide for AI agents and MCP clients
- `docs/V1.5.1_TEAM_ONBOARDING.md` - Onboarding guide for team members
- `docs/internal/` - Internal team documentation, design discussions
- `docs/research/` - Research findings, benchmarks, experimental work

**Purpose:** Organized, discoverable, topic-specific documentation.

#### docs/release_notes/ (Version-Specific Documentation)
Format: `RELEASE_NOTES_v{VERSION}.md`

**Content Requirements:**
- Executive summary of the release
- New features with examples
- Bug fixes and improvements
- Performance metrics and benchmarks
- Breaking changes and migration guide
- Known issues and limitations
- Contributors and acknowledgments

**Examples:**
- `docs/release_notes/RELEASE_NOTES_v1.5.0.md`
- `docs/release_notes/RELEASE_NOTES_v1.5.1.md`
- `docs/release_notes/RELEASE_NOTES_v2.0.0.md`

**Purpose:** Historical record and migration guide for users upgrading versions.

#### release_artifacts/ (Structured Evidence and Validation)
Organized by version: `release_artifacts/v{VERSION}/`

**Standard Contents:**
- `v{VERSION}_mcp_tools_evidence.json` - MCP tool specifications and inventory
- `v{VERSION}_test_evidence.json` - Test execution results, coverage metrics
- `v{VERSION}_performance_evidence.json` - Benchmark results and comparisons
- `v{VERSION}_security_evidence.json` - Security scan results and vulnerability status
- `v{VERSION}_deployment_evidence.json` - Deployment validation results

**Evidence File Structure (JSON):**
```json
{
  "version": "1.5.0",
  "timestamp": "2025-12-13T10:00:00Z",
  "metrics": {
    "test_count": 2045,
    "coverage_percentage": 95.2,
    "passing_tests": 2045
  },
  "tools_inventory": [
    {
      "name": "analyze_code",
      "status": "stable",
      "description": "Parse and extract code structure"
    }
  ],
  "acceptance_criteria": {
    "coverage_threshold_met": true,
    "security_scan_passed": true,
    "all_tests_passing": true
  }
}
```

**Purpose:** Audit trail, verification records, and reproducible evidence.

#### examples/ (Code Examples and Demonstrations)
Contains runnable example code for all integrations:
- `examples/claude_example.py` - Claude API integration
- `examples/autogen_example.py` - AutoGen framework example
- `examples/langchain_example.py` - LangChain integration
- `examples/crewai_example.py` - CrewAI framework example
- `examples/security_analysis_example.py` - Security scanning demo
- `examples/symbolic_execution_example.py` - Symbolic execution demo

**Purpose:** Concrete, executable demonstrations of Code Scalpel capabilities.

### Document Maintenance Rules

**When Adding New Documentation:**
1. **Classify first:** Determine if document is:
   - Root-level (project status, governance)
   - Docs subdirectory (feature/topic documentation)
   - Release artifacts (evidence and validation)
   - Examples (runnable code)

2. **File naming:** Use descriptive names with underscores or version tags:
   - Topics: `TOPIC_DESCRIPTION.md` (e.g., `agent_integration.md`)
   - Versions: `DOCUMENT_NAME_v{VERSION}.md` (e.g., `RELEASE_NOTES_v1.5.0.md`)
   - Evidence: `v{VERSION}_{type}_evidence.json` (e.g., `v1.5.0_test_evidence.json`)

3. **Index updates:** 
   - Update `docs/INDEX.md` to list new documents
   - Update root `README.md` if document affects project overview
   - Add to relevant section headers in all-encompassing guides

4. **Cross-references:** Link between documents using markdown relative paths:
   - Same directory: `[Link text](document.md)`
   - Different directory: `[Link text](../other_dir/document.md)`
   - With sections: `[Link text](../path/document.md#section-heading)`

**When Updating Documentation:**
1. **Change tagging:** Mark documentation updates with version/date:
   ```markdown
   > [20251215_DOCS] Updated agent integration examples
   ```

2. **Consistency check:** Ensure terminology and examples match current codebase
3. **Link validation:** Test that relative links still work after changes
4. **TOC updates:** Update table of contents if headers change

**Document Lifecycle:**
- **Active:** Current version guides, latest release notes
- **Archived:** Previous release notes (kept for historical reference)
- **Deprecated:** Old documentation marked as such, kept for reference only
  ```markdown
  > **DEPRECATED:** This documentation is outdated. See [new guide](link.md) instead.
  ```

### Document Quality Standards

**Style Consistency:**
- Professional, clinical tone (no emojis, no casual language)
- Markdown headers hierarchically: `#` → `##` → `###`
- Use code blocks with language specification: ` ```python`
- Include table of contents in long documents

**Content Accuracy:**
- Code examples must be tested against current codebase
- Version numbers must match actual releases
- API documentation must match actual function signatures
- Feature claims must be verified against source code

**Accessibility:**
- Clear section headings for scannability
- Bullet points for lists (not numbered unless order matters)
- Tables for comparing options
- "See also" sections linking related documents
- Plain English; avoid jargon without explanation

### Documentation Tools and Automation

**Verify Documentation:**
- Before committing, check all relative links work: `grep -r "\[.*\](.*\.md)" docs/`
- Validate JSON evidence files: `python -m json.tool release_artifacts/v*/\*.json`
- Ensure all release notes are in `docs/release_notes/` directory

**Keep Updated:**
- When releasing a new version, create corresponding release notes and evidence files
- Update `docs/INDEX.md` to reflect new documentation
- Archive old release notes (don't delete)
- Update version references in example files

## Documentation Style

- **NO EMOJIS:** Professional, clinical tone only.
- **Truth over Hype:** Clearly label features as "Beta" or "Experimental" if they are not fully robust.
- **Format:** Use Markdown headers, tables, and bullet points for scannability.


## Code Style

- **Python 3.9+** standards
- **Formatting:** Strict `Black` (line length 88)
- **Linting:** Strict `Ruff`
- **Type Hints:** Required for all function signatures
- **Docstrings:** Required for public functions and classes

## Project Context

# [20260327_DOCS] Updated for v2.1.2 "PHP & Oracle Patch" release
Code Scalpel v2.1.2 is an MCP server toolkit for AI-driven surgical code operations.

| Module | Status | Coverage |
|--------|--------|----------|
| AST Analysis | Stable | 100% |
| PDG Builder | Stable | 100% |
| PDG Analyzer | Stable | 100% |
| PDG Slicer | Stable | 100% |
| Symbolic Engine | Stable | 100% |
| Security Analysis | Stable | 100% |
| MCP Server | Stable | 22 tools |
| Polyglot Parsers | Stable | 90%+ |
| Autonomy Engine | Stable | 90%+ |
| Unified Cache | Stable | 95%+ |

**Version:** 2.1.2 (March 27, 2026)
**Test Suite:** 7,700+ tests passing (100% pass rate)
**Coverage Gate:** ≥90% combined (statement + branch)
**Current Coverage:** 94.86%+ combined (96%+ stmt, 90%+ branch)

**MCP Tools (Current - v2.1.2 - 22 tools):**
- `analyze_code` - Parse and extract code structure (13 languages: Python, JS, TS, Java, Go, Kotlin, PHP, Ruby, Swift, Rust, C, C++, C#)
- `extract_code` - Surgical extraction by symbol name with cross-file deps (polyglot)
- `update_symbol` - Safely replace functions/classes/methods in files
- `rename_symbol` - Rename functions/classes/methods throughout codebase
- `security_scan` - Taint-based vulnerability detection (polyglot)
- `unified_sink_detect` - Unified polyglot sink detection with confidence (13 languages)
- `cross_file_security_scan` - Cross-module taint tracking (polyglot)
- `generate_unit_tests` - Symbolic execution test generation
- `simulate_refactor` - Verify refactor preserves behavior
- `symbolic_execute` - Symbolic path exploration with Z3
- `crawl_project` - Project-wide analysis (Python-first, expanding)
- `scan_dependencies` - Scan for vulnerable dependencies (OSV API)
- `get_file_context` - Get surrounding context for code locations (polyglot)
- `get_symbol_references` - Find all uses of a symbol (Python-first)
- `get_cross_file_dependencies` - Analyze cross-file dependency chains (Python-first, JS/TS slice)
- `get_call_graph` - Generate call graphs and trace execution flow (Python + JS/TS function parity)
- `get_graph_neighborhood` - Extract k-hop neighborhood subgraph (Python + JS/TS)
- `get_project_map` - Generate comprehensive project structure map
- `validate_paths` - Validate path accessibility for Docker deployments
- `verify_policy_integrity` - Cryptographic policy file verification
- `code_policy_check` - Check code against style guides and compliance standards
- `type_evaporation_scan` - Detect TypeScript type evaporation vulnerabilities

**Latest Release:** v2.1.2
- Release Date: March 27, 2026
- Previous Release: v2.1.0 (March 2, 2026) - Go language support
- Release Notes: `docs/release_notes/RELEASE_NOTES_v2.0.0.md`
- Evidence Files: `release_artifacts/v2.0.0/`, `release_artifacts/v2.1.0/`
- **Recent Changes:**
  - v2.1.2: CLI Oracle patch for error recovery
  - v2.1.1: Metadata sync for PyPI packaging
  - v2.1.0: Go language support added (13 total languages)

## Communication

- Be direct and concise
- Explain technical decisions when relevant
- Provide options when there are tradeoffs
- Ask clarifying questions rather than assuming
- Never announce tool names to the user