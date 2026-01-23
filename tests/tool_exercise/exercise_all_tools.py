#!/usr/bin/env python3
"""Exercise all 22 Code Scalpel MCP tools and document results.

This script systematically calls each tool and captures the output
to validate claims and document actual behavior.
"""

import asyncio
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import MCP tool implementations
from code_scalpel.mcp.tools.analyze import analyze_code
from code_scalpel.mcp.tools.context import (
    crawl_project,
    get_file_context,
    get_symbol_references,
)
from code_scalpel.mcp.tools.extraction import (
    extract_code,
    rename_symbol,
    update_symbol,
)
from code_scalpel.mcp.tools.graph import (
    cross_file_security_scan,
    get_call_graph,
    get_cross_file_dependencies,
    get_graph_neighborhood,
    get_project_map,
)
from code_scalpel.mcp.tools.policy import (
    code_policy_check,
    validate_paths,
    verify_policy_integrity,
)
from code_scalpel.mcp.tools.security import (
    scan_dependencies,
    security_scan,
    type_evaporation_scan,
    unified_sink_detect,
)
from code_scalpel.mcp.tools.symbolic import (
    generate_unit_tests,
    simulate_refactor,
    symbolic_execute,
)
from tests.tool_exercise.test_fixtures import (
    JAVA_CODE,
    JAVASCRIPT_CODE,
    PYTHON_CODE_BASIC,
    PYTHON_CODE_COMPLEX,
    PYTHON_CODE_VULNERABLE,
    SYMBOLIC_EXECUTION_CODE,
    TYPESCRIPT_CODE_BACKEND,
    TYPESCRIPT_CODE_FRONTEND,
)


