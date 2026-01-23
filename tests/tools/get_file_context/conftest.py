"""
Shared fixtures for get_file_context tier-specific tests.

This conftest provides:
- Tier fixtures that mock different capability sets
- Test project fixtures with well-written and smelly code samples
- Community, Pro, and Enterprise capability fixtures
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ============================================================================
# TIER CAPABILITY FIXTURES
# ============================================================================


@pytest.fixture
def community_tier_caps():
    """
    Community tier capabilities - basic extraction only, no code quality metrics.

    Returns:
        dict: Capability dictionary for Community tier
    """
    return {
        "tier": "community",
        "capabilities": [],  # No code quality, no metadata
        "max_context_lines": 500,
    }


@pytest.fixture
def pro_tier_caps():
    """
    Pro tier capabilities - adds code quality metrics.

    Returns:
        dict: Capability dictionary for Pro tier with code quality features
    """
    return {
        "tier": "pro",
        "capabilities": [
            "code_smell_detection",
            "documentation_coverage",
            "maintainability_metrics",
            "semantic_analysis",
        ],
        "max_context_lines": 2000,
    }


@pytest.fixture
def enterprise_tier_caps():
    """
    Enterprise tier capabilities - adds organizational metadata and compliance.

    Returns:
        dict: Capability dictionary for Enterprise tier with all features
    """
    return {
        "tier": "enterprise",
        "capabilities": [
            "code_smell_detection",
            "documentation_coverage",
            "maintainability_metrics",
            "semantic_analysis",
            "custom_metadata",
            "compliance_detection",
            "codeowners_analysis",
            "technical_debt_estimation",
            "historical_analysis",
            "pii_redaction",
            "secret_masking",
        ],
        "max_context_lines": None,  # Unlimited
    }


# ============================================================================
# TEST PROJECT FIXTURES
# ============================================================================


@pytest.fixture
def temp_python_project():
    """
    Create a temporary Python project with well-written and smelly code.

    Returns:
        Path: Path to temporary project directory
    """
    tmpdir = Path(tempfile.mkdtemp())

    # Good code example
    good_code = '''"""
    Well-written module with proper documentation.
    """

def calculate_sum(numbers: list[int]) -> int:
    """
    Calculate sum of a list of numbers.

    Args:
        numbers: List of integers to sum

    Returns:
        Sum of all numbers in the list
    """
    return sum(numbers)


class DataProcessor:
    """Process and transform data."""

    def __init__(self, name: str):
        """Initialize processor with a name."""
        self.name = name

    def process(self, data: dict) -> dict:
        """Process input data and return result."""
        return {k: v * 2 for k, v in data.items()}
'''

    # Smelly code example
    smelly_code = '''
def process_user_data(u, p, e, a, ph, c, z):
    """Process user - too many parameters!"""
    if u is not None:
        if len(u) > 0:
            if u[0] != "":
                if p is not None:
                    if len(p) > 0:
                        if e is not None:
                            if len(e) > 0:
                                if a is not None:
                                    if len(a) > 0:
                                        result = {}
                                        result["user"] = u
                                        result["pass"] = p
                                        result["email"] = e
                                        result["address"] = a
                                        result["phone"] = ph
                                        result["city"] = c
                                        result["zip"] = z
                                        return result
    return None


class GodClass:
    """Class that does too many things."""

    def calculate_tax(self):
        pass

    def send_email(self):
        pass

    def process_payment(self):
        pass

    def generate_report(self):
        pass

    def authenticate_user(self):
        pass

    def validate_address(self):
        pass

    def calculate_shipping(self):
        pass

    def manage_inventory(self):
        pass

    def track_analytics(self):
        pass

    def notify_customer(self):
        pass

try:
    dangerous_function()
except:
    pass
'''

    # Undocumented code
    undocumented = """
def process(x):
    return x * 2

class Handler:
    def handle(self, data):
        return data

def fetch_data(url):
    pass
