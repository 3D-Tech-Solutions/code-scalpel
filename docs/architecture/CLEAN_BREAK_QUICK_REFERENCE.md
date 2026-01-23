## Quick Reference & Important Links

### Command Reference
```bash
# Community tier (no license needed)
pip install code-scalpel
code-scalpel init  # Creates ~/.code-scalpel/ structure
uvx code-scalpel   # Start MCP server

# Pro/Enterprise setup
cp license.jwt ~/.code-scalpel/license/
# Restart MCP server - enhancements auto-download

# Diagnostics
code-scalpel --diagnose
# Shows: Core version, License status, Downloaded enhancements

# Testing (from within repo)
cd code-scalpel && pytest tests/ -v --cov
cd code-scalpel-pro && pytest tests/ -v
cd code-scalpel-enterprise && pytest tests/ -v

# Building
cd code-scalpel && python -m build                    # Community wheel
cd code-scalpel-pro && python build.py                # Pro enhancement
cd code-scalpel-enterprise && python build.py         # Enterprise enhancement
```

### File Checklist Reference

#### Core Package Files (code-scalpel/)
```
✓ = Already exists in monolith
○ = Needs to be created or heavily modified
△ = Needs to be modified

src/code_scalpel/mcp/
  ○ enhancement_loader.py        [NEW - Dynamic enhancement loading]
  △ server.py                    [MODIFY - Strip Pro/Ent, add enhancement loading]
  ✓ contract.py
  ✓ response_config.py

src/code_scalpel/licensing/
  ○ enhancement_manager.py       [NEW - Download/verify enhancements]
  ○ tiers.py                     [NEW - Tier capability definitions]
  △ features.py                  [MODIFY - Community only, remove Pro/Ent]
  ✓ jwt_validator.py
  ✓ config_loader.py

src/code_scalpel/
  ○ cli.py                       [NEW - init & --diagnose commands]
  ✓ [all other modules unchanged]

pyproject.toml
  △ [Version 4.0.0, add requests dependency]

tests/
  ○ test_community_features.py        [NEW]
  ○ test_enhancement_loader.py        [NEW]
  ○ test_tools_community_limits.py    [NEW]
  ○ test_pro_integration.py           [NEW]
  ○ test_enterprise_integration.py    [NEW]
  ✓ [existing tests, ensure still pass]

docs/
  ○ INSTALLATION.md              [NEW/UPDATED]
  ○ UPGRADE.md                   [NEW]
  ○ LICENSING.md                 [NEW]
  ○ TROUBLESHOOTING.md           [NEW]
  ○ CODE_INVENTORY.md            [NEW - Track Pro/Ent code locations]
  △ README.md                    [UPDATED - Explain tiers]
  △ CHANGELOG.md                 [UPDATED - Document v4.0.0 changes]
```

#### Pro Package Files (code-scalpel-pro/)
```
code_scalpel_pro/
  ○ __init__.py                  [NEW]
  ○ capabilities.py              [NEW - Pro capabilities for all 22 tools]
  ○ tools/
    ○ __init__.py                [NEW]
    ○ [20+ enhancement modules]  [NEW - Extracted from monolith]
  ○ metadata.json                [NEW - Version, compatibility]
  ○ pyproject.toml               [NEW]
  ○ build.py                     [NEW - Build wheel, generate checksum]

tests/
  ○ test_pro_enhancements.py     [NEW]
  ○ test_pro_integration.py      [NEW]

docs/
  ○ INTERNAL_README.md           [NEW]
  ○ PRO_FEATURES.md              [NEW]
  ○ PRO_ENHANCEMENTS_MAP.md      [NEW - Track which tools get enhanced]

.github/workflows/
  ○ build-pro-enhancement.yml    [NEW - CI/CD for Pro package]
```

#### Enterprise Package Files (code-scalpel-enterprise/)
```
code_scalpel_enterprise/
  ○ __init__.py                  [NEW]
  ○ capabilities.py              [NEW - Enterprise capabilities]
  ○ tools/
    ○ __init__.py                [NEW]
    ○ [20+ enhancement modules]  [NEW]
  ○ governance/
    ○ __init__.py                [NEW]
    ○ opa_engine.py              [NEW]
    ○ policy_loader.py           [NEW]
    ○ audit_logger.py            [NEW]
  ○ policy_engine/
    ○ __init__.py                [NEW]
    ○ compliance_rules.py         [NEW]
    ○ pdf_reporter.py            [NEW]
  ○ autonomy/
    ○ __init__.py                [NEW]
    ○ agent_controller.py         [NEW]
    ○ budgeting.py               [NEW]
  ○ metadata.json                [NEW - With Pro dependency]
  ○ pyproject.toml               [NEW]
  ○ build.py                     [NEW]

tests/
  ○ test_enterprise_enhancements.py [NEW]
  ○ test_governance.py              [NEW]
  ○ test_compliance.py              [NEW]

docs/
  ○ INTERNAL_README.md           [NEW]
  ○ ENTERPRISE_FEATURES.md       [NEW]
  ○ ENTERPRISE_ENHANCEMENTS_MAP.md [NEW]

.github/workflows/
  ○ build-enterprise-enhancement.yml [NEW - CI/CD]
```

