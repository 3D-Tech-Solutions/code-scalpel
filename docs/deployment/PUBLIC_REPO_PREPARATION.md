# Public Repository Preparation Guide
**Creating Community Tier Public Repository**

> [20260108_STRATEGY] Package separation strategy for true open-core distribution

---

## Architecture Change Required

The current v3.3.0 implementation uses **runtime tier checks** in a single package. This needs to change to:

❌ **Current (Incorrect):** Single package with all code + runtime tier checks  
✅ **Target (Correct):** Separate packages loaded as plugins based on license validation

### Package Structure

```
code-scalpel (Community - MIT, Public GitHub)
├── Community tier features only
├── Plugin system for Pro/Enterprise
└── License validation hooks

code-scalpel-pro (Commercial, Private Repo)
├── Depends on: code-scalpel
├── Pro feature implementations
└── Registers Pro features at MCP server boot

code-scalpel-enterprise (Commercial, Private Repo)
├── Depends on: code-scalpel-pro
├── Enterprise feature implementations
└── Registers Enterprise features at MCP server boot
```

---

## Strategy: Extract Pro/Enterprise Features

The public repo must contain **only Community tier features**. Pro/Enterprise features are loaded dynamically as plugins after license validation.

### Phase 1: Feature Extraction Analysis

#### 1. Identify Pro/Enterprise Features Per Tool

For each MCP tool, identify what's Community vs Pro vs Enterprise:

**Complete Tool-by-Tool Feature Matrix (All 22 Tools):**

| # | Tool | Community | Pro | Enterprise |
|---|------|-----------|-----|------------|
| 1 | `analyze_code` | Python/JS/TS/Java AST parsing, max 1MB files | Cognitive complexity, code smells, Halstead metrics, framework detection, max 10MB | Custom analyzers, compliance mapping, unlimited size |
| 2 | `code_policy_check` | Basic style rules (PEP8, ESLint) | Custom rules, org policies, multi-language | Compliance auditing (HIPAA, SOC2, PCI-DSS), governance workflows |
| 3 | `crawl_project` | Max 100 files, language detection, basic complexity | Unlimited files, parallel processing, framework detection, dependency mapping | Distributed crawling, historical trends, compliance scanning |
| 4 | `cross_file_security_scan` | Cross-file taint (depth=3, modules=10) | Advanced taint (depth=10, modules=100), confidence scoring | Unlimited depth/modules, microservice boundary detection |
| 5 | `extract_code` | Single symbol extraction (Python/JS/TS/Java) | Cross-file dependencies (Python), React component metadata | Org-wide resolution, service boundary detection, microservice packaging |
| 6 | `generate_unit_tests` | Max 5 test cases, pytest only | Max 20 test cases, pytest + unittest, data-driven tests | Unlimited test cases, bug reproduction from crash logs |
| 7 | `get_call_graph` | Depth=3, max 50 nodes, Python/JS/TS | Depth=50, max 500 nodes, polymorphism resolution | Unlimited nodes, hot path ID, dead code detection, architectural enforcement |
| 8 | `get_cross_file_dependencies` | Depth=1 (direct only), max 50 files | Depth=5, max 500 files, alias resolution, wildcard handling, re-export chains | Architectural firewall, layer boundary enforcement, custom dependency rules |
| 9 | `get_file_context` | Functions/classes/imports list, max 20 imports, security warnings | Semantic summarization, intent extraction, smart context expansion (2000 lines) | Code quality metrics, compliance flags, architectural tags |
| 10 | `get_graph_neighborhood` | k=1 hop, max 50 nodes | k=5 hops, max 500 nodes, semantic neighbors | Unlimited hops/nodes, graph query language (custom traversals) |
| 11 | `get_project_map` | Package/module hierarchy, complexity hotspots | Architecture patterns, framework detection, city map visualization | Architectural compliance, debt quantification, CODEOWNERS integration |
| 12 | `get_symbol_references` | Max 10 files searched, Python only | Unlimited files, multi-language, shadowing detection | Risk scoring, CODEOWNERS attribution, team coordination |
| 13 | `rename_symbol` | Same-file renames (Python/JS/TS/Java) | Cross-file renames, batch operations | Audit trail, breaking change detection, team notifications |
| 14 | `scan_dependencies` | Max 50 deps, CVE detection (Python/JS/Java) | Unlimited deps, license scanning, transitive dependencies | Policy violations, SBOM generation, supply chain risk scoring |
| 15 | `security_scan` | Max 50 findings, max 500KB files, SQL/XSS/Command/Path basic taint | Unlimited findings, NoSQL/LDAP/Secret detection, CSRF/SSRF | Custom policies, compliance reports, SAST integration, crypto validation |
| 16 | `simulate_refactor` | Basic behavior verification, security diff | Code smell detection, semantic equivalence hints | Full behavioral analysis, rollback strategies, risk quantification |
| 17 | `symbolic_execute` | Max 50 paths, max 10 loop depth, Int/Bool/String/Float | Unlimited paths, max 100 loop depth, List/Dict types, concolic execution | Unbounded exploration, custom constraints, formal verification |
| 18 | `type_evaporation_scan` | Frontend-only, max 50 files, explicit any detection | Frontend+backend correlation, implicit any, network boundary analysis | Zod/Pydantic schema generation, API contract validation, schema coverage |
| 19 | `unified_sink_detect` | Python/JS/TS/Java sink detection, CWE mapping | Confidence scoring, context-aware detection | Custom sink patterns, framework-specific rules, org-specific patterns |
| 20 | `update_symbol` | Single symbol replacement, syntax validation, backup creation | Multi-file atomic updates, cross-reference updates | Audit trail, team coordination, policy enforcement |
| 21 | `validate_paths` | Path accessibility checking, Docker detection, batch validation | (Same as Community) | (Same as Community) |
| 22 | `verify_policy_integrity` | Basic cryptographic verification (HMAC-SHA256) | Certificate chain validation, revocation checking | Custom CAs, HSM integration, multi-tenant support, version tracking |

