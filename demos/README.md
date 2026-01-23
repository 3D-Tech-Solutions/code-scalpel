# Code Scalpel MCP Server - Demo Catalog
 
**Comprehensive demos for presenting, recording, and showcasing Code Scalpel capabilities**
 
Version: 1.0.0 | Last Updated: 2026-01-19
 
---
 
## 📚 What's Included
 
This directory contains everything you need to demonstrate Code Scalpel to any audience:
 
- ✅ **4 Tier-Based Demos** - Installation, Community, Pro, Enterprise
- ✅ **Sample Code** - Vulnerable apps, polyglot examples, cross-file scenarios
- ✅ **Presentation Guide** - Talking points, ROI calculations, objection handling
- ✅ **Planning Document** - Demo strategy and success metrics
- ✅ **Ready to Record** - Scripts optimized for video production
 
---
 
## 🎯 Quick Start
 
### Choose Your Demo Path
 
**For Individual Developers**:
→ [Demo 1: Installation & Quick Start](./1_installation_quickstart/)
→ [Demo 2: Community Features](./2_community_features/)
 
**For Engineering Teams**:
→ [Demo 1: Installation & Quick Start](./1_installation_quickstart/)
→ [Demo 2: Community Features](./2_community_features/)
→ [Demo 3: Pro Features](./3_pro_features/)
 
**For Enterprise Organizations**:
→ [Demo 1: Installation & Quick Start](./1_installation_quickstart/)
→ [Demo 2: Community Features](./2_community_features/)
→ [Demo 3: Pro Features](./3_pro_features/)
→ [Demo 4: Enterprise Features](./4_enterprise_features/)
 
---
 
## 📂 Directory Structure
 
```
demos/
├── README.md                          # This file - demo catalog
├── DEMO_PLAN.md                       # Overall demo strategy
├── PRESENTATION_GUIDE.md              # Master presentation script
│
├── 1_installation_quickstart/         # 5-minute demo
│   ├── README.md                      # Demo script
│   ├── demo_app.py                    # Sample code
│   ├── sample_config.json             # MCP configuration
│   ├── installation_checklist.md      # Setup checklist
│   └── troubleshooting.md             # Common issues
│
├── 2_community_features/              # 10-15 minute demo
│   ├── README.md                      # Demo script
│   ├── demo_app.py                    # Clean sample code
│   └── vulnerable_app.py              # Intentionally vulnerable code
│
├── 3_pro_features/                    # 15-20 minute demo
│   ├── README.md                      # Demo script
│   └── modern_attacks.py              # NoSQL, LDAP, secrets, etc.
│
└── 4_enterprise_features/             # 20-30 minute demo
    └── README.md                      # Demo script
```
 
---
 
## 🎬 Demo Breakdown
 
### Demo 1: Installation & Quick Start
 
**Duration**: 5 minutes
**Target Audience**: First-time users, conference talks
**Difficulty**: Beginner
 
**What You'll Show**:
1. Install Code Scalpel (`pip install code-scalpel`)
2. Configure MCP server in Claude Desktop
3. Make first tool call (extract a function)
4. See token efficiency in action (200x reduction)
 
**Key Takeaway**: "From zero to running in 5 minutes"
 
**Files**: [1_installation_quickstart/](./1_installation_quickstart/)
 
---
 
### Demo 2: Community Features (Free Tier)
 
**Duration**: 10-15 minutes
**Target Audience**: Developers evaluating free vs paid tiers
**Difficulty**: Intermediate
 
**What You'll Show**:
1. **Code Extraction** - Pull just what you need from large files
2. **Security Scanning** - Find OWASP Top 10 vulnerabilities
3. **Project Navigation** - Call graphs, dependency analysis
4. **Code Modification** - Safe refactoring with backups
5. **Test Generation** - Auto-generate unit tests
 
**Key Takeaway**: "All 19 tools available for free - production-ready"
 
**Files**: [2_community_features/](./2_community_features/)
 
---
 
### Demo 3: Pro Features
 
**Duration**: 15-20 minutes
**Target Audience**: Engineering teams, decision makers
**Difficulty**: Intermediate
 
**What You'll Show**:
1. **Unlimited Findings** - No 50-result cap
2. **Sanitizer Recognition** - 70% fewer false positives
3. **Confidence Scoring** - Prioritize real issues
4. **Advanced Security** - NoSQL injection, secrets, LDAP
5. **Remediation Suggestions** - Fix snippets included
6. **Data-Driven Tests** - 95% code coverage automatically
 
