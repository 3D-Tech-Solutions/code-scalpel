"""
Rule Detection Tests for code_policy_check Tool

[20260104_TEST] Phase 1 Configuration Validation Tests - Rule Detection

Tests verify that code_policy_check properly detects violations of configured rules
across all rule categories: PY (Python), SEC (Security), ASYNC, and BP (Best Practices).

Test Categories:
1. Community tier rules (PY001-PY010)
2. Pro tier security rules (SEC001-SEC010)
3. Pro tier async rules (ASYNC001-ASYNC005)
4. Pro tier best practice rules (BP001-BP007)
5. Rule ID formatting and consistency

Uses real license files from tests/licenses/ directory (no mocking).
Uses tmp_path fixture to create temporary test files.
"""

import os
from pathlib import Path

import pytest

from code_scalpel.mcp.server import code_policy_check

# License file paths (relative to tests/)
LICENSES_DIR = Path(__file__).parent.parent.parent / "licenses"
PRO_LICENSE = LICENSES_DIR / "code_scalpel_license_pro_20260101_190345.jwt"
ENTERPRISE_LICENSE = LICENSES_DIR / "code_scalpel_license_enterprise_20260101_190754.jwt"


@pytest.fixture
def clear_license_env():
    """Clear license environment before test, restore after."""
    old_value = os.environ.get("CODE_SCALPEL_LICENSE_PATH")
    if "CODE_SCALPEL_LICENSE_PATH" in os.environ:
        del os.environ["CODE_SCALPEL_LICENSE_PATH"]
    yield
    # Restore after test
    if old_value:
        os.environ["CODE_SCALPEL_LICENSE_PATH"] = old_value
    elif "CODE_SCALPEL_LICENSE_PATH" in os.environ:
        del os.environ["CODE_SCALPEL_LICENSE_PATH"]


@pytest.fixture
def set_pro_license(clear_license_env):
    """Set Pro license for test."""
    os.environ["CODE_SCALPEL_LICENSE_PATH"] = str(PRO_LICENSE)
    yield


@pytest.fixture
def set_enterprise_license(clear_license_env):
    """Set Enterprise license for test."""
    os.environ["CODE_SCALPEL_LICENSE_PATH"] = str(ENTERPRISE_LICENSE)
    yield


class TestCommunityRuleDetection:
    """Test detection of Community tier rules (PY001-PY010)."""

    @pytest.mark.asyncio
    async def test_detects_py001_bare_except(self, tmp_path, clear_license_env):
        """Verify PY001: Bare except clause detection."""
        test_file = tmp_path / "test_bare_except.py"
        test_file.write_text("""
try:
    risky_operation()
except:  # PY001 violation
    pass
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "PY001"]
        assert len(violations) > 0, "Should detect PY001: Bare except clause"

    @pytest.mark.asyncio
    async def test_detects_py002_mutable_default(self, tmp_path, clear_license_env):
        """Verify PY002: Mutable default argument detection."""
        test_file = tmp_path / "test_mutable_default.py"
        test_file.write_text("""
def add_item(item, items=[]):  # PY002 violation
    items.append(item)
    return items
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "PY002"]
        assert len(violations) > 0, "Should detect PY002: Mutable default argument"

    @pytest.mark.asyncio
    async def test_detects_py003_global_statement(self, tmp_path, clear_license_env):
        """Verify PY003: Global statement detection."""
        # [20260105_TEST] Expand Community coverage for remaining PY rules.
        test_file = tmp_path / "test_global.py"
        test_file.write_text("""
value = 0

def increment():
    global value  # PY003 violation
    value += 1
    return value
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "PY003"]
        assert violations, "Should detect PY003: Global statement"

    @pytest.mark.asyncio
    async def test_detects_py004_star_import(self, tmp_path, clear_license_env):
        """Verify PY004: Star import detection."""
        test_file = tmp_path / "test_star_import.py"
        test_file.write_text("""
from math import *  # PY004 violation

def area(r):
    return pi * r * r
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "PY004"]
        assert violations, "Should detect PY004: Star import"

    @pytest.mark.asyncio
    async def test_detects_py005_assert_usage(self, tmp_path, clear_license_env):
        """Verify PY005: Assert statement detection."""
        test_file = tmp_path / "test_assert.py"
        test_file.write_text("""
def check_flag(flag):
    assert flag  # PY005 violation
    return bool(flag)
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "PY005"]
        assert violations, "Should detect PY005: Assert statement"

    @pytest.mark.asyncio
    async def test_detects_py006_exec_usage(self, tmp_path, clear_license_env):
        """Verify PY006: exec() usage detection."""
        test_file = tmp_path / "test_exec.py"
        test_file.write_text("""
payload = "print('hello')"
exec(payload)  # PY006 violation
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "PY006"]
        assert violations, "Should detect PY006: exec() usage"

    @pytest.mark.asyncio
    async def test_detects_py007_eval_usage(self, tmp_path, clear_license_env):
        """Verify PY007: eval() usage detection."""
        test_file = tmp_path / "test_eval.py"
        test_file.write_text("""
user_input = input("Enter expression: ")
result = eval(user_input)  # PY007 violation
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "PY007"]
        assert len(violations) > 0, "Should detect PY007: eval() usage"

    @pytest.mark.asyncio
    async def test_detects_py008_type_comparison(self, tmp_path, clear_license_env):
        """Verify PY008: type() comparison detection."""
        test_file = tmp_path / "test_type_compare.py"
        test_file.write_text("""
def is_int(value):
    if type(value) == int:  # PY008 violation
        return True
    return False
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "PY008"]
        assert violations, "Should detect PY008: type() comparison"

    @pytest.mark.asyncio
    async def test_detects_py009_empty_except_block(self, tmp_path, clear_license_env):
        """Verify PY009: Empty except block detection."""
        test_file = tmp_path / "test_empty_except.py"
        test_file.write_text("""
def handler():
    try:
        risky()
    except Exception:  # PY009 violation
        pass
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "PY009"]
        assert violations, "Should detect PY009: Empty except block"

    @pytest.mark.asyncio
    async def test_detects_py010_input_for_password(self, tmp_path, clear_license_env):
        """Verify PY010: input() used for passwords detection."""
        test_file = tmp_path / "test_password_input.py"
        test_file.write_text("""
password = input("Enter password: ")  # PY010 violation
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "PY010"]
        assert violations, "Should detect PY010: input() for passwords"


