"""Source sanitization helpers for permissive parsing."""

from __future__ import annotations

import re

# [20260116_BUGFIX] Pre-sanitize malformed source before ast.parse.
_CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")
_JINJA_BLOCK_PATTERN = re.compile(r"\{[%#].*?[%#]\}")
_JINJA_EXPR_PATTERN = re.compile(r"\{\{.*?\}\}")


def sanitize_python_source(code: str) -> tuple[str, bool]:
    """Sanitize Python source for permissive parsing.

    Replaces merge conflict markers and Jinja template syntax with safe
    placeholders while preserving line count.
    """
    changed = False
    out_lines: list[str] = []

    for raw_line in code.splitlines(keepends=True):
        line = raw_line
        stripped = line.lstrip()
        indent = line[: len(line) - len(stripped)]

        if any(stripped.startswith(marker) for marker in _CONFLICT_MARKERS):
            changed = True
            out_lines.append(f"{indent}# [SCALPEL] stripped conflict marker\n")
            continue

        if "{%" in line or "{#" in line:
            if _JINJA_BLOCK_PATTERN.search(line):
                changed = True
                out_lines.append(f"{indent}# [SCALPEL] stripped template line\n")
                continue

        if "{{" in line and _JINJA_EXPR_PATTERN.search(line):
            changed = True
            line = _JINJA_EXPR_PATTERN.sub("None", line)

        out_lines.append(line)

    return "".join(out_lines), changed
