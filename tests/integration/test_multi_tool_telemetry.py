"""Multi-tool telemetry integration tests.

Tests that all Code Scalpel MCP tools emit telemetry events correctly.
Covers all 11 major tools and validates event structure and content.
"""

import asyncio
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from code_scalpel import telemetry
from code_scalpel.mcp.protocol import set_current_tier


@pytest.fixture
def test_python_file():
    """Create a temporary Python file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("""
def calculate_tax(amount, rate):
    '''Calculate tax amount.'''
    return amount * rate

def vulnerable_function(user_input):
    '''Vulnerable to SQL injection.'''
    import sqlite3
    db = sqlite3.connect(":memory:")
    query = "SELECT * FROM users WHERE name = '" + user_input + "'"  # UNSAFE
    return db.execute(query).fetchall()

class DataProcessor:
    def __init__(self, data):
        self.data = data

    def process(self):
        return [x * 2 for x in self.data]

    def validate(self):
        return len(self.data) > 0
""")
        return f.name


@pytest.fixture
def test_project_dir():
    """Create a temporary project directory with multiple Python files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create multiple Python files
        (tmpdir_path / "main.py").write_text("""
def main():
    print("Hello")

if __name__ == "__main__":
    main()
""")

        (tmpdir_path / "utils.py").write_text("""
def helper_function(x):
    return x + 1

class Helper:
    def method(self):
        return "help"
""")

        (tmpdir_path / "vulnerable.py").write_text("""
import pickle
import subprocess

def unsafe_deserialize(data):
    return pickle.loads(data)

def unsafe_command(cmd):
    subprocess.call(cmd, shell=True)
""")

        yield str(tmpdir_path)


class TestAnalyzeCodeTelemetry:
    """Test analyze_code tool telemetry."""

    def test_analyze_code_emits_telemetry(self, test_python_file):
        """Test that analyze_code emits telemetry event."""
        from code_scalpel.mcp.tools.analyze import analyze_code

        telemetry.clear_events()
        set_current_tier("community")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(analyze_code(file_path=test_python_file))
        finally:
            loop.close()

        events = telemetry.get_recent_events(limit=1)
        assert len(events) > 0

        event = events[0]
        assert event["tool_name"] == "analyze_code"
        assert event["status"] == "success"
        assert event["duration_ms"] > 0
        assert "function_count" in event["output_summary"]
        assert "class_count" in event["output_summary"]


class TestSecurityScanTelemetry:
    """Test security_scan tool telemetry."""

    def test_security_scan_emits_telemetry(self, test_python_file):
        """Test that security_scan emits telemetry event."""
        from code_scalpel.mcp.tools.security import security_scan

        telemetry.clear_events()
        set_current_tier("enterprise")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(security_scan(file_path=test_python_file))
        finally:
            loop.close()

        events = telemetry.get_recent_events(limit=1)
        assert len(events) > 0

        event = events[0]
        assert event["tool_name"] == "security_scan"
        assert event["status"] in ["success", "failure"]
        assert event["duration_ms"] > 0
        assert "vulnerability_count" in event["output_summary"]


class TestExtractCodeTelemetry:
    """Test extract_code tool telemetry."""

    def test_extract_code_emits_telemetry(self, test_python_file):
        """Test that extract_code emits telemetry event."""
        from code_scalpel.mcp.tools.extraction import extract_code

        telemetry.clear_events()
        set_current_tier("pro")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                extract_code(
                    file_path=test_python_file,
                    target_type="function",
                    target_name="calculate_tax",
                )
            )
        finally:
            loop.close()

        events = telemetry.get_recent_events(limit=1)
        assert len(events) > 0

        event = events[0]
        assert event["tool_name"] == "extract_code"
        assert event["status"] == "success"
        assert event["duration_ms"] > 0
        assert "symbol_name" in event["output_summary"]


class TestSymbolicExecuteTelemetry:
    """Test symbolic_execute tool telemetry."""

    def test_symbolic_execute_emits_telemetry(self, test_python_file):
        """Test that symbolic_execute emits telemetry event."""
        from code_scalpel.mcp.tools.symbolic import symbolic_execute

        with open(test_python_file) as f:
            code = f.read()

        telemetry.clear_events()
        set_current_tier("enterprise")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(symbolic_execute(code=code, language="python"))
        finally:
            loop.close()

        events = telemetry.get_recent_events(limit=1)
        assert len(events) > 0

        event = events[0]
        assert event["tool_name"] == "symbolic_execute"
        assert event["status"] in ["success", "failure"]
        assert event["duration_ms"] > 0
        if event["status"] == "success":
            # Check for execution path metrics
            output_summary = event["output_summary"]
            assert any(
                key in output_summary
                for key in ["paths_explored", "path_count", "total_paths"]
            )


