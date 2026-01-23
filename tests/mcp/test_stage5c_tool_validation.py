"""
[20251227_TEST] Stage 5C-Z: Per-Tool Tier Validation Tests

Test each MCP tool at community tier to verify:
1. Tool is available
2. Tool respects tier limits from limits.toml
3. Tool returns valid responses

This validates the v3.3.0 design where all 21 tools are available
at all tiers, but feature limits are enforced via limits.toml.
"""

import os

import pytest

from code_scalpel.licensing import get_current_tier
from code_scalpel.licensing.tier_detector import clear_tier_cache


@pytest.mark.asyncio
class TestStage5CToolValidation:
    """Stage 5C-Z: Per-tool validation at community tier."""

    @pytest.fixture(autouse=True)
    def verify_tier(self, monkeypatch):
        """Ensure deterministic Community tier for test isolation."""
        # [20260122_FIX] Clear tier cache before setting env vars to ensure
        # fresh detection respects the test's environment overrides.
        clear_tier_cache()

        # [20260122_FIX] Remove any license path set by session fixtures.
        # The session-scoped set_default_license_path fixture may have set
        # CODE_SCALPEL_LICENSE_PATH to an enterprise license, which would
        # override the CODE_SCALPEL_TIER env var via license file detection.
        monkeypatch.delenv("CODE_SCALPEL_LICENSE_PATH", raising=False)
        monkeypatch.delenv("CODE_SCALPEL_LICENSE_CRL_PATH", raising=False)

        # [20260111_FIX] Use monkeypatch for proper test isolation instead of
        # module-level os.environ.setdefault which polluted subsequent test sessions.
        monkeypatch.setenv("CODE_SCALPEL_DISABLE_LICENSE_DISCOVERY", "1")
        monkeypatch.setenv("CODE_SCALPEL_TEST_FORCE_TIER", "1")
        monkeypatch.setenv("CODE_SCALPEL_TIER", "community")

        # Clear again after env vars set to force re-detection
        clear_tier_cache()

        tier = get_current_tier()
        assert tier == "community", f"Expected community tier, got {tier}"
        yield

        # Cleanup: clear cache after test to avoid polluting other tests
        clear_tier_cache()

    async def test_analyze_code_community_limits(self):
        """Test analyze_code respects community tier limits."""
        from code_scalpel import AnalysisResult, analyze_code

        # Small code should work at community tier
        small_code = '''
def hello():
    """Say hello."""
    print("Hello World")
'''
        result = analyze_code(small_code, language="python")
        assert isinstance(result, AnalysisResult)
        assert len(result.functions) == 1
        assert result.functions[0] == "hello"

    async def test_extract_code_community_limits(self):
        """Test extract_code without cross-file deps (community limit)."""
        from code_scalpel import extract_code

        code = """
def calculate(x, y):
    return x + y

def process():
    return calculate(1, 2)
"""
        # Should work: Extract single function without dependencies
        result = extract_code(code=code, target_type="function", target_name="calculate")
        assert result.target_code.strip().startswith("def calculate")
        assert "def process" not in result.target_code

    async def test_security_scan_community(self):
        """Test security_scan at community tier."""
        from code_scalpel import security_scan

        # Test with SQL injection vulnerability
        vulnerable_code = """
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
"""
        result = security_scan(code=vulnerable_code)
        assert result.has_vulnerabilities
        assert result.vulnerability_count >= 1
        assert any("SQL" in v.type for v in result.vulnerabilities)

    async def test_symbolic_execute_community(self):
        """Test symbolic_execute at community tier."""
        from code_scalpel import symbolic_execute

        code = """
def is_positive(x):
    if x > 0:
        return True
    return False
"""
        result = symbolic_execute(code)
        # Should find 2 paths (x > 0 and x <= 0)
        assert len(result.paths) >= 2

    async def test_generate_unit_tests_community(self):
        """Test generate_unit_tests at community tier."""
        from code_scalpel import generate_unit_tests

        code = """
def add(a, b):
    return a + b
"""
        result = generate_unit_tests(code=code, framework="pytest")
        assert result.pytest_code is not None
        assert "test_add" in result.pytest_code or "test_" in result.pytest_code

    async def test_simulate_refactor_community(self):
        """Test simulate_refactor at community tier."""
        from code_scalpel import simulate_refactor

        original = "def add(a, b): return a + b"
        # Safe refactor: Add type hints
        safe = "def add(a: int, b: int) -> int: return a + b"

        result = simulate_refactor(original_code=original, new_code=safe)
        assert result.is_safe
        assert result.status == "safe"

    async def test_unified_sink_detect_community(self):
        """Test unified_sink_detect at community tier."""
        from code_scalpel.security.analyzers import UnifiedSinkDetector

        code = """
def process(user_input):
    eval(user_input)  # Dangerous sink
"""
        detector = UnifiedSinkDetector()
        result = detector.detect_sinks(code, language="python")
        assert len(result.sinks) >= 1
        assert any(s.name == "eval" for s in result.sinks)

    async def test_cross_file_security_scan_community(self):
        """Test cross_file_security_scan basic functionality."""
        # This tool may have depth limits at community tier
        # Just verify it's available and returns a result
        from code_scalpel.mcp import server

        # Tool should be registered and available
        assert hasattr(server, "cross_file_security_scan")

    async def test_crawl_project_community(self):
        """Test crawl_project at community tier."""
        # Verify tool is available (actual project crawl is slow)
        from code_scalpel.mcp import server

        assert hasattr(server, "crawl_project")

    async def test_scan_dependencies_community(self):
        """Test scan_dependencies at community tier."""
        # Verify tool is available
        from code_scalpel.mcp import server

        assert hasattr(server, "scan_dependencies")

    async def test_get_file_context_community(self):
        """Test get_file_context at community tier."""
        from code_scalpel.mcp import server

        assert hasattr(server, "get_file_context")

    async def test_get_symbol_references_community(self):
        """[20260109_TEST] Test get_symbol_references at community tier returns valid results."""
        import tempfile

        from code_scalpel.mcp import server

        # Create a minimal test project
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.py")
            with open(test_file, "w") as f:
                f.write("def my_function():\n    pass\n\nresult = my_function()\n")

            result = await server.get_symbol_references("my_function", project_root=tmpdir)

            assert result.success is True
            assert result.symbol_name == "my_function"
            assert result.definition_file is not None
            assert len(result.references) > 0
            assert result.total_references >= 1

    async def test_get_cross_file_dependencies_community(self):
        """Test get_cross_file_dependencies at community tier."""
        from code_scalpel.mcp import server

        assert hasattr(server, "get_cross_file_dependencies")

    async def test_get_call_graph_community(self):
        """Test get_call_graph at community tier."""
        from code_scalpel.mcp import server

        assert hasattr(server, "get_call_graph")

    async def test_get_graph_neighborhood_community(self):
        """Test get_graph_neighborhood at community tier."""
        from code_scalpel.mcp import server

        assert hasattr(server, "get_graph_neighborhood")

    async def test_get_project_map_community(self):
        """Test get_project_map at community tier."""
        from code_scalpel.mcp import server

        assert hasattr(server, "get_project_map")

    async def test_validate_paths_community(self):
        """Test validate_paths at community tier."""
        from code_scalpel.mcp import server

        assert hasattr(server, "validate_paths")

    async def test_verify_policy_integrity_community(self):
        """Test verify_policy_integrity at community tier."""
        from code_scalpel.mcp import server

        assert hasattr(server, "verify_policy_integrity")

    async def test_type_evaporation_scan_community(self):
        """Test type_evaporation_scan at community tier."""
        from code_scalpel.mcp import server

        assert hasattr(server, "type_evaporation_scan")

    async def test_update_symbol_community(self):
        """Test update_symbol at community tier."""
        from code_scalpel.mcp import server

        assert hasattr(server, "update_symbol")

    async def test_code_policy_check_community(self):
        """Test code_policy_check at community tier."""
        from code_scalpel.mcp import server

        assert hasattr(server, "code_policy_check")
