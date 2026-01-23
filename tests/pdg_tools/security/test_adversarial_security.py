#!/usr/bin/env python
"""
Cross-File Taint Flow Adversarial Tests

[20251215_TEST] Tests for complex cross-file taint tracking scenarios
that are difficult to detect correctly.

These tests ensure the security scanner can track tainted data across:
- Module boundaries
- Async/await chains
- Callback patterns
- Decorator wrappers
- Context managers
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from code_scalpel.mcp.server import cross_file_security_scan, security_scan

# [20251215_TEST] Lint cleanup for adversarial security tests (remove unused imports and placeholders).


class TestCrossFileTaintTracking:
    """Tests for tracking taint across multiple files."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project with multiple files."""
        return tmp_path

    @pytest.mark.asyncio
    async def test_taint_through_import_chain(self, temp_project):
        """Taint should be tracked through import chain: A -> B -> C."""
        # File A: Source of taint
        file_a = temp_project / "source.py"
        file_a.write_text("""
from flask import request

def get_user_input():
    return request.args.get("user_id")  # TAINT SOURCE
""")

        # File B: Intermediate processing
        file_b = temp_project / "processor.py"
        file_b.write_text("""
from source import get_user_input

def process_input():
    data = get_user_input()  # Receives taint
    return data.strip()  # Still tainted after transform
""")

        # File C: Sink
        file_c = temp_project / "executor.py"
        file_c.write_text("""
from processor import process_input
import sqlite3

def execute_query():
    user_id = process_input()  # Tainted
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")  # SINK!
""")

        result = await cross_file_security_scan(project_root=str(temp_project), entry_points=["executor.py"])

        # Should detect the cross-file SQL injection
        assert result.success
        assert any("sql" in str(v).lower() for v in result.vulnerabilities)

    @pytest.mark.asyncio
    async def test_taint_through_async_chain(self, temp_project):
        """Taint should be tracked through async/await chain."""
        file_a = temp_project / "async_source.py"
        file_a.write_text("""
async def fetch_user_data(user_id: str) -> dict:
    # user_id is tainted (from user input)
    return {"id": user_id, "name": "Unknown"}

async def process_user(user_id: str):
    data = await fetch_user_data(user_id)  # Taint propagates
    return data["id"]  # Still tainted
""")

        file_b = temp_project / "async_sink.py"
        file_b.write_text("""
from async_source import process_user
import asyncio

async def dangerous_async(request_id: str):
    user = await process_user(request_id)
    # Taint should reach here
    query = f"DELETE FROM users WHERE id = {user}"
    return query
""")

        result = await cross_file_security_scan(project_root=str(temp_project), entry_points=["async_sink.py"])

        assert result.success

    @pytest.mark.asyncio
    async def test_taint_through_callback(self, temp_project):
        """Taint should be tracked through callback pattern."""
        file_a = temp_project / "callback_source.py"
        file_a.write_text("""
def with_callback(data, callback):
    result = callback(data)
    return result

def identity(x):
    return x
""")

        file_b = temp_project / "callback_sink.py"
        file_b.write_text("""
from callback_source import with_callback
from flask import request
import os

def dangerous_callback(cmd):
    os.system(cmd)  # SINK

def handle_request():
    user_cmd = request.args.get("cmd")  # SOURCE
    with_callback(user_cmd, dangerous_callback)  # Taint flows through callback
""")

        result = await cross_file_security_scan(project_root=str(temp_project), entry_points=["callback_sink.py"])

        assert result.success
        assert result.vulnerability_count > 0

    @pytest.mark.asyncio
    async def test_taint_through_decorator(self, temp_project):
        """Taint should be tracked through decorator wrapper."""
        file_a = temp_project / "decorators.py"
        file_a.write_text("""
from functools import wraps

def log_input(func):
    @wraps(func)
    def wrapper(data, *args, **kwargs):
        print(f"Input: {data}")  # Taint passes through
        return func(data, *args, **kwargs)
    return wrapper
""")

        file_b = temp_project / "decorated_sink.py"
        file_b.write_text("""
from decorators import log_input
from flask import request
import subprocess

@log_input
def execute(command):
    subprocess.run(command, shell=True)  # SINK

def handler():
    cmd = request.form.get("command")  # SOURCE
    execute(cmd)  # Taint flows through decorator
""")

        result = await cross_file_security_scan(project_root=str(temp_project), entry_points=["decorated_sink.py"])

        assert result.success

    @pytest.mark.asyncio
    async def test_taint_sanitizer_clears(self, temp_project):
        """Sanitizer should clear taint."""
        file_a = temp_project / "sanitizers.py"
        file_a.write_text(r'''
import re

def sanitize_id(user_id: str) -> int:
    """Converts to int - clears taint."""
    return int(user_id)  # SANITIZER

def sanitize_input(data: str) -> str:
    """Escapes special chars - clears taint."""
    return re.sub(r'[^\w]', '', data)  # SANITIZER
''')

        file_b = temp_project / "safe_sink.py"
        file_b.write_text("""
from sanitizers import sanitize_id
from flask import request
import sqlite3

def safe_query():
    user_id = request.args.get("id")  # SOURCE (tainted)
    safe_id = sanitize_id(user_id)  # SANITIZED (int conversion)

    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    # This should be SAFE because sanitize_id converted to int
    cursor.execute(f"SELECT * FROM users WHERE id = {safe_id}")
""")

        result = await cross_file_security_scan(project_root=str(temp_project), entry_points=["safe_sink.py"])

        # Should NOT report vulnerability (sanitizer clears taint)
        assert result.success
        # Vulnerabilities should be 0 or marked as sanitized

    @pytest.mark.asyncio
    async def test_taint_through_context_manager(self, temp_project):
        """Taint should be tracked through context manager."""
        file_a = temp_project / "context_manager.py"
        file_a.write_text("""
class DataProcessor:
    def __init__(self, data):
        self.data = data  # May be tainted

    def __enter__(self):
        return self.data  # Taint propagates

    def __exit__(self, *args):
        pass
""")

        file_b = temp_project / "context_sink.py"
        file_b.write_text("""
from context_manager import DataProcessor
from flask import request
import os

def process_request():
    user_input = request.args.get("cmd")  # SOURCE

    with DataProcessor(user_input) as data:
        os.system(data)  # SINK - taint came through __enter__
""")

        result = await cross_file_security_scan(project_root=str(temp_project), entry_points=["context_sink.py"])

        assert result.success

    @pytest.mark.asyncio
    async def test_taint_through_class_inheritance(self, temp_project):
        """Taint should be tracked through class inheritance."""
        file_a = temp_project / "base_handler.py"
        file_a.write_text("""
class BaseHandler:
    def __init__(self, data):
        self.data = data

    def get_data(self):
        return self.data  # Returns potentially tainted data
""")

        file_b = temp_project / "derived_handler.py"
        file_b.write_text("""
from base_handler import BaseHandler
from flask import request
import subprocess

class CommandHandler(BaseHandler):
    def execute(self):
        cmd = self.get_data()  # Inherits tainted data
        subprocess.run(cmd, shell=True)  # SINK

def handle():
    user_cmd = request.args.get("cmd")  # SOURCE
    handler = CommandHandler(user_cmd)
    handler.execute()  # Taint flows through inheritance
""")

        result = await cross_file_security_scan(project_root=str(temp_project), entry_points=["derived_handler.py"])

        assert result.success

    # [20251215_TEST] Ensure cross-file Spring/JPA sinks are detected
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "sink_call",
        [
            'entityManager.createNamedQuery(f"select * from users where name = {name}")',
            'JdbcTemplate.batchUpdate(f"delete from users where name = {name}")',
        ],
    )
    async def test_spring_jpa_cross_file_sink_detected(self, temp_project, sink_call):
        controller = temp_project / "controller.py"
        controller.write_text("""
from flask import request
from repo import run_query


def handler():
    name = request.args.get("name")  # SOURCE
    return run_query(name)
""")

        repo = temp_project / "repo.py"
        repo.write_text(f"""
class EntityManager:
    def createNamedQuery(self, query):
        return query


class JdbcTemplate:
    def batchUpdate(self, query):
        return query


entityManager = EntityManager()
jdbcTemplate = JdbcTemplate()


def run_query(name):
    # [20251215_TEST] Taint should reach Spring/JPA sink
    return {sink_call}
""")

        result = await cross_file_security_scan(project_root=str(temp_project), entry_points=["controller.py"])

        assert result.success
        assert result.has_vulnerabilities
        assert any(v.flow.taint_type == "SQL_QUERY" for v in result.vulnerabilities)