**Action Items:**
- [ ] Document exact feature split for each tool (create FEATURE_EXTRACTION_PLAN.md)
- [ ] Identify shared utilities that stay in Community
- [ ] Identify Pro-only utilities
- [ ] Identify Enterprise-only utilities

#### 2. Plugin Architecture Design

- [ ] **Design plugin registration system**:
  ```python
  # In community package: src/code_scalpel/plugins/registry.py
  class FeatureRegistry:
      """Register Pro/Enterprise feature extensions."""
      _features: Dict[str, FeaturePlugin] = {}
      
      @classmethod
      def register(cls, feature: FeaturePlugin):
          """Register a feature plugin (called by Pro/Enterprise packages)."""
          cls._features[feature.name] = feature
      
      @classmethod
      def get_feature(cls, name: str) -> Optional[FeaturePlugin]:
          """Get registered feature plugin."""
          return cls._features.get(name)
  ```

- [ ] **Design license validation hook**:
  ```python
  # In community package: src/code_scalpel/licensing/validator.py
  class LicenseValidator:
      """Validate Pro/Enterprise licenses at MCP server boot."""
      
      @staticmethod
      def validate_license() -> LicenseTier:
          """Check for valid license, return tier."""
          # Check for code-scalpel-pro package + valid license
          # Check for code-scalpel-enterprise package + valid license
          # Return: COMMUNITY | PRO | ENTERPRISE
          pass
      
      @staticmethod
      def load_tier_plugins(tier: LicenseTier):
          """Load appropriate plugins based on validated tier."""
          if tier >= LicenseTier.PRO:
              try:
                  import code_scalpel_pro
                  code_scalpel_pro.register_features()
              except ImportError:
                  pass
          
          if tier >= LicenseTier.ENTERPRISE:
              try:
                  import code_scalpel_enterprise
                  code_scalpel_enterprise.register_features()
              except ImportError:
                  pass
  ```

