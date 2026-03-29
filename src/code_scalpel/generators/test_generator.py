"""Test Generator - Convert Symbolic Execution Results to Unit Tests.

This module converts the mathematical proofs from Z3 symbolic execution
into executable unit tests. Each path through the code gets a test case
with concrete inputs that trigger that specific path.

Example:
    >>> from code_scalpel.generators import TestGenerator
    >>> generator = TestGenerator()
    >>> result = generator.generate(code, function_name="classify")
    >>> print(result.pytest_code)
    # Generated pytest tests with concrete inputs for each path
"""

import ast
import re
from dataclasses import dataclass
from typing import Any, TypedDict, cast

from code_scalpel.ir.nodes import (
    IRAssign,
    IRAugAssign,
    IRAttribute,
    IRBinaryOp,
    IRBoolOp,
    IRClassDef,
    IRCompare,
    IRConstant,
    IRExport,
    IRFunctionDef,
    IRIf,
    IRName,
    IRNode,
    IRReturn,
    IRTernary,
    IRUnaryOp,
)


class SymbolicResultDict(TypedDict, total=False):
    """Type-safe structure for symbolic execution results.

    Based on AnalysisResult.to_dict() from symbolic_execution_tools.engine.
    """

    paths: list[dict[str, Any]]  # PathResult.to_dict() output
    all_variables: dict[str, str]
    feasible_count: int
    infeasible_count: int
    total_paths: int


_JAVA_UNRESOLVED = object()


def _find_first_ir_callable(
    nodes: list[IRNode], function_name: str | None = None
) -> IRFunctionDef | None:
    """[20260315_FEATURE] Find the first matching callable through class/export IR wrappers."""
    for node in nodes:
        if isinstance(node, IRFunctionDef):
            if function_name is None or node.name == function_name:
                return node
        if isinstance(node, IRExport) and node.declaration is not None:
            nested = _find_first_ir_callable([node.declaration], function_name)
            if nested is not None:
                return nested
        if isinstance(node, IRClassDef):
            nested = _find_first_ir_callable(node.body, function_name)
            if nested is not None:
                return nested
    return None


@dataclass
class TestCase:
    """A single generated test case."""

    __test__ = False  # [20251215_BUGFIX] Exclude from pytest collection

    path_id: int
    function_name: str
    inputs: dict[str, Any]
    expected_behavior: str
    path_conditions: list[str]
    description: str
    expected_result: Any = None  # Expected return value if known

    def to_pytest(self, index: int) -> str:
        """Convert test case to pytest function."""
        lines = [
            f"def test_{self.function_name}_path_{self.path_id}():",
            '    """',
            f"    Path {self.path_id}: {self.description}",
            f"    Conditions: {', '.join(self.path_conditions) or 'No branches'}",
            '    """',
        ]

        # [20251229_FEATURE] v3.3.0 - Enterprise: Bug reproduction test with pytest.raises
        if "Reproduces bug:" in self.expected_behavior:
            # Extract exception type from expected_behavior
            exception_type = self.expected_behavior.split("Reproduces bug: ")[1].strip()

            # Setup inputs
            if self.inputs:
                for var, value in self.inputs.items():
                    lines.append(f"    {var} = {repr(value)}")
                lines.append("")

            # Expect exception
            lines.append(f"    # Bug reproduction: expecting {exception_type}")
            lines.append(f"    with pytest.raises({exception_type}):")

            # Call function with inputs that trigger the bug
            args = ", ".join(f"{k}={k}" for k in self.inputs.keys())
            lines.append(f"        {self.function_name}({args})")

            return "\n".join(lines)

        # Normal path test case
        # Setup inputs
        if self.inputs:
            for var, value in self.inputs.items():
                lines.append(f"    {var} = {repr(value)}")
            lines.append("")

        # Call function with inputs
        args = ", ".join(f"{k}={k}" for k in self.inputs.keys())
        lines.append(f"    result = {self.function_name}({args})")
        lines.append("")

        # Generate meaningful assertion based on expected result
        lines.append("    # Verify path execution")
        if self.expected_result is not None:
            # We have a concrete expected result
            lines.append(f"    assert result == {repr(self.expected_result)}")
        elif self.expected_behavior and "returns True" in self.expected_behavior:
            lines.append("    assert result is True")
        elif self.expected_behavior and "returns False" in self.expected_behavior:
            lines.append("    assert result is False")
        else:
            # Fallback to basic assertion
            lines.append("    assert result is not None  # Function returned a value")

        return "\n".join(lines)