### Dependency Tracking

#### Community Package Dependencies (stable)
```
mcp>=1.23.0
pydantic>=2.11.0
PyJWT[crypto]>=2.10.1
tree-sitter>=0.21.0
requests>=2.31.0          [NEW - for enhancement downloads]
[all existing dependencies]
```

#### Pro Package Dependencies
```
None (no runtime dependencies)
Built as standalone enhancement wheel
Downloaded to ~/.code-scalpel/enhancements/pro/
```

#### Enterprise Package Dependencies
```
code-scalpel-pro==4.0.0   [Declared in metadata.json]
(downloaded as part of enhancement bundle)
```

### Metadata File Templates

#### code-scalpel-pro/metadata.json
```json
{
  "name": "code-scalpel-pro",
  "version": "4.0.0",
  "compatible_core_versions": [">=4.0.0,<5.0.0"],
  "requires_tier": "pro",
  "requires_license_key": true,
  "download_url": "https://enhancements.code-scalpel.com/pro/4.0.0/",
  "checksum_algorithm": "sha256",
  "checksum": "[generated during build]",
  "dependencies": []
}
```

#### code-scalpel-enterprise/metadata.json
```json
{
  "name": "code-scalpel-enterprise",
  "version": "4.0.0",
  "compatible_core_versions": [">=4.0.0,<5.0.0"],
  "requires_tier": "enterprise",
  "requires_license_key": true,
  "dependencies": ["code-scalpel-pro==4.0.0"],
  "download_url": "https://enhancements.code-scalpel.com/enterprise/4.0.0/",
  "checksum_algorithm": "sha256",
  "checksum": "[generated during build]"
}
```

### Repository Setup Checklist
- [ ] **code-scalpel** (public)
  - [ ] Created on GitHub
  - [ ] Set to public
  - [ ] Branch protection: main requires PR review
  - [ ] CI/CD workflows configured
  - [ ] PyPI publishing secrets added

- [ ] **code-scalpel-pro** (private)
  - [ ] Created on GitHub
  - [ ] Set to private
  - [ ] Team access configured
  - [ ] Branch protection: main requires PR review
  - [ ] Enhancement server upload credentials in Secrets

- [ ] **code-scalpel-enterprise** (private)
  - [ ] Created on GitHub
  - [ ] Set to private
  - [ ] Team access configured
  - [ ] Branch protection: main requires PR review
  - [ ] Enhancement server upload credentials in Secrets

### Enhancement Server Setup Checklist
- [ ] **Choose endpoint:**
  - [ ] GitHub Packages (private repo)
  - [ ] Artifactory
  - [ ] Custom S3 bucket
  - [ ] Other: __________

- [ ] **Configure authentication:**
  - [ ] API keys/tokens generated
  - [ ] Stored in GitHub Secrets
  - [ ] Documented in internal wiki

- [ ] **Create version API:**
  - [ ] GET /api/versions/{tier}/{version}/
  - [ ] GET /health/
  - [ ] Returns metadata + download URL + checksum

### Version Numbering Strategy
```
v4.0.0 - Initial split release
  code-scalpel: 4.0.0 (Community)
  code-scalpel-pro: 4.0.0 (Pro enhancements)
  code-scalpel-enterprise: 4.0.0 (Enterprise enhancements)

v4.0.1 - Bug fix in Community
  code-scalpel: 4.0.1
  code-scalpel-pro: 4.0.0 (unchanged, if compatible)
  code-scalpel-enterprise: 4.0.0 (unchanged, if compatible)

v4.1.0 - New Pro feature (backward compatible with Core 4.0.x)
  code-scalpel: 4.0.1 (no change needed)
  code-scalpel-pro: 4.1.0
  code-scalpel-enterprise: 4.0.0 (unchanged)

v5.0.0 - Breaking changes (all must update together)
  code-scalpel: 5.0.0
  code-scalpel-pro: 5.0.0
  code-scalpel-enterprise: 5.0.0
```

### Support & Escalation
- [ ] **Setup GitHub Discussions** (for community)
- [ ] **Setup email support** (support@code-scalpel.com)
- [ ] **Create status page** (for enhancement server health)
- [ ] **Slack channel** (for Pro/Enterprise customers, if applicable)
- [ ] **Document escalation path** (Community → Pro tier issues)

---

## Document History
- **v1.0** - Initial comprehensive checklist (January 8, 2026)
  - Phases 1-6 fully detailed
  - Risk management strategies
  - Success metrics & KPIs
  - Quick reference section

## Related Documents
- [clean_break.md](clean_break.md) - Full architecture plan with detailed explanations
- [CODE_INVENTORY.md](../../CODE_INVENTORY.md) - Track Pro/Enterprise code locations (to be created)
- [MIGRATION_v3_to_v4.md](../../MIGRATION_v3_to_v4.md) - User migration guide (to be created)
