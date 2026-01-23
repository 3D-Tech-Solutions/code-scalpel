# Code Scalpel MCP Server - Demo Plan
 
## Overview
This document outlines a comprehensive demo strategy for showcasing Code Scalpel MCP server capabilities to different audiences and use cases.
 
## Target Audiences
1. **Individual Developers** - Looking for AI-powered code analysis tools
2. **Engineering Teams** - Need collaborative code quality and security
3. **Enterprise Organizations** - Require compliance, governance, and advanced security
 
## Demo Structure
 
### 🎯 Demo Tier 1: Installation & Quick Start (5 minutes)
**Goal**: Get from zero to running MCP server in minutes
 
**What to show**:
- Installation via `pip install code-scalpel`
- MCP server configuration in Claude Desktop
- First tool call: `extract_code` to get a function
- Token efficiency showcase (50 tokens vs 10,000)
 
**Key talking points**:
- Zero-config installation
- Works with Claude Desktop, VS Code, Cursor
- Immediate value without setup complexity
 
**Demo file**: `demos/1_installation_quickstart/`
 
---
 
### 🆓 Demo Tier 2: Community Features (10 minutes)
**Goal**: Showcase what's available in the FREE tier
 
**What to show**:
1. **Code Extraction** (`extract_code`)
   - Multi-language support (Python, JS, TS, Java)
   - Context-aware extraction with dependencies
   - Token efficiency for large files
 
2. **Code Analysis** (`analyze_code`)
   - Get structure without execution
   - Complexity metrics
   - Import analysis
 
3. **Security Scanning** (`security_scan`)
   - OWASP Top 10 detection
   - SQL injection, XSS examples
   - 50 findings limit (Community tier)
 
4. **Symbol References** (`get_symbol_references`)
   - Find all usages across project
   - Refactoring safety
 
5. **Project Navigation** (`get_project_map`)
   - Architecture overview
   - Module relationships
 
**Key talking points**:
- "All tools available at every tier"
- "Community tier provides production-ready analysis"
- "Perfect for individual developers and small projects"
- "No credit card required to start"
 
**Demo file**: `demos/2_community_features/`
 
---
 
### 💎 Demo Tier 3: Pro Features (15 minutes)
**Goal**: Show why teams should upgrade to Pro ($29-49/mo)
 
**What to show**:
1. **Advanced Security** (Pro vs Community comparison)
   - **Sanitizer recognition**: Show how Pro detects proper sanitization
   - **Confidence scoring**: Risk-based prioritization
   - **NoSQL/LDAP injection**: Beyond OWASP Top 10
   - **Secret detection**: API keys, credentials in code
   - **Unlimited findings**: No 50-result cap
 
2. **Cross-File Analysis**
   - Type evaporation detection (implicit `any` across boundaries)
   - Trace vulnerabilities across modules
 
3. **Advanced Testing** (`generate_unit_tests`)
   - Data-driven test generation
   - Edge case coverage
   - Symbolic execution with Z3
 
4. **Remediation Suggestions**
   - Automated fix recommendations
   - Code snippets for secure patterns
 
**Side-by-side comparison**:
```
Community Tier:
- 50 findings max
- Basic OWASP Top 10
- No sanitizer detection
- Files up to 1MB
 
Pro Tier:
- Unlimited findings
- All vulnerability types
- Sanitizer recognition
- Confidence scoring
- Secret detection
- Files up to 10MB
```
 
**Key talking points**:
- "Pro tier unlocks unlimited findings for large codebases"
- "Sanitizer recognition reduces false positives by 70%"
- "Confidence scoring helps prioritize critical issues"
- "Perfect for engineering teams with production code"
- "ROI: Find one critical bug = months of subscription value"
 
**Demo file**: `demos/3_pro_features/`
 
---
 
### 🏢 Demo Tier 4: Enterprise Features (20 minutes)
**Goal**: Demonstrate why large organizations need Enterprise tier
 
**What to show**:
1. **Custom Policy Engine**
   - Organization-specific coding standards
   - Compliance frameworks (PCI-DSS, SOC2, HIPAA)
   - Cryptographic policy verification
   - Tamper-proof policy signatures
 
2. **Advanced Security**
   - Cross-file taint tracking (trace vulnerabilities across 10+ files)
   - Reachability analysis (is vulnerable code actually called?)
   - Priority finding ordering (business impact + technical severity)
   - Bug reproduction from crash logs
 
3. **Type Safety at Scale**
   - Type evaporation analysis with runtime validation
   - API contract validation (frontend/backend compatibility)
   - Zod schema generation from TypeScript types
   - Network boundary analysis
 
4. **Governance & Compliance**
   - Compliance report generation
   - Audit trails with MCP analytics
   - License management (JWT-based)
   - Organization-wide policy enforcement
 
5. **Enterprise Infrastructure**
   - Files up to 100MB
   - Custom rules engine
   - Integration with CI/CD pipelines
   - SSO and user management (roadmap)
 