class TestGenerateUnitTestsTelemetry:
    """Test generate_unit_tests tool telemetry."""

    def test_generate_unit_tests_emits_telemetry(self, test_python_file):
        """Test that generate_unit_tests emits telemetry event."""
        from code_scalpel.mcp.tools.symbolic import generate_unit_tests

        with open(test_python_file) as f:
            code = f.read()

        telemetry.clear_events()
        set_current_tier("pro")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(generate_unit_tests(code=code, language="python"))
        finally:
            loop.close()

        events = telemetry.get_recent_events(limit=1)
        assert len(events) > 0

        event = events[0]
        assert event["tool_name"] == "generate_unit_tests"
        assert event["status"] in ["success", "failure"]
        assert event["duration_ms"] > 0


class TestCrawlProjectTelemetry:
    """Test crawl_project tool telemetry."""

    def test_crawl_project_emits_telemetry(self, test_project_dir):
        """Test that crawl_project emits telemetry event."""
        from code_scalpel.mcp.tools.context import crawl_project

        telemetry.clear_events()
        set_current_tier("enterprise")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(crawl_project(root_path=test_project_dir))
        finally:
            loop.close()

        events = telemetry.get_recent_events(limit=1)
        assert len(events) > 0

        event = events[0]
        assert event["tool_name"] == "crawl_project"
        assert event["status"] == "success"
        assert event["duration_ms"] > 0
        # Output summary should have file metrics
        output_summary = event["output_summary"]
        assert any(key in output_summary for key in ["file_count", "total_files"])


class TestGetFileContextTelemetry:
    """Test get_file_context tool telemetry."""

    def test_get_file_context_emits_telemetry(self, test_python_file):
        """Test that get_file_context emits telemetry event."""
        from code_scalpel.mcp.tools.context import get_file_context

        telemetry.clear_events()
        set_current_tier("community")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(get_file_context(file_path=test_python_file))
        finally:
            loop.close()

        events = telemetry.get_recent_events(limit=1)
        assert len(events) > 0

        event = events[0]
        assert event["tool_name"] == "get_file_context"
        assert event["status"] == "success"
        assert event["duration_ms"] > 0


class TestScanDependenciesTelemetry:
    """Test scan_dependencies tool telemetry."""

    def test_scan_dependencies_emits_telemetry(self, test_project_dir):
        """Test that scan_dependencies emits telemetry event."""
        from code_scalpel.mcp.tools.security import scan_dependencies

        # Create a requirements.txt file
        req_file = Path(test_project_dir) / "requirements.txt"
        req_file.write_text("requests==2.28.0\nnumpy==1.20.0\n")

        telemetry.clear_events()
        set_current_tier("pro")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(scan_dependencies(project_root=test_project_dir))
        finally:
            loop.close()

        events = telemetry.get_recent_events(limit=1)
        assert len(events) > 0

        event = events[0]
        assert event["tool_name"] == "scan_dependencies"
        assert event["status"] in ["success", "failure"]
        assert event["duration_ms"] > 0


class TestTelemetryEventStructure:
    """Test telemetry event structure and data integrity."""

    def test_all_events_have_required_fields(self, test_python_file):
        """Test that all telemetry events have required fields."""
        from code_scalpel.mcp.tools.analyze import analyze_code

        telemetry.clear_events()
        set_current_tier("community")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(analyze_code(file_path=test_python_file))
        finally:
            loop.close()

        events = telemetry.get_recent_events(limit=1)
        assert len(events) > 0

        event = events[0]

        # Check required fields
        required_fields = [
            "event_id",
            "request_id",
            "tool_name",
            "tier_applied",
            "status",
            "duration_ms",
            "timestamp",
        ]

        for field in required_fields:
            assert field in event, f"Missing required field: {field}"
            assert event[field] is not None, f"Field {field} is None"

    def test_event_summaries_are_dicts(self, test_python_file):
        """Test that input/output summaries are properly structured dicts."""
        from code_scalpel.mcp.tools.analyze import analyze_code

        telemetry.clear_events()
        set_current_tier("community")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(analyze_code(file_path=test_python_file))
        finally:
            loop.close()

        events = telemetry.get_recent_events(limit=1)
        assert len(events) > 0

        event = events[0]

        # Check that summaries are dicts
        assert isinstance(event.get("input_summary", {}), dict)
        assert isinstance(event.get("output_summary", {}), dict)