**Key Takeaway**: "Pro tier pays for itself by finding one critical bug"
 
**ROI Calculation**:
- Cost: $49/month
- Value: $2,500/month in time savings
- Break-even: Week 1
 
**Files**: [3_pro_features/](./3_pro_features/)
 
---
 
### Demo 4: Enterprise Features
 
**Duration**: 20-30 minutes
**Target Audience**: CTOs, Security teams, Compliance officers
**Difficulty**: Advanced
 
**What You'll Show**:
1. **Cross-File Taint Tracking** - Trace vulnerabilities across 10+ files
2. **Custom Policy Engine** - Enforce org-specific standards
3. **Compliance Reporting** - Auto-generate SOC2/PCI-DSS reports
4. **Reachability Analysis** - Find exploitable vulnerabilities
5. **Type Evaporation Detection** - Frontend/backend type safety
6. **Bug Reproduction** - Generate tests from crash logs
 
**Key Takeaway**: "Enterprise tier for compliance and governance at scale"
 
**ROI Calculation**:
- Cost: $300,000/year (50 seats)
- Value: $5.1M/year (audit savings + productivity + breach prevention)
- Break-even: Month 1
 
**Files**: [4_enterprise_features/](./4_enterprise_features/)
 
---
 
## 🎤 Presentation Guide
 
For comprehensive talking points, ROI calculations, and audience-specific scripts, see:
 
**[PRESENTATION_GUIDE.md](./PRESENTATION_GUIDE.md)**
 
Includes:
- Universal opening script
- Tier-specific talking points
- Objection handling
- FAQ responses
- Call-to-action templates
- Visual aids and slide templates
 
---
 
## 📊 Demo Format Templates
 
### 5-Minute Conference Talk
 
**Agenda**:
1. Problem statement (1 min)
2. Live installation (1.5 min)
3. First tool call (1.5 min)
4. CTA - "Try it free" (1 min)
 
**Use**: [Demo 1](./1_installation_quickstart/)
 
---
 
### 15-Minute Webinar
 
**Agenda**:
1. Problem + solution (3 min)
2. Installation demo (2 min)
3. Community features highlight reel (7 min)
4. Q&A + CTA (3 min)
 
**Use**: [Demo 1](./1_installation_quickstart/) + [Demo 2](./2_community_features/)
 
---
 
### 30-Minute Sales Demo
 
**Agenda**:
1. Problem statement (3 min)
2. Installation (2 min)
3. Community tier showcase (5 min)
4. **Pause for questions** (2 min)
5. Pro tier comparison (10 min)
6. ROI calculation (4 min)
7. Q&A + trial signup (4 min)
 
**Use**: [Demos 1-3](./1_installation_quickstart/)
 
---
 
### 60-Minute Enterprise Pitch
 
**Agenda**:
1. Executive problem statement (3 min)
2. Quick demo of core value (5 min)
3. Community tier (5 min)
4. Pro tier + ROI (10 min)
5. **Pause for questions** (5 min)
6. Enterprise deep dive (20 min)
7. Total ROI calculation (7 min)
8. Q&A + next steps (5 min)
 
**Use**: [All Demos 1-4](./1_installation_quickstart/)
 
---
 
## 🎥 Video Recording Checklist
 
Planning to record these demos? Use this checklist:
 
### Pre-Recording
 
- [ ] Review demo script thoroughly
- [ ] Test all sample code and tools
- [ ] Verify Claude Desktop MCP connection
- [ ] Clean desktop, close unnecessary apps
- [ ] Set terminal font size to 18pt+
- [ ] Test microphone audio levels
- [ ] Prepare fallback slides/screenshots
 
### Recording
 
- [ ] Use 1920×1080 resolution minimum
- [ ] Record at 30 FPS
- [ ] Enable cursor highlighting
- [ ] Speak clearly and not too fast
- [ ] Pause 2 seconds between sections (for editing)
- [ ] Leave 5 seconds of silence at start/end
 
### Post-Recording
 
- [ ] Add chapter markers
- [ ] Include text overlays for key points
- [ ] Speed up slow parts (installations, waits)
- [ ] Add intro/outro with branding
- [ ] Create YouTube thumbnail
- [ ] Add call-to-action end card
- [ ] Generate closed captions
- [ ] Upload with descriptive title + tags
 
### Distribution
 