class TestProSecurityRuleDetection:
    """Test detection of Pro tier security rules (SEC001-SEC010)."""

    @pytest.mark.asyncio
    async def test_detects_sec001_hardcoded_password(self, tmp_path, set_pro_license):
        """Verify SEC001: Hardcoded password detection."""
        test_file = tmp_path / "test_hardcoded_password.py"
        test_file.write_text("""
PASSWORD = "super_secret_123"  # SEC001 violation
API_KEY = "sk-1234567890abcdef"  # SEC001 violation
""")
        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "SEC001"]
        assert len(violations) > 0, "Should detect SEC001: Hardcoded password"

    @pytest.mark.asyncio
    async def test_detects_sec002_sql_concatenation(self, tmp_path, set_pro_license):
        """Verify SEC002: SQL string concatenation detection."""
        test_file = tmp_path / "test_sql_concat.py"
        test_file.write_text("""
def get_user(username):
    cursor.execute("SELECT * FROM users WHERE name = '" + username + "'")  # SEC002 violation
""")
        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "SEC002"]
        assert violations, "Should detect SEC002: SQL string concatenation"

    @pytest.mark.asyncio
    async def test_detects_sec003_os_system_usage(self, tmp_path, set_pro_license):
        """Verify SEC003: os.system() usage detection."""
        test_file = tmp_path / "test_os_system.py"
        test_file.write_text("""
import os
filename = user_input
os.system(f"cat {filename}")  # SEC003 violation
""")
        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "SEC003"]
        assert len(violations) > 0, "Should detect SEC003: os.system() usage"

    @pytest.mark.asyncio
    async def test_detects_sec004_subprocess_shell_true(self, tmp_path, set_pro_license):
        """Verify SEC004: subprocess with shell=True detection."""
        test_file = tmp_path / "test_subprocess_shell.py"
        test_file.write_text("""
import subprocess

def run_command(cmd):
    subprocess.run(cmd, shell=True)  # SEC004 violation
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "SEC004"]
        assert violations, "Should detect SEC004: subprocess shell=True"

    @pytest.mark.asyncio
    async def test_detects_sec005_pickle_usage(self, tmp_path, set_pro_license):
        """Verify SEC005: pickle usage detection."""
        test_file = tmp_path / "test_pickle_usage.py"
        test_file.write_text("""
import pickle

def load(data):
    return pickle.loads(data)  # SEC005 violation
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "SEC005"]
        assert violations, "Should detect SEC005: pickle.loads usage"

    @pytest.mark.asyncio
    async def test_detects_sec006_yaml_unsafe_load(self, tmp_path, set_pro_license):
        """Verify SEC006: yaml.load without Loader detection."""
        test_file = tmp_path / "test_yaml_load.py"
        test_file.write_text("""
import yaml

def read_config(stream):
    return yaml.load(stream)  # SEC006 violation
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "SEC006"]
        assert violations, "Should detect SEC006: yaml.load without Loader"

    @pytest.mark.asyncio
    async def test_detects_sec007_hardcoded_ip(self, tmp_path, set_pro_license):
        """Verify SEC007: Hardcoded IP address detection."""
        test_file = tmp_path / "test_hardcoded_ip.py"
        test_file.write_text("""
SERVER_IP = "192.168.0.10"  # SEC007 violation
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "SEC007"]
        assert violations, "Should detect SEC007: Hardcoded IP"

    @pytest.mark.asyncio
    async def test_detects_sec008_insecure_ssl(self, tmp_path, set_pro_license):
        """Verify SEC008: Insecure SSL verification disabled detection."""
        test_file = tmp_path / "test_insecure_ssl.py"
        test_file.write_text("""
requests.get("https://example.com", verify=False)  # SEC008 violation
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "SEC008"]
        assert violations, "Should detect SEC008: SSL verify disabled"

    @pytest.mark.asyncio
    async def test_detects_sec009_debug_mode(self, tmp_path, set_pro_license):
        """Verify SEC009: Debug mode detection."""
        test_file = tmp_path / "test_debug_mode.py"
        test_file.write_text("""
DEBUG = True  # SEC009 violation

def run_app(app):
    app.run(debug=True)
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "SEC009"]
        assert violations, "Should detect SEC009: Debug mode enabled"

    @pytest.mark.asyncio
    async def test_detects_sec010_weak_hash(self, tmp_path, set_pro_license):
        """Verify SEC010: Weak hash detection."""
        test_file = tmp_path / "test_weak_hash.py"
        test_file.write_text("""
import hashlib

def digest(data):
    return hashlib.md5(data).hexdigest()  # SEC010 violation
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "SEC010"]
        assert violations, "Should detect SEC010: MD5 usage"


class TestProAsyncRuleDetection:
    """Test detection of Pro tier async rules (ASYNC001-ASYNC005)."""

    @pytest.mark.asyncio
    async def test_detects_async001_missing_await(self, tmp_path, set_pro_license):
        """Verify ASYNC001: Missing await detection."""
        test_file = tmp_path / "test_missing_await.py"
        test_file.write_text("""
class Client:
    async def fetch(self):
        return "data"


async def process_data(client: Client):
    client.fetch()  # ASYNC001 violation - missing await on coroutine call
    return "ok"
""")
        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "ASYNC001"]
        assert violations, "Should detect ASYNC001: Missing await"

    @pytest.mark.asyncio
    async def test_detects_async002_blocking_call(self, tmp_path, set_pro_license):
        """Verify ASYNC002: Blocking call in async function detection."""
        test_file = tmp_path / "test_blocking_call.py"
        test_file.write_text("""
import time

async def process_request():
    time.sleep(5)  # ASYNC002 violation - should use asyncio.sleep()
    return "done"
""")
        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "ASYNC002"]
        assert len(violations) > 0, "Should detect ASYNC002: Blocking call in async"

    @pytest.mark.asyncio
    async def test_detects_async003_nested_asyncio_run(self, tmp_path, set_pro_license):
        """Verify ASYNC003: Nested asyncio.run detection."""
        test_file = tmp_path / "test_nested_asyncio_run.py"
        test_file.write_text("""
import asyncio

async def runner():
    return asyncio.run(asyncio.sleep(0))  # ASYNC003 violation
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "ASYNC003"]
        assert violations, "Should detect ASYNC003: Nested asyncio.run"

    @pytest.mark.asyncio
    async def test_detects_async004_unhandled_task(self, tmp_path, set_pro_license):
        """Verify ASYNC004: Unhandled task detection."""
        test_file = tmp_path / "test_unhandled_task.py"
        test_file.write_text("""
import asyncio

async def orchestrate():
    asyncio.create_task(asyncio.sleep(1))  # ASYNC004 violation
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "ASYNC004"]
        assert violations, "Should detect ASYNC004: Unhandled task"

    @pytest.mark.asyncio
    async def test_detects_async005_async_gen_cleanup(self, tmp_path, set_pro_license):
        """Verify ASYNC005: Async generator cleanup detection."""
        test_file = tmp_path / "test_async_gen_cleanup.py"
        test_file.write_text("""
async def consume(gen):
    async for item in gen:  # ASYNC005 violation (async generator without aclose())
        print(item)
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "ASYNC005"]
        assert violations, "Should detect ASYNC005: Async generator cleanup"


