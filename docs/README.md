# Code Scalpel Documentation

Welcome to the Code Scalpel documentation! This directory contains comprehensive guides, references, and examples for using Code Scalpel.

---

## Quick Navigation

| What You Need | Where to Go |
|---------------|-------------|
| First time user? | [Getting Started](getting_started/getting_started.md) |
| Looking for something specific? | [Documentation Index](INDEX.md) |
| Want to contribute? | [CONTRIBUTING.md](../CONTRIBUTING.md) |
| Integration examples? | [Examples](getting_started/examples.md) |
| API reference? | [Module Documentation](#module-documentation) |

---

## Getting Started

- **[Getting Started Guide](getting_started/getting_started.md)** - Complete setup and first steps
- **[Comprehensive Guide](COMPREHENSIVE_GUIDE.md)** - Full documentation with examples
- **[Quick Reference](QUICK_REFERENCE_DOCS.md)** - Fast lookup for common tasks
- **[Examples](getting_started/examples.md)** - Code examples and use cases
- **[Graph Engine Guide](guides/graph_engine_guide.md)** - Unified graph analysis

---

## Module Documentation

### Core Analysis Tools

- **[AST Tools](modules/AST_TOOLS.md)** - Code parsing, analysis, and transformation
- **[PDG Tools](modules/PDG_TOOLS.md)** - Program dependence graphs and data flow analysis
- **[Symbolic Execution](modules/SYMBOLIC_EXECUTION.md)** - Path exploration and constraint solving
- **[MCP Server](modules/MCP_SERVER.md)** - Model Context Protocol server for AI assistants

### Governance & Policy System

- **[Policy Engine](../src/code_scalpel/policy_engine/README.md)** - OPA/Rego declarative policies
- **[Change Budgets](../src/code_scalpel/policy/README.md)** - Quantitative blast radius control
- **[Unified Governance](../src/code_scalpel/governance/README.md)** - Orchestration layer
- **[Configuration Guide](../.code-scalpel/README.md)** - Complete configuration reference

### Multi-Language Support

- **[Polyglot Parsers Index](parsers/DOCUMENTATION_INDEX.md)** - Multi-language parser documentation
- **[Python Parser](parsers/python_parser.md)** - Python-specific features
- **[C++ Parsers](parsers/CPP_PARSERS_README.md)** - C++ support
- **[C# Parsers](parsers/CSHARP_PARSERS_README.md)** - C# support
- **[Go Parsers](parsers/GO_PARSERS_README.md)** - Go support
- **[Swift Parsers](parsers/SWIFT_PARSERS_README.md)** - Swift support

### Integrations

- **[Integrations](modules/INTEGRATIONS.md)** - Autogen, CrewAI, LangChain
- **[AI Agent Integration](guides/agent_integration.md)** - Integration patterns for AI frameworks
- **[CI/CD Integration](guides/ci_integration_guide.md)** - Continuous integration setup
- **[Autonomy Quick Start](guides/autonomy_quickstart.md)** - v3.0 autonomy features

---

## Current Release (v3.1.x)

### Release Notes

- **[v3.1.0](release_notes/RELEASE_NOTES_v3.1.0.md)** - Enhanced extraction & unified language detection (Current)
- **[v3.0.4](release_notes/RELEASE_NOTES_v3.0.4.md)** - Stage 3 API Contract & Cross-Service features
- **[v3.0.2](release_notes/RELEASE_NOTES_v3.0.2.md)** - Stage 2 Foundation Refinement
- **[v3.0.0](release_notes/RELEASE_NOTES_v3.0.0.md)** - Autonomy release (Comprehensive coverage, stability)
- **[v2.5.0](release_notes/RELEASE_NOTES_v2.5.0.md)** - Guardian release (Policy engine, governance)
- **[All Release Notes](release_notes/)** - Complete version history

### Migration & Upgrade

- **[Migration Guide v2.5→v3.0+](guides/migration/MIGRATION_GUIDE.md)** - Upgrade from v2.5.0
- **[API Changes v3.0.0](release_notes/API_CHANGES_v3.0.0.md)** - Complete API reference for v3.0.0
- **[Known Issues v3.0.0](release_notes/KNOWN_ISSUES_v3.0.0.md)** - Current limitations and workarounds

---

## Architecture & Design

### Core Architecture

- **[System Design](architecture/SYSTEM_DESIGN.md)** - High-level architecture overview
- **[Component Diagrams](architecture/COMPONENT_DIAGRAMS.md)** - Visual component relationships
- **[Sequence Diagrams](architecture/SEQUENCE_DIAGRAMS.md)** - Interaction flows
- **[MCP Integration Patterns](architecture/MCP_INTEGRATION_PATTERNS.md)** - MCP-specific patterns

### Specialized Topics

- **[LLM Context Optimization](architecture/LLM_CONTEXT_OPTIMIZATION.md)** - Token efficiency strategies
- **[Scalability Analysis](architecture/SCALABILITY_ANALYSIS.md)** - Performance at scale

### Feature Documentation

- **[Features Index](features/)** - Feature implementation details
- **[Cache Consolidation](features/CACHE_CONSOLIDATION_v3.0.5.md)** - Caching improvements
- **[Security Sink Detector](features/unified_sink_detector.md)** - Vulnerability detection
- **[Compliance Reporting](features/compliance_reporting.md)** - Compliance system

### Architecture Decision Records (ADRs)

- **[ADR-001: IR Layer Design](adr/ADR-001-ir-layer-design.md)**
- **[ADR-002: Z3 Solver Choice](adr/ADR-002-z3-solver-choice.md)**
- **[ADR-003: MCP Native Design](adr/ADR-003-mcp-native-design.md)**
- **[ADR-004: Loop Bounding Strategy](adr/ADR-004-loop-bounding-strategy.md)**
- **[ADR-005: Multi-Language Approach](adr/ADR-005-multi-language-approach.md)**
- **[ADR-006: Security Taint Model](adr/ADR-006-security-taint-model.md)**
- **[ADR-070: Caching Strategy](adr/ADR-070-caching-strategy.md)**

---

## Deployment & Operations

### Docker & Production

- **[Docker Quick Start](../DOCKER_QUICK_START.md)** - Fast Docker deployment
- **[Docker Deployment](deployment/DOCKER_DEPLOYMENT_COMPLETE_SUMMARY.md)** - Complete deployment guide
- **[Docker Troubleshooting](deployment/DOCKER_CONNECTION_TROUBLESHOOTING.md)** - Connection issues
- **[LAN Connection Troubleshooting](deployment/LAN_CONNECTION_TROUBLESHOOTING.md)** - Network issues

### Configuration

- **[Testing Configurations](configuration/TESTING_CONFIGURATIONS.md)** - Test environment setup
- **[Configuration Guide](Configuration_Guide.md)** - Complete configuration reference

### Testing & Quality

- **[Testing Documentation](testing/)** - Test coverage and QA
- **[Release Gate Checklist](guides/release_gate_checklist.md)** - Quality gates
- **[CI/CD Troubleshooting](ci_cd/troubleshooting.md)** - Common CI issues
- **[Enhancement Roadmap](guides/enhancement_roadmap.md)** - Future features

---

## Security & Compliance

### Security Documentation

- **[Security Policy](../SECURITY.md)** - Vulnerability reporting and security policies
- **[Unified Sink Detector](features/unified_sink_detector.md)** - Security vulnerability detection
- **[Unified Sink Implementation](features/UNIFIED_SINK_IMPLEMENTATION.md)** - Implementation details

### Compliance Frameworks

- **[OWASP Top 10 Mapping](compliance/OWASP_TOP_10_MAPPING.md)** - OWASP coverage
- **[CWE Coverage Matrix](compliance/CWE_COVERAGE_MATRIX.md)** - CWE vulnerability types
- **[NIST CSF Alignment](compliance/NIST_CSF_ALIGNMENT.md)** - NIST Cybersecurity Framework
- **[PCI DSS Relevance](compliance/PCI_DSS_RELEVANCE.md)** - Payment Card Industry standards
- **[SOC2 Controls Mapping](compliance/SOC2_CONTROLS_MAPPING.md)** - SOC2 compliance
- **[Data Boundary](compliance/data_boundary.md)** - Data handling policies

---

## Performance & Optimization

- **[Caching and Optimization](performance/caching_and_optimization.md)** - Performance tuning
- **[Cache Consolidation v3.0.5](features/CACHE_CONSOLIDATION_v3.0.5.md)** - Caching improvements

---

## Internal Documentation

### For Contributors & Maintainers

- **[Product Backlog](internal/PRODUCT_BACKLOG.md)** - Feature backlog and planning
- **[Release Protocol](internal/RELEASE_PROTOCOL.md)** - Release management process
- **[Coverage Analysis](internal/COVERAGE_ANALYSIS.md)** - Test coverage details
- **[Executive Summary](internal/EXECUTIVE_SUMMARY.md)** - Project overview for stakeholders
- **[Checklist](internal/CHECKLIST.md)** - Development checklists

### Historical Records

- **[Development Summaries](summaries/)** - Historical development records
- **[Archived Documentation](archive/)** - Deprecated or superseded docs

---

## Project Management

- **[Project Charter](project-management/PROJECT_CHARTER.md)** - Project goals and scope
- **[Release Management](project-management/RELEASE_MANAGEMENT.md)** - Release process
- **[Metrics Dashboard](project-management/METRICS_DASHBOARD.md)** - Project metrics
- **[Risk Register](project-management/RISK_REGISTER.md)** - Risk tracking
- **[Stakeholder Analysis](project-management/STAKEHOLDER_ANALYSIS.md)** - Stakeholder management
- **[Lessons Learned](project-management/LESSONS_LEARNED.md)** - Post-mortem insights

---

## Research & Advanced Topics

- **[Code Scalpel v2 Recommendations](research/CODE_SCALPEL_V2_RECOMMENDATIONS.md)** - v2.0 design research
- **[MCP Server Toolset Requirements](research/MCP%20Server%20Toolset%20Requirements%20Research.md)** - MCP requirements analysis

---

## Additional Resources

### External Links

- **[GitHub Repository](https://github.com/3D-Tech-Solutions/code-scalpel)** - Source code and issues
- **[PyPI Package](https://pypi.org/project/code-scalpel/)** - Package downloads
- **[MCP Protocol Documentation](https://modelcontextprotocol.io/)** - Model Context Protocol
- **[Open Policy Agent](https://www.openpolicyagent.org/)** - OPA/Rego policy engine

### Community & Support

- **GitHub Issues** - Bug reports and feature requests
- **GitHub Discussions** - Questions and community discussion
- **Pull Requests** - Contribute code improvements

---

## Documentation Organization

This documentation follows a structured organization:

1. **Root README** - Project overview and quick start
2. **CONTRIBUTING.md** - Development guide for contributors
3. **docs/** - All detailed documentation (this directory)
4. **src/code_scalpel/*/README.md** - Module-specific documentation
5. **.code-scalpel/README.md** - Configuration guide

For more details on documentation structure, see [DOCUMENT_ORGANIZATION.md](DOCUMENT_ORGANIZATION.md).

---

**Last Updated:** December 21, 2025  
**Current Version:** v3.0.4 "Ninja Warrior"
