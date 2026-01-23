#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path


def _read_project_version() -> str:
    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        raise RuntimeError("pyproject.toml not found; run from repo root")

    try:
        import tomllib  # py>=3.11
    except ModuleNotFoundError:  # pragma: no cover
        import tomli as tomllib  # type: ignore[no-redef]

    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    version = data.get("project", {}).get("version")
    if not isinstance(version, str) or not version.strip():
        raise RuntimeError("project.version missing in pyproject.toml")
    return version.strip()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: ensure_commit_version.py <commit-msg-file>", file=sys.stderr)
        return 2

    commit_msg_path = Path(argv[1])
    if not commit_msg_path.exists():
        print(f"commit message file not found: {commit_msg_path}", file=sys.stderr)
        return 2

    version = _read_project_version()
    tag = f"v{version}"

    msg = commit_msg_path.read_text(encoding="utf-8")
    if tag in msg:
        return 0

    # Don’t touch merge commits.
    first_line = (msg.splitlines() or [""])[0]
    if first_line.startswith("Merge "):
        return 0

    # Prepend version tag to the first non-comment line.
    lines = msg.splitlines(True)  # keepends
    out: list[str] = []
    inserted = False
    for line in lines:
        if inserted:
            out.append(line)
            continue

        if not line.strip() or line.lstrip().startswith("#"):
            out.append(line)
            continue

        # If the commit already starts with some version-like token, don't double-prefix.
        if re.search(r"\bv\d+\.\d+\.\d+\b", line):
            inserted = True
            out.append(line)
            continue

        out.append(f"{tag}: {line.lstrip()}")
        inserted = True

    if not inserted:
        out = [f"{tag}: \n"]

    commit_msg_path.write_text("".join(out), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
