# CI/CD Troubleshooting Guide <!-- [20251214_DOCS] v1.5.5 CI reliability work -->

## Quick Triage
- Identify failing job/stage and copy the exact error snippet.
- Re-run the failing job once to detect flakiness; capture if pass-on-rerun.
- Check dependency resolution: ensure lock/pins match `requirements.txt` and wheel cache is warm.
- Verify Python version and platform matrix matches supported list.

## Common Fixes
- **Flaky tests:** rerun with `pytest -k <pattern> --maxfail=1 -q`; mark flaky + owner; open ticket; deflake before removing quarantine.
- **Cache issues:** drop CI cache and rebuild wheels; ensure cache key includes OS + Python + requirements hash.
- **Timeouts:** increase per-stage timeout or reduce parallelism; prefer targeted test subsets for smoke.
- **Lint/format drift:** run `python -m ruff check .` and `python -m black --check .` locally; commit fixes.

## Smoke Gate (planned)
- Add a fast pipeline job running: `python -m ruff check .`, `python -m black --check .`, and `python -m pytest tests/smoke -q` (or scripts/smoke.ps1 on Windows).

## Logging & Artifacts
- Save failing logs to `release_artifacts/v1.5.5/ci_cd_reliability_log.json` with root cause, fix, and owner.
- For flaky reruns, record first-fail/second-pass timestamps and environment.

## Escalation
- If deterministic failures persist, bisect recent changes; if dependency-related, pin/upgrade and document in release notes.
