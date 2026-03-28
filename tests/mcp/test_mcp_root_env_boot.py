# [20260311_TEST] Validate MCP --root boot behavior exposes CODE_SCALPEL_PROJECT_ROOT.
import os
from pathlib import Path
from types import SimpleNamespace

from code_scalpel.mcp import server as mcp_server


class _StubMCP:
    def __init__(self):
        self.settings = SimpleNamespace(host=None, port=None, transport_security=None)
        self.run_calls: list[tuple[tuple, dict]] = []

    def run(self, *args, **kwargs):  # noqa: ANN401
        self.run_calls.append((args, kwargs))


def test_run_server_sets_root_env_before_tier_resolution(monkeypatch, tmp_path):
    """[20260311_TEST] Ensure --root is exported before startup tier evaluation."""
    stub = _StubMCP()
    monkeypatch.setattr(mcp_server, "mcp", stub)

    root_dir = tmp_path / "project_root"
    root_dir.mkdir(parents=True, exist_ok=True)
    expected_root = str(root_dir.resolve())

    original_root = mcp_server.get_project_root()
    original_env_root = os.environ.get("CODE_SCALPEL_PROJECT_ROOT")

    def _fake_compute_effective_tier_for_startup(
        *, requested_tier, validator
    ):  # noqa: ARG001
        assert os.environ.get("CODE_SCALPEL_PROJECT_ROOT") == expected_root
        return "community", None

    monkeypatch.setattr(
        mcp_server,
        "compute_effective_tier_for_startup",
        _fake_compute_effective_tier_for_startup,
    )

    try:
        mcp_server.run_server(transport="stdio", root_path=str(root_dir))

        assert stub.run_calls[-1][0] == ()
        assert os.environ.get("CODE_SCALPEL_PROJECT_ROOT") == expected_root
        assert mcp_server.get_project_root() == Path(expected_root)
    finally:
        mcp_server.set_project_root(original_root)
        if original_env_root is None:
            os.environ.pop("CODE_SCALPEL_PROJECT_ROOT", None)
        else:
            os.environ["CODE_SCALPEL_PROJECT_ROOT"] = original_env_root
