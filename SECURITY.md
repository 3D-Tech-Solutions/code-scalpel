# Security Policy

## Reporting a Vulnerability
- Email: time@3dtechsolutions.us (monitored business days).
- Provide: affected version, reproduction steps, impact, and any proofs of concept.
- Please avoid including secrets or customer data; minimize payloads to essentials.

## Response Targets
- Acknowledgement: within 1 business day.
- Triage: within 3 business days.
- Fix or mitigation plan: within 7 business days for High/Critical; within 15 business days for Medium; within 30 business days for Low.

## Disclosure
- We prefer coordinated disclosure. We will propose a publication date after a fix or mitigation is available and users have a clear upgrade path.
- Do not post details publicly until we confirm a remediation or provide explicit consent.

## Scope
- In scope: MCP server, surgical tools, AST/PDG/symbolic/security analysis modules, official docs and release artifacts.
- Out of scope: third-party dependencies themselves, demo/example code, and any forks not maintained by 3D Tech Solutions LLC.

## Safe Harbor
- Research conducted under this policy will not be pursued legally if performed in good faith and reported privately.
- Do not exploit in production, access other users’ data, or cause denial of service.

## Governance & Roles
- Maintainer (release authority): ensures gates are satisfied and artifacts are signed.
- Security lead: triage, CVE coordination, vuln scan/SBOM review, signing verification.
- Reviewer: enforces tests/lint/coverage/mutation/fuzz gates on PRs.

<!-- [20251218_DOCS] Release gates and SLA commitments for v3.0.0 -->

## Service Levels & Escalation
- Intake SLA: acknowledgement ≤1 business day (Primary), ≤2 business days (Secondary).
- Triage SLA: prioritization within 3 business days; owner assigned (Maintainer or Security lead).
- Resolution targets: High/Critical ≤7 business days; Medium ≤15 business days; Low ≤30 business days; exceptions require Maintainer + Security lead approval and documented workaround.
- Escalation: if targets slip, notify Maintainer, Security lead, and Reviewer; publish interim mitigation in evidence bundle and SECURITY.md changelog.

## Release Gate Checklist (v3.0.0+)
- Tests: `python -m pytest` green; mutation smoke + parser/interpreter fuzz results recorded.
- Coverage: ≥90% combined (statement + branch); coverage report stored under `release_artifacts/v3.0.0/` and badge/docs updated.
- Lint/Format: `ruff check .` and `python -m black --check .` clean; waivers must be documented.
- Supply chain: SBOM generated and stored under `release_artifacts/v3.0.0/`; dependency vuln scan (OSV/pip-audit) logged with tool version/date/hash.
- Signing: release artifacts signed with Sigstore/Cosign; verification steps captured in `release_artifacts/v3.0.0/v3.0.0_credibility_evidence.json`.
- Evidence: credibility bundle completed, including benchmarks, interop recipes, and DX smoke script references.
- Approvals: Maintainer + Security lead + Reviewer sign off; any deviation documented in the evidence bundle and release notes.

## Release Security Expectations (v3.0.0)
- Signing: Sigstore/Cosign signatures for release artifacts; verification instructions recorded in `release_artifacts/v3.0.0/v3.0.0_credibility_evidence.json`.
- SBOM: Generated for distributed packages; stored under `release_artifacts/v3.0.0/` and linked in evidence JSON.
- Vulnerability scan: Dependency scan (e.g., OSV/pip-audit) recorded in evidence JSON with date/tool/hash.
- Coverage & quality gates: ≥90% combined coverage, ruff/black clean, pytest clean, mutation smoke + parser/interpreter fuzz noted.

## Contact
- Primary: time@3dtechsolutions.us
- Secondary: aescolopio@3dtechsolutions.us

## Versioning
- Policy version: 2025-12-18
- Applies starting with release v3.0.0 and forward.