class TestProBestPracticeRuleDetection:
    """Test detection of Pro tier best practice rules (BP001-BP007)."""

    @pytest.mark.asyncio
    async def test_detects_bp001_missing_type_hints(self, tmp_path, set_pro_license):
        """Verify BP001: Missing type hints detection."""
        test_file = tmp_path / "test_type_hints.py"
        test_file.write_text("""
def calculate_total(price, quantity):  # BP001 violation - no type hints
    return price * quantity
""")
        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "BP001"]
        assert len(violations) > 0, "Should detect BP001: Missing type hints"

    @pytest.mark.asyncio
    async def test_detects_bp002_missing_docstring(self, tmp_path, set_pro_license):
        """Verify BP002: Missing docstring detection."""
        test_file = tmp_path / "test_docstring.py"
        test_file.write_text("""
def important_function(x, y):  # BP002 violation - no docstring
    return x + y
""")
        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "BP002"]
        assert len(violations) > 0, "Should detect BP002: Missing docstring"

    @pytest.mark.asyncio
    async def test_detects_bp003_too_many_arguments(self, tmp_path, set_pro_license):
        """Verify BP003: Too many arguments detection."""
        test_file = tmp_path / "test_many_args.py"
        test_file.write_text("""
def complex_function(a, b, c, d, e, f, g, h):  # BP003 violation - 8 args
    return a + b + c + d + e + f + g + h
""")
        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "BP003"]
        assert len(violations) > 0, "Should detect BP003: Too many arguments"

    @pytest.mark.asyncio
    async def test_detects_bp004_function_too_long(self, tmp_path, set_pro_license):
        """Verify BP004: Function too long detection (>50 lines)."""
        lines = "\n".join(["    return i" for i in range(60)])
        test_file = tmp_path / "test_function_length.py"
        test_file.write_text(f"""
def oversized():
{lines}
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "BP004"]
        assert violations, "Should detect BP004: Function too long"

    @pytest.mark.asyncio
    async def test_detects_bp006_file_without_context(self, tmp_path, set_pro_license):
        """Verify BP006: File opened without context manager detection."""
        test_file = tmp_path / "test_file_no_context.py"
        test_file.write_text("""
def read_data():
    f = open("data.txt")  # BP006 violation
    return f.read()
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "BP006"]
        assert violations, "Should detect BP006: open without context manager"

    @pytest.mark.asyncio
    async def test_detects_bp007_magic_number(self, tmp_path, set_pro_license):
        """Verify BP007: Magic number detection."""
        test_file = tmp_path / "test_magic_number.py"
        test_file.write_text("""
RETRY_LIMIT = 1234  # BP007 violation
""")

        result = await code_policy_check(paths=[str(test_file)])

        violations = [v for v in result.violations if v.get("rule_id") == "BP007"]
        assert violations, "Should detect BP007: Magic number"


