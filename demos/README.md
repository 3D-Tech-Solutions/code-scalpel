# Code Scalpel — Demo Catalog

**Everything you need to record, present, and share Code Scalpel demos.**

Version: 2.0.0 | Last Updated: 2026-02-27

---

## Directory Structure

```
demos/
├── public/                            # Shareable demo materials
│   ├── 01-installation-quickstart/    # 5-min: zero to running
│   ├── 02-community-features/         # 10-min: free tier
│   ├── 03-pro-features/               # 15-min: Pro tier
│   ├── 04-enterprise-compliance/      # 20-min: HIPAA/SOC2/GDPR/PCI-DSS
│   │   └── sample_apps/               # Realistic apps with embedded violations
│   ├── notebooks/                     # Jupyter notebooks for live/interactive demos
│   └── platforms/                     # LinkedIn, Reddit, YouTube posting guides
│
└── internal/                          # Internal docs (not for public sharing)
    ├── DEMO_PLAN.md                   # Demo strategy and success metrics
    └── PRESENTATION_GUIDE.md          # Talking points, objections, ROI calculations
```

---

## Quick Start

### Choose your demo path

| Audience | Recording Script | Notebook |
|----------|-----------------|---------|
| First-time user | [01-installation-quickstart/README.md](./public/01-installation-quickstart/README.md) | [notebooks/01_installation_quickstart.ipynb](./public/notebooks/01_installation_quickstart.ipynb) |
| Developer evaluating free tier | [02-community-features/README.md](./public/02-community-features/README.md) | [notebooks/02_community_features.ipynb](./public/notebooks/02_community_features.ipynb) |
| Engineering team / Pro buyer | [03-pro-features/README.md](./public/03-pro-features/README.md) | [notebooks/03_pro_features.ipynb](./public/notebooks/03_pro_features.ipynb) |
| CTO / Security / Compliance | [04-enterprise-compliance/COMPLIANCE_DEMO_SCRIPT.md](./public/04-enterprise-compliance/COMPLIANCE_DEMO_SCRIPT.md) | [notebooks/04_enterprise_compliance.ipynb](./public/notebooks/04_enterprise_compliance.ipynb) |

### Choose your format

| Format | Best For |
|--------|---------|
| **Recording script** (`.md`) | Pre-recorded video, LinkedIn clips, YouTube walkthroughs |
| **Jupyter notebook** (`.ipynb`) | Live webinars, workshops, hands-on sessions |

```bash
# Run notebooks interactively
pip install jupyter
jupyter notebook demos/public/notebooks/
```

---

## Demo Tiers

### Demo 1: Installation & Quick Start — 5 minutes
Zero to first tool call. Token efficiency showcase (50 tokens vs 10,000).

**Key takeaway**: "From zero to running in 5 minutes."

→ [public/01-installation-quickstart/](./public/01-installation-quickstart/)

---

### Demo 2: Community Features (Free) — 10 minutes
Security scanning, code extraction, call graphs, test generation — all free.

**Key takeaway**: "All 23 tools available without a subscription."

→ [public/02-community-features/](./public/02-community-features/)

---

### Demo 3: Pro Features — 15 minutes
Unlimited findings, sanitizer recognition, confidence scoring, NoSQL/LDAP injection detection.

**Key takeaway**: "Pro tier pays for itself by finding one critical bug."

→ [public/03-pro-features/](./public/03-pro-features/)

---

### Demo 4: Enterprise Compliance — 20 minutes
HIPAA, SOC2, GDPR, PCI-DSS scanning on four realistic sample applications.

**Key takeaway**: "Score: 0/100. Code Scalpel found every blocker in one scan."

→ [public/04-enterprise-compliance/](./public/04-enterprise-compliance/)

---

## Platform Guides

Tips for publishing demos on each platform:

- **LinkedIn** → [public/platforms/linkedin/](./public/platforms/linkedin/)
- **Reddit** → [public/platforms/reddit/](./public/platforms/reddit/)
- **Twitter/X** → [public/platforms/twitter/](./public/platforms/twitter/)
- **All platforms** → [public/platforms/ALL_PLATFORMS_QUICK_GUIDE.md](./public/platforms/ALL_PLATFORMS_QUICK_GUIDE.md)

---

## Recording Checklist

### Before recording
- [ ] Review the recording script for your chosen demo
- [ ] Run the Jupyter notebook once to verify outputs
- [ ] Verify Claude Desktop MCP connection is active
- [ ] Clean desktop, close unnecessary apps
- [ ] Set terminal/editor font to 18pt+

### Recording
- [ ] 1920×1080 minimum resolution
- [ ] Pause 2 seconds between sections (for editing)
- [ ] Leave 5 seconds silence at start/end

### After recording
- [ ] Add chapter markers
- [ ] Add text overlays for key score reveals (e.g. PCI-DSS: 0/100)
- [ ] Add intro/outro branding
- [ ] Post using platform-specific guidance in [public/platforms/](./public/platforms/)
