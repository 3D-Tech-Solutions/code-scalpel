#!/bin/bash
# [20260313_DOCS] Local docs wrapper that disables git-revision timestamps for worktrees without full git history.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$REPO_ROOT"
export MKDOCS_ENABLE_GIT_REVISION_DATE=false

exec bash "$REPO_ROOT/scripts/build_docs.sh" --strict "$@"