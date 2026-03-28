"""Focused Oracle scenario coverage for tools with complete guidance contracts.

[20260311_TEST] Expand beyond one representative error per tool and verify
scenario-complete guidance for the first completed batch of public MCP tools.
"""

from __future__ import annotations

import pytest

from code_scalpel.mcp.validators.core import ValidationError


pytestmark = pytest.mark.asyncio


def _get_error_code(result) -> str | None:
    error = getattr(result, "error", None)
    if error is None:
        return None
    return getattr(error, "error_code", None)


class TestGetCapabilitiesOracleCoverage:
    async def test_invalid_tier_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.system import get_capabilities

        result = await get_capabilities(tier="ultimate")

        assert _get_error_code(result) == "invalid_argument"
        assert result.error.error_details["available_tiers"]

    async def test_unknown_tool_returns_not_found(self):
        from code_scalpel.mcp.tools.system import get_capabilities

        result = await get_capabilities(tool_name="definitely_missing_tool")

        assert _get_error_code(result) == "not_found"
        assert "available_tools" in result.error.error_details


class TestUnifiedSinkDetectOracleCoverage:
    async def test_empty_code_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.security import unified_sink_detect

        result = await unified_sink_detect("   ")

        assert _get_error_code(result) == "invalid_argument"

    async def test_unsupported_language_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.security import unified_sink_detect

        result = await unified_sink_detect("print('hi')", language="elixir")

        assert _get_error_code(result) == "invalid_argument"
        assert "supported_languages" in result.error.error_details

    async def test_out_of_range_threshold_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.security import unified_sink_detect

        result = await unified_sink_detect(
            "print('hi')",
            language="python",
            confidence_threshold=1.5,
        )

        assert _get_error_code(result) == "invalid_argument"
        assert result.error.error_details["confidence_threshold"] == 1.5


class TestSymbolicExecuteOracleCoverage:
    async def test_empty_code_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.symbolic import symbolic_execute

        result = await symbolic_execute("   ")

        assert _get_error_code(result) == "invalid_argument"

    async def test_unsupported_language_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.symbolic import symbolic_execute

        result = await symbolic_execute("def demo(x):\n    return x\n", language="ruby")

        assert _get_error_code(result) == "invalid_argument"
        assert "supported_languages" in result.error.error_details

    async def test_invalid_max_paths_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.symbolic import symbolic_execute

        result = await symbolic_execute(
            "def demo(x):\n    return x\n",
            max_paths=0,
        )

        assert _get_error_code(result) == "invalid_argument"

    async def test_internal_helper_failure_returns_internal_error(self, monkeypatch):
        from code_scalpel.mcp.tools import symbolic as symbolic_module
        from code_scalpel.mcp.tools.symbolic import symbolic_execute

        monkeypatch.setattr(
            symbolic_module.sym_helpers,
            "_symbolic_execute_sync",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
        )

        result = await symbolic_execute("def demo(x):\n    return x\n")

        assert _get_error_code(result) == "internal_error"


class TestSimulateRefactorOracleCoverage:
    async def test_missing_new_code_and_patch_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.symbolic import simulate_refactor

        result = await simulate_refactor("def demo():\n    return 1\n")

        assert _get_error_code(result) == "invalid_argument"

    async def test_both_new_code_and_patch_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.symbolic import simulate_refactor

        result = await simulate_refactor(
            "def demo():\n    return 1\n",
            new_code="def demo():\n    return 2\n",
            patch="@@\n-1\n+2",
        )

        assert _get_error_code(result) == "invalid_argument"
        assert result.error.error_details["new_code_provided"] is True
        assert result.error.error_details["patch_provided"] is True

    async def test_internal_helper_failure_returns_internal_error(self, monkeypatch):
        from code_scalpel.mcp.tools import symbolic as symbolic_module
        from code_scalpel.mcp.tools.symbolic import simulate_refactor

        monkeypatch.setattr(
            symbolic_module.sym_helpers,
            "_simulate_refactor_sync",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
        )

        result = await simulate_refactor(
            "def demo():\n    return 1\n",
            new_code="def demo():\n    return 2\n",
        )

        assert _get_error_code(result) == "internal_error"