- [ ] **Design MCP server boot sequence**:
  ```python
  # In community package: src/code_scalpel/mcp/server.py
  async def initialize_server():
      """Initialize MCP server with license-based feature loading."""
      # 1. Validate license
      tier = LicenseValidator.validate_license()
      
      # 2. Load tier-specific plugins
      LicenseValidator.load_tier_plugins(tier)
      
      # 3. Register MCP tools (Community + loaded plugins)
      register_community_tools(mcp)
      
      # 4. Register plugin tools (if Pro/Enterprise loaded)
      for feature in FeatureRegistry.get_all():
          feature.register_tools(mcp)
  ```

#### 3. Security & Sensitive Data Review

- [ ] **Remove sensitive files** (already in .gitignore, verify not committed):
  ```bash
  # Check for accidentally committed sensitive files
  git log --all --full-history -- .env
  git log --all --full-history -- *.pem
  git log --all --full-history -- *.key
  git log --all --full-history -- .code-scalpel/license*.jwt
  git log --all --full-history -- certs/
  ```

- [ ] **Remove internal documents** (move to private repo):
  - docs/internal/ ✅ (already in .gitignore)
  - docs/status/ ✅ (already in .gitignore)
  - docs/analysis/ ✅ (already in .gitignore)
  - docs/go_to_market/ ⚠️ (currently public, should move to private)
  - docs/testing/ ⚠️ (internal assessments, should clean or move)

- [ ] **Audit commit history** for accidentally committed secrets:
  ```bash
  # Use git-secrets or similar
  git secrets --scan-history
  ```

- [ ] **Remove all Pro/Enterprise feature code**:
  ```bash
  # Extract Pro features to separate repo
  # Extract Enterprise features to separate repo
  # Ensure Community package has no Pro/Enterprise code paths
  ```

#### 2. Documentation Cleanup

- [ ] **Keep public-facing docs**:
  - README.md ✅
  - SECURITY.md ✅
  - CONTRIBUTING.md ✅
  - CHANGELOG.md ✅
  - LICENSE ✅
  - DOCKER_QUICK_START.md ✅
  - docs/COMPREHENSIVE_GUIDE.md
  - docs/guides/
  - docs/architecture/
  - docs/reference/
  - docs/release_notes/

- [ ] **Remove or move private strategy docs**:
  ```bash
  # Move GTM strategy to private repo
  mkdir ../code-scalpel-private
  git mv docs/go_to_market ../code-scalpel-private/
  git mv docs/internal ../code-scalpel-private/
  git mv docs/testing ../code-scalpel-private/  # Internal assessment docs
  ```

#### 3. README Updates for Public Audience

- [ ] Update README.md with:
  - Clear value proposition (why Code Scalpel vs alternatives)
  - Quick start guide (install + first MCP tool call)
  - Link to comprehensive guide
  - Community tier capabilities clearly listed
  - Pro/Enterprise "Learn More" links (not pricing)
  - Discord/community links
  - Contributing guidelines reference

- [ ] Add badges:
  ```markdown
  [![PyPI](https://badge.fury.io/py/code-scalpel.svg)](https://pypi.org/project/code-scalpel/)
  [![Tests](https://img.shields.io/badge/tests-4388%20passed-brightgreen.svg)](https://github.com/3D-Tech-Solutions/code-scalpel)
  [![Coverage](https://img.shields.io/badge/coverage-94%25-brightgreen.svg)](release_artifacts/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
  [![Discord](https://img.shields.io/discord/YOUR_ID?label=discord&logo=discord)](https://discord.gg/YOUR_INVITE)
  ```

#### 4. Community Setup

- [ ] **Create Discord server** (if not exists)
  - #general, #support, #showcase, #development channels
  - Clear community guidelines
  - Link in README.md

- [ ] **Enable GitHub Discussions**
  - Categories: Q&A, Show & Tell, Feature Requests, Ideas

- [ ] **Issue templates**:
  - Bug report template
  - Feature request template
  - Security vulnerability template (private)

- [ ] **Pull request template**:
  - Checklist: tests, docs, changelog
  - CLA requirement (if needed)

#### 5. Licensing Clarity

