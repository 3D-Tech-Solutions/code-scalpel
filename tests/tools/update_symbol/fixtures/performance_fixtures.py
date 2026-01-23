# [20260103_TEST] Performance test fixtures for update_symbol tool
"""
Performance test fixtures for update_symbol tool.

Generates various sizes of functions, classes, and files for benchmarking:
- Small: <50 LOC
- Medium: 50-200 LOC
- Large: 200-500 LOC
- Very Large: 500+ LOC
"""


def generate_small_function(name: str = "small_function", complexity: str = "simple") -> str:
    """
    Generate small function (< 50 LOC).

    Args:
        name: Function name
        complexity: "simple" or "branching"

    Returns:
        Python source code string
    """
    if complexity == "simple":
        return f'''def {name}(a, b):
    """Small simple function for performance testing."""
    result = a + b
    return result
'''
    else:  # branching
        return f'''def {name}(a, b):
    """Small function with branches for performance testing."""
    result = a + b
    if result > 10:
        result *= 2
    elif result < 0:
        result = 0
    else:
        result += 1
    return result
'''


def generate_medium_function(name: str = "medium_function", lines: int = 100) -> str:
    """
    Generate medium function (50-200 LOC).

    Args:
        name: Function name
        lines: Target line count (actual may vary slightly)

    Returns:
        Python source code string
    """
    # Generate function with nested conditionals, loops, and logic
    lines_code = [
        f'def {name}(data, threshold=10, mode="standard"):',
        f'    """Medium function with {lines} lines for performance testing."""',
        "    result = []",
        "    error_count = 0",
        "    ",
        "    # Validate input",
        "    if not isinstance(data, (list, tuple)):",
        '        raise TypeError("data must be list or tuple")',
        "    ",
        "    # Process each item",
        "    for i, item in enumerate(data):",
        "        try:",
        "            # Apply transformation based on mode",
        '            if mode == "standard":',
        "                if item > threshold:",
        "                    processed = item * 2",
        "                elif item < 0:",
        "                    processed = 0",
        "                else:",
        "                    processed = item + 1",
        '            elif mode == "aggressive":',
        "                processed = item ** 2",
        "            else:",
        "                processed = item",
        "            ",
        "            # Additional processing",
        "            if processed % 2 == 0:",
        "                processed += 1",
        "            ",
        "            # Validate result",
        "            if processed > 1000:",
        "                processed = 1000",
        "            ",
        "            result.append(processed)",
        "        except Exception as e:",
        "            error_count += 1",
        "            continue",
    ]

    # Pad with additional logic to reach target line count
    current_lines = len(lines_code)
    remaining = lines - current_lines - 5  # Reserve 5 for closing

    for i in range(remaining // 3):
        lines_code.append("    ")
        lines_code.append(f"    # Processing step {i}")
        lines_code.append(f"    pass  # Placeholder {i}")

    # Closing lines
    lines_code.extend(
        [
            "    ",
            "    # Return results",
            "    return {",
            '        "results": result,',
            '        "errors": error_count',
            "    }",
        ]
    )

    return "\n".join(lines_code) + "\n"


def generate_large_function(name: str = "large_function", lines: int = 300) -> str:
    """
    Generate large function (200-500 LOC).

    Args:
        name: Function name
        lines: Target line count

    Returns:
        Python source code string
    """
    lines_code = [
        f"def {name}(dataset, config=None, validate=True, debug=False):",
        f'    """Large complex function with {lines} lines for stress testing."""',
        "    import json",
        "    from datetime import datetime",
        "    ",
        "    # Initialize configuration",
        "    if config is None:",
        "        config = {",
        '            "threshold": 100,',
        '            "mode": "standard",',
        '            "max_errors": 10,',
        '            "retry_count": 3',
        "        }",
        "    ",
        "    # Initialize tracking variables",
        "    processed_count = 0",
        "    error_count = 0",
        "    warnings = []",
        "    results = []",
        "    ",
        "    # Phase 1: Validation",
        "    if validate:",
        "        if not isinstance(dataset, list):",
        '            raise TypeError("dataset must be list")',
        "        ",
        "        for idx, item in enumerate(dataset):",
        "            if not isinstance(item, (int, float)):",
        '                warnings.append(f"Item {idx} is not numeric")',
        "    ",
        "    # Phase 2: Pre-processing",
        "    cleaned_data = []",
        "    for item in dataset:",
        "        try:",
        "            if isinstance(item, (int, float)):",
        "                cleaned_data.append(float(item))",
        "        except ValueError:",
        "            error_count += 1",
        '            if error_count > config["max_errors"]:',
        "                break",
        "    ",
        "    # Phase 3: Main processing",
        "    for item in cleaned_data:",
        "        retry_count = 0",
        "        success = False",
        "        ",
        '        while retry_count < config["retry_count"] and not success:',
        "            try:",
        "                # Complex transformation logic",
        '                if config["mode"] == "standard":',
        '                    if item > config["threshold"]:',
        "                        processed = item * 2",
        "                    elif item < 0:",
        "                        processed = abs(item)",
        "                    else:",
        "                        processed = item + 10",
        '                elif config["mode"] == "aggressive":',
        "                    processed = item ** 2",
        "                    if processed > 10000:",
        "                        processed = 10000",
        "                else:",
        "                    processed = item",
        "                ",
        "                # Additional transformations",
        "                if processed % 3 == 0:",
        "                    processed *= 1.1",
        "                ",
        "                if processed < 0:",
        "                    processed = 0",
        "                ",
        "                results.append(processed)",
        "                processed_count += 1",
        "                success = True",
        "            except Exception as e:",
        "                retry_count += 1",
        "                if debug:",
        '                    print(f"Error processing {item}: {e}")',
    ]

    # Pad with additional logic blocks to reach target
    current_lines = len(lines_code)
    remaining = lines - current_lines - 15  # Reserve for closing

    for i in range(remaining // 4):
        lines_code.extend(
            [
                "    ",
                f"    # Additional processing step {i}",
                f"    # This is placeholder logic block {i}",
                "    pass",
            ]
        )

    # Closing lines
    lines_code.extend(
        [
            "    ",
            "    # Phase 4: Post-processing",
            "    final_results = []",
            "    for r in results:",
            "        if r > 0:",
            "            final_results.append(r)",
            "    ",
            "    # Return comprehensive results",
            "    return {",
            '        "success": True,',
            '        "processed_count": processed_count,',
            '        "error_count": error_count,',
            '        "warnings": warnings,',
            '        "results": final_results,',
            '        "timestamp": datetime.now().isoformat()',
            "    }",
        ]
    )

    return "\n".join(lines_code) + "\n"


def generate_very_large_class(name: str = "VeryLargeClass", method_count: int = 20) -> str:
    """
    Generate very large class (500+ LOC) with multiple methods.

    Args:
        name: Class name
        method_count: Number of methods to generate

    Returns:
        Python source code string
    """
    lines = [
        f"class {name}:",
        f'    """Very large class with {method_count} methods for stress testing."""',
        "    ",
        "    def __init__(self, config=None):",
        '        """Initialize the class with configuration."""',
        "        self.config = config or {}",
        "        self.data = []",
        "        self.errors = []",
        "        self.warnings = []",
        "        self.processed_count = 0",
        "    ",
    ]

    # Generate multiple methods
    for i in range(method_count):
        lines.extend(
            [
                f"    def method_{i}(self, value, threshold={i * 10}):",
                f'        """Method {i} for processing data."""',
                "        try:",
                "            if value > threshold:",
                f"                result = value * {i + 1}",
                "            else:",
                f"                result = value + {i}",
                "            ",
                "            # Validate result",
                "            if result < 0:",
                "                result = 0",
                "            elif result > 10000:",
                "                result = 10000",
                "            ",
                "            self.processed_count += 1",
                "            return result",
                "        except Exception as e:",
                "            self.errors.append(str(e))",
                "            return None",
                "    ",
            ]
        )

    # Add utility methods
    lines.extend(
        [
            "    def get_status(self):",
            '        """Get current processing status."""',
            "        return {",
            '            "processed": self.processed_count,',
            '            "errors": len(self.errors),',
            '            "warnings": len(self.warnings)',
            "        }",
            "    ",
            "    def reset(self):",
            '        """Reset all state."""',
            "        self.data.clear()",
            "        self.errors.clear()",
            "        self.warnings.clear()",
            "        self.processed_count = 0",
        ]
    )

    return "\n".join(lines) + "\n"


def generate_file_with_n_functions(n: int, lines_per_function: int = 50) -> str:
    """
    Generate file with N functions of specified size.

    Args:
        n: Number of functions
        lines_per_function: Approximate lines per function

    Returns:
        Python source code string
    """
    lines = [
        f'"""Module with {n} functions for batch performance testing."""',
        "",
    ]

    for i in range(n):
        if lines_per_function < 50:
            func_code = generate_small_function(f"func_{i}", "branching")
        elif lines_per_function < 200:
            func_code = generate_medium_function(f"func_{i}", lines_per_function)
        else:
            func_code = generate_large_function(f"func_{i}", lines_per_function)

        lines.append(func_code)
        lines.append("")

    return "\n".join(lines)


def generate_interdependent_modules(count: int, base_dir) -> list:
    """
    Generate N interdependent Python modules for multi-file testing.

    Args:
        count: Number of modules to create
        base_dir: Path object for directory

    Returns:
        List of Path objects for created files
    """

    files = []

    for i in range(count):
        file_path = base_dir / f"module_{i}.py"

        # Generate imports from previous modules
        imports = []
        if i > 0:
            imports.append(f"from module_{i-1} import process_{i-1}")

        # Generate function that uses imports
        lines = [
            f'"""Module {i} for multi-file testing."""',
            "",
        ]
        lines.extend(imports)
        lines.extend(
            [
                "",
                f"def process_{i}(data):",
                f'    """Process data in module {i}."""',
            ]
        )

        if i > 0:
            lines.append(f"    data = process_{i-1}(data)")

        lines.extend(
            [
                f"    return data * {i + 1}",
                "",
                f"def validate_{i}(value):",
                f'    """Validate value in module {i}."""',
                f"    return value > {i * 10}",
            ]
        )

        file_path.write_text("\n".join(lines))
        files.append(file_path)

    return files


# Replacement functions for test scenarios
def get_small_function_replacement(name: str = "small_function") -> str:
    """Get replacement code for small function (updated logic)."""
    return f'''def {name}(a, b):
    """Updated small function with improved logic."""
    result = a + b + 1  # Added increment
    return result
'''


def get_medium_function_replacement(name: str = "medium_function") -> str:
    """Get replacement code for medium function (updated logic)."""
    return f'''def {name}(data, threshold=20, mode="enhanced"):
    """Updated medium function with enhanced processing."""
    result = []
    error_count = 0

    # Enhanced validation
    if not isinstance(data, (list, tuple)):
        raise TypeError("data must be list or tuple")

    # Enhanced processing
    for item in data:
        try:
            if mode == "enhanced":
                processed = item * 3  # Enhanced multiplier
            else:
                processed = item

            if processed > 2000:
                processed = 2000

            result.append(processed)
        except Exception:
            error_count += 1

    return {{"results": result, "errors": error_count}}
'''


def get_large_function_replacement(name: str = "large_function") -> str:
    """Get replacement code for large function (updated logic)."""
    return generate_large_function(name, 320)  # Slightly larger replacement


def get_very_large_class_replacement(name: str = "VeryLargeClass") -> str:
    """Get replacement code for very large class (updated logic)."""
    return generate_very_large_class(name, 22)  # More methods in replacement