**Real-world scenarios**:
- **Scenario 1**: Compliance audit preparation
  - Run `code_policy_check` against SOC2 standards
  - Generate compliance report for auditors
  - Fix violations with `simulate_refactor`
 
- **Scenario 2**: M&A due diligence
  - Scan acquired codebase for vulnerabilities
  - Cross-file taint tracking for critical flows
  - Reachability analysis to prioritize fixes
 
- **Scenario 3**: API breaking change detection
  - Validate frontend/backend type contracts
  - Generate Zod schemas for runtime validation
  - Prevent type evaporation across service boundaries
 
**Key talking points**:
- "Enterprise tier is for organizations with compliance requirements"
- "Custom policies enforce your org's standards automatically"
- "Cross-file taint tracking finds vulnerabilities others miss"
- "Reachability analysis reduces noise by 80%"
- "ROI: Avoid one compliance violation = years of Enterprise tier"
- "Perfect for: FinTech, HealthTech, regulated industries"
 
**Demo file**: `demos/4_enterprise_features/`
 
---
 
### 🎬 Demo Tier 5: Full Workflow Demo (30 minutes)
**Goal**: End-to-end demonstration of real-world scenarios
 
**What to show**:
1. **Onboarding a new developer**
   - Install via `pip install code-scalpel`
   - Configure MCP in Claude Desktop
   - Ask Claude: "Map out the authentication system"
   - Use `get_call_graph` and `get_project_map`
 
2. **Finding and fixing a security vulnerability**
   - Run `security_scan` on suspicious module
   - Identify SQL injection with Pro tier confidence scoring
   - Use `simulate_refactor` to test fix
   - Apply fix with `update_symbol`
   - Verify with re-scan
 
3. **Safe refactoring**
   - Use `get_symbol_references` to find all usages
   - Use `rename_symbol` to safely rename across project
   - Generate unit tests with `generate_unit_tests`
   - Simulate refactor with `simulate_refactor`
 
4. **Dependency security audit**
   - Run `scan_dependencies` to check for CVEs
   - Review vulnerability reports
   - Upgrade affected packages
 
**Demo file**: `demos/5_full_workflows/`
 
---
 
## Demo Assets Needed
 
### 1. Sample Codebases
Create realistic but small codebases for each demo:
 
- **`vulnerable_webapp/`** - Flask/Express app with intentional vulnerabilities
  - SQL injection (Community can find)
  - XSS with sanitization (Pro detects sanitizer)
  - Cross-file taint flow (Enterprise tracks)
  - Type evaporation at API boundary (Enterprise validates)
 
- **`microservices/`** - Multi-service architecture
  - Frontend (TypeScript React)
  - Backend (Python FastAPI)
  - Shared types (demonstrates contract validation)
 
- **`legacy_codebase/`** - Older code needing modernization
  - Complex dependencies
  - Policy violations
  - Compliance issues
 
### 2. Video Recording Scripts
For each demo tier, provide:
- Setup instructions
- Step-by-step narration script
- Expected outputs
- Troubleshooting tips
 
### 3. Presentation Slides
Key slides for each section:
- Problem statement
- Solution demonstration
- Tier comparison table
- Pricing and ROI
- Getting started CTA
 
### 4. Interactive Notebooks
Jupyter notebooks for hands-on demos:
- Can run live during presentations
- Include explanatory markdown
- Show code + output together
- Easy to share with prospects
 
---
 
## Measurement & Success Criteria
 
### Demo Effectiveness Metrics
- **Installation success rate**: Can viewer install in < 5 minutes?
- **Value clarity**: Does viewer understand tier differences?
- **Call to action**: Clear next steps for each tier?
 
### A/B Testing Ideas
- Order of feature presentation
- Code examples (security vs. refactoring first)
- Length (5 min quick demo vs. 30 min deep dive)
 
---
 
## Distribution Channels
 
1. **YouTube**
   - Playlist: "Code Scalpel MCP Server Demos"
   - Short-form: TikTok/Reels for installation (60 seconds)
   - Long-form: Full feature walkthroughs (15-30 min)
 
2. **Documentation**
   - Embed videos in docs.code-scalpel.dev
   - Interactive CodeSandbox examples
   - Live demo environment
 
3. **Sales & Marketing**
   - Demo recordings for sales calls
   - Case studies with metrics
   - Customer testimonials
 
4. **Developer Relations**
   - Conference talks
   - Hackathon sponsorships
   - Blog posts with demo code
 
---
 
## Timeline
 
**Week 1**: Create demo codebases and scripts
**Week 2**: Record video demos (1-4)
**Week 3**: Create presentation materials
**Week 4**: Publish and promote
 
---
 
## Next Steps
 
1. ✅ Create demo directory structure
2. ✅ Build sample vulnerable codebases
3. ✅ Write demo scripts for each tier
4. ✅ Create presentation talking points
5. ⏳ Record videos
6. ⏳ Publish to YouTube
7. ⏳ Integrate into documentation