- [ ] **Update LICENSE file header** in README.md:
  ```markdown
  ## License & Tiers
  
  **Community Edition:** MIT License (free, unlimited use)
  - All 22 MCP tools included
  - Runtime limits on some features (file counts, depth limits)
  - Perfect for individual developers and small teams
  
  **Pro Edition:** Commercial license required
  - Unlimited processing (no file/depth limits)
  - Advanced cross-file analysis
  - Priority support
  - [Learn more](https://codescalpel.dev/pro)
  
  **Enterprise Edition:** Commercial license required
  - All Pro features
  - Custom policies, compliance reporting
  - SSO/SAML, RBAC
  - SLA support
  - [Contact sales](https://codescalpel.dev/enterprise)
  ```

#### 6. CI/CD Public Visibility

- [ ] **Update GitHub Actions** for public repo:
  - Remove any private registry pushes
  - Ensure all secrets are properly configured
  - Make workflow badges public

- [ ] **Remove private dependencies** (if any):
  - Check requirements.txt for internal packages
  - Verify all dependencies are on public PyPI

#### 7. Git History Cleanup (Optional)

If commit history has sensitive data that can't be removed via .gitignore:

- [ ] **Option A: Rewrite history** (DANGEROUS):
  ```bash
  # Use BFG Repo-Cleaner or git filter-repo
  git filter-repo --path-glob '*.pem' --invert-paths
  git push --force --all origin
  ```

- [ ] **Option B: Start fresh** (SAFER):
  ```bash
  # Archive current repo, create new clean repo
  # Import only clean commits
  ```

---

## Execution Plan

### Step 1: Create Feature Extraction Plan

**Critical First Step:** Document exactly what gets extracted from each tool.

```bash
cd /mnt/k/backup/Develop/code-scalpel
# Create detailed feature extraction document
# This will guide the code split
```

**Required Document:** `FEATURE_EXTRACTION_PLAN.md`

Must include:
- Tool-by-tool analysis
- What code stays in Community
- What code moves to Pro package
- What code moves to Enterprise package
- Interface contracts between packages
- Plugin registration patterns

### Step 2: Create Package Structure

```bash
# Create three separate repositories
cd /mnt/k/backup/Develop

# 1. Community (public, MIT)
git clone code-scalpel code-scalpel-community
cd code-scalpel-community
# Extract only Community features
# Add plugin system
# Add license validation hooks

# 2. Pro (private, commercial)
mkdir code-scalpel-pro
cd code-scalpel-pro
git init
# Extract Pro features from original repo
# Create setup.py with dependency on code-scalpel
# Implement feature registration

# 3. Enterprise (private, commercial)
mkdir code-scalpel-enterprise
cd code-scalpel-enterprise
git init
# Extract Enterprise features from original repo
# Create setup.py with dependency on code-scalpel-pro
# Implement feature registration
```

### Step 3: Create Private Backup Repo (Safety Net)

```bash
# On GitHub: Create private repo "code-scalpel-full-backup"
cd /mnt/k/backup/Develop
git clone code-scalpel code-scalpel-full-backup
cd code-scalpel-full-backup
git remote rename origin old-origin
git remote add origin git@github.com:3D-Tech-Solutions/code-scalpel-full-backup.git
git push -u origin --all
git push -u origin --tags
```

### Step 4: Move Private Docs

```bash
cd /mnt/k/backup/Develop/code-scalpel

# Move GTM strategy to private repo
mkdir -p ../code-scalpel-private-docs/go_to_market
mv docs/go_to_market/* ../code-scalpel-private-docs/go_to_market/

# Move internal testing docs
mkdir -p ../code-scalpel-private-docs/testing
mv docs/testing/* ../code-scalpel-private-docs/testing/

# Move internal management docs
mkdir -p ../code-scalpel-private-docs/internal
mv docs/internal/* ../code-scalpel-private-docs/internal/

# Move week 1 launch materials
mkdir -p ../code-scalpel-private-docs/week_1_launch
mv docs/week_1_launch/* ../code-scalpel-private-docs/week_1_launch/

# Commit removals
git add -A
git commit -m "docs: Move private strategy/internal docs to separate repo for public release

Moved to private repository:
- GTM strategy and launch playbooks
- Internal testing assessments
- Week 1 launch materials
- Project management documents

Keeps public repo focused on technical documentation.

[20260108_REFACTOR] v3.3.0 - Public repository preparation"
```