@dataclass
class GeneratedTestSuite:
    """A complete generated test suite."""

    function_name: str
    test_cases: list[TestCase]
    source_code: str
    language: str = "python"
    framework: str = "pytest"

    @property
    def pytest_code(self) -> str:
        """Generate complete pytest file content."""
        lines = [
            '"""',
            f"Auto-generated tests for {self.function_name}",
            "",
            "Generated by Code Scalpel Test Generator using symbolic execution.",
            "Each test case represents a unique execution path through the code.",
            '"""',
            "",
            "import pytest",
            "",
            "# Original function under test",
            self._extract_function_code(),
            "",
            "",
            "# Generated test cases",
        ]

        for i, test_case in enumerate(self.test_cases):
            lines.append(test_case.to_pytest(i))
            lines.append("")
            lines.append("")

        return "\n".join(lines)

    @property
    def unittest_code(self) -> str:
        """Generate complete unittest file content."""
        lines = [
            '"""',
            f"Auto-generated tests for {self.function_name}",
            "",
            "Generated by Code Scalpel Test Generator using symbolic execution.",
            '"""',
            "",
            "import unittest",
            "",
            "# Original function under test",
            self._extract_function_code(),
            "",
            "",
            f"class Test{self._camel_case(self.function_name)}(unittest.TestCase):",
        ]

        for i, test_case in enumerate(self.test_cases):
            lines.append(self._to_unittest_method(test_case, i))
            lines.append("")

        lines.extend(
            [
                "",
                'if __name__ == "__main__":',
                "    unittest.main()",
            ]
        )

        return "\n".join(lines)

    def _extract_function_code(self) -> str:
        """Extract just the target function from source code."""
        try:
            tree = ast.parse(self.source_code)
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.FunctionDef)
                    and node.name == self.function_name
                ):
                    return ast.unparse(node)
        except Exception:
            pass
        return f"# Function {self.function_name} - include from source"

    def _to_unittest_method(self, test_case: TestCase, index: int) -> str:
        """Convert test case to unittest method."""
        lines = [
            f"    def test_path_{test_case.path_id}(self):",
            f'        """Path {test_case.path_id}: {test_case.description}"""',
        ]

        if test_case.inputs:
            for var, value in test_case.inputs.items():
                lines.append(f"        {var} = {repr(value)}")

        args = ", ".join(f"{k}={k}" for k in test_case.inputs.keys())
        lines.append(f"        result = {self.function_name}({args})")
        lines.append("        # Verify path is reachable")
        lines.append("        self.assertTrue(True)  # Path executed successfully")

        return "\n".join(lines)

    @staticmethod
    def _camel_case(name: str) -> str:
        """Convert snake_case to CamelCase."""
        return "".join(word.capitalize() for word in name.split("_"))

    def generate_parametrized_tests(self) -> str:
        """Generate parametrized/data-driven tests (Pro tier).

        [20251229_FEATURE] v3.3.0 - Pro tier: Data-driven test generation.

        Combines multiple test cases into a single parametrized test using
        @pytest.mark.parametrize, reducing test code duplication.

        Returns:
            Complete pytest file with parametrized tests
        """
        if not self.test_cases:
            return self.pytest_code

        lines = [
            '"""',
            f"Auto-generated parametrized tests for {self.function_name}",
            "",
            "Generated by Code Scalpel Test Generator using symbolic execution.",
            "Data-driven tests combine multiple execution paths into parametrized tests.",
            '"""',
            "",
            "import pytest",
            "",
            "# Original function under test",
            self._extract_function_code(),
            "",
            "",
        ]

        # Group test cases by parameter signature
        param_groups: dict[tuple[str, ...], list[TestCase]] = {}
        for tc in self.test_cases:
            param_sig = tuple(sorted(tc.inputs.keys()))
            if param_sig not in param_groups:
                param_groups[param_sig] = []
            param_groups[param_sig].append(tc)

        # Generate parametrized test for each group
        for idx, (param_sig, test_cases) in enumerate(param_groups.items()):
            if len(test_cases) == 1:
                # Single test case - use regular function
                lines.append(test_cases[0].to_pytest(idx))
                lines.append("")
                lines.append("")
            else:
                # Multiple test cases - use parametrize
                lines.append(self._generate_parametrized_test(test_cases, idx))
                lines.append("")
                lines.append("")

        return "\n".join(lines)

    def _generate_parametrized_test(
        self, test_cases: list[TestCase], group_idx: int
    ) -> str:
        """Generate a single parametrized test for a group of test cases."""
        if not test_cases:
            return ""

        # Get parameter names from first test case
        param_names = list(test_cases[0].inputs.keys())
        param_str = ", ".join(param_names)

        # Build parameter values list
        test_data = []
        test_ids = []
        for tc in test_cases:
            values = tuple(tc.inputs[p] for p in param_names)
            test_data.append(values)
            test_ids.append(f"path_{tc.path_id}")

        lines = [
            f'@pytest.mark.parametrize("{param_str}", [',
        ]

        for values in test_data:
            lines.append(f"    {repr(values)},")

        lines.append(f"], ids={repr(test_ids)})")
        lines.append(
            f"def test_{self.function_name}_parametrized_{group_idx}({param_str}):"
        )
        lines.append('    """')
        lines.append(f"    Data-driven test for {self.function_name}")
        lines.append("    Tests multiple execution paths with different inputs")
        lines.append('    """')

        # Call function with parameters
        args = ", ".join(f"{p}={p}" for p in param_names)
        lines.append(f"    result = {self.function_name}({args})")
        lines.append("")
        lines.append("    # Verify function executes without error")
        lines.append("    assert result is not None  # Path executed successfully")

        return "\n".join(lines)

    def generate_unittest_subtests(self) -> str:
        """Generate unittest with subTest for data-driven testing (Pro tier).

        [20251229_FEATURE] v3.3.0 - Pro tier: Data-driven unittest generation.

        Uses unittest.TestCase.subTest() context manager to run multiple
        test cases within a single test method.

        Returns:
            Complete unittest file with subTest-based data-driven tests
        """
        if not self.test_cases:
            return self.unittest_code

        lines = [
            '"""',
            f"Auto-generated tests for {self.function_name}",
            "",
            "Generated by Code Scalpel Test Generator using symbolic execution.",
            "Data-driven tests using subTest for multiple execution paths.",
            '"""',
            "",
            "import unittest",
            "",
            "# Original function under test",
            self._extract_function_code(),
            "",
            "",
            f"class Test{self._camel_case(self.function_name)}(unittest.TestCase):",
        ]

        # Group test cases by parameter signature
        param_groups: dict[tuple[str, ...], list[TestCase]] = {}
        for tc in self.test_cases:
            param_sig = tuple(sorted(tc.inputs.keys()))
            if param_sig not in param_groups:
                param_groups[param_sig] = []
            param_groups[param_sig].append(tc)

        # Generate test method for each parameter group
        for idx, (param_sig, test_cases) in enumerate(param_groups.items()):
            if len(test_cases) == 1:
                # Single test case - use regular method
                lines.append(self._to_unittest_method(test_cases[0], idx))
            else:
                # Multiple test cases - use subTest
                lines.append(self._generate_unittest_subtest_method(test_cases, idx))
            lines.append("")

        lines.extend(
            [
                "",
                'if __name__ == "__main__":',
                "    unittest.main()",
            ]
        )

        return "\n".join(lines)

    def _generate_unittest_subtest_method(
        self, test_cases: list[TestCase], group_idx: int
    ) -> str:
        """Generate a unittest method using subTest for multiple test cases."""
        if not test_cases:
            return ""

        param_names = list(test_cases[0].inputs.keys())

        lines = [
            f"    def test_{self.function_name}_data_driven_{group_idx}(self):",
            '        """Data-driven test using subTest for multiple paths"""',
            "        test_data = [",
        ]

        for tc in test_cases:
            values = tuple(tc.inputs[p] for p in param_names)
            lines.append(f"            {repr(values)},  # path_{tc.path_id}")

        lines.append("        ]")
        lines.append("")
        lines.append("        for test_inputs in test_data:")

        # Unpack test inputs
        for i, param in enumerate(param_names):
            lines.append(f"            {param} = test_inputs[{i}]")

        lines.append(
            f"            with self.subTest({', '.join(f'{p}={p}' for p in param_names)}):"
        )

        # Call function with unpacked parameters
        args = ", ".join(f"{p}={p}" for p in param_names)
        lines.append(f"                result = {self.function_name}({args})")
        lines.append(
            "                self.assertIsNotNone(result)  # Path executed successfully"
        )

        return "\n".join(lines)


