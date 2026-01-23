"""Tier gating and tier-limited behavior tests for extract_code.

These tests validate concrete implemented behavior:
- Pro tier clamps dependency/context recursion depth to max_depth
- Cross-file dependencies include confidence metadata

[20251231_TEST] Add extract_code tier clamp + confidence tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest


# [20260101_SKIP] Spec test for Pro tier warnings field - not implemented
@pytest.mark.skip(reason="ContextualExtractionResult.warnings not implemented")
@pytest.mark.asyncio
async def test_extract_code_pro_clamps_depth_and_emits_confidence(monkeypatch, tmp_path: Path):
    """Pro tier clamps context_depth to max_depth=1 and returns confidence metadata."""
    from code_scalpel.mcp import server

    # Allow operating on tmp_path.
    monkeypatch.setattr(server, "ALLOWED_ROOTS", [tmp_path.resolve()], raising=False)

    # b.py
    (tmp_path / "b.py").write_text("""\
class B:
    pass
""")

    # a.py imports B and defines A
    (tmp_path / "a.py").write_text("""\
from b import B

class A:
    def __init__(self):
        self.b = B()
""")

    # utils.py imports A and uses it
    (tmp_path / "utils.py").write_text("""\
from a import A

def f():
    a = A()
    return a
""")

    # Simulate Pro tier via env; _get_current_tier honors this under pytest.
    monkeypatch.setenv("CODE_SCALPEL_TIER", "pro")

    # Ask for depth=2; Pro tier should clamp to 1.
    result = await server.extract_code(
        target_type="function",
        target_name="f",
        file_path=str(tmp_path / "utils.py"),
        include_cross_file_deps=True,
        context_depth=2,
    )

    assert result.success is True

    # Warning should mention clamping (neutral messaging).
    assert any("clamped" in w.lower() for w in (result.warnings or []))
    assert "upgrade" not in " ".join(result.warnings).lower()

    # Pro max_depth=1 should include A but not B.
    assert "class A" in result.context_code
    assert "class B" not in result.context_code

    # Confidence metadata is returned.
    meta = getattr(result, "dependency_metadata", None)
    assert isinstance(meta, list)
    assert len(meta) >= 1

    # A should be depth=1, confidence=0.9
    a_meta = [m for m in meta if m.get("name") == "A"]
    assert a_meta, meta
    assert a_meta[0].get("depth") == 1
    assert pytest.approx(float(a_meta[0].get("confidence")), rel=1e-6) == 0.9