### Step 3: Update .gitignore for Public Repo

Already has most exclusions, verify:

```gitignore
# Already in .gitignore (verify):
.code-scalpel/license*.jwt
certs/
keys/
*.pem
*.key
docs/internal/
docs/status/
docs/analysis/
docs/summaries/
docs/project-management/
```

### Step 4: Clean README for Public Audience

Update README.md:
- Emphasize community tier value (not "limited free trial")
- Clear "why Code Scalpel" positioning vs Copilot
- Quick start > feature list
- Community links (Discord, Discussions)
- Remove internal roadmap details

### Step 5: Enable Community Features

On GitHub repository settings:
- [ ] Make repository public
- [ ] Enable Issues
- [ ] Enable Discussions
- [ ] Enable Wiki (optional)
- [ ] Add topics: `mcp-server`, `ai-tools`, `code-analysis`, `python`, `ast`
- [ ] Add description: "MCP Server Toolkit for AI Agents - Surgical code operations with AST, PDG, and Symbolic Execution"

### Step 6: Add Issue/PR Templates

```bash
mkdir -p .github/ISSUE_TEMPLATE
cat > .github/ISSUE_TEMPLATE/bug_report.yml << 'TEMPLATE'
name: Bug Report
description: Report a bug in Code Scalpel
title: "[Bug]: "
labels: ["bug", "triage"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for reporting a bug! Please fill out the information below.
  - type: input
    id: version
    attributes:
      label: Code Scalpel Version
      description: Output of `pip show code-scalpel`
      placeholder: "3.3.0"
    validations:Package)

✅ **Community tier source code** (MIT license)  
✅ **Plugin system infrastructure** (FeatureRegistry, plugin interfaces)  
✅ **License validation hooks** (validation logic, not licenses themselves)  
✅ **Community MCP tools** (base functionality only)  
✅ **Documentation** (guides, architecture, Community tier API reference)  
✅ **Examples** (Community tier integration examples)  
✅ **Tests** (Community tier test suite)  
✅ **Release notes** (Community tier versions)

**Community Tier Tools (Base Functionality - All 22 Tools Included):**

1. **analyze_code** - Python/JS/TS/Java AST parsing (max 1MB files)
2. **code_policy_check** - Basic style checking (PEP8, ESLint)
3. **crawl_project** - Max 100 files, language detection, basic complexity
4. **cross_file_security_scan** - Cross-file taint tracking (depth=3, modules=10)
5. **extract_code** - Single symbol extraction (Python/JS/TS/Java)
6. **generate_unit_tests** - Max 5 test cases, pytest only
7. **get_call_graph** - Depth=3, max 50 nodes, Python/JS/TS
8. **get_cross_file_dependencies** - Depth=1 (direct only), max 50 files
9. **get_file_context** - Functions/classes/imports, max 20 imports
10. **get_graph_neighborhood** - k=1 hop, max 50 nodes
11. **get_project_map** - Package/module hierarchy, complexity hotspots
12. **get_symbol_references** - Max 10 files searched, Python only
13. **rename_symbol** - Same-file renames (Python/JS/TS/Java)
14. **scan_dependencies** - Max 50 deps, CVE detection (Python/JS/Java)
15. **security_scan** - Max 50 findings, SQL/XSS/Command/Path taint
16. **simulate_refactor** - Basic behavior verification, security diff
17. **symbolic_execute** - Max 50 paths, Int/Bool/String/Float types
18. **type_evaporation_scan** - Frontend-only, max 50 files
19. **unified_sink_detect** - Python/JS/TS/Java sink detection, CWE mapping
20. **update_symbol** - Single symbol replacement with backups
21. **validate_paths** - Path accessibility checking, Docker detection
22. **verify_policy_integrity** - Basic HMAC-SHA256 verification

## What Moves to Pro Package (Private Repo)

⚠️ **Pro tier feature implementations**  
⚠️ **Pro plugin registration code**  
⚠️ **Cross-file analysis capabilities**  
⚠️ **Advanced security scanning**  
⚠️ **Unlimited processing features**  
⚠️ **Pro tier tests**  
⚠️ **Pro tier documentation**

## What Moves to Enterprise Package (Private Repo)

⚠️ **Enterprise tier feature implementations**  
⚠️ **Enterprise plugin registration code**  
⚠️ **Custom policy engines**  
⚠️ **Compliance reporting (HIPAA, SOC2, PCI-DSS)**  
⚠️ **SSO/SAML integration**  
⚠️ **Organization-wide analysis**  
⚠️ **Audit trails and versioning**  
⚠️ **Enterprise tier tests**  
⚠️ **Enterprise tier documentation**

## What Moves to Internal Docs Repo (Private)

⚠️ **GTM strategy** (competitive intelligence)  
⚠️ **Internal testing assessments** (not user-facing)  
⚠️ **Week 1 launch materials** (internal execution docs)  
⚠️ **Project management docs** (internal status tracking)  
⚠️ **Full feature extraction plan** (shows Pro/Enterprise capabilities
        2. 
        3. 
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: Expected Behavior
      description: What you expected to happen
    validations:
      required: true
  - type: textarea
    id: actual
    attributes:
      label: Actual Behavior
      description: What actually happened
    validations:
      required: true
TEMPLATE
```