class TestRuleIDFormatting:
    """Test rule ID formatting and consistency."""

    @pytest.mark.asyncio
    async def test_rule_ids_follow_format(self, tmp_path, clear_license_env):
        """Verify all rule IDs follow the pattern: CATEGORY###."""
        test_file = tmp_path / "test_mixed_violations.py"
        test_file.write_text("""
try:
    risky_operation()
except:
    pass

PASSWORD = "secret"

def func(items=[]):
    pass
""")
        result = await code_policy_check(paths=[str(test_file)])

        violations = result.violations

        for violation in violations:
            rule_id = violation.get("rule_id")
            assert rule_id is not None, "All violations must have rule_id"

            # Check format: CATEGORY###
            assert len(rule_id) >= 5, f"Rule ID {rule_id} too short"
            category = rule_id[:-3]
            number = rule_id[-3:]

            assert category in [
                "PY",
                "SEC",
                "ASYNC",
                "BP",
            ], f"Rule ID {rule_id} has invalid category {category}"
            assert number.isdigit(), f"Rule ID {rule_id} number part {number} is not numeric"

    @pytest.mark.asyncio
    async def test_violations_include_required_fields(self, tmp_path, clear_license_env):
        """Verify all violations include required fields."""
        test_file = tmp_path / "test_required_fields.py"
        test_file.write_text("""
try:
    risky_operation()
except:
    pass
""")
        result = await code_policy_check(paths=[str(test_file)])

        violations = result.violations
        assert len(violations) > 0, "Should have at least one violation"

        required_fields = ["rule_id", "file", "line", "message", "severity"]

        for violation in violations:
            for field in required_fields:
                assert field in violation, f"Violation missing required field: {field}"
                assert violation[field] is not None, f"Violation field {field} is None"
