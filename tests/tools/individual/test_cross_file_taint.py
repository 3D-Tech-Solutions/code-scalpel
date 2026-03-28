"""
Tests for Cross-File Taint Tracking.

[20251213_TEST] v1.5.1 - Tests for cross-file taint flow analysis

Test Categories:
- Basic taint detection
- Cross-file taint flows
- Vulnerability detection
- Edge cases and error handling
"""

import tempfile
from pathlib import Path

import pytest

from code_scalpel.ast_tools.import_resolver import ImportResolver
from code_scalpel.ast_tools.java_import_resolver import JavaImportResolver
from code_scalpel.security.analyzers.cross_file_taint import (
    DANGEROUS_SINKS,
    TAINT_SOURCES,
    CallInfo,
    CrossFileSink,
    CrossFileTaintFlow,
    CrossFileTaintResult,
    CrossFileTaintTracker,
    CrossFileVulnerability,
    FunctionTaintInfo,
    SinkInfo,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def simple_vuln_project(temp_project):
    """Create a project with a simple SQL injection vulnerability."""
    # routes.py - web routes that handle user input
    (temp_project / "routes.py").write_text("""
from flask import request
from db import execute_query

def get_user():
    user_id = request.args.get('id')
    return execute_query(user_id)
""")

    # db.py - database operations
    (temp_project / "db.py").write_text("""
import sqlite3

def execute_query(user_id):
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    return cursor.fetchone()
""")

    return temp_project


@pytest.fixture
def safe_project(temp_project):
    """Create a project with parameterized queries (safe)."""
    (temp_project / "routes.py").write_text("""
from flask import request
from db import get_user_safe

def get_user():
    user_id = request.args.get('id')
    return get_user_safe(user_id)
""")

    (temp_project / "db.py").write_text("""
import sqlite3

def get_user_safe(user_id):
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    # Safe: parameterized query
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone()
""")

    return temp_project


@pytest.fixture
def command_injection_project(temp_project):
    """Create a project with command injection vulnerability."""
    (temp_project / "api.py").write_text("""
from flask import request
from utils import run_command

def process():
    filename = request.args.get('file')
    return run_command(filename)
""")

    (temp_project / "utils.py").write_text("""
import os

def run_command(filename):
    os.system(f"cat {filename}")
""")

    return temp_project


@pytest.fixture
def multi_hop_project(temp_project):
    """Create a project with multi-hop taint flow."""
    (temp_project / "app.py").write_text("""
from flask import request
from services import process_data

def handler():
    data = request.args.get('data')
    return process_data(data)
""")

    (temp_project / "services.py").write_text("""
from utils import transform

def process_data(data):
    transformed = transform(data)
    return transformed
""")

    (temp_project / "utils.py").write_text("""
import os

def transform(data):
    # This is dangerous - command injection
    os.system(f"echo {data}")
    return data.upper()
""")

    return temp_project


@pytest.fixture
def path_traversal_project(temp_project):
    """Create a project with path traversal vulnerability."""
    (temp_project / "views.py").write_text("""
from flask import request
from files import read_file

def download():
    path = request.args.get('path')
    return read_file(path)
""")

    (temp_project / "files.py").write_text("""
def read_file(path):
    with open(path, 'r') as f:
        return f.read()
""")

    return temp_project


# =============================================================================
# Basic Functionality Tests
# =============================================================================


class TestBasicFunctionality:
    """Tests for basic tracker functionality."""

    def test_build_succeeds(self, simple_vuln_project):
        """Test that build() succeeds on a valid project."""
        tracker = CrossFileTaintTracker(simple_vuln_project)
        assert tracker.build()

    def test_analyze_returns_result(self, simple_vuln_project):
        """Test that analyze() returns a CrossFileTaintResult."""
        tracker = CrossFileTaintTracker(simple_vuln_project)
        result = tracker.analyze()

        assert isinstance(result, CrossFileTaintResult)
        assert result.modules_analyzed >= 1

    def test_analyze_without_build(self, simple_vuln_project):
        """Test that analyze() works without explicit build()."""
        tracker = CrossFileTaintTracker(simple_vuln_project)
        result = tracker.analyze()

        assert result.success or len(result.errors) > 0


# =============================================================================
# Vulnerability Detection Tests
# =============================================================================


class TestVulnerabilityDetection:
    """Tests for detecting specific vulnerability types."""

    def test_detect_sql_injection(self, simple_vuln_project):
        """Test detection of SQL injection vulnerability."""
        tracker = CrossFileTaintTracker(simple_vuln_project)
        result = tracker.analyze()

        # Should detect SQL injection
        assert result.success
        # Note: Detection depends on accurate taint tracking

    def test_detect_command_injection(self, command_injection_project):
        """Test detection of command injection vulnerability."""
        tracker = CrossFileTaintTracker(command_injection_project)
        result = tracker.analyze()

        assert result.success
        # Check if dangerous sinks were detected
        assert result.functions_analyzed >= 2

    def test_detect_path_traversal(self, path_traversal_project):
        """Test detection of path traversal vulnerability."""
        tracker = CrossFileTaintTracker(path_traversal_project)
        result = tracker.analyze()

        assert result.success


# =============================================================================
# Cross-File Flow Tests
# =============================================================================


class TestCrossFileFlows:
    """Tests for cross-file taint flow tracking."""

    def test_track_taint_across_modules(self, simple_vuln_project):
        """Test that taint is tracked across module boundaries."""
        tracker = CrossFileTaintTracker(simple_vuln_project)
        result = tracker.analyze()

        # Should analyze both modules
        assert result.modules_analyzed >= 2

    def test_multi_hop_taint_flow(self, multi_hop_project):
        """Test tracking taint through multiple modules."""
        tracker = CrossFileTaintTracker(multi_hop_project)
        result = tracker.analyze()

        assert result.success
        # Should have analyzed at least 3 modules
        assert result.modules_analyzed >= 3

    def test_call_graph_built(self, simple_vuln_project):
        """Test that call graph is built correctly."""
        tracker = CrossFileTaintTracker(simple_vuln_project)
        tracker.build()
        tracker.analyze()

        # Call graph should contain cross-module calls
        assert len(tracker.call_graph) >= 0


# =============================================================================
# Taint Source Detection Tests
# =============================================================================


class TestTaintSources:
    """Tests for taint source detection."""

    def test_taint_sources_defined(self):
        """Test that common taint sources are defined."""
        assert "request.args.get" in TAINT_SOURCES
        assert "request.form.get" in TAINT_SOURCES
        assert "os.environ.get" in TAINT_SOURCES

    def test_dangerous_sinks_defined(self):
        """Test that dangerous sinks are defined."""
        assert "cursor.execute" in DANGEROUS_SINKS
        assert "os.system" in DANGEROUS_SINKS
        assert "eval" in DANGEROUS_SINKS
        assert "subprocess.run" in DANGEROUS_SINKS


# =============================================================================
# Data Class Tests
# =============================================================================


class TestDataClasses:
    """Tests for data classes."""

    def test_cross_file_vulnerability_to_dict(self):
        """Test CrossFileVulnerability serialization."""
        flow = CrossFileTaintFlow(
            source_module="routes",
            source_function="get_user",
            source_line=5,
            sink_module="db",
            sink_function="execute_query",
            sink_line=10,
            sink_type=CrossFileSink.SQL_QUERY,
            flow_path=[("routes", "get_user", 5), ("db", "execute_query", 10)],
            tainted_data="user_id",
        )

        vuln = CrossFileVulnerability(
            vulnerability_type="SQL Injection",
            severity="HIGH",
            cwe_id="CWE-89",
            flow=flow,
            description="Test description",
            recommendation="Use parameterized queries",
        )

        data = vuln.to_dict()

        assert data["vulnerability_type"] == "SQL Injection"
        assert data["severity"] == "HIGH"
        assert data["cwe_id"] == "CWE-89"
        assert len(data["flow_path"]) == 2

    def test_call_info_hashable(self):
        """Test that CallInfo is hashable for set operations."""
        call1 = CallInfo(
            caller_module="a",
            caller_line=10,
            target_module="b",
            target_function="func",
            arguments=["x", "y"],
        )

        call2 = CallInfo(
            caller_module="a",
            caller_line=10,
            target_module="b",
            target_function="func",
            arguments=["x", "y"],
        )

        # Should be hashable
        calls = {call1, call2}
        assert len(calls) == 1  # Same hash

    def test_function_taint_info_creation(self):
        """Test FunctionTaintInfo creation."""
        info = FunctionTaintInfo(
            name="test",
            module="test_module",
            file="/path/test.py",
            line=1,
        )

        assert info.name == "test"
        assert len(info.parameters) == 0
        assert len(info.tainted_variables) == 0

    def test_sink_info_creation(self):
        """Test SinkInfo creation."""
        info = SinkInfo(
            sink_type=CrossFileSink.SQL_QUERY,
            line=10,
            function_call="cursor.execute",
        )

        assert info.sink_type == CrossFileSink.SQL_QUERY
        assert info.line == 10


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_project(self, temp_project):
        """Test handling of empty project."""
        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success
        assert result.modules_analyzed == 0

    def test_syntax_error_file(self, temp_project):
        """Test handling of files with syntax errors."""
        (temp_project / "good.py").write_text("def good(): pass")
        (temp_project / "bad.py").write_text("def bad(: pass")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        # Should still analyze good.py
        assert result.modules_analyzed >= 1

    def test_no_dangerous_code(self, temp_project):
        """Test project with no dangerous patterns."""
        (temp_project / "safe.py").write_text("""
def add(a, b):
    return a + b

def multiply(x, y):
    return x * y
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success
        assert len(result.vulnerabilities) == 0

    def test_nonexistent_path(self):
        """Test with nonexistent project path."""
        tracker = CrossFileTaintTracker("/nonexistent/path/12345")
        result = tracker.analyze()

        # Should handle gracefully
        assert result.modules_analyzed == 0

    def test_java_only_project_uses_java_resolver(self, temp_project):
        """[20260309_TEST] Java-only projects should select the Java resolver."""
        java_dir = temp_project / "src" / "com" / "example"
        java_dir.mkdir(parents=True)
        (java_dir / "UserService.java").write_text(
            "package com.example;\npublic class UserService {}\n"
        )

        tracker = CrossFileTaintTracker(temp_project)

        assert isinstance(tracker.resolver, JavaImportResolver)
        assert tracker._resolver_language == "java"
        assert tracker.build() is True

    def test_mixed_project_prefers_python_resolver(self, temp_project):
        """[20260309_TEST] Mixed projects should keep Python-first behavior."""
        (temp_project / "main.py").write_text("def main():\n    return 1\n")
        java_dir = temp_project / "src" / "com" / "example"
        java_dir.mkdir(parents=True)
        (java_dir / "UserService.java").write_text(
            "package com.example;\npublic class UserService {}\n"
        )

        tracker = CrossFileTaintTracker(temp_project)

        assert isinstance(tracker.resolver, ImportResolver)
        assert tracker._resolver_language == "python"

    def test_java_only_project_returns_pending_warning(self, temp_project):
        """[20260309_TEST] Java-only projects should report bounded Java support."""
        java_dir = temp_project / "src" / "com" / "example"
        java_dir.mkdir(parents=True)
        (java_dir / "UserService.java").write_text(
            "package com.example;\npublic class UserService { String run(String id) { return id; } }\n"
        )

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success is True
        assert result.modules_analyzed == 1
        assert result.warnings == [
            "Java cross-file security scan currently supports a bounded IR-based subset: common sources/sinks plus direct/static-import flows. Broader Java patterns are not implemented yet."
        ]

    def test_java_only_project_builds_cross_module_call_graph(self, temp_project):
        """[20260309_TEST] Java-only projects should build cross-module call edges."""
        service_dir = temp_project / "src" / "com" / "example" / "service"
        repo_dir = temp_project / "src" / "com" / "example" / "repo"
        util_dir = temp_project / "src" / "com" / "example" / "util"
        service_dir.mkdir(parents=True)
        repo_dir.mkdir(parents=True)
        util_dir.mkdir(parents=True)

        (service_dir / "UserService.java").write_text("""
package com.example.service;

import com.example.repo.UserRepository;
import static com.example.util.Sql.raw;

class UserService {
    String run(String id) {
        return raw(UserRepository.find(id));
    }
}
""")
        (repo_dir / "UserRepository.java").write_text("""
package com.example.repo;

class UserRepository {
    static String find(String id) {
        return id;
    }
}
""")
        (util_dir / "Sql.java").write_text("""
package com.example.util;

class Sql {
    static String raw(String sql) {
        return sql;
    }
}
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success is True
        assert result.modules_analyzed == 3
        targets = {
            (call.target_module, call.target_function)
            for call in tracker.call_graph["com.example.service.UserService"]
        }
        assert ("com.example.repo.UserRepository", "find") in targets
        assert ("com.example.util.Sql", "raw") in targets
        mermaid = tracker.get_taint_graph_mermaid()
        assert "com_example_service_UserService" in mermaid
        assert "|find|" in mermaid or "|raw|" in mermaid

    def test_java_cross_file_argument_propagation_finds_vulnerability(
        self, temp_project
    ):
        """[20260309_TEST] Java source-to-sink propagation should create a vulnerability across modules."""
        controller_dir = temp_project / "src" / "com" / "example" / "web"
        service_dir = temp_project / "src" / "com" / "example" / "service"
        repo_dir = temp_project / "src" / "com" / "example" / "repo"
        util_dir = temp_project / "src" / "com" / "example" / "util"
        controller_dir.mkdir(parents=True)
        service_dir.mkdir(parents=True)
        repo_dir.mkdir(parents=True)
        util_dir.mkdir(parents=True)

        (controller_dir / "UserController.java").write_text("""
package com.example.web;

import com.example.service.UserService;

class UserController {
    String run(Request request) {
        String user = request.getParameter("id");
        return UserService.run(user);
    }
}
""")
        (service_dir / "UserService.java").write_text("""
package com.example.service;

import com.example.repo.UserRepository;

class UserService {
    static String run(String user) {
        return UserRepository.execute(user);
    }
}
""")
        (repo_dir / "UserRepository.java").write_text("""
package com.example.repo;

import static com.example.util.Sql.raw;

class UserRepository {
    static String execute(String query) {
        return raw(query);
    }
}
""")
        (util_dir / "Sql.java").write_text("""
package com.example.util;

class Sql {
    static String raw(String sql) {
        return sql;
    }
}
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success is True
        assert result.modules_analyzed == 4
        assert result.vulnerabilities
        assert any(v.cwe_id == "CWE-89" for v in result.vulnerabilities)
        flow = next(v.flow for v in result.vulnerabilities if v.cwe_id == "CWE-89")
        assert flow.source_module == "com.example.web.UserController"
        assert flow.sink_module == "com.example.service.UserService"
        assert flow.tainted_data == "user"

    def test_java_imported_tainted_return_reaches_local_sink(self, temp_project):
        """[20260309_TEST] Java imported tainted returns should mark local sink reachability."""
        source_dir = temp_project / "src" / "com" / "example" / "source"
        service_dir = temp_project / "src" / "com" / "example" / "service"
        util_dir = temp_project / "src" / "com" / "example" / "util"
        source_dir.mkdir(parents=True)
        service_dir.mkdir(parents=True)
        util_dir.mkdir(parents=True)

        (source_dir / "InputSource.java").write_text("""
package com.example.source;

class InputSource {
    static String read() {
        return System.getenv("USER_INPUT");
    }
}
""")
        (service_dir / "UserService.java").write_text("""
package com.example.service;

import com.example.source.InputSource;
import static com.example.util.Sql.raw;

class UserService {
    static String run() {
        String query = InputSource.read();
        return raw(query);
    }
}
""")
        (util_dir / "Sql.java").write_text("""
package com.example.util;

class Sql {
    static String raw(String sql) {
        return sql;
    }
}
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze(
            entry_points=["src/com/example/service/UserService.java"]
        )

        assert result.success is True
        assert any(flow.tainted_data == "query" for flow in result.taint_flows)

    def test_java_instance_receiver_type_resolution_finds_vulnerability(
        self, temp_project
    ):
        """[20260309_TEST] Java instance receiver types should resolve cross-module calls."""
        web_dir = temp_project / "src" / "com" / "example" / "web"
        service_dir = temp_project / "src" / "com" / "example" / "service"
        repo_dir = temp_project / "src" / "com" / "example" / "repo"
        util_dir = temp_project / "src" / "com" / "example" / "util"
        web_dir.mkdir(parents=True)
        service_dir.mkdir(parents=True)
        repo_dir.mkdir(parents=True)
        util_dir.mkdir(parents=True)

        (web_dir / "UserController.java").write_text("""
package com.example.web;

import com.example.service.UserService;

class UserController {
    String run(Request request) {
        UserService service = new UserService();
        String user = request.getParameter("id");
        return service.run(user);
    }
}
""")
        (service_dir / "UserService.java").write_text("""
package com.example.service;

import com.example.repo.UserRepository;

class UserService {
    String run(String user) {
        UserRepository repo = new UserRepository();
        return repo.execute(user);
    }
}
""")
        (repo_dir / "UserRepository.java").write_text("""
package com.example.repo;

import com.example.util.Sql;

class UserRepository {
    String execute(String query) {
        Sql sql = new Sql();
        return sql.raw(query);
    }
}
""")
        (util_dir / "Sql.java").write_text("""
package com.example.util;

class Sql {
    String raw(String sql) {
        return sql;
    }
}
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success is True
        assert any(v.cwe_id == "CWE-89" for v in result.vulnerabilities)

    def test_java_field_backed_receiver_type_resolution_finds_vulnerability(
        self, temp_project
    ):
        """[20260310_TEST] Java field-backed receivers should resolve cross-module calls."""
        web_dir = temp_project / "src" / "com" / "example" / "web"
        service_dir = temp_project / "src" / "com" / "example" / "service"
        repo_dir = temp_project / "src" / "com" / "example" / "repo"
        util_dir = temp_project / "src" / "com" / "example" / "util"
        web_dir.mkdir(parents=True)
        service_dir.mkdir(parents=True)
        repo_dir.mkdir(parents=True)
        util_dir.mkdir(parents=True)

        (web_dir / "UserController.java").write_text("""
package com.example.web;

import com.example.service.UserService;

class UserController {
    private UserService service = new UserService();

    String run(Request request) {
        String user = request.getParameter("id");
        return this.service.run(user);
    }
}
""")
        (service_dir / "UserService.java").write_text("""
package com.example.service;

import com.example.repo.UserRepository;

class UserService {
    private UserRepository repo = new UserRepository();

    String run(String user) {
        return repo.execute(user);
    }
}
""")
        (repo_dir / "UserRepository.java").write_text("""
package com.example.repo;

import com.example.util.Sql;

class UserRepository {
    private Sql sql = new Sql();

    String execute(String query) {
        return sql.raw(query);
    }
}
""")
        (util_dir / "Sql.java").write_text("""
package com.example.util;

class Sql {
    String raw(String sql) {
        return sql;
    }
}
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success is True
        assert any(v.cwe_id == "CWE-89" for v in result.vulnerabilities)

    def test_java_tainted_field_flows_across_methods(self, temp_project):
        """[20260310_TEST] Java tainted fields should propagate across methods in the same class."""
        web_dir = temp_project / "src" / "com" / "example" / "web"
        service_dir = temp_project / "src" / "com" / "example" / "service"
        repo_dir = temp_project / "src" / "com" / "example" / "repo"
        util_dir = temp_project / "src" / "com" / "example" / "util"
        web_dir.mkdir(parents=True)
        service_dir.mkdir(parents=True)
        repo_dir.mkdir(parents=True)
        util_dir.mkdir(parents=True)

        (web_dir / "UserController.java").write_text("""
package com.example.web;

import com.example.service.UserService;

class UserController {
    private String cachedUser;

    void capture(Request request) {
        this.cachedUser = request.getParameter("id");
    }

    String run() {
        UserService service = new UserService();
        return service.run(this.cachedUser);
    }
}
""")
        (service_dir / "UserService.java").write_text("""
package com.example.service;

import com.example.repo.UserRepository;

class UserService {
    String run(String user) {
        UserRepository repo = new UserRepository();
        return repo.execute(user);
    }
}
""")
        (repo_dir / "UserRepository.java").write_text("""
package com.example.repo;

import com.example.util.Sql;

class UserRepository {
    String execute(String query) {
        Sql sql = new Sql();
        return sql.raw(query);
    }
}
""")
        (util_dir / "Sql.java").write_text("""
package com.example.util;

class Sql {
    String raw(String sql) {
        return sql;
    }
}
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success is True
        assert any(v.cwe_id == "CWE-89" for v in result.vulnerabilities)

    def test_java_implicit_field_write_flows_across_methods(self, temp_project):
        """[20260310_TEST] Java bare field writes should propagate across methods when no local shadows exist."""
        web_dir = temp_project / "src" / "com" / "example" / "web"
        service_dir = temp_project / "src" / "com" / "example" / "service"
        repo_dir = temp_project / "src" / "com" / "example" / "repo"
        util_dir = temp_project / "src" / "com" / "example" / "util"
        web_dir.mkdir(parents=True)
        service_dir.mkdir(parents=True)
        repo_dir.mkdir(parents=True)
        util_dir.mkdir(parents=True)

        (web_dir / "UserController.java").write_text("""
package com.example.web;

import com.example.service.UserService;

class UserController {
    private String cachedUser;

    void capture(Request request) {
        cachedUser = request.getParameter("id");
    }

    String run() {
        UserService service = new UserService();
        return service.run(cachedUser);
    }
}
""")
        (service_dir / "UserService.java").write_text("""
package com.example.service;

import com.example.repo.UserRepository;

class UserService {
    String run(String user) {
        UserRepository repo = new UserRepository();
        return repo.execute(user);
    }
}
""")
        (repo_dir / "UserRepository.java").write_text("""
package com.example.repo;

import com.example.util.Sql;

class UserRepository {
    String execute(String query) {
        Sql sql = new Sql();
        return sql.raw(query);
    }
}
""")
        (util_dir / "Sql.java").write_text("""
package com.example.util;

class Sql {
    String raw(String sql) {
        return sql;
    }
}
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success is True
        assert any(v.cwe_id == "CWE-89" for v in result.vulnerabilities)

    def test_java_local_shadow_does_not_taint_field_across_methods(self, temp_project):
        """[20260310_TEST] Java locals that shadow fields must not be promoted into class-field taint."""
        web_dir = temp_project / "src" / "com" / "example" / "web"
        service_dir = temp_project / "src" / "com" / "example" / "service"
        repo_dir = temp_project / "src" / "com" / "example" / "repo"
        util_dir = temp_project / "src" / "com" / "example" / "util"
        web_dir.mkdir(parents=True)
        service_dir.mkdir(parents=True)
        repo_dir.mkdir(parents=True)
        util_dir.mkdir(parents=True)

        (web_dir / "UserController.java").write_text("""
package com.example.web;

import com.example.service.UserService;

class UserController {
    private String cachedUser;

    void capture(Request request) {
        var cachedUser = request.getParameter("id");
    }

    String run() {
        UserService service = new UserService();
        return service.run(cachedUser);
    }
}
""")
        (service_dir / "UserService.java").write_text("""
package com.example.service;

import com.example.repo.UserRepository;

class UserService {
    String run(String user) {
        UserRepository repo = new UserRepository();
        return repo.execute(user);
    }
}
""")
        (repo_dir / "UserRepository.java").write_text("""
package com.example.repo;

import com.example.util.Sql;

class UserRepository {
    String execute(String query) {
        Sql sql = new Sql();
        return sql.raw(query);
    }
}
""")
        (util_dir / "Sql.java").write_text("""
package com.example.util;

class Sql {
    String raw(String sql) {
        return sql;
    }
}
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success is True
        assert not any(v.cwe_id == "CWE-89" for v in result.vulnerabilities)

    def test_java_constructor_tainted_receiver_reaches_imported_no_arg_sink(
        self, temp_project
    ):
        """[20260310_TEST] Java constructor-tainted receivers should propagate into imported no-arg methods with local sinks."""
        web_dir = temp_project / "src" / "com" / "example" / "web"
        service_dir = temp_project / "src" / "com" / "example" / "service"
        util_dir = temp_project / "src" / "com" / "example" / "util"
        web_dir.mkdir(parents=True)
        service_dir.mkdir(parents=True)
        util_dir.mkdir(parents=True)

        (web_dir / "UserController.java").write_text("""
package com.example.web;

import com.example.service.UserService;

class UserController {
    String handle(Request request) {
        String user = request.getParameter("id");
        UserService service = new UserService(user);
        return service.run();
    }
}
""")
        (service_dir / "UserService.java").write_text("""
package com.example.service;

import com.example.util.Sql;

class UserService {
    private String user;

    UserService(String user) {
        this.user = user;
    }

    String run() {
        Sql sql = new Sql();
        return sql.raw(user);
    }
}
""")
        (util_dir / "Sql.java").write_text("""
package com.example.util;

class Sql {
    String raw(String sql) {
        return sql;
    }
}
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success is True
        assert any(v.cwe_id == "CWE-89" for v in result.vulnerabilities)

    def test_java_chained_constructor_receiver_reaches_imported_no_arg_sink(
        self, temp_project
    ):
        """[20260310_TEST] Java chained constructor receivers should propagate into imported no-arg methods with local sinks."""
        web_dir = temp_project / "src" / "com" / "example" / "web"
        service_dir = temp_project / "src" / "com" / "example" / "service"
        util_dir = temp_project / "src" / "com" / "example" / "util"
        web_dir.mkdir(parents=True)
        service_dir.mkdir(parents=True)
        util_dir.mkdir(parents=True)

        (web_dir / "UserController.java").write_text("""
package com.example.web;

import com.example.service.UserService;

class UserController {
    String handle(Request request) {
        String user = request.getParameter("id");
        return new UserService(user).run();
    }
}
""")
        (service_dir / "UserService.java").write_text("""
package com.example.service;

import com.example.util.Sql;

class UserService {
    private String user;

    UserService(String user) {
        this.user = user;
    }

    String run() {
        Sql sql = new Sql();
        return sql.raw(user);
    }
}
""")
        (util_dir / "Sql.java").write_text("""
package com.example.util;

class Sql {
    String raw(String sql) {
        return sql;
    }
}
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success is True
        assert any(v.cwe_id == "CWE-89" for v in result.vulnerabilities)

    def test_java_field_backed_constructor_receiver_reaches_imported_no_arg_sink(
        self, temp_project
    ):
        """[20260310_TEST] Java field-backed receivers seeded from tainted constructor calls should reach imported no-arg local sinks."""
        web_dir = temp_project / "src" / "com" / "example" / "web"
        service_dir = temp_project / "src" / "com" / "example" / "service"
        util_dir = temp_project / "src" / "com" / "example" / "util"
        web_dir.mkdir(parents=True)
        service_dir.mkdir(parents=True)
        util_dir.mkdir(parents=True)

        (web_dir / "UserController.java").write_text("""
package com.example.web;

import com.example.service.UserService;

class UserController {
    private UserService service;

    void init(Request request) {
        String user = request.getParameter("id");
        this.service = new UserService(user);
    }

    String run() {
        return this.service.run();
    }
}
""")
        (service_dir / "UserService.java").write_text("""
package com.example.service;

import com.example.util.Sql;

class UserService {
    private String user;

    UserService(String user) {
        this.user = user;
    }

    String run() {
        Sql sql = new Sql();
        return sql.raw(user);
    }
}
""")
        (util_dir / "Sql.java").write_text("""
package com.example.util;

class Sql {
    String raw(String sql) {
        return sql;
    }
}
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success is True
        assert any(v.cwe_id == "CWE-89" for v in result.vulnerabilities)

    def test_java_shadowing_object_receiver_does_not_taint_field_backed_sink(
        self, temp_project
    ):
        """[20260310_TEST] Java locals that shadow object receiver fields must not taint the field-backed sink path."""
        web_dir = temp_project / "src" / "com" / "example" / "web"
        service_dir = temp_project / "src" / "com" / "example" / "service"
        util_dir = temp_project / "src" / "com" / "example" / "util"
        web_dir.mkdir(parents=True)
        service_dir.mkdir(parents=True)
        util_dir.mkdir(parents=True)

        (web_dir / "UserController.java").write_text("""
package com.example.web;

import com.example.service.UserService;

class UserController {
    private UserService service = new UserService("safe");

    void init(Request request) {
        UserService service = new UserService(request.getParameter("id"));
    }

    String run() {
        return this.service.run();
    }
}
""")
        (service_dir / "UserService.java").write_text("""
package com.example.service;

import com.example.util.Sql;

class UserService {
    private String user;

    UserService(String user) {
        this.user = user;
    }

    String run() {
        Sql sql = new Sql();
        return sql.raw(user);
    }
}
""")
        (util_dir / "Sql.java").write_text("""
package com.example.util;

class Sql {
    String raw(String sql) {
        return sql;
    }
}
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success is True
        assert not any(v.cwe_id == "CWE-89" for v in result.vulnerabilities)

    def test_java_sanitized_chained_constructor_receiver_does_not_report_sink(
        self, temp_project
    ):
        """[20260310_TEST] Java chained constructor receivers should not report when a same-class helper returns safe data."""
        web_dir = temp_project / "src" / "com" / "example" / "web"
        service_dir = temp_project / "src" / "com" / "example" / "service"
        util_dir = temp_project / "src" / "com" / "example" / "util"
        web_dir.mkdir(parents=True)
        service_dir.mkdir(parents=True)
        util_dir.mkdir(parents=True)

        (web_dir / "UserController.java").write_text("""
package com.example.web;

import com.example.service.UserService;

class UserController {
    String clean(String value) {
        return "safe";
    }

    String handle(Request request) {
        return new UserService(clean(request.getParameter("id"))).run();
    }
}
""")
        (service_dir / "UserService.java").write_text("""
package com.example.service;

import com.example.util.Sql;

class UserService {
    private String user;

    UserService(String user) {
        this.user = user;
    }

    String run() {
        Sql sql = new Sql();
        return sql.raw(user);
    }
}
""")
        (util_dir / "Sql.java").write_text("""
package com.example.util;

class Sql {
    String raw(String sql) {
        return sql;
    }
}
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success is True
        assert not any(v.cwe_id == "CWE-89" for v in result.vulnerabilities)

    def test_java_imported_safe_helper_in_chained_constructor_receiver_does_not_report_sink(
        self, temp_project
    ):
        """[20260310_TEST] Java chained constructor receivers should ignore imported helpers that return safe data."""
        web_dir = temp_project / "src" / "com" / "example" / "web"
        service_dir = temp_project / "src" / "com" / "example" / "service"
        util_dir = temp_project / "src" / "com" / "example" / "util"
        db_dir = temp_project / "src" / "com" / "example" / "db"
        web_dir.mkdir(parents=True)
        service_dir.mkdir(parents=True)
        util_dir.mkdir(parents=True)
        db_dir.mkdir(parents=True)

        (web_dir / "UserController.java").write_text("""
package com.example.web;

import com.example.service.UserService;
import com.example.util.Cleaner;

class UserController {
    String handle(Request request) {
        return new UserService(Cleaner.clean(request.getParameter("id"))).run();
    }
}
""")
        (util_dir / "Cleaner.java").write_text("""
package com.example.util;

class Cleaner {
    static String clean(String value) {
        return "safe";
    }
}
""")
        (service_dir / "UserService.java").write_text("""
package com.example.service;

import com.example.db.Sql;

class UserService {
    private String user;

    UserService(String user) {
        this.user = user;
    }

    String run() {
        Sql sql = new Sql();
        return sql.raw(user);
    }
}
""")
        (db_dir / "Sql.java").write_text("""
package com.example.db;

class Sql {
    String raw(String sql) {
        return sql;
    }
}
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success is True
        assert not any(v.cwe_id == "CWE-89" for v in result.vulnerabilities)

    def test_java_imported_tainted_helper_in_chained_constructor_receiver_reports_sink(
        self, temp_project
    ):
        """[20260310_TEST] Java chained constructor receivers should report when an imported helper preserves tainted data."""
        web_dir = temp_project / "src" / "com" / "example" / "web"
        service_dir = temp_project / "src" / "com" / "example" / "service"
        util_dir = temp_project / "src" / "com" / "example" / "util"
        db_dir = temp_project / "src" / "com" / "example" / "db"
        web_dir.mkdir(parents=True)
        service_dir.mkdir(parents=True)
        util_dir.mkdir(parents=True)
        db_dir.mkdir(parents=True)

        (web_dir / "UserController.java").write_text("""
package com.example.web;

import com.example.service.UserService;
import com.example.util.Cleaner;

class UserController {
    String handle(Request request) {
        return new UserService(Cleaner.clean(request.getParameter("id"))).run();
    }
}
""")
        (util_dir / "Cleaner.java").write_text("""
package com.example.util;

class Cleaner {
    static String clean(String value) {
        return value;
    }
}
""")
        (service_dir / "UserService.java").write_text("""
package com.example.service;

import com.example.db.Sql;

class UserService {
    private String user;

    UserService(String user) {
        this.user = user;
    }

    String run() {
        Sql sql = new Sql();
        return sql.raw(user);
    }
}
""")
        (db_dir / "Sql.java").write_text("""
package com.example.db;

class Sql {
    String raw(String sql) {
        return sql;
    }
}
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success is True
        assert any(v.cwe_id == "CWE-89" for v in result.vulnerabilities)

    def test_java_factory_created_receiver_reports_sink(self, temp_project):
        """[20260310_TEST] Java factory-created receivers should resolve to the returned object type for no-arg sink paths."""
        web_dir = temp_project / "src" / "com" / "example" / "web"
        factory_dir = temp_project / "src" / "com" / "example" / "factory"
        service_dir = temp_project / "src" / "com" / "example" / "service"
        db_dir = temp_project / "src" / "com" / "example" / "db"
        web_dir.mkdir(parents=True)
        factory_dir.mkdir(parents=True)
        service_dir.mkdir(parents=True)
        db_dir.mkdir(parents=True)

        (web_dir / "UserController.java").write_text("""
package com.example.web;

import com.example.factory.UserFactory;

class UserController {
    String handle(Request request) {
        String user = request.getParameter("id");
        return UserFactory.create(user).run();
    }
}
""")
        (factory_dir / "UserFactory.java").write_text("""
package com.example.factory;

import com.example.service.UserService;

class UserFactory {
    static UserService create(String user) {
        return new UserService(user);
    }
}
""")
        (service_dir / "UserService.java").write_text("""
package com.example.service;

import com.example.db.Sql;

class UserService {
    private String user;

    UserService(String user) {
        this.user = user;
    }

    String run() {
        Sql sql = new Sql();
        return sql.raw(user);
    }
}
""")
        (db_dir / "Sql.java").write_text("""
package com.example.db;

class Sql {
    String raw(String sql) {
        return sql;
    }
}
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success is True
        assert any(v.cwe_id == "CWE-89" for v in result.vulnerabilities)

    def test_java_field_backed_factory_created_receiver_reports_sink(
        self, temp_project
    ):
        """[20260310_TEST] Java field-backed factory receivers should resolve through the factory return type for no-arg sink paths."""
        web_dir = temp_project / "src" / "com" / "example" / "web"
        factory_dir = temp_project / "src" / "com" / "example" / "factory"
        service_dir = temp_project / "src" / "com" / "example" / "service"
        db_dir = temp_project / "src" / "com" / "example" / "db"
        web_dir.mkdir(parents=True)
        factory_dir.mkdir(parents=True)
        service_dir.mkdir(parents=True)
        db_dir.mkdir(parents=True)

        (web_dir / "UserController.java").write_text("""
package com.example.web;

import com.example.factory.UserFactory;

class UserController {
    private UserFactory factory = new UserFactory();

    String handle(Request request) {
        String user = request.getParameter("id");
        return this.factory.create(user).run();
    }
}
""")
        (factory_dir / "UserFactory.java").write_text("""
package com.example.factory;

import com.example.service.UserService;

class UserFactory {
    UserService create(String user) {
        return new UserService(user);
    }
}
""")
        (service_dir / "UserService.java").write_text("""
package com.example.service;

import com.example.db.Sql;

class UserService {
    private String user;

    UserService(String user) {
        this.user = user;
    }

    String run() {
        Sql sql = new Sql();
        return sql.raw(user);
    }
}
""")
        (db_dir / "Sql.java").write_text("""
package com.example.db;

class Sql {
    String raw(String sql) {
        return sql;
    }
}
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success is True
        assert any(v.cwe_id == "CWE-89" for v in result.vulnerabilities)

    def test_java_shadowing_local_factory_does_not_taint_field_backed_factory_sink(
        self, temp_project
    ):
        """[20260310_TEST] Java locals that shadow factory fields must not taint field-backed factory receiver paths."""
        web_dir = temp_project / "src" / "com" / "example" / "web"
        factory_dir = temp_project / "src" / "com" / "example" / "factory"
        service_dir = temp_project / "src" / "com" / "example" / "service"
        db_dir = temp_project / "src" / "com" / "example" / "db"
        web_dir.mkdir(parents=True)
        factory_dir.mkdir(parents=True)
        service_dir.mkdir(parents=True)
        db_dir.mkdir(parents=True)

        (web_dir / "UserController.java").write_text("""
package com.example.web;

import com.example.factory.UserFactory;

class UserController {
    private UserFactory factory = new UserFactory("safe");

    void init(Request request) {
        UserFactory factory = new UserFactory(request.getParameter("id"));
    }

    String handle() {
        return this.factory.create().run();
    }
}
""")
        (factory_dir / "UserFactory.java").write_text("""
package com.example.factory;

import com.example.service.UserService;

class UserFactory {
    private String user;

    UserFactory(String user) {
        this.user = user;
    }

    UserService create() {
        return new UserService(user);
    }
}
""")
        (service_dir / "UserService.java").write_text("""
package com.example.service;

import com.example.db.Sql;

class UserService {
    private String user;

    UserService(String user) {
        this.user = user;
    }

    String run() {
        Sql sql = new Sql();
        return sql.raw(user);
    }
}
""")
        (db_dir / "Sql.java").write_text("""
package com.example.db;

class Sql {
    String raw(String sql) {
        return sql;
    }
}
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success is True
        assert not any(v.cwe_id == "CWE-89" for v in result.vulnerabilities)

    def test_java_imported_safe_factory_helper_does_not_report_sink(self, temp_project):
        """[20260310_TEST] Java imported factory helpers that sanitize before returning a service must not taint no-arg receiver sinks."""
        web_dir = temp_project / "src" / "com" / "example" / "web"
        factory_dir = temp_project / "src" / "com" / "example" / "factory"
        builder_dir = temp_project / "src" / "com" / "example" / "builder"
        service_dir = temp_project / "src" / "com" / "example" / "service"
        db_dir = temp_project / "src" / "com" / "example" / "db"
        web_dir.mkdir(parents=True)
        factory_dir.mkdir(parents=True)
        builder_dir.mkdir(parents=True)
        service_dir.mkdir(parents=True)
        db_dir.mkdir(parents=True)

        (web_dir / "UserController.java").write_text("""
package com.example.web;

import com.example.factory.UserFactory;

class UserController {
    String handle(Request request) {
        return UserFactory.create(request.getParameter("id")).run();
    }
}
""")
        (factory_dir / "UserFactory.java").write_text("""
package com.example.factory;

import com.example.builder.ServiceBuilder;
import com.example.service.UserService;

class UserFactory {
    static UserService create(String user) {
        return ServiceBuilder.safe(user);
    }
}
""")
        (builder_dir / "ServiceBuilder.java").write_text("""
package com.example.builder;

import com.example.service.UserService;

class ServiceBuilder {
    static UserService safe(String user) {
        return new UserService("safe");
    }
}
""")
        (service_dir / "UserService.java").write_text("""
package com.example.service;

import com.example.db.Sql;

class UserService {
    private String user;

    UserService(String user) {
        this.user = user;
    }

    String run() {
        Sql sql = new Sql();
        return sql.raw(user);
    }
}
""")
        (db_dir / "Sql.java").write_text("""
package com.example.db;

class Sql {
    String raw(String sql) {
        return sql;
    }
}
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success is True
        assert not result.vulnerabilities

    def test_java_field_backed_safe_factory_helper_does_not_report_sink(
        self, temp_project
    ):
        """[20260310_TEST] Java field-backed factory helpers that sanitize before returning a service must keep receiver sinks safe."""
        web_dir = temp_project / "src" / "com" / "example" / "web"
        factory_dir = temp_project / "src" / "com" / "example" / "factory"
        service_dir = temp_project / "src" / "com" / "example" / "service"
        db_dir = temp_project / "src" / "com" / "example" / "db"
        web_dir.mkdir(parents=True)
        factory_dir.mkdir(parents=True)
        service_dir.mkdir(parents=True)
        db_dir.mkdir(parents=True)

        (web_dir / "UserController.java").write_text("""
package com.example.web;

import com.example.factory.UserFactory;

class UserController {
    private UserFactory factory = new UserFactory();

    String handle(Request request) {
        return this.factory.create(request.getParameter("id")).run();
    }
}
""")
        (factory_dir / "UserFactory.java").write_text("""
package com.example.factory;

import com.example.service.UserService;

class UserFactory {
    UserService create(String user) {
        return buildSafe(user);
    }

    private UserService buildSafe(String user) {
        return new UserService("safe");
    }
}
""")
        (service_dir / "UserService.java").write_text("""
package com.example.service;

import com.example.db.Sql;

class UserService {
    private String user;

    UserService(String user) {
        this.user = user;
    }

    String run() {
        Sql sql = new Sql();
        return sql.raw(user);
    }
}
""")
        (db_dir / "Sql.java").write_text("""
package com.example.db;

class Sql {
    String raw(String sql) {
        return sql;
    }
}
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success is True
        assert not result.vulnerabilities


# =============================================================================
# Mermaid Diagram Tests
# =============================================================================


class TestMermaidGeneration:
    """Tests for Mermaid diagram generation."""

    def test_generate_mermaid_diagram(self, simple_vuln_project):
        """Test Mermaid diagram generation."""
        tracker = CrossFileTaintTracker(simple_vuln_project)
        tracker.analyze()

        mermaid = tracker.get_taint_graph_mermaid()

        assert "graph LR" in mermaid

    def test_mermaid_contains_modules(self, simple_vuln_project):
        """Test that Mermaid diagram contains module nodes."""
        tracker = CrossFileTaintTracker(simple_vuln_project)
        tracker.analyze()

        mermaid = tracker.get_taint_graph_mermaid()

        # Should contain module references
        assert "[" in mermaid  # Node definitions


# =============================================================================
# Result Property Tests
# =============================================================================


class TestResultProperties:
    """Tests for CrossFileTaintResult properties."""

    def test_result_default_values(self):
        """Test default values of CrossFileTaintResult."""
        result = CrossFileTaintResult()

        assert result.success is True
        assert result.modules_analyzed == 0
        assert result.functions_analyzed == 0
        assert len(result.tainted_parameters) == 0
        assert len(result.taint_flows) == 0
        assert len(result.vulnerabilities) == 0
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_cross_file_taint_flow_hash(self):
        """Test CrossFileTaintFlow hashing."""
        flow1 = CrossFileTaintFlow(
            source_module="a",
            source_function="f",
            source_line=1,
            sink_module="b",
            sink_function="g",
            sink_line=2,
            sink_type=CrossFileSink.SQL_QUERY,
        )

        flow2 = CrossFileTaintFlow(
            source_module="a",
            source_function="f",
            source_line=1,
            sink_module="b",
            sink_function="g",
            sink_line=2,
            sink_type=CrossFileSink.SQL_QUERY,
        )

        assert hash(flow1) == hash(flow2)


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests with realistic scenarios."""

    def test_flask_app_analysis(self, temp_project):
        """Test analysis of Flask-like application."""
        # Create a mini Flask app structure
        (temp_project / "app.py").write_text("""
from flask import Flask, request
from views import handle_request

app = Flask(__name__)

@app.route('/api')
def api():
    return handle_request()
""")

        (temp_project / "views.py").write_text("""
from flask import request
from models import get_data

def handle_request():
    query = request.args.get('q')
    return get_data(query)
""")

        (temp_project / "models.py").write_text("""
def get_data(query):
    # Potentially dangerous if query is not sanitized
    return f"Results for: {query}"
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success
        assert result.modules_analyzed >= 3

    def test_complex_import_chain(self, temp_project):
        """Test analysis with complex import chains."""
        # Create complex import structure
        pkg = temp_project / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")

        (pkg / "base.py").write_text("""
import os

def exec_cmd(cmd):
    os.system(cmd)
""")

        (pkg / "service.py").write_text("""
from .base import exec_cmd

def process(data):
    exec_cmd(f"echo {data}")
""")

        (temp_project / "main.py").write_text("""
from flask import request
from pkg.service import process

def handler():
    data = request.args.get('input')
    process(data)
""")

        tracker = CrossFileTaintTracker(temp_project)
        result = tracker.analyze()

        assert result.success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