class TestGetGraphNeighborhoodOracleCoverage:
    async def test_invalid_node_id_returns_correction_needed(self):
        from code_scalpel.mcp.tools.graph import get_graph_neighborhood

        result = await get_graph_neighborhood(center_node_id="invalid")

        assert _get_error_code(result) == "correction_needed"


class TestAnalyzeCodeOracleCoverage:
    async def test_missing_input_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.analyze import analyze_code

        result = await analyze_code()

        assert _get_error_code(result) == "invalid_argument"

    async def test_unsupported_language_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.analyze import analyze_code

        result = await analyze_code(code="print('hi')", language="elixir")

        assert _get_error_code(result) == "invalid_argument"
        assert "supported_languages" in result.error.error_details

    async def test_static_tools_without_file_path_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.analyze import analyze_code

        result = await analyze_code(code="int main() { return 0; }", static_tools=["cppcheck"])

        assert _get_error_code(result) == "invalid_argument"

    async def test_invalid_file_path_returns_correction_needed(self, monkeypatch):
        from code_scalpel.mcp.tools import analyze as analyze_module
        from code_scalpel.mcp.tools.analyze import analyze_code

        resolver_error = FileNotFoundError("Cannot access file: /K:/repo/missing.py")
        monkeypatch.setattr(
            analyze_module,
            "resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await analyze_code(file_path="/K:/repo/missing.py")

        assert _get_error_code(result) == "correction_needed"


class TestSecurityScanOracleCoverage:
    async def test_missing_input_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.security import security_scan

        result = await security_scan()

        assert _get_error_code(result) == "invalid_argument"

    async def test_invalid_threshold_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.security import security_scan

        result = await security_scan(code="print('hi')", confidence_threshold=2.0)

        assert _get_error_code(result) == "invalid_argument"
        assert result.error.error_details["confidence_threshold"] == 2.0

    async def test_invalid_file_path_returns_correction_needed(self, monkeypatch):
        from code_scalpel.mcp.tools import security as security_module
        from code_scalpel.mcp.tools.security import security_scan

        resolver_error = FileNotFoundError("Cannot access file: /K:/repo/vuln.py")
        monkeypatch.setattr(
            security_module,
            "resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await security_scan(file_path="/K:/repo/vuln.py")

        assert _get_error_code(result) == "correction_needed"


class TestTypeEvaporationScanOracleCoverage:
    async def test_missing_frontend_input_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.security import type_evaporation_scan

        result = await type_evaporation_scan(backend_code="def handler():\n    return 1\n")

        assert _get_error_code(result) == "invalid_argument"

    async def test_missing_backend_input_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.security import type_evaporation_scan

        result = await type_evaporation_scan(frontend_code="const value = 1;")

        assert _get_error_code(result) == "invalid_argument"

    async def test_invalid_frontend_file_path_returns_correction_needed(self, monkeypatch):
        from code_scalpel.mcp.tools import security as security_module
        from code_scalpel.mcp.tools.security import type_evaporation_scan

        resolver_error = FileNotFoundError("Cannot access file: /K:/repo/frontend.ts")
        monkeypatch.setattr(
            security_module,
            "resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await type_evaporation_scan(
            frontend_file_path="/K:/repo/frontend.ts",
            backend_code="def handler():\n    return 1\n",
        )

        assert _get_error_code(result) == "correction_needed"


class TestScanDependenciesOracleCoverage:
    async def test_invalid_timeout_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.security import scan_dependencies

        result = await scan_dependencies(timeout=0)

        assert _get_error_code(result) == "invalid_argument"
        assert result.error.error_details["timeout"] == 0

    async def test_invalid_path_returns_correction_needed(self, monkeypatch):
        from code_scalpel.mcp.tools import security as security_module
        from code_scalpel.mcp.tools.security import scan_dependencies

        resolver_error = FileNotFoundError("Cannot access file: /K:/repo")
        monkeypatch.setattr(
            security_module,
            "resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await scan_dependencies(path="/K:/repo")

        assert _get_error_code(result) == "correction_needed"


class TestGenerateUnitTestsOracleCoverage:
    async def test_missing_input_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.symbolic import generate_unit_tests

        result = await generate_unit_tests()

        assert _get_error_code(result) == "invalid_argument"

    async def test_unsupported_language_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.symbolic import generate_unit_tests

        result = await generate_unit_tests(code="def demo():\n    return 1\n", language="ruby")

        assert _get_error_code(result) == "invalid_argument"

    async def test_unsupported_framework_returns_invalid_argument(self, monkeypatch):
        from code_scalpel.mcp.tools import symbolic as symbolic_module
        from code_scalpel.mcp.tools.symbolic import generate_unit_tests

        monkeypatch.setattr(
            symbolic_module.feature_caps,
            "get_tool_capabilities",
            lambda tool_name, tier: {
                "limits": {"max_test_cases": 10, "test_frameworks": ["pytest"]},
                "capabilities": set(),
            },
        )

        result = await generate_unit_tests(
            code="def demo():\n    return 1\n",
            framework="nose",
        )

        assert _get_error_code(result) == "invalid_argument"

    async def test_data_driven_requires_upgrade(self, monkeypatch):
        from code_scalpel.mcp.tools import symbolic as symbolic_module
        from code_scalpel.mcp.tools.symbolic import generate_unit_tests

        monkeypatch.setattr(
            symbolic_module.feature_caps,
            "get_tool_capabilities",
            lambda tool_name, tier: {
                "limits": {"max_test_cases": 10, "test_frameworks": ["pytest"]},
                "capabilities": set(),
            },
        )

        result = await generate_unit_tests(
            code="def demo():\n    return 1\n",
            data_driven=True,
        )

        assert _get_error_code(result) == "upgrade_required"

    async def test_invalid_file_path_returns_correction_needed(self, monkeypatch):
        from code_scalpel.mcp.tools import symbolic as symbolic_module
        from code_scalpel.mcp.tools.symbolic import generate_unit_tests

        resolver_error = FileNotFoundError("Cannot access file: /K:/repo/sample.py")
        monkeypatch.setattr(
            symbolic_module,
            "resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await generate_unit_tests(file_path="/K:/repo/sample.py")

        assert _get_error_code(result) == "correction_needed"

    async def test_missing_function_name_returns_correction_needed(self, monkeypatch):
        from code_scalpel.mcp.tools import symbolic as symbolic_module
        from code_scalpel.mcp.tools.symbolic import generate_unit_tests

        def fake_generate(*args, **kwargs):
            raise ValidationError("Function 'missing_function' not found.")

        monkeypatch.setattr(
            symbolic_module.sym_helpers,
            "_generate_tests_sync",
            fake_generate,
        )

        result = await generate_unit_tests(
            code="def real_function():\n    return 1\n",
            function_name="missing_function",
        )

        assert _get_error_code(result) == "correction_needed"

    async def test_invalid_direction_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.graph import get_graph_neighborhood

        result = await get_graph_neighborhood(
            center_node_id="python::app.main::function::main",
            direction="sideways",
        )

        assert _get_error_code(result) == "invalid_argument"
        assert result.error.error_details["direction"] == "sideways"

    async def test_invalid_project_root_returns_correction_needed(self, monkeypatch):
        from code_scalpel.mcp.tools import graph as graph_module
        from code_scalpel.mcp.tools.graph import get_graph_neighborhood

        resolver_error = FileNotFoundError(
            "Cannot access file: /K:/repo/sample (not found)\n\nSuggestion:\n  /mnt/k/repo/sample"
        )
        monkeypatch.setattr(
            graph_module,
            "resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await get_graph_neighborhood(
            center_node_id="python::app.main::function::main",
            project_root="/K:/repo/sample",
        )

        assert _get_error_code(result) == "correction_needed"


class TestExtractCodeOracleCoverage:
    async def test_missing_input_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.extraction import extract_code

        result = await extract_code(target_type="function", target_name="demo")

        assert _get_error_code(result) == "invalid_argument"

    async def test_invalid_target_type_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.extraction import extract_code

        result = await extract_code(
            target_type="variable",
            target_name="demo",
            code="x = 1\n",
        )

        assert _get_error_code(result) == "invalid_argument"
        assert result.error.error_details["target_type"] == "variable"

    async def test_invalid_file_path_returns_correction_needed(self, monkeypatch):
        from code_scalpel.mcp.tools import extraction as extraction_module
        from code_scalpel.mcp.tools.extraction import extract_code

        resolver_error = FileNotFoundError("Cannot access file: /K:/repo/missing.py")
        monkeypatch.setattr(
            extraction_module,
            "resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await extract_code(
            target_type="function",
            target_name="demo",
            file_path="/K:/repo/missing.py",
        )

        assert _get_error_code(result) == "correction_needed"

    async def test_missing_symbol_returns_correction_needed(self, monkeypatch):
        from code_scalpel.mcp.tools import extraction as extraction_module
        from code_scalpel.mcp.tools.extraction import extract_code

        async def fake_extract(*args, **kwargs):
            raise ValidationError("Symbol 'process_dta' not found.")

        monkeypatch.setattr(extraction_module, "_extract_code", fake_extract)

        result = await extract_code(
            target_type="function",
            target_name="process_dta",
            code="def process_data():\n    return 1\n",
        )

        assert _get_error_code(result) == "correction_needed"


class TestRenameSymbolOracleCoverage:
    async def test_invalid_target_type_returns_invalid_argument(self, tmp_path):
        from code_scalpel.mcp.tools.extraction import rename_symbol

        source_file = tmp_path / "sample.py"
        source_file.write_text("def process_data():\n    return 1\n", encoding="utf-8")

        result = await rename_symbol(
            file_path=str(source_file),
            target_type="variable",
            target_name="process_data",
            new_name="process_item",
        )

        assert _get_error_code(result) == "invalid_argument"

    async def test_empty_new_name_returns_invalid_argument(self, tmp_path):
        from code_scalpel.mcp.tools.extraction import rename_symbol

        source_file = tmp_path / "sample.py"
        source_file.write_text("def process_data():\n    return 1\n", encoding="utf-8")

        result = await rename_symbol(
            file_path=str(source_file),
            target_type="function",
            target_name="process_data",
            new_name="   ",
        )

        assert _get_error_code(result) == "invalid_argument"

    async def test_invalid_file_path_returns_correction_needed(self, monkeypatch):
        from code_scalpel.mcp.tools import extraction as extraction_module
        from code_scalpel.mcp.tools.extraction import rename_symbol

        resolver_error = FileNotFoundError("Cannot access file: /K:/repo/sample.py")
        monkeypatch.setattr(
            extraction_module,
            "resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await rename_symbol(
            file_path="/K:/repo/sample.py",
            target_type="function",
            target_name="process_data",
            new_name="process_item",
        )

        assert _get_error_code(result) == "correction_needed"

    async def test_missing_symbol_returns_correction_needed(self, monkeypatch, tmp_path):
        from code_scalpel.mcp.tools import extraction as extraction_module
        from code_scalpel.mcp.tools.extraction import rename_symbol

        source_file = tmp_path / "sample.py"
        source_file.write_text("def process_data():\n    return 1\n", encoding="utf-8")

        async def fake_rename(*args, **kwargs):
            raise ValidationError("Symbol 'process_dta' not found.")

        monkeypatch.setattr(extraction_module, "_rename_symbol", fake_rename)

        result = await rename_symbol(
            file_path=str(source_file),
            target_type="function",
            target_name="process_dta",
            new_name="process_item",
        )

        assert _get_error_code(result) == "correction_needed"


class TestUpdateSymbolOracleCoverage:
    async def test_invalid_operation_returns_invalid_argument(self, tmp_path):
        from code_scalpel.mcp.tools.extraction import update_symbol

        source_file = tmp_path / "sample.py"
        source_file.write_text("def process_data():\n    return 1\n", encoding="utf-8")

        result = await update_symbol(
            file_path=str(source_file),
            target_type="function",
            target_name="process_data",
            operation="delete",
            new_code="def process_data():\n    return 2\n",
        )

        assert _get_error_code(result) == "invalid_argument"

    async def test_missing_new_code_returns_invalid_argument(self, tmp_path):
        from code_scalpel.mcp.tools.extraction import update_symbol

        source_file = tmp_path / "sample.py"
        source_file.write_text("def process_data():\n    return 1\n", encoding="utf-8")

        result = await update_symbol(
            file_path=str(source_file),
            target_type="function",
            target_name="process_data",
            new_code="   ",
        )

        assert _get_error_code(result) == "invalid_argument"

    async def test_invalid_file_path_returns_correction_needed(self, monkeypatch):
        from code_scalpel.mcp.tools import extraction as extraction_module
        from code_scalpel.mcp.tools.extraction import update_symbol

        resolver_error = FileNotFoundError("Cannot access file: /K:/repo/sample.py")
        monkeypatch.setattr(
            extraction_module,
            "resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await update_symbol(
            file_path="/K:/repo/sample.py",
            target_type="function",
            target_name="process_data",
            new_code="def process_data():\n    return 2\n",
        )

        assert _get_error_code(result) == "correction_needed"

    async def test_missing_symbol_returns_correction_needed(self, monkeypatch, tmp_path):
        from code_scalpel.mcp.tools import extraction as extraction_module
        from code_scalpel.mcp.tools.extraction import update_symbol

        source_file = tmp_path / "sample.py"
        source_file.write_text("def process_data():\n    return 1\n", encoding="utf-8")

        async def fake_update(*args, **kwargs):
            raise ValidationError("Symbol 'process_dta' not found.")

        monkeypatch.setattr(extraction_module, "_update_symbol", fake_update)

        result = await update_symbol(
            file_path=str(source_file),
            target_type="function",
            target_name="process_dta",
            new_code="def process_data():\n    return 2\n",
        )

        assert _get_error_code(result) == "correction_needed"


class TestCrawlProjectOracleCoverage:
    async def test_invalid_complexity_threshold_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.context import crawl_project

        result = await crawl_project(complexity_threshold=0)

        assert _get_error_code(result) == "invalid_argument"
        assert result.error.error_details["complexity_threshold"] == 0

    async def test_invalid_pattern_type_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.context import crawl_project

        result = await crawl_project(pattern="*.py", pattern_type="contains")

        assert _get_error_code(result) == "invalid_argument"
        assert result.error.error_details["pattern_type"] == "contains"

    async def test_invalid_root_path_returns_correction_needed(self, monkeypatch):
        from code_scalpel.mcp.tools import context as context_module
        from code_scalpel.mcp.tools.context import crawl_project

        resolver_error = FileNotFoundError("Cannot access file: /K:/repo")
        monkeypatch.setattr(
            context_module,
            "resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await crawl_project(root_path="/K:/repo")

        assert _get_error_code(result) == "correction_needed"


class TestGetFileContextOracleCoverage:
    async def test_invalid_file_path_returns_correction_needed(self, monkeypatch):
        from code_scalpel.mcp.tools import context as context_module
        from code_scalpel.mcp.tools.context import get_file_context

        resolver_error = FileNotFoundError("Cannot access file: /K:/repo/sample.py")
        monkeypatch.setattr(
            context_module,
            "resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await get_file_context(file_path="/K:/repo/sample.py")

        assert _get_error_code(result) == "correction_needed"

    async def test_unsupported_extension_stays_tool_level_failure(self, tmp_path):
        from code_scalpel.mcp.tools.context import get_file_context

        source_file = tmp_path / "sample.xyz"
        source_file.write_text("plain text\n", encoding="utf-8")

        result = await get_file_context(file_path=str(source_file))

        # The path is valid, so Oracle should not rewrite this into a path correction.
        assert _get_error_code(result) is None
        assert isinstance(result.error, str)
        assert "Unsupported language 'unknown'" in result.error

    async def test_missing_file_path_prefers_oracle_correction_over_tool_failure(self, tmp_path):
        from code_scalpel.mcp.tools.context import get_file_context

        existing = tmp_path / "worker.py"
        existing.write_text("def run():\n    return 1\n", encoding="utf-8")

        result = await get_file_context(file_path=str(tmp_path / "worker_typo.py"))

        assert _get_error_code(result) == "correction_needed"

    async def test_internal_helper_failure_returns_internal_error(self, monkeypatch, tmp_path):
        from code_scalpel.mcp.tools import context as context_module
        from code_scalpel.mcp.tools.context import get_file_context

        source_file = tmp_path / "sample.py"
        source_file.write_text("def demo():\n    return 1\n", encoding="utf-8")
        monkeypatch.setattr(context_module, "resolve_path", lambda path: str(source_file))

        async def fake_get_file_context(file_path: str):
            raise RuntimeError("boom")

        monkeypatch.setattr(context_module, "_get_file_context", fake_get_file_context)

        result = await get_file_context(file_path=str(source_file))

        assert _get_error_code(result) == "internal_error"


class TestGetSymbolReferencesOracleCoverage:
    async def test_empty_symbol_name_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.context import get_symbol_references

        result = await get_symbol_references(symbol_name="   ")

        assert _get_error_code(result) == "invalid_argument"

    async def test_invalid_project_root_returns_correction_needed(self, monkeypatch):
        from code_scalpel.mcp.tools import context as context_module
        from code_scalpel.mcp.tools.context import get_symbol_references

        resolver_error = FileNotFoundError("Cannot access file: /K:/repo")
        monkeypatch.setattr(
            context_module,
            "resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await get_symbol_references(symbol_name="helper", project_root="/K:/repo")

        assert _get_error_code(result) == "correction_needed"

    async def test_absent_symbol_returns_empty_successful_lookup(self, tmp_path):
        from code_scalpel.mcp.tools.context import get_symbol_references

        source_file = tmp_path / "sample.py"
        source_file.write_text("def real_function():\n    return 1\n", encoding="utf-8")

        result = await get_symbol_references(
            symbol_name="missing_function",
            project_root=str(tmp_path),
        )

        assert _get_error_code(result) is None
        assert result.data["success"] is True
        assert result.data["total_references"] == 0


class TestGetCallGraphOracleCoverage:
    async def test_invalid_depth_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.graph import get_call_graph

        result = await get_call_graph(depth=0)

        assert _get_error_code(result) == "invalid_argument"
        assert result.error.error_details["depth"] == 0

    async def test_partial_path_query_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.graph import get_call_graph

        result = await get_call_graph(paths_from="api:entry")

        assert _get_error_code(result) == "invalid_argument"

    async def test_invalid_project_root_returns_correction_needed(self, monkeypatch):
        from code_scalpel.mcp.tools import graph as graph_module
        from code_scalpel.mcp.tools.graph import get_call_graph

        resolver_error = FileNotFoundError("Cannot access file: /K:/repo")
        monkeypatch.setattr(
            graph_module,
            "resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await get_call_graph(project_root="/K:/repo")

        assert _get_error_code(result) == "correction_needed"


class TestGetProjectMapOracleCoverage:
    async def test_invalid_complexity_threshold_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.graph import get_project_map

        result = await get_project_map(complexity_threshold=0)

        assert _get_error_code(result) == "invalid_argument"

    async def test_invalid_min_isolation_score_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.graph import get_project_map

        result = await get_project_map(min_isolation_score=1.5)

        assert _get_error_code(result) == "invalid_argument"
        assert result.error.error_details["min_isolation_score"] == 1.5

    async def test_invalid_project_root_returns_correction_needed(self, monkeypatch):
        from code_scalpel.mcp.tools import graph as graph_module
        from code_scalpel.mcp.tools.graph import get_project_map

        resolver_error = FileNotFoundError("Cannot access file: /K:/repo")
        monkeypatch.setattr(
            graph_module,
            "resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await get_project_map(project_root="/K:/repo")

        assert _get_error_code(result) == "correction_needed"

    async def test_missing_project_root_prefers_oracle_correction(self, tmp_path):
        from code_scalpel.mcp.tools.graph import get_project_map

        existing = tmp_path / "project"
        existing.mkdir()
        (existing / "main.py").write_text("def main():\n    return 1\n", encoding="utf-8")

        result = await get_project_map(project_root=str(tmp_path / "projec"))

        assert _get_error_code(result) == "correction_needed"

    async def test_valid_unsupported_language_project_remains_conservative_noop(self, tmp_path):
        from code_scalpel.mcp.tools.graph import get_project_map

        (tmp_path / "Worker.kt").write_text(
            "class Worker {\n    fun run() {}\n}\n",
            encoding="utf-8",
        )

        result = await get_project_map(project_root=str(tmp_path))

        assert _get_error_code(result) is None
        project_map = getattr(result, "data", result)
        if isinstance(project_map, dict):
            assert project_map["success"] is True
            assert project_map["total_files"] == 0
            assert project_map["languages"] == {}
        else:
            assert project_map.success is True
            assert project_map.total_files == 0
            assert project_map.languages == {}


class TestGetCrossFileDependenciesOracleCoverage:
    async def test_empty_target_symbol_returns_invalid_argument(self, tmp_path):
        from code_scalpel.mcp.tools.graph import get_cross_file_dependencies

        source_file = tmp_path / "sample.py"
        source_file.write_text("def demo():\n    return 1\n", encoding="utf-8")

        result = await get_cross_file_dependencies(
            target_file=str(source_file),
            target_symbol="   ",
        )

        assert _get_error_code(result) == "invalid_argument"

    async def test_invalid_confidence_decay_factor_returns_invalid_argument(self, tmp_path):
        from code_scalpel.mcp.tools.graph import get_cross_file_dependencies

        source_file = tmp_path / "sample.py"
        source_file.write_text("def demo():\n    return 1\n", encoding="utf-8")

        result = await get_cross_file_dependencies(
            target_file=str(source_file),
            target_symbol="demo",
            confidence_decay_factor=1.2,
        )

        assert _get_error_code(result) == "invalid_argument"
        assert result.error.error_details["confidence_decay_factor"] == 1.2

    async def test_invalid_target_file_returns_correction_needed(self, monkeypatch):
        from code_scalpel.mcp.tools import graph as graph_module
        from code_scalpel.mcp.tools.graph import get_cross_file_dependencies

        resolver_error = FileNotFoundError("Cannot access file: /K:/repo/sample.py")
        monkeypatch.setattr(
            graph_module,
            "resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await get_cross_file_dependencies(
            target_file="/K:/repo/sample.py",
            target_symbol="demo",
        )

        assert _get_error_code(result) == "correction_needed"


class TestCrossFileSecurityScanOracleCoverage:
    async def test_invalid_max_depth_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.graph import cross_file_security_scan

        result = await cross_file_security_scan(max_depth=0)

        assert _get_error_code(result) == "invalid_argument"

    async def test_invalid_confidence_threshold_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.graph import cross_file_security_scan

        result = await cross_file_security_scan(confidence_threshold=1.5)

        assert _get_error_code(result) == "invalid_argument"
        assert result.error.error_details["confidence_threshold"] == 1.5

    async def test_invalid_project_root_returns_correction_needed(self, monkeypatch):
        from code_scalpel.mcp.tools import graph as graph_module
        from code_scalpel.mcp.tools.graph import cross_file_security_scan

        resolver_error = FileNotFoundError("Cannot access file: /K:/repo")
        monkeypatch.setattr(
            graph_module,
            "resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await cross_file_security_scan(project_root="/K:/repo")

        assert _get_error_code(result) == "correction_needed"


class TestValidatePathsOracleCoverage:
    async def test_empty_paths_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.policy import validate_paths

        result = await validate_paths(paths=[])

        assert _get_error_code(result) == "invalid_argument"

    async def test_invalid_project_root_returns_correction_needed(self, monkeypatch):
        from code_scalpel.mcp.tools import policy as policy_module
        from code_scalpel.mcp.tools.policy import validate_paths

        resolver_error = FileNotFoundError("Cannot access file: /K:/repo")
        monkeypatch.setattr(
            policy_module,
            "resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await validate_paths(paths=["src/app.py"], project_root="/K:/repo")

        assert _get_error_code(result) == "correction_needed"


class TestVerifyPolicyIntegrityOracleCoverage:
    async def test_invalid_manifest_source_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.policy import verify_policy_integrity

        result = await verify_policy_integrity(manifest_source="http")

        assert _get_error_code(result) == "invalid_argument"
        assert result.error.error_details["manifest_source"] == "http"

    async def test_invalid_policy_dir_returns_correction_needed(self, monkeypatch):
        from code_scalpel.mcp.tools import policy as policy_module
        from code_scalpel.mcp.tools.policy import verify_policy_integrity

        resolver_error = FileNotFoundError("Cannot access file: /K:/repo/.code-scalpel")
        monkeypatch.setattr(
            policy_module,
            "resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await verify_policy_integrity(policy_dir="/K:/repo/.code-scalpel")

        assert _get_error_code(result) == "correction_needed"


class TestCodePolicyCheckOracleCoverage:
    async def test_empty_paths_returns_invalid_argument(self):
        from code_scalpel.mcp.tools.policy import code_policy_check

        result = await code_policy_check(paths=[])

        assert _get_error_code(result) == "invalid_argument"

    async def test_invalid_path_returns_correction_needed(self, monkeypatch):
        from code_scalpel.mcp.tools import policy as policy_module
        from code_scalpel.mcp.tools.policy import code_policy_check

        resolver_error = FileNotFoundError("Cannot access file: /K:/repo/app.py")
        monkeypatch.setattr(
            policy_module,
            "resolve_path",
            lambda path, project_root=None: (_ for _ in ()).throw(resolver_error),
        )

        result = await code_policy_check(paths=["/K:/repo/app.py"])

        assert _get_error_code(result) == "correction_needed"

    async def test_compliance_request_requires_upgrade(self, monkeypatch, tmp_path):
        from code_scalpel.mcp.tools import policy as policy_module
        from code_scalpel.mcp.tools.policy import code_policy_check

        source_file = tmp_path / "app.py"
        source_file.write_text("print('hi')\n", encoding="utf-8")
        monkeypatch.setattr(policy_module, "resolve_path", lambda path: str(source_file))
        monkeypatch.setattr(policy_module, "_get_current_tier", lambda: "community")

        result = await code_policy_check(
            paths=[str(source_file)],
            compliance_standards=["SOC2"],
        )

        assert _get_error_code(result) == "upgrade_required"
