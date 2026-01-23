"""[20260114_FEATURE] Generate website tool catalog JSON from deep-dive docs.

This script extracts a small, web-friendly summary for each MCP tool from:
- docs/tools/deep_dive/TOOL_CAPABILITY_MATRIX.md
- docs/tools/deep_dive/*_DEEP_DIVE.md

Output:
- website/assets/tool_catalog.json

Design goals:
- Keep output concise and consistent
- Fail soft: missing sections become empty fields
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEEP_DIVE_DIR = REPO_ROOT / "docs" / "tools" / "deep_dive"
MATRIX_PATH = DEEP_DIVE_DIR / "TOOL_CAPABILITY_MATRIX.md"
OUTPUT_PATH = REPO_ROOT / "website" / "assets" / "tool_catalog.json"

GITHUB_DEEP_DIVE_BASE = "https://github.com/3D-Tech-Solutions/code-scalpel/blob/main/docs/tools/deep_dive/"


@dataclass(frozen=True)
class ToolRow:
    name: str
    status: str
    tier: str
    key_capabilities: list[str]
    deep_dive_file: str


def _strip_md(text: str) -> str:
    # Remove inline code and emphasis markers for web display.
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    return text.strip()


def _parse_matrix_rows(md: str) -> list[ToolRow]:
    rows: list[ToolRow] = []

    in_table = False
    for raw_line in md.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("| Tool Name"):
            in_table = True
            continue
        if in_table and line.startswith("| :---"):
            continue
        if in_table and line.startswith("## "):
            break
        if not in_table:
            continue
        if not (line.startswith("|") and line.endswith("|")):
            continue

        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) != 5:
            continue

        name = _strip_md(parts[0])
        status = _strip_md(parts[1])
        tier = _strip_md(parts[2])

        caps_raw = parts[3]
        caps_raw = caps_raw.replace("<br>", "\n")
        caps = []
        for cap_line in caps_raw.splitlines():
            cap_line = cap_line.strip()
            cap_line = cap_line.lstrip("•").strip()
            if cap_line:
                caps.append(_strip_md(cap_line))

        deep_dive_match = re.search(r"\(([^)]+_DEEP_DIVE\.md)\)", parts[4])
        deep_dive_file = deep_dive_match.group(1) if deep_dive_match else ""

        rows.append(
            ToolRow(
                name=name,
                status=status,
                tier=tier,
                key_capabilities=caps,
                deep_dive_file=deep_dive_file,
            )
        )

    return rows


def _extract_heading_section(md: str, heading: str) -> str:
    # Find a heading like "### Purpose Statement" and capture content until next ###/## heading.
    # Fail soft.
    pattern = re.compile(rf"^###\s+{re.escape(heading)}\s*$", re.MULTILINE)
    match = pattern.search(md)
    if not match:
        return ""

    start = match.end()
    tail = md[start:]

    # Stop at next "### " or "## " heading.
    stop = re.search(r"^##{2,3}\s+", tail, flags=re.MULTILINE)
    chunk = tail[: stop.start()] if stop else tail

    return chunk.strip()


def _first_paragraph(text: str) -> str:
    lines = [ln.rstrip() for ln in text.splitlines()]
    out: list[str] = []
    for ln in lines:
        if ln.strip() == "":
            if out:
                break
            continue
        # Skip blockquotes and list markers in paragraph extraction.
        if ln.lstrip().startswith(">"):
            continue
        if ln.lstrip().startswith(("- ", "* ")):
            if out:
                break
            continue
        out.append(ln.strip())
    return _strip_md(" ".join(out))


def _parse_bullets(text: str, max_items: int = 6) -> list[str]:
    items: list[str] = []
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("- "):
            items.append(_strip_md(s[2:]))
        elif s.startswith("* "):
            items.append(_strip_md(s[2:]))
        elif re.match(r"^\*\s{3,}\S", s):
            # Some deep dives use "*   " style
            items.append(_strip_md(re.sub(r"^\*\s+", "", s)))
        if len(items) >= max_items:
            break
    return [i for i in items if i]


def _extract_signature(md: str) -> str:
    section = _extract_heading_section(md, "Signature")
    if not section:
        return ""

    # Find first fenced code block after Signature
    fence = re.search(r"```[a-zA-Z0-9_-]*\n(.*?)\n```", section, flags=re.DOTALL)
    if not fence:
        return ""

    code = fence.group(1).strip("\n")
    lines = code.splitlines()
    if len(lines) > 14:
        code = "\n".join(lines[:14]) + "\n…"
    return code


def _extract_meta_field(md: str, label: str) -> str:
    # e.g., **Status:** Stable
    m = re.search(rf"\*\*{re.escape(label)}\*\*:\s*(.+)", md)
    return _strip_md(m.group(1)) if m else ""


def build_catalog() -> dict[str, Any]:
    matrix_md = MATRIX_PATH.read_text(encoding="utf-8")
    rows = _parse_matrix_rows(matrix_md)

    tools: list[dict[str, Any]] = []
    for row in rows:
        deep_dive_path = DEEP_DIVE_DIR / row.deep_dive_file
        deep_md = deep_dive_path.read_text(encoding="utf-8") if deep_dive_path.exists() else ""

        purpose_block = _extract_heading_section(deep_md, "Purpose Statement")
        benefits_block = _extract_heading_section(deep_md, "Key Benefits")
        when_block = _extract_heading_section(deep_md, "When to Use This Tool")
        not_suitable_block = _extract_heading_section(deep_md, "Not Suitable For")

        tool_obj: dict[str, Any] = {
            "name": row.name,
            "status": row.status,
            "tierAvailability": row.tier,
            "keyCapabilities": row.key_capabilities,
            "purpose": _first_paragraph(purpose_block) if purpose_block else "",
            "keyBenefits": _parse_bullets(benefits_block) if benefits_block else [],
            "whenToUse": _parse_bullets(when_block) if when_block else [],
            "notSuitableFor": (_parse_bullets(not_suitable_block) if not_suitable_block else []),
            "signature": _extract_signature(deep_md),
            "toolVersion": _extract_meta_field(deep_md, "Tool Version"),
            "lastUpdated": _extract_meta_field(deep_md, "Last Updated"),
            "deepDiveFile": row.deep_dive_file,
            "deepDiveUrl": (f"{GITHUB_DEEP_DIVE_BASE}{row.deep_dive_file}" if row.deep_dive_file else ""),
        }

        tools.append(tool_obj)

    return {
        "generatedAt": "2026-01-14",
        "source": {
            "matrix": str(MATRIX_PATH.relative_to(REPO_ROOT)),
            "deepDiveDir": str(DEEP_DIVE_DIR.relative_to(REPO_ROOT)),
        },
        "tools": tools,
    }


def main() -> None:
    catalog = build_catalog()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(catalog, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print(f"Wrote {OUTPUT_PATH} ({len(catalog['tools'])} tools)")


if __name__ == "__main__":
    main()