class ToolExerciser:
    """Exercise all MCP tools and collect results."""

    def __init__(self):
        self.results = {}
        self.errors = {}
        self.start_time = None
        self.project_root = Path(__file__).parent.parent.parent

    def to_serializable(self, obj: Any) -> Any:
        """Convert Pydantic models and other objects to JSON-serializable format."""
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            return obj.dict()
        if hasattr(obj, "__dict__"):
            return {k: self.to_serializable(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
        if isinstance(obj, dict):
            return {k: self.to_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self.to_serializable(v) for v in obj]
        if isinstance(obj, (set, frozenset)):
            return list(obj)
        if isinstance(obj, Path):
            return str(obj)
        return obj

    async def exercise_tool(self, name: str, func, *args, **kwargs) -> dict:
        """Exercise a single tool and record result."""
        print(f"\n{'='*60}")
        print(f"Testing: {name}")
        print(f"{'='*60}")

        start = datetime.now()
        result = {
            "tool_name": name,
            "status": "unknown",
            "execution_time_ms": 0,
            "output": None,
            "error": None,
            "claims_validated": [],
        }

        try:
            output = await func(*args, **kwargs)
            end = datetime.now()
            result["status"] = "success"
            result["execution_time_ms"] = int((end - start).total_seconds() * 1000)
            result["output"] = self.to_serializable(output)

            # Print summary
            print("  Status: SUCCESS")
            print(f"  Time: {result['execution_time_ms']}ms")

            # Extract key metrics based on tool type
            if hasattr(output, "success"):
                print(f"  Success: {output.success}")
            if hasattr(output, "vulnerability_count"):
                print(f"  Vulnerabilities: {output.vulnerability_count}")
            if hasattr(output, "functions"):
                print(f"  Functions found: {len(output.functions) if output.functions else 0}")
            if hasattr(output, "classes"):
                print(f"  Classes found: {len(output.classes) if output.classes else 0}")

        except Exception as e:
            end = datetime.now()
            result["status"] = "error"
            result["execution_time_ms"] = int((end - start).total_seconds() * 1000)
            result["error"] = str(e)
            result["traceback"] = traceback.format_exc()
            print("  Status: ERROR")
            print(f"  Error: {e}")

        self.results[name] = result
        return result

    async def run_all(self):
        """Run all tool exercises."""
        self.start_time = datetime.now()
        print("\n" + "=" * 80)
        print("CODE SCALPEL - COMPLETE TOOL EXERCISE")
        print(f"Started: {self.start_time.isoformat()}")
        print("=" * 80)

        # ============================================================
        # CATEGORY 1: CORE ANALYSIS & SURGERY (8 tools)
        # ============================================================
        print("\n\n" + "#" * 80)
        print("# CATEGORY 1: CORE ANALYSIS & SURGERY")
        print("#" * 80)

        # 1. analyze_code
        await self.exercise_tool("analyze_code", analyze_code, code=PYTHON_CODE_COMPLEX, language="python")

        # Test polyglot support
        await self.exercise_tool(
            "analyze_code_javascript",
            analyze_code,
            code=JAVASCRIPT_CODE,
            language="javascript",
        )

        await self.exercise_tool("analyze_code_java", analyze_code, code=JAVA_CODE, language="java")

        # 2. extract_code
        await self.exercise_tool(
            "extract_code",
            extract_code,
            target_type="function",
            target_name="process_users",
            code=PYTHON_CODE_COMPLEX,
            language="python",
        )

        await self.exercise_tool(
            "extract_code_class",
            extract_code,
            target_type="class",
            target_name="UserService",
            code=PYTHON_CODE_COMPLEX,
            language="python",
        )

        # 3. update_symbol - skip actual file modification, test with in-memory
        # Note: This tool requires a real file, so we'll create a temp file
        temp_file = self.project_root / "tests" / "tool_exercise" / "temp_update_test.py"
        temp_file.write_text(PYTHON_CODE_BASIC)
        try:
            await self.exercise_tool(
                "update_symbol",
                update_symbol,
                file_path=str(temp_file),
                target_type="function",
                target_name="greet",
                new_code='''def greet(name: str) -> str:
    """Return a friendly greeting message."""
    return f"Hi there, {name}!"
''',
                operation="replace",
            )
        finally:
            if temp_file.exists():
                temp_file.unlink()

        # 4. rename_symbol - test with temp file
        temp_file = self.project_root / "tests" / "tool_exercise" / "temp_rename_test.py"
        temp_file.write_text(PYTHON_CODE_BASIC)
        try:
            await self.exercise_tool(
                "rename_symbol",
                rename_symbol,
                file_path=str(temp_file),
                target_type="function",
                target_name="calculate_sum",
                new_name="add_numbers",
            )
        finally:
            if temp_file.exists():
                temp_file.unlink()
            # Also clean up backup
            backup = Path(str(temp_file) + ".backup")
            if backup.exists():
                backup.unlink()

        # 5. symbolic_execute
        await self.exercise_tool(
            "symbolic_execute",
            symbolic_execute,
            code=SYMBOLIC_EXECUTION_CODE,
            max_paths=5,
            max_depth=10,
        )

        # 6. generate_unit_tests
        await self.exercise_tool(
            "generate_unit_tests",
            generate_unit_tests,
            code=SYMBOLIC_EXECUTION_CODE,
            function_name="calculate_discount",
            framework="pytest",
        )

        # 7. simulate_refactor
        await self.exercise_tool(
            "simulate_refactor",
            simulate_refactor,
            original_code=PYTHON_CODE_BASIC,
            new_code=PYTHON_CODE_BASIC.replace("greet", "say_hello"),
        )

        # 8. crawl_project
        await self.exercise_tool(
            "crawl_project",
            crawl_project,
            root_path=str(self.project_root / "src" / "code_scalpel"),
            exclude_dirs=["__pycache__", ".git", "node_modules"],
            complexity_threshold=15,
        )

        # ============================================================
        # CATEGORY 2: CONTEXT & GRAPH NAVIGATION (7 tools)
        # ============================================================
        print("\n\n" + "#" * 80)
        print("# CATEGORY 2: CONTEXT & GRAPH NAVIGATION")
        print("#" * 80)

        # 9. get_file_context
        test_file = self.project_root / "src" / "code_scalpel" / "mcp" / "tools" / "analyze.py"
        await self.exercise_tool("get_file_context", get_file_context, file_path=str(test_file))

        # 10. get_symbol_references
        await self.exercise_tool(
            "get_symbol_references",
            get_symbol_references,
            symbol_name="analyze_code",
            project_root=str(self.project_root / "src" / "code_scalpel"),
            include_tests=False,
        )

        # 11. get_call_graph
        await self.exercise_tool(
            "get_call_graph",
            get_call_graph,
            project_root=str(self.project_root / "src" / "code_scalpel" / "mcp"),
            depth=3,
        )

        # 12. get_graph_neighborhood
        await self.exercise_tool(
            "get_graph_neighborhood",
            get_graph_neighborhood,
            center_node_id="python::code_scalpel.mcp.tools.analyze::function::analyze_code",
            k=2,
            max_nodes=50,
            project_root=str(self.project_root / "src" / "code_scalpel"),
        )

        # 13. get_project_map
        await self.exercise_tool(
            "get_project_map",
            get_project_map,
            project_root=str(self.project_root / "src" / "code_scalpel" / "mcp"),
            include_complexity=True,
            complexity_threshold=10,
        )

        # 14. get_cross_file_dependencies
        await self.exercise_tool(
            "get_cross_file_dependencies",
            get_cross_file_dependencies,
            target_file="tools/analyze.py",
            target_symbol="analyze_code",
            project_root=str(self.project_root / "src" / "code_scalpel" / "mcp"),
            max_depth=2,
        )

        # 15. cross_file_security_scan
        await self.exercise_tool(
            "cross_file_security_scan",
            cross_file_security_scan,
            project_root=str(self.project_root / "src" / "code_scalpel" / "mcp"),
            max_depth=3,
            timeout_seconds=30.0,
            max_modules=50,
        )

        # ============================================================
        # CATEGORY 3: SECURITY ANALYSIS (4 tools)
        # ============================================================
        print("\n\n" + "#" * 80)
        print("# CATEGORY 3: SECURITY ANALYSIS")
        print("#" * 80)

        # 16. security_scan
        await self.exercise_tool("security_scan", security_scan, code=PYTHON_CODE_VULNERABLE)

        # Test with clean code too
        await self.exercise_tool("security_scan_clean", security_scan, code=PYTHON_CODE_BASIC)

        # 17. unified_sink_detect
        await self.exercise_tool(
            "unified_sink_detect",
            unified_sink_detect,
            code=PYTHON_CODE_VULNERABLE,
            language="python",
            confidence_threshold=0.6,
        )

        # Test polyglot
        await self.exercise_tool(
            "unified_sink_detect_js",
            unified_sink_detect,
            code=JAVASCRIPT_CODE,
            language="javascript",
            confidence_threshold=0.6,
        )

        # 18. type_evaporation_scan
        await self.exercise_tool(
            "type_evaporation_scan",
            type_evaporation_scan,
            frontend_code=TYPESCRIPT_CODE_FRONTEND,
            backend_code=TYPESCRIPT_CODE_BACKEND,
            frontend_file="frontend.ts",
            backend_file="backend.py",
        )

        # 19. scan_dependencies
        await self.exercise_tool(
            "scan_dependencies",
            scan_dependencies,
            path=str(self.project_root),
            scan_vulnerabilities=True,
            include_dev=False,
            timeout=10.0,
        )

        # ============================================================
        # CATEGORY 4: GOVERNANCE & COMPLIANCE (3 tools)
        # ============================================================
        print("\n\n" + "#" * 80)
        print("# CATEGORY 4: GOVERNANCE & COMPLIANCE")
        print("#" * 80)

        # 20. validate_paths
        await self.exercise_tool(
            "validate_paths",
            validate_paths,
            paths=[
                str(self.project_root / "src"),
                str(self.project_root / "tests"),
                str(self.project_root / "nonexistent_path"),
            ],
            project_root=str(self.project_root),
        )

        # 21. verify_policy_integrity
        await self.exercise_tool(
            "verify_policy_integrity",
            verify_policy_integrity,
            policy_dir=str(self.project_root / ".code-scalpel"),
            manifest_source="file",
        )

        # 22. code_policy_check
        await self.exercise_tool(
            "code_policy_check",
            code_policy_check,
            paths=[str(self.project_root / "src" / "code_scalpel" / "mcp" / "tools" / "analyze.py")],
            rules=["naming_conventions", "docstrings"],
            compliance_standards=None,
            generate_report=False,
        )

        # ============================================================
        # SUMMARY
        # ============================================================
        end_time = datetime.now()
        total_time = (end_time - self.start_time).total_seconds()

        print("\n\n" + "=" * 80)
        print("EXERCISE COMPLETE - SUMMARY")
        print("=" * 80)

        success_count = sum(1 for r in self.results.values() if r["status"] == "success")
        error_count = sum(1 for r in self.results.values() if r["status"] == "error")

        print(f"\nTotal tools tested: {len(self.results)}")
        print(f"Successful: {success_count}")
        print(f"Errors: {error_count}")
        print(f"Total time: {total_time:.2f}s")

        if error_count > 0:
            print("\nFailed tools:")
            for name, result in self.results.items():
                if result["status"] == "error":
                    print(f"  - {name}: {result['error']}")

        return self.results

    def save_results(self, filepath: Path):
        """Save results to JSON file."""
        output = {
            "timestamp": self.start_time.isoformat() if self.start_time else None,
            "tools_tested": len(self.results),
            "success_count": sum(1 for r in self.results.values() if r["status"] == "success"),
            "error_count": sum(1 for r in self.results.values() if r["status"] == "error"),
            "results": self.results,
        }

        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(output, f, indent=2, default=str)

        print(f"\nResults saved to: {filepath}")


async def main():
    """Main entry point."""
    exerciser = ToolExerciser()
    results = await exerciser.run_all()

    # Save results
    output_path = Path(__file__).parent / "tool_exercise_results.json"
    exerciser.save_results(output_path)

    return results


if __name__ == "__main__":
    asyncio.run(main())
