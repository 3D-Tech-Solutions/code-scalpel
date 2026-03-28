#!/bin/bash
# build_docs.sh — Build the public website from the main repo root.
#
# Content source:  docs/website/docs/   (edit here)
# Build config:    website/mkdocs.yml   (canonical; docs/website/mkdocs.yml symlinks here)
# Build output:    website/site/        (git-ignored)
# Deploy:          docs/website/deploy.sh or website/deploy.sh (rsync to Hostinger)
#
# [20260224_DOCS] Created to provide a single entry point for documentation builds.
#
# Usage:
#   bash scripts/build_docs.sh          # build only
#   bash scripts/build_docs.sh --serve  # local preview at http://127.0.0.1:8000
#   bash scripts/build_docs.sh --deploy # build + deploy to Hostinger
#   bash scripts/build_docs.sh --strict # build with strict mode (treat warnings as errors)
#   bash scripts/build_docs_local.sh    # strict local build without git revision warnings

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEBSITE_DIR="$REPO_ROOT/website"
DOCS_SOURCE="$REPO_ROOT/docs/website/docs"
DEPLOY_SCRIPT="$REPO_ROOT/docs/website/deploy.sh"

# ── colours ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[docs]${NC} $*"; }
warn()  { echo -e "${YELLOW}[docs]${NC} $*"; }
error() { echo -e "${RED}[docs]${NC} $*" >&2; }

# ── mkdocs resolver: prefer PATH, fall back to uv run ──────────────────────────
MKDOCS_CMD="mkdocs"
if ! command -v mkdocs &>/dev/null; then
    if command -v uv &>/dev/null; then
        # Use uv to run mkdocs with all required plugins
        MKDOCS_CMD="uv run --with mkdocs-material --with mkdocs-material-extensions --with mkdocs-jupyter --with mkdocs-git-revision-date-localized-plugin --with mkdocs-minify-plugin --with mkdocs-glightbox --with pymdown-extensions --with pygments mkdocs"
    else
        error "mkdocs not found. Install with: pip install mkdocs-material"
        exit 1
    fi
fi

# ── preflight checks ───────────────────────────────────────────────────────────
check_prerequisites() {
    if [[ -z "$MKDOCS_CMD" ]]; then
        error "mkdocs not found. Install with: pip install mkdocs-material"
        exit 1
    fi
    if [[ ! -f "$WEBSITE_DIR/mkdocs.yml" ]]; then
        error "mkdocs.yml not found at $WEBSITE_DIR/mkdocs.yml"
        exit 1
    fi
    if [[ ! -d "$DOCS_SOURCE" ]]; then
        error "Docs source not found at $DOCS_SOURCE"
        exit 1
    fi
    # Ensure website/docs -> website/site symlink exists (serves docs at /docs/ for any static server)
    if [[ ! -L "$WEBSITE_DIR/docs" ]]; then
        info "Creating website/docs -> website/site symlink..."
        ln -sfn site "$WEBSITE_DIR/docs"
    fi
}

# ── parse arguments ────────────────────────────────────────────────────────────
SERVE=false
DEPLOY=false
STRICT=""

for arg in "$@"; do
    case "$arg" in
        --serve)   SERVE=true  ;;
        --deploy)  DEPLOY=true ;;
        --strict)  STRICT="--strict" ;;
        -h|--help)
            echo "Usage: $0 [--serve] [--deploy] [--strict]"
            echo "  --serve   Start local preview server at http://127.0.0.1:8000"
            echo "  --deploy  Build then deploy to Hostinger via rsync"
            echo "  --strict  Treat warnings as errors during build"
            exit 0 ;;
        *)
            error "Unknown argument: $arg"; exit 1 ;;
    esac
done

# ── main ───────────────────────────────────────────────────────────────────────
check_prerequisites

cd "$WEBSITE_DIR"

if $SERVE; then
    info "Starting local preview server..."
    info "Content source: $DOCS_SOURCE"
    info "Press Ctrl+C to stop"
    exec $MKDOCS_CMD serve --config-file mkdocs.yml
fi

info "Building documentation..."
info "  Source : docs/website/docs/"
info "  Config : website/mkdocs.yml"
info "  Output : website/site/"

$MKDOCS_CMD build --config-file mkdocs.yml ${STRICT}

info "Build complete → website/site/"

if $DEPLOY; then
    if [[ ! -f "$DEPLOY_SCRIPT" ]]; then
        error "Deploy script not found: $DEPLOY_SCRIPT"
        exit 1
    fi
    info "Deploying to Hostinger..."
    bash "$DEPLOY_SCRIPT"
fi
