# Standalone by Default, Enterprise-Compatible by Design

> [20260306_DOCS] Positioning reference for README, internal messaging, enterprise conversations, and future website updates.

## Core Statement

**Code Scalpel is standalone by default, enterprise-compatible by design.**

That means:

- Code Scalpel provides meaningful value without requiring licensed third-party scanners.
- Code Scalpel can plug into existing enterprise security and compliance ecosystems when those tools already exist.
- Code Scalpel does not force teams into a rip-and-replace decision.

## Why This Positioning Matters

This positioning is stronger than either extreme.

- **Not standalone enough:** If Code Scalpel depends on third-party scanners for core value, then it is harder to adopt, harder to evaluate, and weaker for individual developers and smaller teams.
- **Too purist about independence:** If Code Scalpel refuses to integrate with tools like Coverity or SonarQube, then enterprise adoption becomes harder because large organizations already have approved scanners, audit requirements, and existing workflows.

The better position is:

- Native analysis first.
- External integration where it adds enterprise value.

## Product Boundary

The standalone boundary for Code Scalpel should be:

### 1. Native first-party analysis

These should remain core product capabilities:

- Syntax parsing
- Structural analysis
- IR normalization
- Call graph and dependency analysis
- Taint analysis
- Symbolic execution
- Baseline security findings

### 2. Native support for open local tools

Where execution is realistic and license-free, Code Scalpel can directly run local tools and parse the results.

Examples:

- Ruff
- Flake8
- ESLint
- golangci-lint
- SwiftLint

### 3. Adapter support for enterprise scanners and platforms

For licensed, server-based, or workflow-heavy tools, Code Scalpel should parse exported reports or API payloads and normalize them into one internal model.

Examples:

- Coverity
- SonarQube
- ReSharper InspectCode
- Exakat
- rust-analyzer LSP diagnostics

### 4. Optional execution connectors, never core runtime dependencies

Enterprise tools may be supported through optional connectors, but the core product should not depend on them for basic value.

## Approved Positioning Language

Use this language in internal and external messaging.

### Short version

**Code Scalpel is standalone by default, enterprise-compatible by design.**

### Medium version

Code Scalpel provides first-party parsing and analysis as its core product value. It also supports enterprise environments by ingesting findings from existing scanners and platforms, normalizing them into a consistent internal analysis layer rather than requiring a rip-and-replace.

### Longer version

Code Scalpel delivers first-party parsing, IR normalization, structural analysis, taint analysis, symbolic execution, and baseline security findings out of the box. When organizations already rely on enterprise scanners and compliance tooling, Code Scalpel can ingest their exported JSON, XML, SARIF, or API results and normalize them into a unified analysis model. This makes Code Scalpel immediately useful on its own while also making it easy to plug into mature enterprise security workflows.

## What Marketing Should Say

### Good claims

- Works standalone from day one.
- Does not require licensed third-party scanners for core value.
- Integrates cleanly with existing enterprise security and compliance stacks.
- Unifies native and third-party findings in one analysis layer.
- Reduces adoption friction because teams can start small and expand into enterprise workflows later.

### Claims to avoid

- "Replaces every enterprise scanner."
- "Eliminates the need for Coverity, SonarQube, or existing AppSec platforms."
- "Code Scalpel runs every enterprise tool directly."
- "You must use enterprise scanners to get value from Code Scalpel."

Those claims weaken credibility.

## FAQ for Internal Teams

### Does third-party tool support weaken the standalone story?

No. It strengthens the enterprise story as long as the core product remains independently valuable.

### Should Code Scalpel try to replace tools like Coverity?

Not as a positioning statement. Code Scalpel should compete through native analysis quality and workflow integration, not by making weak claims about replacing entrenched enterprise platforms in every scenario.

### Why keep enterprise adapters if we want a strong standalone product?

Because enterprises rarely remove existing scanners immediately. Adapter support lets Code Scalpel land inside existing security and compliance programs instead of forcing an all-or-nothing decision.

### What is the strongest product framing?

Code Scalpel is a standalone analysis engine with optional adapters for enterprise scanner ecosystems.

## Architecture Guidance

When implementing parser and scanner support, keep the model clean:

- **Native analyzers:** first-party logic owned by Code Scalpel.
- **Local CLI runners:** execute open tools locally when practical.
- **External report parsers:** parse JSON, XML, SARIF, and similar exports.
- **Server or API connectors:** retrieve findings from enterprise systems where direct execution is not realistic.

Every tool integration should make it clear whether it is:

- Native
- Local CLI
- External report
- Server or API based

## Suggested Website Direction Later

When the marketing team updates the website, the best framing is:

**Hero-level message:**
Code Scalpel is a standalone analysis engine for AI-driven code operations, with optional adapters for enterprise scanners and compliance platforms.

**Supporting message:**
You get immediate value out of the box, while larger teams can plug into the tools they already trust.

## Final Position

The product should not be framed as dependent on third-party scanners.

It should be framed as:

- Strong on its own
- Better in enterprise environments
- Honest about native capabilities versus federated integrations

That is the right architectural story and the right market story.