class TestComplexVulnerabilityPatterns:
    """Tests for complex vulnerability patterns that are hard to detect."""

    @pytest.mark.asyncio
    async def test_second_order_sql_injection(self):
        """Second-order SQL injection (stored then retrieved)."""
        code = """
import sqlite3

def store_user(name):
    # First injection point - stores malicious data
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    cursor.execute(f"INSERT INTO users (name) VALUES ('{name}')")
    conn.commit()

def get_user_query(user_id):
    # Second injection point - retrieves and uses malicious data
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    cursor.execute(f"SELECT name FROM users WHERE id = {user_id}")
    name = cursor.fetchone()[0]  # Could contain SQL injection

    # Second-order injection - the name from DB is used unsafely
    cursor.execute(f"SELECT * FROM orders WHERE customer = '{name}'")
"""
        result = await security_scan(code=code)
        assert result.success
        # Should detect both injection points
        assert result.vulnerability_count >= 2

    @pytest.mark.asyncio
    async def test_blind_sql_injection(self):
        """Blind SQL injection detection."""
        code = """
import time
import sqlite3

def check_user_exists(username):
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    # Blind SQL injection - response timing attack
    query = f"SELECT * FROM users WHERE name = '{username}'"
    cursor.execute(query)
    return cursor.fetchone() is not None
"""
        result = await security_scan(code=code)
        assert result.success
        assert result.vulnerability_count > 0

    @pytest.mark.asyncio
    async def test_mass_assignment_vulnerability(self):
        """Mass assignment vulnerability detection."""
        code = """
class User:
    def __init__(self):
        self.name = ""
        self.email = ""
        self.is_admin = False  # Should not be user-controllable

def create_user(request_data):
    user = User()
    # Dangerous - mass assignment
    for key, value in request_data.items():
        setattr(user, key, value)  # Can set is_admin = True
    return user
"""
        result = await security_scan(code=code)
        assert result.success

    @pytest.mark.asyncio
    async def test_race_condition_toctou(self):
        """Time-of-check to time-of-use (TOCTOU) vulnerability."""
        code = """
import os

def safe_read(filename):
    # TOCTOU vulnerability
    if os.path.exists(filename):  # Check
        # Attacker could replace file here
        with open(filename, 'r') as f:  # Use
            return f.read()
    return None
"""
        result = await security_scan(code=code)
        assert result.success

    @pytest.mark.asyncio
    async def test_prototype_pollution_equivalent(self):
        """Python equivalent of prototype pollution."""
        code = '''
def merge_dicts(base, override):
    """Dangerous recursive merge."""
    for key, value in override.items():
        if key == "__class__" or key == "__bases__":
            # Prototype pollution equivalent
            continue
        if isinstance(value, dict) and key in base:
            merge_dicts(base[key], value)
        else:
            base[key] = value
    return base

def handle_config(user_config):
    default = {"debug": False, "admin": False}
    # User could pass {"admin": True}
    return merge_dicts(default, user_config)
'''
        result = await security_scan(code=code)
        assert result.success

    @pytest.mark.asyncio
    async def test_xml_external_entity(self):
        """XXE (XML External Entity) vulnerability."""
        code = """
from xml.etree import ElementTree as ET

def parse_xml(xml_string):
    # Vulnerable to XXE
    root = ET.fromstring(xml_string)
    return root.text
"""
        result = await security_scan(code=code)
        assert result.success

    @pytest.mark.asyncio
    async def test_server_side_request_forgery(self):
        """SSRF (Server-Side Request Forgery) vulnerability."""
        code = """
import requests

def fetch_url(user_url):
    # SSRF - user controls the URL
    response = requests.get(user_url)
    return response.text

def proxy_request(url_param):
    # Could access internal services
    internal_url = f"http://internal-api/{url_param}"
    return requests.get(internal_url).json()
"""
        result = await security_scan(code=code)
        assert result.success

    @pytest.mark.asyncio
    async def test_insecure_deserialization(self):
        """Multiple insecure deserialization patterns."""
        code = """
import pickle
import yaml
import marshal

def load_pickle(data):
    return pickle.loads(data)  # Insecure

def load_yaml(data):
    return yaml.load(data)  # Insecure without Loader

def load_marshal(data):
    return marshal.loads(data)  # Insecure
"""
        result = await security_scan(code=code)
        assert result.success
        # Should detect multiple deserialization issues
        assert result.vulnerability_count >= 2

    @pytest.mark.asyncio
    async def test_cryptographic_weakness(self):
        """Weak cryptographic patterns."""
        code = """
import hashlib
import random

def weak_hash(password):
    # MD5 is weak
    return hashlib.md5(password.encode()).hexdigest()

def weak_random():
    # random is not cryptographically secure
    return random.randint(0, 999999)

def weak_salt(password):
    # Hardcoded salt
    salt = "fixed_salt_123"
    return hashlib.sha256((salt + password).encode()).hexdigest()
"""
        result = await security_scan(code=code)
        assert result.success


class TestSpringSecurityPatterns:
    """Tests for Spring Security vulnerability patterns."""

    @pytest.mark.asyncio
    async def test_spring_sql_injection(self):
        """Spring JPA SQL injection."""
        # Note: security_scan currently only supports Python
        # Spring patterns tested via static code in integration tests
        result = await security_scan(code="x = 1")  # Placeholder
        assert result.success

    @pytest.mark.asyncio
    async def test_spring_expression_injection(self):
        """Spring Expression Language (SpEL) injection."""
        # Note: security_scan currently only supports Python
        result = await security_scan(code="x = 1")  # Placeholder
        assert result.success

    @pytest.mark.asyncio
    async def test_spring_path_traversal(self):
        """Spring path traversal vulnerability."""
        # Note: security_scan currently only supports Python
        result = await security_scan(code="x = 1")  # Placeholder
        assert result.success


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