class TestGenerator:
    """Generate unit tests from symbolic execution results.

    This generator takes the output of symbolic execution (paths with
    concrete input values) and produces executable test code.

    Supported frameworks:
    - pytest (default)
    - unittest

    Supported languages:
    - Python (full support)
    - JavaScript (planned)
    - Java (planned)
    """

    __test__ = False  # [20251215_BUGFIX] Exclude from pytest collection

    def __init__(self, framework: str = "pytest"):
        """Initialize the test generator.

        Args:
            framework: Test framework to generate for ("pytest" or "unittest")
        """
        if framework not in ("pytest", "unittest"):
            raise ValueError(f"Unsupported framework: {framework}")
        self.framework = framework

    def generate(
        self,
        code: str,
        function_name: str | None = None,
        symbolic_result: SymbolicResultDict | dict[str, Any] | None = None,
        language: str = "python",
    ) -> GeneratedTestSuite:
        """[20260315_BUGFIX] Generate a test suite from source or symbolic results.
        Args:
            code: Source code to generate tests for
            function_name: Name of function to test (auto-detected if None)
            symbolic_result: Pre-computed symbolic execution result from AnalysisResult.to_dict() (optional)
            language: Source language ("python", "javascript", "java")

        Returns:
            GeneratedTestSuite with test cases for each execution path
        """
        # Auto-detect function name if not provided
        if function_name is None:
            function_name = self._detect_main_function(code, language)

        # Run symbolic execution if result not provided
        if symbolic_result is None:
            symbolic_result = self._run_symbolic_execution(code, language)

        # Extract test cases from paths
        test_cases = self._extract_test_cases(
            symbolic_result, function_name, code, language
        )

        return GeneratedTestSuite(
            function_name=function_name,
            test_cases=test_cases,
            source_code=code,
            language=language,
            framework=self.framework,
        )

    def generate_from_symbolic_result(
        self,
        symbolic_result: SymbolicResultDict,
        code: str,
        function_name: str,
        language: str = "python",
    ) -> GeneratedTestSuite:
        """[20260315_BUGFIX] Generate tests directly from a symbolic result dict.

        Args:
            symbolic_result: Dict with paths, symbolic_variables, constraints from AnalysisResult.to_dict()
            code: Original source code
            function_name: Name of function being tested
            language: Source language

        Returns:
            GeneratedTestSuite with test cases
        """
        test_cases = self._extract_test_cases(
            symbolic_result, function_name, code, language
        )

        return GeneratedTestSuite(
            function_name=function_name,
            test_cases=test_cases,
            source_code=code,
            language=language,
            framework=self.framework,
        )

    def generate_bug_reproduction_test(
        self,
        code: str,
        crash_log: str,
        function_name: str | None = None,
        language: str = "python",
    ) -> GeneratedTestSuite:
        """Generate a test that reproduces a bug from crash log (Enterprise tier).

        [20251229_FEATURE] v3.3.0 - Enterprise tier: Bug reproduction test generation.

        Parses crash logs and stack traces to extract:
        - Exception type and message
        - Input values that trigger the bug
        - Stack trace context

        Args:
            code: Source code with the bug
            crash_log: Crash log or stack trace output
            function_name: Name of function to test (auto-detected if None)
            language: Source language

        Returns:
            GeneratedTestSuite with bug reproduction test case
        """
        if function_name is None:
            function_name = self._detect_main_function(code, language)

        # Parse crash log to extract bug information
        bug_info = self._parse_crash_log(crash_log, function_name, language)

        # Create a test case that reproduces the bug
        test_case = TestCase(
            path_id=0,
            function_name=function_name,
            inputs=bug_info["inputs"],
            expected_behavior=f"Reproduces bug: {bug_info['exception_type']}",
            path_conditions=[
                f"Triggers {bug_info['exception_type']}: {bug_info['exception_message']}"
            ],
            description=f"Bug reproduction test for {bug_info['exception_type']}",
            expected_result=None,  # Expect exception, not return value
        )

        return GeneratedTestSuite(
            function_name=function_name,
            test_cases=[test_case],
            source_code=code,
            language=language,
            framework=self.framework,
        )

    def _parse_crash_log(
        self, crash_log: str, function_name: str, language: str
    ) -> dict[str, Any]:
        """Parse crash log to extract bug reproduction information.

        Supports:
        - Python tracebacks (Traceback, Exception: message)
        - Java stack traces (Exception in thread, at ...)
        - JavaScript errors (Error: message, at ...)
        """
        bug_info: dict[str, Any] = {
            "exception_type": "UnknownError",
            "exception_message": "",
            "inputs": {},
            "line_number": None,
        }

        if language == "python":
            # Parse Python traceback
            # Extract exception type and message
            exception_match = re.search(
                r"(\w+(?:Error|Exception)):\s*(.+?)(?:\n|$)", crash_log
            )
            if exception_match:
                bug_info["exception_type"] = exception_match.group(1)
                bug_info["exception_message"] = exception_match.group(2).strip()

            # Extract line number
            line_match = re.search(r'File ".*?", line (\d+)', crash_log)
            if line_match:
                bug_info["line_number"] = int(line_match.group(1))

            # Try to extract input values from error message
            # Common patterns: "invalid value: X", "cannot process X", etc.
            value_patterns = [
                r"value[:\s]+['\"]?([^'\"\s]+)['\"]?",
                r"input[:\s]+['\"]?([^'\"\s]+)['\"]?",
                r"argument[:\s]+['\"]?([^'\"\s]+)['\"]?",
                r"with[:\s]+['\"]?([^'\"\s]+)['\"]?",
            ]

            for pattern in value_patterns:
                match = re.search(pattern, crash_log, re.IGNORECASE)
                if match:
                    extracted_value = match.group(1)
                    # Try to convert to appropriate type
                    try:
                        if extracted_value.isdigit():
                            bug_info["inputs"]["value"] = int(extracted_value)
                        elif extracted_value.replace(".", "", 1).isdigit():
                            bug_info["inputs"]["value"] = float(extracted_value)
                        else:
                            bug_info["inputs"]["value"] = extracted_value
                    except (ValueError, AttributeError):
                        bug_info["inputs"]["value"] = extracted_value
                    break

        elif language == "javascript":
            # Parse JavaScript error
            error_match = re.search(r"(\w+Error):\s*(.+?)(?:\n|$)", crash_log)
            if error_match:
                bug_info["exception_type"] = error_match.group(1)
                bug_info["exception_message"] = error_match.group(2).strip()

        elif language == "java":
            # Parse Java stack trace
            exception_match = re.search(
                r"([\w.]+(?:Exception|Error)):\s*(.+?)(?:\n|$)", crash_log
            )
            if exception_match:
                bug_info["exception_type"] = exception_match.group(1).split(".")[-1]
                bug_info["exception_message"] = exception_match.group(2).strip()

        # If no inputs extracted, use a default placeholder
        if not bug_info["inputs"]:
            bug_info["inputs"] = {"value": None}

        return bug_info

    def _detect_main_function(self, code: str, language: str) -> str:
        """Detect the main function to test."""
        if language == "python":
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Skip private/dunder methods
                        if not node.name.startswith("_"):
                            return node.name
            except SyntaxError:
                pass
        elif language == "javascript":
            # Simple regex for JS function detection
            match = re.search(r"function\s+(\w+)\s*\(", code)
            if match:
                return match.group(1)
            # Arrow function
            match = re.search(r"const\s+(\w+)\s*=\s*(?:async\s*)?\(", code)
            if match:
                return match.group(1)
        elif language == "typescript":
            patterns = [
                r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(",
                r"(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\(",
                r"(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?[A-Za-z_$][\w$]*\s*=>",
            ]
            for pattern in patterns:
                match = re.search(pattern, code)
                if match:
                    return match.group(1)
        elif language == "java":
            # Java method detection
            match = re.search(r"(?:public|private|protected)?\s*\w+\s+(\w+)\s*\(", code)
            if match:
                return match.group(1)

        return "target_function"

    def _run_symbolic_execution(self, code: str, language: str) -> dict[str, Any]:
        """Run symbolic execution on the code."""
        try:
            from code_scalpel.symbolic_execution_tools.engine import SymbolicAnalyzer

            analyzer = SymbolicAnalyzer(enable_cache=False)
            result = analyzer.analyze(code, language=language)
            result_dict = result.to_dict()

            # [20260309_FEATURE] The shared Java symbolic engine currently emits a
            # coarse single path in some cases. Fall back to branch-aware IR path
            # analysis so generate_unit_tests can still emit concrete Java cases.
            if language == "java":
                raw_paths = result_dict.get("paths", [])
                has_branch_conditions = any(
                    path.get("constraints")
                    for path in raw_paths
                    if isinstance(path, dict)
                )
                if not has_branch_conditions:
                    return self._basic_path_analysis(code, language)

            return result_dict
        except (ImportError, ValueError, SyntaxError, Exception):
            # Fallback to basic path analysis when symbolic execution fails.
            # This keeps generate_unit_tests reliable even if Z3 cannot solve
            # or the analyzer hits an unsupported construct.
            return self._basic_path_analysis(code, language)

    def _basic_path_analysis(self, code: str, language: str) -> dict[str, Any]:
        """Basic path analysis fallback when symbolic execution unavailable."""
        paths = []
        symbolic_vars = []
        constraints = []

        if language == "python":
            try:
                tree = ast.parse(code)

                # Find function parameters (symbolic variables)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        symbolic_vars = [arg.arg for arg in node.args.args]
                        break

                # Find branch conditions
                path_id = 0
                for node in ast.walk(tree):
                    if isinstance(node, ast.If):
                        condition = ast.unparse(node.test)
                        constraints.append(condition)

                        # True branch
                        paths.append(
                            {
                                "path_id": path_id,
                                "conditions": [condition],
                                "state": {
                                    var: self._generate_satisfying_value(
                                        condition, var, True
                                    )
                                    for var in symbolic_vars
                                },
                                "reachable": True,
                            }
                        )
                        path_id += 1

                        # False branch
                        paths.append(
                            {
                                "path_id": path_id,
                                "conditions": [f"not ({condition})"],
                                "state": {
                                    var: self._generate_satisfying_value(
                                        condition, var, False
                                    )
                                    for var in symbolic_vars
                                },
                                "reachable": True,
                            }
                        )
                        path_id += 1

                # If no branches, single path
                if not paths:
                    paths.append(
                        {
                            "path_id": 0,
                            "conditions": [],
                            "state": {var: 0 for var in symbolic_vars},
                            "reachable": True,
                        }
                    )

            except SyntaxError:
                pass

        elif language == "java":
            func_node = self._get_java_function_ir(code)
            if func_node is not None:
                symbolic_vars = [param.name for param in func_node.params if param.name]
                raw_paths = self._enumerate_java_paths(func_node.body)
                if not raw_paths:
                    raw_paths = [[]]

                for condition_list in raw_paths:
                    for condition in condition_list:
                        if condition not in constraints:
                            constraints.append(condition)

                for path_id, condition_list in enumerate(raw_paths):
                    state = self._build_java_state_for_conditions(
                        condition_list, symbolic_vars
                    )
                    paths.append(
                        {
                            "path_id": path_id,
                            "conditions": condition_list,
                            "state": state,
                            "reachable": True,
                        }
                    )

                if not paths:
                    paths.append(
                        {
                            "path_id": 0,
                            "conditions": [],
                            "state": {var: 0 for var in symbolic_vars},
                            "reachable": True,
                        }
                    )

        return {
            "paths": paths,
            "symbolic_vars": symbolic_vars,
            "constraints": constraints,
        }

    def _get_java_function_context(
        self, code: str, function_name: str | None = None
    ) -> tuple[IRFunctionDef | None, dict[str, Any]]:
        """[20260309_BUGFIX] Return Java method IR plus simple enclosing field initializers."""
        try:
            from code_scalpel.ir.normalizers.java_normalizer import JavaNormalizer

            ir_module = JavaNormalizer().normalize(code)
        except Exception:
            return None, {}

        def collect_class_fields(class_node: IRClassDef) -> dict[str, Any]:
            fields: dict[str, Any] = {}
            for child in class_node.body:
                if not isinstance(child, IRAssign):
                    continue
                target = child.targets[0] if child.targets else None
                if isinstance(target, IRName):
                    fields[target.id] = child.value
            return fields

        def walk(nodes: list[IRNode]) -> tuple[IRFunctionDef | None, dict[str, Any]]:
            for node in nodes:
                if isinstance(node, IRFunctionDef):
                    if function_name is None or node.name == function_name:
                        return node, {}
                if isinstance(node, IRClassDef):
                    class_fields = collect_class_fields(node)
                    for child in node.body:
                        if isinstance(child, IRFunctionDef):
                            if function_name is None or child.name == function_name:
                                return child, class_fields
                        if isinstance(child, IRClassDef):
                            nested, nested_fields = walk([child])
                            if nested is not None:
                                return nested, nested_fields
            return None, {}

        return walk(getattr(ir_module, "body", []))

    def _get_java_function_ir(
        self, code: str, function_name: str | None = None
    ) -> IRFunctionDef | None:
        """Return a Java method/function IR node from the snippet."""
        func_node, _ = self._get_java_function_context(code, function_name)
        return func_node

    def _get_typescript_function_ir(
        self, code: str, function_name: str | None = None
    ) -> IRFunctionDef | None:
        """[20260315_FEATURE] Return a TypeScript function IR node from the snippet."""
        try:
            from code_scalpel.ir.normalizers.typescript_normalizer import (
                TypeScriptNormalizer,
            )

            ir_module = TypeScriptNormalizer().normalize(code)
        except Exception:
            return None

        return _find_first_ir_callable(getattr(ir_module, "body", []), function_name)

    def _java_expr_to_text(self, expr: Any) -> str:
        """Render a readable Java IR expression for path and return analysis."""
        if expr is None:
            return "condition"
        if isinstance(expr, IRName):
            return expr.id or "name"
        if isinstance(expr, IRConstant):
            if isinstance(expr.value, str):
                return repr(expr.value)
            return str(expr.value)
        if isinstance(expr, IRCompare):
            left_text = self._java_expr_to_text(expr.left)
            current = left_text
            parts = []
            for op, comparator in zip(expr.ops, expr.comparators):
                right_text = self._java_expr_to_text(comparator)
                parts.append(f"{current} {op.value} {right_text}")
                current = right_text
            return " and ".join(parts) if parts else left_text
        if isinstance(expr, IRBoolOp):
            op_text = f" {expr.op.value} " if expr.op is not None else " && "
            return op_text.join(self._java_expr_to_text(value) for value in expr.values)
        if isinstance(expr, IRUnaryOp):
            op_text = expr.op.value if expr.op is not None else "!"
            return f"{op_text}{self._java_expr_to_text(expr.operand)}"
        return str(expr)

    def _enumerate_java_paths(self, statements: list[IRNode]) -> list[list[str]]:
        """Enumerate simple Java branch condition paths from IR statements."""

        def walk_block(
            block: list[IRNode], active_paths: list[list[str]]
        ) -> tuple[list[list[str]], list[list[str]]]:
            terminal_paths: list[list[str]] = []
            current_paths = active_paths

            for stmt in block:
                if isinstance(stmt, IRReturn):
                    if isinstance(stmt.value, IRTernary):
                        condition = self._java_expr_to_text(stmt.value.test)
                        for base in current_paths:
                            terminal_paths.append(base + [condition])
                            terminal_paths.append(base + [f"!({condition})"])
                        return terminal_paths, []
                    terminal_paths.extend(current_paths)
                    return terminal_paths, []

                if not isinstance(stmt, IRIf):
                    continue

                condition = self._java_expr_to_text(stmt.test)
                next_active: list[list[str]] = []

                for base in current_paths:
                    true_terminal, true_active = walk_block(
                        stmt.body, [base + [condition]]
                    )
                    terminal_paths.extend(true_terminal)

                    if stmt.orelse:
                        false_terminal, false_active = walk_block(
                            stmt.orelse, [base + [f"!({condition})"]]
                        )
                    else:
                        false_terminal, false_active = (
                            [],
                            [base + [f"!({condition})"]],
                        )

                    terminal_paths.extend(false_terminal)
                    next_active.extend(true_active)
                    next_active.extend(false_active)

                current_paths = next_active

            return terminal_paths, current_paths

        terminal_paths, fallthrough_paths = walk_block(statements, [[]])
        all_paths = terminal_paths + fallthrough_paths
        return all_paths or [[]]

    def _condition_matches_value(self, condition: str, var: str, value: Any) -> bool:
        """Check whether a concrete value satisfies a simple generated condition."""
        condition = condition.strip()
        should_satisfy = True
        if condition.startswith("!(") and condition.endswith(")"):
            should_satisfy = False
            condition = condition[2:-1].strip()

        if condition == var:
            result = bool(value)
            return result if should_satisfy else not result

        match = re.search(rf"{var}\s*([<>]=?|==|!=)\s*(-?\d+(?:\.\d+)?)", condition)
        if not match:
            return True

        op = match.group(1)
        threshold = float(match.group(2))
        numeric_value = float(value)
        comparisons = {
            ">": numeric_value > threshold,
            ">=": numeric_value >= threshold,
            "<": numeric_value < threshold,
            "<=": numeric_value <= threshold,
            "==": numeric_value == threshold,
            "!=": numeric_value != threshold,
        }
        result = comparisons.get(op, True)
        return result if should_satisfy else not result

    def _build_java_state_for_conditions(
        self, conditions: list[str], symbolic_vars: list[str]
    ) -> dict[str, Any]:
        """Create concrete Java inputs that satisfy the enumerated path conditions."""
        state = {var: 0 for var in symbolic_vars}

        for condition in conditions:
            for var in symbolic_vars:
                if var not in condition:
                    continue
                if condition == var or condition == f"!({var})":
                    state[var] = condition == var
                    continue
                should_satisfy = not (
                    condition.startswith("!(") and condition.endswith(")")
                )
                base_condition = (
                    condition[2:-1].strip()
                    if condition.startswith("!(") and condition.endswith(")")
                    else condition
                )
                candidate = self._generate_satisfying_value(
                    base_condition, var, should_satisfy
                )
                if not self._condition_matches_value(condition, var, state[var]):
                    state[var] = candidate

        return state

    def _generate_satisfying_value(
        self, condition: str, var: str, should_satisfy: bool
    ) -> Any:
        """Generate a value that satisfies (or doesn't satisfy) a condition."""
        # Parse common patterns
        # Support both integer and float comparisons (e.g., x > 0, x > 100.0)
        patterns = [
            # Float patterns (must come before int patterns)
            (
                rf"{var}\s*>\s*(\d+\.?\d*)",
                lambda m: (
                    float(m.group(1)) + 1.0
                    if should_satisfy
                    else float(m.group(1)) - 1.0
                ),
            ),
            (
                rf"{var}\s*<\s*(\d+\.?\d*)",
                lambda m: (
                    float(m.group(1)) - 1.0
                    if should_satisfy
                    else float(m.group(1)) + 1.0
                ),
            ),
            (
                rf"{var}\s*>=\s*(\d+\.?\d*)",
                lambda m: (
                    float(m.group(1)) if should_satisfy else float(m.group(1)) - 1.0
                ),
            ),
            (
                rf"{var}\s*<=\s*(\d+\.?\d*)",
                lambda m: (
                    float(m.group(1)) if should_satisfy else float(m.group(1)) + 1.0
                ),
            ),
            (
                rf"{var}\s*==\s*(\d+\.?\d*)",
                lambda m: (
                    float(m.group(1)) if should_satisfy else float(m.group(1)) + 1.0
                ),
            ),
            (
                rf"{var}\s*!=\s*(\d+\.?\d*)",
                lambda m: (
                    float(m.group(1)) + 1.0 if should_satisfy else float(m.group(1))
                ),
            ),
        ]

        for pattern, value_fn in patterns:
            match = re.search(pattern, condition)
            if match:
                val = value_fn(match)
                # Return int if it's a whole number without decimal in original
                if "." not in match.group(1) and val == int(val):
                    return int(val)
                return val

        # Default values
        return 1 if should_satisfy else -1

    def _extract_test_cases(
        self,
        symbolic_result: SymbolicResultDict | dict[str, Any],
        function_name: str,
        code: str,
        language: str,
    ) -> list[TestCase]:
        """Extract test cases from symbolic execution result."""
        test_cases = []
        paths = symbolic_result.get("paths", [])

        # Extract type hints from function signature
        param_types = self._extract_parameter_types(code, function_name, language)

        # Analyze code to map path conditions to expected return values
        return_value_map = self._analyze_return_paths(code, function_name, language)

        # Track seen input combinations for deduplication
        seen_inputs: set[tuple] = set()

        for path in paths:
            path_id = path.get("path_id", len(test_cases))
            # Support both old format (conditions) and new format (constraints)
            conditions = path.get("conditions", path.get("constraints", []))
            # Support both old format (state) and new format (model/variables)
            state = path.get("state", path.get("model", path.get("variables", {})))
            reachable = path.get("reachable", True)
            # New format uses status instead of reachable
            if path.get("status") == "infeasible":
                reachable = False

            if not reachable:
                continue

            # Extract reproduction inputs - ONLY for actual function parameters
            inputs = {}
            # Filter state to only include actual function parameters (from param_types)
            # This excludes intermediate variables like 'discount' that are defined inside the function
            if state:
                for var, value in state.items():
                    # Only include if it's a known function parameter
                    if var in param_types or (not param_types):
                        # If no param_types available, still include but will be filtered later
                        expected_type = param_types.get(var)
                        inputs[var] = self._to_python_value(value, expected_type)

            # If param_types is available, ensure we only have actual parameters
            if param_types:
                inputs = {k: v for k, v in inputs.items() if k in param_types}

            # Deduplicate: skip if we've seen this exact input combination
            input_key = tuple(sorted((k, repr(v)) for k, v in inputs.items()))
            if input_key in seen_inputs:
                continue
            seen_inputs.add(input_key)

            # Generate description
            if conditions:
                desc_conditions = [str(c) for c in conditions[:2]]
                description = f"Triggers path where {' and '.join(desc_conditions)}"
                if len(conditions) > 2:
                    description += f" (and {len(conditions) - 2} more conditions)"
            else:
                description = "Default/linear execution path"

            # Infer expected result from path conditions
            expected_result = self._infer_expected_result(
                conditions, return_value_map, inputs
            )

            # If possible, compute the expected return value from the actual
            # control flow using the concrete inputs (without executing user code).
            # This fixes cases where symbolic execution falls back to a shallow
            # path analysis and condition->return matching becomes ambiguous.
            interpreted = self._safe_interpret_return(
                code, function_name, inputs, language
            )
            if interpreted is not None:
                expected_result = interpreted

            expected_behavior = "Executes without error"
            if expected_result is True:
                expected_behavior = "returns True"
            elif expected_result is False:
                expected_behavior = "returns False"

            test_cases.append(
                TestCase(
                    path_id=path_id,
                    function_name=function_name,
                    inputs=inputs,
                    expected_behavior=expected_behavior,
                    path_conditions=conditions,
                    description=description,
                    expected_result=expected_result,
                )
            )

        # Ensure at least one test case
        if not test_cases:
            test_cases.append(
                TestCase(
                    path_id=0,
                    function_name=function_name,
                    inputs={},
                    expected_behavior="Executes without error",
                    path_conditions=[],
                    description="Basic execution test",
                )
            )

        return test_cases

    def _safe_interpret_return(
        self,
        code: str,
        function_name: str,
        inputs: dict[str, Any],
        language: str,
    ) -> Any:
        """Best-effort, safe evaluation of which return value is produced.

        This does NOT execute arbitrary code. It only interprets:
        - if/elif/else control flow
        - simple boolean/comparison expressions for conditions
        - return of constants / True / False / None

        Returns:
            A concrete expected return value, or None if unsupported.
        """
        if language == "java":
            func_node, class_fields = self._get_java_function_context(
                code, function_name
            )  # type: ignore[assignment]
            if func_node is None:
                return None
            java_state = dict(inputs)
            for field_name, field_value in class_fields.items():
                evaluated = self._evaluate_java_expr(field_value, java_state)
                if evaluated is None:
                    evaluated = self._java_ir_value_to_python(field_value)
                if evaluated is not None:
                    java_state[field_name] = evaluated
            return self._safe_interpret_return_java(cast(list, func_node.body), java_state)  # type: ignore[arg-type]

        if language == "typescript":
            func_node = self._get_typescript_function_ir(code, function_name)  # type: ignore[assignment]
            if func_node is None:
                return None
            return self._safe_interpret_return_java(cast(list, func_node.body), dict(inputs))  # type: ignore[arg-type]

        if language != "python":
            return None

        try:
            tree = ast.parse(code)
        except Exception:
            return None

        func_node: ast.FunctionDef | ast.AsyncFunctionDef | None = None
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == function_name
            ):
                func_node = node
                break
        if func_node is None:
            return None

        def eval_expr(expr: ast.AST) -> Any:
            if isinstance(expr, ast.Constant):
                return expr.value

            if isinstance(expr, ast.Name):
                if expr.id in {"True", "False", "None"}:
                    return {"True": True, "False": False, "None": None}[expr.id]
                return inputs.get(expr.id)

            if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.Not):
                v = eval_expr(expr.operand)
                if isinstance(v, bool):
                    return not v
                return None

            if isinstance(expr, ast.BoolOp) and isinstance(expr.op, (ast.And, ast.Or)):
                vals = [eval_expr(v) for v in expr.values]
                if any(v is None for v in vals):
                    return None
                if isinstance(expr.op, ast.And):
                    return all(bool(v) for v in vals)
                return any(bool(v) for v in vals)

            if isinstance(expr, ast.Compare):
                left = eval_expr(expr.left)
                if left is None:
                    return None
                # Support chained comparisons
                current = left
                for op, comparator in zip(expr.ops, expr.comparators):
                    right = eval_expr(comparator)
                    if right is None:
                        return None
                    ok: bool | None = None
                    try:
                        if isinstance(op, ast.Gt):
                            ok = current > right
                        elif isinstance(op, ast.GtE):
                            ok = current >= right
                        elif isinstance(op, ast.Lt):
                            ok = current < right
                        elif isinstance(op, ast.LtE):
                            ok = current <= right
                        elif isinstance(op, ast.Eq):
                            ok = current == right
                        elif isinstance(op, ast.NotEq):
                            ok = current != right
                        else:
                            return None
                    except (TypeError, ValueError):
                        # Unsupported comparison due to type mismatch.
                        return None
                    if not ok:
                        return False
                    current = right
                return True

            return None

        def walk_statements(stmts: list[ast.stmt]) -> Any:
            for st in stmts:
                if isinstance(st, ast.Return):
                    if st.value is None:
                        return None
                    return eval_expr(st.value)

                if isinstance(st, ast.If):
                    cond_val = eval_expr(st.test)
                    if cond_val is None:
                        return None
                    branch = st.body if bool(cond_val) else st.orelse
                    rv = walk_statements(branch)
                    if rv is not None or any(isinstance(x, ast.Return) for x in branch):
                        return rv
                    # Continue after if if branch had no return

            return None

        return walk_statements(func_node.body)

    def _evaluate_java_condition(self, expr: Any, inputs: dict[str, Any]) -> Any:
        """Evaluate a narrow Java IR condition against concrete inputs."""
        return self._evaluate_java_expr(expr, inputs)

    def _evaluate_java_expr(self, expr: Any, inputs: dict[str, Any]) -> Any:
        """Evaluate a narrow Java IR expression against concrete inputs."""
        if isinstance(expr, IRConstant):
            return expr.value
        if isinstance(expr, IRName):
            return inputs.get(expr.id)
        if isinstance(expr, IRAttribute):
            if isinstance(expr.value, IRName) and expr.value.id == "this":
                return inputs.get(expr.attr)
            base = self._evaluate_java_expr(expr.value, inputs)
            if isinstance(base, dict):
                return base.get(expr.attr)
            return None
        if isinstance(expr, IRTernary):
            test_val = self._evaluate_java_expr(expr.test, inputs)
            if test_val is None:
                return None
            branch = expr.body if bool(test_val) else expr.orelse
            return self._evaluate_java_expr(branch, inputs)
        if isinstance(expr, IRUnaryOp):
            operand = self._evaluate_java_expr(expr.operand, inputs)
            if operand is None:
                return None
            if expr.op is not None and expr.op.value in {"!", "not"}:
                return not bool(operand)
            if expr.op is not None and expr.op.value == "-":
                try:
                    return -operand
                except (TypeError, ValueError):
                    return None
            if expr.op is not None and expr.op.value == "+":
                try:
                    return +operand
                except (TypeError, ValueError):
                    return None
            return None
        if isinstance(expr, IRBoolOp):
            values = [self._evaluate_java_expr(v, inputs) for v in expr.values]
            if any(v is None for v in values):
                return None
            if expr.op is not None and expr.op.value == "and":
                return all(bool(v) for v in values)
            if expr.op is not None and expr.op.value == "or":
                return any(bool(v) for v in values)
            return None
        if isinstance(expr, IRCompare):
            left = self._evaluate_java_expr(expr.left, inputs)
            if left is None:
                return None
            current = left
            for op, comparator in zip(expr.ops, expr.comparators):
                right = self._evaluate_java_expr(comparator, inputs)
                if right is None:
                    return None
                try:
                    if op.value == ">":
                        ok = current > right
                    elif op.value == ">=":
                        ok = current >= right
                    elif op.value == "<":
                        ok = current < right
                    elif op.value == "<=":
                        ok = current <= right
                    elif op.value == "==":
                        ok = current == right
                    elif op.value == "!=":
                        ok = current != right
                    else:
                        return None
                except (TypeError, ValueError):
                    return None
                if not ok:
                    return False
                current = right
            return True
        if isinstance(expr, IRBinaryOp):
            left = self._evaluate_java_expr(expr.left, inputs)
            right = self._evaluate_java_expr(expr.right, inputs)
            if left is None or right is None or expr.op is None:
                return None
            try:
                if expr.op.value == "+":
                    return left + right
                if expr.op.value == "-":
                    return left - right
                if expr.op.value == "*":
                    return left * right
                if expr.op.value == "/":
                    return left / right
                if expr.op.value == "%":
                    return left % right
            except (TypeError, ValueError, ZeroDivisionError):
                return None
        return None

    def _safe_interpret_return_java(
        self, statements: list[IRNode], inputs: dict[str, Any]
    ) -> Any:
        """[20260309_BUGFIX] Safely interpret simple Java returns with branch-aware state."""
        returned, value, _state = self._interpret_java_block(statements, inputs)
        if not returned or value is _JAVA_UNRESOLVED:
            return None
        return value

    def _get_java_target_value(self, target: Any, state: dict[str, Any]) -> Any:
        """[20260309_FEATURE] Resolve assignable Java targets from interpreter state."""
        if isinstance(target, IRName):
            return state.get(target.id)
        if isinstance(target, IRAttribute):
            if isinstance(target.value, IRName) and target.value.id == "this":
                return state.get(target.attr)
            base = self._evaluate_java_expr(target.value, state)
            if isinstance(base, dict):
                return base.get(target.attr)
        return None

    def _set_java_target_value(
        self, target: Any, state: dict[str, Any], value: Any
    ) -> bool:
        """[20260309_FEATURE] Store assignable Java targets back into interpreter state."""
        if isinstance(target, IRName):
            state[target.id] = value
            return True
        if isinstance(target, IRAttribute):
            if isinstance(target.value, IRName) and target.value.id == "this":
                state[target.attr] = value
                return True
            base = self._evaluate_java_expr(target.value, state)
            if isinstance(base, dict):
                base[target.attr] = value
                return True
        return False

    def _interpret_java_block(
        self, statements: list[IRNode], inputs: dict[str, Any]
    ) -> tuple[bool, Any, dict[str, Any]]:
        """[20260309_FEATURE] Interpret a Java IR block while preserving assignment state."""
        state = dict(inputs)

        for stmt in statements:
            if isinstance(stmt, IRAssign):
                target = stmt.targets[0] if stmt.targets else None
                value = self._evaluate_java_expr(stmt.value, state)
                if value is None:
                    value = self._java_ir_value_to_python(stmt.value)
                if value is not None:
                    self._set_java_target_value(target, state, value)
                continue

            if isinstance(stmt, IRAugAssign):
                current = self._get_java_target_value(stmt.target, state)
                operand = self._evaluate_java_expr(stmt.value, state)
                if current is None or operand is None or stmt.op is None:
                    continue
                try:
                    result = None
                    if stmt.op.value == "+=":
                        result = current + operand
                    elif stmt.op.value == "-=":
                        result = current - operand
                    elif stmt.op.value == "*=":
                        result = current * operand
                    elif stmt.op.value == "/=":
                        result = current / operand
                    elif stmt.op.value == "%=":
                        result = current % operand
                    if result is not None:
                        self._set_java_target_value(stmt.target, state, result)
                except (TypeError, ValueError, ZeroDivisionError):
                    pass
                continue

            if isinstance(stmt, IRReturn):
                direct = self._java_ir_value_to_python(stmt.value)
                if direct is not None:
                    return True, direct, state
                evaluated = self._evaluate_java_expr(stmt.value, state)
                if evaluated is None:
                    return True, _JAVA_UNRESOLVED, state
                return True, evaluated, state

            if isinstance(stmt, IRIf):
                cond_val = self._evaluate_java_condition(stmt.test, state)
                if cond_val is None:
                    return True, _JAVA_UNRESOLVED, state
                branch = stmt.body if bool(cond_val) else stmt.orelse
                returned, branch_value, branch_state = self._interpret_java_block(
                    branch, dict(state)
                )
                if returned:
                    return True, branch_value, branch_state
                state = branch_state

        return False, _JAVA_UNRESOLVED, state

    def _extract_parameter_types(
        self, code: str, function_name: str, language: str
    ) -> dict[str, str]:
        """Extract parameter type hints from function signature.

        Returns:
            Dict mapping parameter names to their type annotations (e.g., {'role': 'str', 'level': 'int'})
        """
        if language == "java":
            func_node = self._get_java_function_ir(code, function_name)
            if func_node is None:
                return {}
            return {
                param.name: param.type_annotation or "Object"
                for param in func_node.params
                if param.name
            }

        if language == "typescript":
            patterns = [
                rf"(?:export\s+)?(?:async\s+)?function\s+{re.escape(function_name)}\s*\(([^)]*)\)",
                rf"(?:export\s+)?const\s+{re.escape(function_name)}\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>",
            ]
            for pattern in patterns:
                match = re.search(pattern, code)
                if not match:
                    continue
                raw_params = match.group(1).strip()
                if not raw_params:
                    return {}
                param_types: dict[str, str] = {}
                for part in raw_params.split(","):
                    chunk = part.strip()
                    if not chunk:
                        continue
                    typed = re.match(
                        r"([A-Za-z_$][\w$]*)\s*:\s*([^=]+?)(?:\s*=.+)?$",
                        chunk,
                    )
                    if typed:
                        param_types[typed.group(1)] = typed.group(2).strip()
                        continue
                    bare = re.match(r"([A-Za-z_$][\w$]*)", chunk)
                    if bare:
                        param_types[bare.group(1)] = "unknown"
                return param_types

        if language != "python":
            return {}

        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    param_types = {}
                    for arg in node.args.args:
                        if arg.annotation:
                            # Extract type from annotation
                            if isinstance(arg.annotation, ast.Name):
                                param_types[arg.arg] = arg.annotation.id
                            elif isinstance(arg.annotation, ast.Constant):
                                param_types[arg.arg] = str(arg.annotation.value)
                    return param_types
        except Exception:
            pass

        return {}

    def _to_python_value(self, value: Any, expected_type: str | None = None) -> Any:
        """Convert Z3 or other symbolic values to Python natives.

        Args:
            value: The value to convert (Z3 object, int, str, etc.)
            expected_type: Expected Python type from type hint ('str', 'int', 'bool', 'float', etc.)

        Returns:
            Python native value matching the expected type
        """
        # Handle Z3 objects first
        if hasattr(value, "as_long"):
            # Z3 IntNumRef
            int_val = value.as_long()
            if expected_type == "str":
                # If function expects string but Z3 gave us int, convert to string
                return f"value_{int_val}"
            elif expected_type == "float":
                # v1.3.0: Convert to float if expected
                return float(int_val)
            return int_val

        if hasattr(value, "as_fraction"):
            # Z3 RealNumRef (for floats)
            frac = value.as_fraction()
            float_val = float(frac.numerator) / float(frac.denominator)
            if expected_type == "int":
                return int(float_val)
            return float_val

        if hasattr(value, "as_string"):
            # Z3 StringVal
            return value.as_string()

        if hasattr(value, "is_true"):
            # Z3 BoolRef
            return bool(value)

        # Handle Python primitives with type coercion
        if isinstance(value, (int, float)):
            if expected_type == "str":
                return str(value)
            elif expected_type == "bool":
                return bool(value)
            elif expected_type == "float":
                # v1.3.0: Ensure float type
                return float(value)
            elif expected_type == "int":
                return int(value)
            return value

        if isinstance(value, str):
            # If we have a type hint, respect it
            if expected_type == "int":
                try:
                    return int(value)
                except ValueError:
                    return 0  # Default safe value
            elif expected_type == "float":
                try:
                    return float(value)
                except ValueError:
                    return 0.0
            elif expected_type == "bool":
                return value.lower() in ("true", "1", "yes")
            # For str or no hint, keep as string
            return value

        return value

    def _analyze_return_paths(
        self, code: str, function_name: str, language: str
    ) -> dict[str, Any]:
        """Analyze code to map conditions to their return values.

        For boolean functions, this maps branch conditions to True/False returns.

        Returns:
            Dict mapping condition patterns to expected return values
        """
        if language == "java":
            func_node = self._get_java_function_ir(code, function_name)
            if func_node is None:
                return {}
            return self._extract_return_map_java(func_node.body)

        if language == "typescript":
            func_node = self._get_typescript_function_ir(code, function_name)
            if func_node is None:
                return {}
            return self._extract_return_map_java(func_node.body)

        if language != "python":
            return {}

        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    return self._extract_return_map(node)
        except Exception:
            pass

        return {}

    def _extract_return_map(self, func_node: ast.FunctionDef) -> dict[str, Any]:
        """Extract mapping of conditions to return values from a function AST.

        Analyzes if-else chains to determine which conditions lead to which returns.
        """
        return_map: dict[str, Any] = {}

        def visit_body(body: list, condition_stack: list[str]):
            """Recursively visit function body, tracking conditions."""
            for stmt in body:
                if isinstance(stmt, ast.Return):
                    # Found a return - map current conditions to return value
                    if stmt.value is not None:
                        ret_val = self._ast_value_to_python(stmt.value)
                        if ret_val is not None:
                            # Create key from conditions
                            cond_key = (
                                " AND ".join(condition_stack)
                                if condition_stack
                                else "default"
                            )
                            return_map[cond_key] = ret_val

                elif isinstance(stmt, ast.If):
                    # Analyze if branch
                    condition_str = (
                        ast.unparse(stmt.test)
                        if hasattr(ast, "unparse")
                        else str(stmt.test)
                    )
                    visit_body(stmt.body, condition_stack + [condition_str])

                    # Analyze else/elif branches
                    if stmt.orelse:
                        negated = f"not ({condition_str})"
                        visit_body(stmt.orelse, condition_stack + [negated])

        visit_body(func_node.body, [])
        return return_map

    def _extract_return_map_java(self, body: list[IRNode]) -> dict[str, Any]:
        """Extract Java branch-condition to return-value mappings from IR."""
        return_map: dict[str, Any] = {}

        def visit(statements: list[IRNode], condition_stack: list[str]) -> None:
            for stmt in statements:
                if isinstance(stmt, IRReturn):
                    ret_val = self._java_ir_value_to_python(stmt.value)
                    cond_key = (
                        " AND ".join(condition_stack) if condition_stack else "default"
                    )
                    return_map[cond_key] = ret_val
                elif isinstance(stmt, IRIf):
                    condition = self._java_expr_to_text(stmt.test)
                    visit(stmt.body, condition_stack + [condition])
                    if stmt.orelse:
                        visit(stmt.orelse, condition_stack + [f"not ({condition})"])

        visit(body, [])
        return return_map

    def _java_ir_value_to_python(self, value: Any) -> Any:
        """Convert a Java IR return expression to a concrete Python value when simple."""
        if isinstance(value, IRConstant):
            return value.value
        if isinstance(value, IRName):
            if value.id == "true":
                return True
            if value.id == "false":
                return False
            if value.id == "null":
                return None
        return None

    def _ast_value_to_python(self, node: ast.expr) -> Any:
        """Convert AST constant/name to Python value."""
        if isinstance(node, ast.Constant):
            return node.value

        # [20251215_BUGFIX] Avoid deprecated ast.NameConstant checks on Python 3.13+
        if isinstance(node, ast.Name):
            if node.id == "True":
                return True
            if node.id == "False":
                return False
            if node.id == "None":
                return None

        return None

    def _infer_expected_result(
        self, conditions: list[str], return_map: dict[str, Any], inputs: dict[str, Any]
    ) -> Any:
        """Infer expected return value from path conditions and return map.

        Uses the analyzed return paths to determine what value should be returned
        for the given set of conditions.
        """
        if not return_map:
            return None

        # Handle empty conditions - return default if available
        if not conditions:
            return return_map.get("default")

        # Normalize all path conditions to a comparable form
        conditions_set = set()
        for c in conditions:
            cond_str = str(c).strip()
            conditions_set.add(cond_str)
            # Also add normalized versions for comparison
            conditions_set.add(cond_str.replace(" ", ""))

        best_match = None
        best_score = -1

        for cond_key, ret_val in return_map.items():
            if cond_key == "default":
                continue

            # Parse the return map key into individual conditions
            # Keys are like "temp > 100" or "temp > 100 AND not (temp > 200)"
            key_parts = []
            for part in cond_key.split(" AND "):
                part = part.strip()
                if part:
                    key_parts.append(part)

            if not key_parts:
                continue

            # Calculate match score
            match_score = 0
            mismatch_count = 0

            for part in key_parts:
                part_normalized = part.replace(" ", "")
                is_negated = part.startswith("not (") and part.endswith(")")

                if is_negated:
                    # Extract the inner condition from "not (condition)"
                    inner = part[5:-1].strip()
                    inner_normalized = inner.replace(" ", "")

                    # Check if this negated condition matches a path condition negation
                    # Path conditions use operators like <= instead of "not (>)"
                    negated_match = False
                    for pc in conditions:
                        pc_str = str(pc).strip()
                        pc_normalized = pc_str.replace(" ", "")

                        # Check for direct match of negated form
                        if f"Not({inner_normalized})" in pc_normalized:
                            negated_match = True
                            break
                        # Check for inverted comparison operators
                        if self._is_negation_match(inner, pc_str):
                            negated_match = True
                            break
                        # Check for explicit "not" in conditions
                        if (
                            inner_normalized in pc_normalized
                            and "not" in pc_str.lower()
                        ):
                            negated_match = True
                            break

                    if negated_match:
                        match_score += 1
                    else:
                        # Check if the positive form is in conditions (mismatch)
                        if any(
                            inner_normalized in str(c).replace(" ", "")
                            for c in conditions
                        ):
                            mismatch_count += 1
                else:
                    # Non-negated condition - check for direct match
                    direct_match = False
                    for pc in conditions:
                        pc_str = str(pc).strip()
                        pc_normalized = pc_str.replace(" ", "")

                        if part_normalized in pc_normalized or part in pc_str:
                            direct_match = True
                            break
                        # Also check for equivalent forms
                        if self._is_equivalent_condition(part, pc_str):
                            direct_match = True
                            break

                    if direct_match:
                        match_score += 1
                    else:
                        # Check if the negated form is in conditions (mismatch)
                        for pc in conditions:
                            if self._is_negation_match(part, str(pc)):
                                mismatch_count += 1
                                break

            # Calculate final score - penalize mismatches heavily
            final_score = match_score - (mismatch_count * 2)

            # Update best match if this is better
            if final_score > best_score:
                best_score = final_score
                best_match = ret_val

        # Only return if we have a positive match
        if best_score > 0:
            return best_match

        # Fall back to default if no good match
        return return_map.get("default")

    def _is_negation_match(self, condition: str, path_condition: str) -> bool:
        """Check if path_condition is the negation of condition.

        For example: "temp > 100" is negated by "temp <= 100"
        """
        # Extract operator and operands from conditions
        import re

        # Pattern to match comparisons like "var > 100" or "var == 'value'"
        pattern = r"(\w+)\s*([<>=!]+)\s*(.+)"

        cond_match = re.match(pattern, condition.strip())
        path_match = re.match(pattern, path_condition.strip())

        if not cond_match or not path_match:
            return False

        cond_var, cond_op, cond_val = cond_match.groups()
        path_var, path_op, path_val = path_match.groups()

        # Variables must match
        if cond_var != path_var:
            return False

        # Values must match (normalize)
        if cond_val.strip().strip("'\"") != path_val.strip().strip("'\""):
            return False

        # Check if operators are negations of each other
        negation_pairs = {
            ">": "<=",
            "<": ">=",
            ">=": "<",
            "<=": ">",
            "==": "!=",
            "!=": "==",
        }

        return negation_pairs.get(cond_op) == path_op

    def _is_equivalent_condition(self, cond1: str, cond2: str) -> bool:
        """Check if two conditions are equivalent (same meaning, different format)."""
        # Normalize both conditions
        c1 = cond1.strip().replace(" ", "")
        c2 = cond2.strip().replace(" ", "")

        if c1 == c2:
            return True

        # Check for common equivalent patterns
        # e.g., "x>100" vs "100<x"
        import re

        pattern = r"(\w+)([<>=!]+)(\d+\.?\d*)"

        m1 = re.match(pattern, c1)
        m2 = re.match(pattern, c2)

        if m1 and m2:
            var1, op1, val1 = m1.groups()
            var2, op2, val2 = m2.groups()

            if var1 == var2 and val1 == val2 and op1 == op2:
                return True

        return False