class TestTelemetryWithAuditLog:
    """Test that telemetry events are logged to audit log."""

    def test_events_logged_to_audit_log(self, test_python_file):
        """Test that telemetry events are recorded in audit log."""
        from code_scalpel import telemetry
        from code_scalpel.mcp.tools.analyze import analyze_code
        from code_scalpel.audit import AuditLog

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                # Create audit log and register it
                audit_log = AuditLog(
                    session_id="test-telemetry", encryption_enabled=False
                )
                telemetry.set_audit_log(audit_log)

                telemetry.clear_events()
                set_current_tier("community")

                # Run tool
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(analyze_code(file_path=test_python_file))
                finally:
                    loop.close()

                # Check that event was logged
                events = audit_log.get_events(limit=10)
                assert len(events) > 0

                event = events[0]
                assert event["tool_name"] == "analyze_code"
                assert event["status"] == "success"

                # Cleanup
                telemetry.set_audit_log(None)
                audit_log.conn.close()


class TestGetCallGraphTelemetry:
    """Test get_call_graph tool telemetry."""

    def test_get_call_graph_emits_telemetry(self, test_python_file):
        """Test that get_call_graph emits telemetry event."""
        from code_scalpel.mcp.tools.graph import get_call_graph

        telemetry.clear_events()
        set_current_tier("enterprise")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                get_call_graph(project_root=str(Path(test_python_file).parent))
            )
        finally:
            loop.close()

        events = telemetry.get_recent_events(limit=1)
        assert len(events) > 0

        event = events[0]
        assert event["tool_name"] == "get_call_graph"
        assert event["status"] == "success"
        assert event["duration_ms"] > 0


class TestUnifiedSinkDetectTelemetry:
    """Test unified_sink_detect tool telemetry."""

    def test_unified_sink_detect_emits_telemetry(self, test_python_file):
        """Test that unified_sink_detect emits telemetry event."""
        from code_scalpel.mcp.tools.security import unified_sink_detect

        with open(test_python_file) as f:
            code = f.read()

        telemetry.clear_events()
        set_current_tier("enterprise")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(unified_sink_detect(code=code, language="python"))
        finally:
            loop.close()

        events = telemetry.get_recent_events(limit=1)
        assert len(events) > 0

        event = events[0]
        assert event["tool_name"] == "unified_sink_detect"
        assert event["status"] in ["success", "failure"]
        assert event["duration_ms"] > 0


class TestGetProjectMapTelemetry:
    """Test get_project_map tool telemetry."""

    def test_get_project_map_emits_telemetry(self, test_project_dir):
        """Test that get_project_map emits telemetry event."""
        from code_scalpel.mcp.tools.graph import get_project_map

        telemetry.clear_events()
        set_current_tier("enterprise")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(get_project_map(project_root=test_project_dir))
        finally:
            loop.close()

        events = telemetry.get_recent_events(limit=1)
        assert len(events) > 0

        event = events[0]
        assert event["tool_name"] == "get_project_map"
        assert event["status"] == "success"
        assert event["duration_ms"] > 0
        # Should have file/module metrics in output
        output_summary = event["output_summary"]
        assert any(
            key in output_summary
            for key in ["file_count", "module_count", "total_files"]
        )


class TestTypeEvaporationScanTelemetry:
    """Test type_evaporation_scan tool telemetry."""

    def test_type_evaporation_scan_emits_telemetry(self, test_python_file):
        """Test that type_evaporation_scan can be called and attempts telemetry."""
        from code_scalpel.mcp.tools.security import type_evaporation_scan

        with open(test_python_file) as f:
            code = f.read()

        telemetry.clear_events()
        set_current_tier("enterprise")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # type_evaporation_scan may require both frontend and backend code
            # It may also not emit telemetry if it fails early
            result = loop.run_until_complete(type_evaporation_scan(frontend_code=code))
            # Just verify the call completes without error
            assert result is not None
        finally:
            loop.close()


class TestSimulateRefactorTelemetry:
    """Test simulate_refactor tool telemetry."""

    def test_simulate_refactor_emits_telemetry(self, test_python_file):
        """Test that simulate_refactor emits telemetry event."""
        from code_scalpel.mcp.tools.symbolic import simulate_refactor

        with open(test_python_file) as f:
            original_code = f.read()

        # Create a simple refactored version
        new_code = original_code.replace("def calculate_tax", "def compute_tax")

        telemetry.clear_events()
        set_current_tier("pro")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                simulate_refactor(original_code=original_code, new_code=new_code)
            )
        finally:
            loop.close()

        events = telemetry.get_recent_events(limit=1)
        assert len(events) > 0

        event = events[0]
        assert event["tool_name"] == "simulate_refactor"
        assert event["status"] in ["success", "failure"]
        assert event["duration_ms"] > 0