### Step 7: Announcement Plan

Once public:

1. **GitHub Release** for v3.3.0 (if not already public)
2. **Tweet** announcement
3. **Blog post** (Dev.to, Medium)
4. **Reddit** r/Python, r/MachineLearning, r/LocalLLaMA
5. **Hacker News** "Show HN: Code Scalpel - MCP Server for Surgical Code Operations"
6. **ProductHunt** (Week 1 plan already exists)

---

## What Stays Public (Community Tier)

✅ **All source code** (MIT license)  
✅ **All 22 MCP tools** (with runtime tier checks)  
✅ **Complete documentation** (guides, architecture, API reference)  
✅ **Examples** (all integration examples)  
✅ **Tests** (full test suite visible)  
✅ **Release notes** (all versions)

## What Moves Private

⚠️ **GTM strategy** (competitive intelligence)  
⚠️ **Internal testing assessments** (not user-facing)  
⚠️ **Week 1 launch materials** (internal execution docs)  
⚠️ **Project management docs** (internal status tracking)  
⚠️ **Pro/Enterprise licensing infrastructure** (if implemented separately)

---

## Post-Publication Monitoring

### Week 1 After Public
- [ ] Monitor GitHub stars/forks/watchers daily
- [ ] Respond to all issues within 24 hours
- [ ] Welcome new contributors
- [ ] Update docs based on first-time user feedback

### Metrics to Track
- GitHub stars (target: 100 in first week)
- PyPI downloads (track via PyPI stats)
- Discord members (target: 30 in first week)
- Issues opened/closed
- Pull requests submitted

---

## Decision: GitHub Organization or Personal?

**Recommendation:** Create `code-scalpel` GitHub organization

Benefits:
- Professional appearance
- Multiple repos under one brand (code-scalpel, code-scalpel-docs, code-scalpel-examples)
- Team members can be added
- Looks more serious to enterprises

---

## Timeline

**Day 1 (Today):**
- ✅ Create private backup repo
- ✅ Move private docs to separate repo
- ✅ Update .gitignore verification
- ✅ Clean commit history check

**Day 2:**
- Clean up README for public audience
- Add issue/PR templates
- Create Discord server
- Prepare announcement materials

**Day 3:**
- Final review
- Make repository public
- Enable Discussions
- Post announcements

---

**Status:** Ready to execute  
**Risk Level:** Low (already open-core, MIT licensed)  
**Effort:** 4-6 hours spread over 2-3 days
