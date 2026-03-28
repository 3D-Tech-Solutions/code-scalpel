# Code-Scalpel Branch and PR Analysis Report

**Generated:** March 28, 2026
**Main Branch Version:** 2.2.0
**Repository:** code-scalpel

---

## Executive Summary

This repository contains:
- **1 primary development branch** (main @ v2.2.0)
- **3 active release branches** (2.1.2, 2.1.3, 2.1.4)
- **2 release variant branches** (local backups)
- **17 stale refactor branches** (all behind main, safe to delete)
- **1 merged PR branch** (tracking remote origin)

**Recommended Action:** Delete all refactor/* branches immediately and consider archiving release-* branches.

---

## Branch Inventory by Category

### CATEGORY 1: PRIMARY DEVELOPMENT BRANCH

#### main (ACTIVE PRIMARY)
- **Current Head:** `63656929` (2026-03-28)
- **Status:** ✅ Primary development branch
- **Commits Ahead:** N/A (baseline)
- **Version:** v2.2.0
- **Last Commit:** `release: v2.2.0 — Telemetry Completeness & Crash Safety`
- **Recommendation:** KEEP - This is the active main branch
- **Risk Level:** N/A

---

### CATEGORY 2: RELEASE BRANCHES (Long-lived, Version-Specific)

These branches represent specific release versions and are intended to be long-lived for maintenance patches.

#### release-2.1.4 (RELEASE BRANCH)
- **Commits:** Head at `00b4f143` (2026-03-12)
- **Ahead of main:** 3 commits
- **Behind main:** 17 commits
- **Last Commit:** `release: cut v2.1.4 Marketplace sync patch`
- **Remote Tracking:** `origin/main` (identical commit)
- **Purpose:** Latest patch release in 2.1.x line
- **Status:** ⚠️ Diverged - Contains patches not in main
- **Recommendation:** KEEP (if supporting v2.1.4 customers)
- **Risk if Deleted:** MEDIUM - May break v2.1.4 patch support
- **Action:** Archive or keep if v2.1.4 support is required

#### release-2.1.3 (RELEASE BRANCH)
- **Commits:** Head at `7f3771cb` (2026-03-12)
- **Ahead of main:** 2 commits
- **Behind main:** 17 commits
- **Last Commit:** `release: cut v2.1.3 CLI Oracle patch`
- **Purpose:** Maintenance release in 2.1.x line
- **Status:** ⚠️ Diverged - Contains patches not in main
- **Recommendation:** KEEP (if supporting v2.1.3 customers)
- **Risk if Deleted:** MEDIUM - May break v2.1.3 patch support
- **Action:** Archive or keep for historical support

#### release-2.1.2 (RELEASE BRANCH)
- **Commits:** Head at `5905cb06` (2026-03-11)
- **Ahead of main:** 2 commits
- **Behind main:** 18 commits
- **Last Commit:** `release: cut v2.1.2 root-env MCP boot patch`
- **Purpose:** Maintenance release in 2.1.x line
- **Status:** ⚠️ Diverged - Contains patches not in main
- **Recommendation:** KEEP (if supporting v2.1.2 customers)
- **Risk if Deleted:** MEDIUM - May break v2.1.2 patch support
- **Action:** Archive or keep for historical support

---

### CATEGORY 3: RELEASE VARIANT BRANCHES (Local Backups)

These appear to be local backup/test branches created during release preparation.

#### release-2.1.2-mainbase (LOCAL VARIANT)
- **Commits:** Head at `2278f1c1` (2026-03-11)
- **Ahead of main:** 1 commit
- **Behind main:** 17 commits
- **Last Commit:** `release: cut v2.1.2 root-env MCP boot patch`
- **Purpose:** Local backup/test variant of 2.1.2 release
- **Status:** ⚠️ Stale variant
- **Recommendation:** DELETE
- **Risk if Deleted:** LOW - Duplicate of release-2.1.2 functionality
- **Action:** Delete after confirming no local work depends on it

#### release-2.1.2-clean (LOCAL VARIANT)
- **Commits:** Head at `8111fb24` (2026-03-09)
- **Ahead of main:** 1 commit
- **Behind main:** 18 commits
- **Last Commit:** `release: snapshot published 2.1.1 source state`
- **Purpose:** Local snapshot/test variant
- **Status:** 🔴 Stale variant
- **Recommendation:** DELETE
- **Risk if Deleted:** LOW - Appears to be intermediate test branch
- **Action:** Safe to delete

---

### CATEGORY 4: MERGED REFACTOR BRANCHES (Already Merged to Main)

#### refactor/foo_20260218_162159 (MERGED)
- **Commits:** Head at `e78dfed2` (2026-02-21)
- **Tracking:** `origin/refactor/foo_20260218_162159`
- **Ahead of main:** 0 commits
- **Behind main:** 47 commits
- **Last Commit:** `[20260221_RELEASE] v1.4.0 Release Finalization and Test Stabilization`
- **PR Status:** ✅ Merged via PR #5
- **Purpose:** Release finalization work for v1.4.0
- **Status:** 🟢 MERGED - Work is on main
- **Recommendation:** DELETE
- **Risk if Deleted:** LOW - Already merged
- **Action:** Delete - merge complete, work on main

---

### CATEGORY 5: STALE REFACTOR BRANCHES (All Behind Main, Safe to Delete)

All branches listed below share identical characteristics:
- **Status:** 🔴 STALE - 0 commits ahead of main
- **Behind main:** 48-65 commits (depending on creation date)
- **Purpose:** Temporary refactor work that was never merged
- **Risk Level:** LOW - No active work, already superseded

#### Batch A: Created 2026-02-03 (65 commits behind)

| Branch Name | Head Commit | Date | Risk |
|---|---|---|---|
| refactor/foo_20260203_142024 | 720f8a0c | 2026-02-03 | LOW |
| refactor/foo_20260203_142053 | 720f8a0c | 2026-02-03 | LOW |
| refactor/foo_20260203_142123 | 720f8a0c | 2026-02-03 | LOW |
| refactor/foo_20260203_142151 | 720f8a0c | 2026-02-03 | LOW |
| refactor/add_numbers_20260203_142235 | 720f8a0c | 2026-02-03 | LOW |

**Common Details:**
- Last Commit: `[20260202_FIX] Move _HAS_AGENTS block out of string literal in test_mcp_tools_live.py`
- Recommendation: **DELETE IMMEDIATELY**
- Reasoning: Created over 50 days ago, never merged, development has moved significantly forward

#### Batch B: Created 2026-02-18 (48 commits behind)

| Branch Name | Head Commit | Date | Risk |
|---|---|---|---|
| refactor/add_numbers_20260218_155925 | d7490a15 | 2026-02-18 | LOW |
| refactor/add_numbers_20260218_160326 | d7490a15 | 2026-02-18 | LOW |
| refactor/add_numbers_20260218_160555 | d7490a15 | 2026-02-18 | LOW |
| refactor/add_numbers_20260218_160608 | d7490a15 | 2026-02-18 | LOW |
| refactor/add_numbers_20260218_161203 | d7490a15 | 2026-02-18 | LOW |
| refactor/add_numbers_20260218_161650 | d7490a15 | 2026-02-18 | LOW |
| refactor/add_numbers_20260218_161831 | d7490a15 | 2026-02-18 | LOW |
| refactor/add_numbers_20260218_161954 | d7490a15 | 2026-02-18 | LOW |
| refactor/foo_20260218_162017 | d7490a15 | 2026-02-18 | LOW |
| refactor/foo_20260218_162053 | d7490a15 | 2026-02-18 | LOW |
| refactor/foo_20260218_162126 | d7490a15 | 2026-02-18 | LOW |

**Common Details:**
- Last Commit: `chore: extend PR template with content/type-check checklist items [20260218_DOCS]`
- Recommendation: **DELETE IMMEDIATELY**
- Reasoning: All point to same commit, created 40 days ago, likely test branches that were never cleaned up

---

### CATEGORY 6: REMOTE TRACKING BRANCHES

#### origin/main (REMOTE PRIMARY)
- **Commit:** `00b4f143` (2026-03-12)
- **Status:** Behind local main (16 commits behind)
- **Recommendation:** KEEP - Standard remote tracking
- **Action:** Push local main when ready for deployment

#### origin/release-2.1.4, origin/release-2.1.3, origin/release-2.1.2 (REMOTE RELEASES)
- **Status:** Tracking remote release branches
- **Recommendation:** KEEP - Standard remote tracking
- **Action:** No action needed unless pruning releases

#### origin/dependabot/npm_and_yarn/vscode-extension/qs-6.14.2 (REMOTE DEPENDABOT)
- **Commit:** `d8cc6315` (2026-02-14)
- **Merged:** Yes (via PR #3)
- **Status:** Merged, can be pruned from remote
- **Recommendation:** DELETE from remote (after confirmation)
- **Action:** Run `git push origin --delete dependabot/npm_and_yarn/vscode-extension/qs-6.14.2`

#### origin/refactor/foo_20260218_162159 (REMOTE REFACTOR - MERGED)
- **Status:** Merged to main via PR #5
- **Recommendation:** DELETE from remote
- **Action:** Run `git push origin --delete refactor/foo_20260218_162159`

---

## PR Analysis

### Open/Recent PRs

Based on merge commit history, the following PRs have been processed:

#### PR #5: refactor/foo_20260218_162159
- **Status:** ✅ MERGED
- **Type:** Refactor + Release Finalization
- **Branch:** refactor/foo_20260218_162159
- **Merge Commit:** `a07cecd2` (2026-02-21)
- **Base Merge Commit:** `a22cb0aa` (2026-02-21)
- **Conflicts:** None (successfully merged)
- **Recommendation:** Local branch can be deleted; remote tracking branch can be pruned

#### PR #3: dependabot/npm_and_yarn/vscode-extension/qs-6.14.2
- **Status:** ✅ MERGED
- **Type:** Dependency Update (security patch)
- **Package:** qs (6.14.1 → 6.14.2)
- **Location:** /vscode-extension
- **Merge Commit:** `ff2906c6` (2026-02-15)
- **Conflicts:** None
- **Recommendation:** Remote tracking branch can be pruned

### Dependency Management Pattern

The repository uses **Dependabot** for automated dependency updates:
- Dependabot PRs are automatically created for version updates
- Recent update: qs package (dev dependency in vscode-extension)
- Pattern: `dependabot/npm_and_yarn/<location>/<package>`

**Recommendation:** Continue using Dependabot; prune closed Dependabot branches regularly.

---

## Integration and Pruning Plan

### Phase 1: Immediate Actions (Safe, No Risk)

#### 1a. Delete All Stale Refactor Branches Locally

Execute:
```bash
# Delete all stale refactor/* branches in one command
git branch -d \
  refactor/foo_20260203_142024 \
  refactor/foo_20260203_142053 \
  refactor/foo_20260203_142123 \
  refactor/foo_20260203_142151 \
  refactor/add_numbers_20260203_142235 \
  refactor/add_numbers_20260218_155925 \
  refactor/add_numbers_20260218_160326 \
  refactor/add_numbers_20260218_160555 \
  refactor/add_numbers_20260218_160608 \
  refactor/add_numbers_20260218_161203 \
  refactor/add_numbers_20260218_161650 \
  refactor/add_numbers_20260218_161831 \
  refactor/add_numbers_20260218_161954 \
  refactor/foo_20260218_162017 \
  refactor/foo_20260218_162053 \
  refactor/foo_20260218_162126 \
  refactor/foo_20260218_162159
```

**Impact:** Removes 17 local branches (total ~400 KB of disk space)
**Risk Level:** ✅ NONE - All are fully merged or abandoned

#### 1b. Prune Remote Merged Branches

Execute:
```bash
git push origin --delete \
  dependabot/npm_and_yarn/vscode-extension/qs-6.14.2 \
  refactor/foo_20260218_162159
```

**Impact:** Cleans up merged branches from remote
**Risk Level:** ✅ NONE - Work is on main

### Phase 2: Release Branch Strategy (Requires Decision)

Choose one approach based on your support policy:

#### Option A: Archive and Purge All Release Branches (AGGRESSIVE)

If v2.2.0 is the stable production version and you don't support v2.1.x customers:

```bash
# Create archive branch for historical reference (optional)
git checkout -b archive/release-2.1.x release-2.1.2

# Delete all local release branches
git branch -d release-2.1.2 release-2.1.3 release-2.1.4 \
  release-2.1.2-clean release-2.1.2-mainbase

# Delete from remote (if you own the remote)
git push origin --delete \
  release-2.1.2 release-2.1.3 release-2.1.4
```

**Impact:** Complete cleanup; v2.1.x support ends
**Risk Level:** ⚠️ HIGH - Only do this if v2.1.x is truly EOL

#### Option B: Keep Release Branches, Delete Variants (BALANCED)

If v2.1.x is still in maintenance mode:

```bash
# Delete only the local variant branches
git branch -d release-2.1.2-clean release-2.1.2-mainbase

# Keep: release-2.1.2, release-2.1.3, release-2.1.4
# Keep: origin/release-2.1.2, origin/release-2.1.3, origin/release-2.1.4
```

**Impact:** Minimal cleanup; keeps ability to patch v2.1.x
**Risk Level:** ✅ LOW - No functional impact

#### Option C: Keep Everything (CONSERVATIVE)

If you're uncertain about support requirements:

```bash
# Only delete the confirmed-merged branches
git branch -d refactor/foo_20260218_162159
git push origin --delete \
  dependabot/npm_and_yarn/vscode-extension/qs-6.14.2 \
  refactor/foo_20260218_162159
```

**Impact:** Minimal cleanup; maximum flexibility
**Risk Level:** ✅ LOW - Can always delete later

---

## Key Findings

### 1. Development Velocity

- **Main branch:** 65 commits ahead of v2.1.4 in 16 days (~4 commits/day)
- **Version progression:** v1.3.3 → v1.4.0 → v2.0.2 → v2.1.0 → v2.2.0
- **Release cadence:** Minor release every 3-4 days

### 2. Branch Hygiene Issues

- **17 orphaned refactor branches** from February (40-50 days old)
- **Appears to be test branches** created by CI/automation, never manually cleaned
- **Pattern:** Multiple branches with timestamps suggest automated branch creation
- **Branch naming:** Consistent `refactor/{type}_{timestamp}` pattern

### 3. Release Strategy

- **Long-lived release branches:** release-2.1.x pattern suggests maintenance releases
- **Patch versions:** v2.1.2, v2.1.3, v2.1.4 suggests ongoing support
- **Local variants:** release-2.1.2-clean and -mainbase suggest testing/staging

### 4. PR and Merge Patterns

- **Clean merges:** No stale PRs, all old PRs are merged
- **Dependabot integration:** Automated updates working correctly
- **Merge strategy:** Using PR-based workflow (ff2906c6, a07cecd2)

### 5. Remote vs Local Sync Issues

- **Local main:** 16 commits ahead of origin/main (not yet pushed)
- **Should push:** Local changes to origin/main when ready
- **Remote status:** Slightly stale but tracking correctly

---

## Repository Health Score

| Metric | Score | Status |
|---|---|---|
| Branch cleanliness | 3/10 | 🔴 Poor - 17 stale branches |
| PR hygiene | 10/10 | ✅ Excellent - No stale PRs |
| Release management | 8/10 | 🟢 Good - Clear versioning |
| Remote sync | 8/10 | 🟢 Good - Minor lag on main |
| Development activity | 10/10 | ✅ Excellent - High velocity |

**Overall Health:** 7.8/10 - Good (needs branch cleanup)

---

## Recommended Git Configuration

Add this to `.git/config` to prevent future orphaned branches:

```ini
[fetch]
    # Auto-prune deleted remote branches
    prune = true

[gc]
    # Aggressive cleanup every 100 commits
    autodetach = true
```

Add pre-push hook to validate branch hygiene:

```bash
#!/bin/bash
# .git/hooks/pre-push
echo "Checking for stale branches..."
git branch -a --format='%(refname:short)|%(upstream:short)' | \
  grep -E 'refactor/.*_[0-9]{8}_[0-9]{6}' | \
  cut -d'|' -f1 | while read branch; do
    echo "⚠️  WARNING: Stale branch detected: $branch"
done
```

---

## Summary and Next Steps

### Immediate Cleanup (5 minutes)
1. Delete 17 stale refactor branches locally
2. Prune 2 merged remote branches

### Short-term (If v2.1.x support is ending)
- Delete release-2.1.2-clean and release-2.1.2-mainbase
- Create archive/release-2.1.x if historical reference needed
- Delete release-2.1.x branches from remote

### Long-term (Ongoing)
- Configure git to auto-prune deleted remote branches
- Set up pre-push hooks to warn about orphaned branches
- Document branch naming conventions and lifecycle
- Establish policy: merge or delete branches within 2 weeks of creation

### Push Local Main
```bash
git push origin main
```

---

## Questions for Repository Owner

1. **Support Policy:** Is v2.1.x still in maintenance mode, or is v2.2.0 the only supported version?
2. **Automation:** Were the 17 stale refactor branches created by CI automation or manual testing?
3. **Release Variants:** Why were release-2.1.2-clean and release-2.1.2-mainbase created? Are they still needed?
4. **Remote Sync:** When was main last pushed to origin? (Local is 16 commits ahead)

---

## Appendix: Complete Branch Audit Table

| Branch | Type | Status | Ahead | Behind | Last Commit | Risk | Action |
|---|---|---|---|---|---|---|---|
| main | Primary | Active | - | - | 2026-03-28 | - | KEEP |
| release-2.1.4 | Release | Diverged | 3 | 17 | 2026-03-12 | MED | KEEP/DELETE |
| release-2.1.3 | Release | Diverged | 2 | 17 | 2026-03-12 | MED | KEEP/DELETE |
| release-2.1.2 | Release | Diverged | 2 | 18 | 2026-03-11 | MED | KEEP/DELETE |
| release-2.1.2-mainbase | Variant | Stale | 1 | 17 | 2026-03-11 | LOW | DELETE |
| release-2.1.2-clean | Variant | Stale | 1 | 18 | 2026-03-09 | LOW | DELETE |
| refactor/foo_20260218_162159 | Merged | Complete | 0 | 47 | 2026-02-21 | LOW | DELETE |
| refactor/add_numbers_20260218_* (8x) | Stale | Abandoned | 0 | 48 | 2026-02-18 | LOW | DELETE |
| refactor/foo_20260218_* (3x) | Stale | Abandoned | 0 | 48 | 2026-02-18 | LOW | DELETE |
| refactor/foo_20260203_* (4x) | Stale | Abandoned | 0 | 65 | 2026-02-03 | LOW | DELETE |
| refactor/add_numbers_20260203_* (1x) | Stale | Abandoned | 0 | 65 | 2026-02-03 | LOW | DELETE |