- [ ] Publish to YouTube
- [ ] Embed in documentation
- [ ] Share on social media (Twitter, LinkedIn)
- [ ] Add to website landing page
- [ ] Send to sales team
- [ ] Update email sequences
 
---
 
## 🎯 Success Metrics
 
Track demo effectiveness with these KPIs:
 
### For Public Demos (YouTube, etc.)
 
**Engagement**:
- View count
- Watch time / retention rate (goal: >70%)
- Likes and comments
- Click-through rate to installation docs (goal: >15%)
 
**Conversion**:
- Installation starts (tracked via download stats)
- GitHub stars/forks
- Discord joins
- Newsletter signups
 
### For Sales Demos
 
**Engagement**:
- Questions asked during demo
- Request for custom demo with their codebase
- Asking about pricing
- Asking about Enterprise features
 
**Conversion**:
- Trial license requested (goal: >50% of demos)
- Follow-up meeting scheduled (goal: >60% of demos)
- Contract signed within 30 days (goal: >25% of trials)
 
---
 
## 🛠️ Customization Guide
 
### Adapting Demos for Your Organization
 
**1. Replace Sample Code**:
- Use your actual codebase (with permission)
- Redact sensitive information
- Show real vulnerabilities you found
 
**2. Customize Talking Points**:
- Add your company's specific use cases
- Include testimonials from your team
- Highlight features you use most
 
**3. Adjust Timing**:
- Skip sections not relevant to your audience
- Deep dive on features that matter to them
- Add custom Q&A based on common questions
 
**4. Create Industry-Specific Versions**:
- **FinTech**: Focus on compliance, custom policies, audit reports
- **HealthTech**: Emphasize HIPAA compliance, data privacy
- **E-commerce**: Highlight security scanning, payment processing safety
- **SaaS**: Show multi-tenancy security, API contract validation
 
---
 
## 📚 Additional Resources
 
### Documentation
- [Full Documentation](https://github.com/3D-Tech-Solutions/code-scalpel)
- [API Reference](https://github.com/3D-Tech-Solutions/code-scalpel/docs/api)
- [MCP Server Guide](https://github.com/3D-Tech-Solutions/code-scalpel/docs/mcp)
 
### Community
- [GitHub Discussions](https://github.com/3D-Tech-Solutions/code-scalpel/discussions)
- [Discord Server](https://discord.gg/code-scalpel) *(placeholder)*
- [Issue Tracker](https://github.com/3D-Tech-Solutions/code-scalpel/issues)
 
### Marketing Materials
- [Website](https://code-scalpel.dev) *(placeholder)*
- [Blog](https://code-scalpel.dev/blog) *(placeholder)*
- [Case Studies](https://code-scalpel.dev/case-studies) *(placeholder)*
 
---
 
## 🤝 Contributing
 
Found an issue with a demo? Have a suggestion for improvement?
 
1. **Report Issues**: [GitHub Issues](https://github.com/3D-Tech-Solutions/code-scalpel/issues)
2. **Suggest Improvements**: [GitHub Discussions](https://github.com/3D-Tech-Solutions/code-scalpel/discussions)
3. **Submit PRs**: Improvements to demo scripts are welcome!
 
---
 
## 📝 Version History
 
### v1.0.0 (2026-01-19)
- Initial demo package release
- 4 tier-based demos (Installation, Community, Pro, Enterprise)
- Comprehensive presentation guide
- Sample vulnerable code for security demos
- ROI calculators and comparison matrices
 
---
 
## 📄 License
 
These demo materials are part of the Code Scalpel project and are released under the MIT License.
 
Copyright (c) 2026 3D-Tech-Solutions
 
---
 
## 🎉 Get Started
 
**Choose your path**:
 
🚀 **First Time User?**
→ Start with [Demo 1: Installation & Quick Start](./1_installation_quickstart/)
 
👥 **Evaluating for Your Team?**
→ Watch [Demo 2: Community Features](./2_community_features/) and [Demo 3: Pro Features](./3_pro_features/)
 
🏢 **Enterprise Decision Maker?**
→ Review all 4 demos, then schedule a custom demo at enterprise@code-scalpel.dev
 
📹 **Want to Record Your Own?**
→ Read [PRESENTATION_GUIDE.md](./PRESENTATION_GUIDE.md) for scripts and tips
 
---
 
**Questions?** Open an issue or join our Discord.
 
**Ready to present?** You have everything you need. Go make Code Scalpel look amazing!
 
---
 
*Happy Demoing!* 🎬