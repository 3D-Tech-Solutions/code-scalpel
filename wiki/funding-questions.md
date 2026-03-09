# Funding Evidence Memo

> [20260309_DOCS] Investor-facing public-evidence brief for Code Scalpel. This memo distinguishes what is publicly verifiable today from what still requires founder-provided diligence material.

## Executive Summary

- **Product is real and shipping:** Code Scalpel is publicly available on GitHub and PyPI at version `2.1.0`.
- **Traction is real but early:** public signals show low-but-nonzero adoption across GitHub, PyPI download proxies, and the VS Code Marketplace.
- **Commercial framing should be:** `22 core tools` plus a separate capability-introspection surface for tier/license discovery.
- **Open-core monetization is implied, not proven:** Community is clearly free; Pro and Enterprise are clearly designed; public pricing and revenue evidence are not available.
- **The main diligence gap is not product existence; it is commercial proof.**

## Publicly Verified Facts

### Product and Release Status

- **Current package version:** `2.1.0`
- **PyPI release date:** `2026-03-02`
- **Latest GitHub-facing release wording in repo:** `v2.1.0 | March 3, 2026`
- **Primary public repository:** `https://github.com/3D-Tech-Solutions/code-scalpel`
- **License posture:** MIT-licensed Community tier with documented Pro/Enterprise license-file flow

### Tool and Packaging Story

- The most defensible commercial wording is **22 core tools**.
- `get_capabilities` should be treated as a **capability-introspection surface** used by agents to understand current tier/license limits, not as part of the 22-core-tool product count.
- Public copy is not yet fully normalized around that distinction, which creates avoidable diligence friction.

### Public Traction Snapshot

#### GitHub

- `10` stars
- `1` fork
- `0` watchers
- `7` releases
- `5` visible contributors on the contributors page, although that public count includes bot/app accounts and should not be presented as human team size

#### PyPI

- Package: `codescalpel`
- Latest public version: `2.1.0`
- `pypistats.org` recent downloads:
  - `13` last day
  - `258` last week
  - `1,250` last month
- `pepy.tech` total downloads: approximately `5.76k`

#### VS Code Marketplace

- Extension listing exists: `3DTechus.code-scalpel`
- `8` installs
- Average rating: `0/5`
- Public listing version: `2.0.0`
- Listing marked `Free`

#### GitHub Activity Signals

- **Issues:** public issues page currently shows `0` open and `0` closed issues
- **Discussions:** public discussions are enabled, but only `1` visible discussion was found in this pass
  - Title: `Code Scalpel is live on PyPI`
  - Category: `Announcements`
  - Comments: `0`

#### Container / GHCR Evidence

- Repo docs reference GHCR distribution paths, but I did **not** find a public GHCR package page that resolved successfully.
- A previous public repository view also showed `No packages published` under GitHub Packages for this repo.
- Current public conclusion: **container distribution may exist in docs and automation, but public pull/download evidence was not verified in this pass**.

## What This Means for an Investor Readout

### Positive Signals

- The product is not hypothetical; it is shipping through multiple public channels.
- Release cadence is active.
- There is at least some measurable early adoption across package installs and extension installs.
- Positioning is differentiated and technically coherent: MCP-first, agent-oriented, deterministic analysis, and optional enterprise adapters.

### Weak Signals / Risks

- Community activity is still thin: no visible issue history and only one visible discussion thread.
- Public traction remains small by venture standards.
- Marketplace version lag and stale public copy reduce polish and can weaken diligence confidence.
- GHCR distribution is referenced, but public pull evidence was not found.

## Publicly Supported Commercial Narrative

- **What can be said confidently:**
  - Code Scalpel is a real open-core developer tool with a free Community tier and designed Pro/Enterprise upsell path.
  - It is distributed through GitHub, PyPI, and the VS Code Marketplace.
  - It has early usage signals and active release activity.
- **What should not be claimed publicly without more evidence:**
  - Meaningful enterprise adoption
  - Proven commercial traction
  - Customer count
  - ARR/MRR
  - Public price validation
  - GHCR pull scale

## Open Diligence Items

1. **Pricing and revenue**
	TODO: provide current Pro/Enterprise packaging, list pricing, discounts, paid pilots, consulting revenue, and any recurring revenue.
2. **Usage beyond public proxies**
	TODO: provide internal active-user counts, active workspaces, returning users, and any telemetry or support-volume evidence.
3. **Benchmark packet**
	TODO: convert token/cost/performance claims into a reproducible evidence bundle suitable for diligence review.
4. **Customer proof**
	TODO: provide logos, testimonials, pilot summaries, or anonymized case studies if they exist.
5. **GHCR clarification**
	TODO: confirm whether container images are public, private, unpublished, or simply linked incorrectly in docs.

## Cleanup Required Before External Use

1. Normalize all user-facing wording to **22 core tools + capability introspection**.
2. Sync Marketplace and package copy with the current `2.1.0` product story.
3. Fix marketplace support links so they point to `3D-Tech-Solutions/code-scalpel` consistently.
4. Decide whether public issue/discussion emptiness is acceptable as-is or whether community engagement should be seeded before fundraising outreach.

## Bottom-Line Assessment

Based on public evidence alone, Code Scalpel looks like a technically serious, early-stage open-core infrastructure product with real public distribution and modest early traction. The product story is stronger than the commercial proof. The next step for funding readiness is not more architectural explanation; it is tighter public packaging, a reproducible benchmark packet, and founder-supplied pricing/revenue/customer evidence.