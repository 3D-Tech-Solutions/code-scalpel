#!/usr/bin/env python
"""[20251214_FEATURE] Generate or clone benchmark fixtures for performance testing.

Usage:
    python tests/fixtures/generate_fixture.py --synthetic 1200
    python tests/fixtures/generate_fixture.py --clone django
    python tests/fixtures/generate_fixture.py --stdlib
"""

from __future__ import annotations

import argparse
import random
import shutil
import subprocess
import sys
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "data"
CLONE_REPOS = {
    "django": "https://github.com/django/django.git",
    "flask": "https://github.com/pallets/flask.git",
    "requests": "https://github.com/psf/requests.git",
}


def generate_synthetic(size: int, name: str = "synthetic") -> Path:
    """Generate synthetic project with realistic import graphs."""
    root = FIXTURES_DIR / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    pkg = root / "pkg"
    pkg.mkdir()

    files: list[str] = []
    for i in range(size):
        mod_name = f"mod_{i}"
        files.append(mod_name)

    # Write files with random imports to siblings
    for i, mod_name in enumerate(files):
        imports: list[str] = []
        # Each file imports 2-5 random siblings (if available)
        if i > 0:
            num_imports = min(random.randint(2, 5), i)
            targets = random.sample(files[:i], num_imports)
            imports = [f"from .{t} import VALUE as {t}_val" for t in targets]

        content = "\n".join(imports) + f"\n\nVALUE = {i}\n"
        (pkg / f"{mod_name}.py").write_text(content, encoding="utf-8")

    # Package init
    (pkg / "__init__.py").write_text("from .mod_0 import VALUE\n", encoding="utf-8")

    print(f"Created synthetic fixture at {root} ({size} files)")
    return root


def clone_repo(name: str) -> Path:
    """Clone a real open-source project (shallow)."""
    if name not in CLONE_REPOS:
        print(f"Unknown repo: {name}. Available: {list(CLONE_REPOS.keys())}")
        sys.exit(1)

    url = CLONE_REPOS[name]
    dest = FIXTURES_DIR / name
    if dest.exists():
        print(f"Fixture {dest} already exists; skipping clone.")
        return dest

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--depth", "1", url, str(dest)], check=True)
    print(f"Cloned {name} to {dest}")
    return dest


def link_stdlib() -> Path:
    """Create symlink or note for Python stdlib Lib folder."""
    import sys as _sys

    stdlib = Path(_sys.prefix) / "Lib"
    if not stdlib.exists():
        # Try base_prefix for venvs
        stdlib = Path(_sys.base_prefix) / "Lib"
    if not stdlib.exists():
        print(f"Could not find stdlib at {stdlib}")
        sys.exit(1)

    dest = FIXTURES_DIR / "stdlib"
    if dest.exists():
        print(f"Fixture {dest} already exists.")
        return dest

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    # On Windows, symlinks may require admin; just note path instead
    dest.write_text(str(stdlib), encoding="utf-8")
    print(f"Stdlib path noted at {dest}: {stdlib}")
    return stdlib


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate benchmark fixtures")
    parser.add_argument("--synthetic", type=int, metavar="N", help="Generate N-file synthetic project")
    parser.add_argument(
        "--clone",
        type=str,
        metavar="REPO",
        help="Clone real repo (django, flask, requests)",
    )
    parser.add_argument("--stdlib", action="store_true", help="Link Python stdlib")
    args = parser.parse_args()

    if args.synthetic:
        generate_synthetic(args.synthetic)
    elif args.clone:
        clone_repo(args.clone)
    elif args.stdlib:
        link_stdlib()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