"""

    # Write files
    (tmpdir / "good_code.py").write_text(good_code)
    (tmpdir / "smelly_code.py").write_text(smelly_code)
    (tmpdir / "undocumented.py").write_text(undocumented)

    yield tmpdir

    # Cleanup
    shutil.rmtree(tmpdir)


@pytest.fixture
def temp_javascript_project():
    """
    Create a temporary JavaScript project for multi-language testing.

    Returns:
        Path: Path to temporary JavaScript project
    """
    tmpdir = Path(tempfile.mkdtemp())

    js_code = """
/**
 * Calculate sum of numbers
 * @param {number[]} numbers - Numbers to sum
 * @returns {number} Sum of all numbers
 */
function calculateSum(numbers) {
  return numbers.reduce((a, b) => a + b, 0);
}

class DataProcessor {
  constructor(name) {
    this.name = name;
  }

  process(data) {
    return Object.entries(data).map(([k, v]) => ({[k]: v * 2}));
  }
}

export { calculateSum, DataProcessor };
"""

    (tmpdir / "processor.js").write_text(js_code)

    yield tmpdir

    shutil.rmtree(tmpdir)


@pytest.fixture
def temp_typescript_project():
    """
    Create a temporary TypeScript project for multi-language testing.

    Returns:
        Path: Path to temporary TypeScript project
    """
    tmpdir = Path(tempfile.mkdtemp())

    ts_code = """
/**
 * Well-typed TypeScript module
 */

interface UserData {
  id: number;
  name: string;
  email: string;
}

/**
 * Process user data
 * @param user - User data to process
 * @returns Processed user data
 */
export function processUser(user: UserData): UserData {
  return {
    ...user,
    name: user.name.toUpperCase(),
  };
}

export class UserProcessor {
  constructor(private name: string) {}

  process(data: UserData): UserData {
    return { ...data, name: this.name };
  }
}
"""

    (tmpdir / "user.ts").write_text(ts_code)

    yield tmpdir

    shutil.rmtree(tmpdir)


@pytest.fixture
def temp_java_project():
    """
    Create a temporary Java project for multi-language testing.

    Returns:
        Path: Path to temporary Java project
    """
    tmpdir = Path(tempfile.mkdtemp())

    java_code = """
/**
 * Data processor utility
 */
package com.example.processor;

import java.util.HashMap;
import java.util.Map;

public class DataProcessor {
    private String name;

    /**
     * Initialize processor with name
     * @param name Processor name
     */
    public DataProcessor(String name) {
        this.name = name;
    }

    /**
     * Process data map
     * @param data Input data
     * @return Processed data
     */
    public Map<String, Integer> process(Map<String, Integer> data) {
        Map<String, Integer> result = new HashMap<>();
        data.forEach((k, v) -> result.put(k, v * 2));
        return result;
    }
}
"""

    (tmpdir / "DataProcessor.java").write_text(java_code)

    yield tmpdir

    shutil.rmtree(tmpdir)


@pytest.fixture
def mock_server():
    """
    Mock the MCP server for testing get_file_context.

    Returns:
        MagicMock: Mocked server with required methods
    """
    server = MagicMock()
    return server


# ============================================================================
# MCP REQUEST FIXTURES
# ============================================================================


@pytest.fixture
def community_request(community_tier_caps):
    """
    Create a Community tier MCP request.

    Returns:
        dict: MCP request parameters
    """
    return {
        "file_path": "test.py",
        "capabilities": community_tier_caps["capabilities"],
        "max_context_lines": community_tier_caps["max_context_lines"],
    }


@pytest.fixture
def pro_request(pro_tier_caps):
    """
    Create a Pro tier MCP request.

    Returns:
        dict: MCP request parameters
    """
    return {
        "file_path": "test.py",
        "capabilities": pro_tier_caps["capabilities"],
        "max_context_lines": pro_tier_caps["max_context_lines"],
    }


@pytest.fixture
def enterprise_request(enterprise_tier_caps):
    """
    Create an Enterprise tier MCP request.

    Returns:
        dict: MCP request parameters
    """
    return {
        "file_path": "test.py",
        "capabilities": enterprise_tier_caps["capabilities"],
        "max_context_lines": enterprise_tier_caps["max_context_lines"],
    }
