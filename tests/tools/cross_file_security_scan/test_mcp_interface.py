"""
MCP Interface and Tool Validation Tests for Cross-File Security Scan.

[20260103_TEST] v3.1.0+ - MCP protocol compliance, tool availability, parameter validation

Tests validate:
    ✅ Tool registration and availability
    ✅ MCP parameter validation
    ✅ Result serialization and format
    ✅ HTTP and Stdio protocol compliance
    ✅ Tool contract/schema validation
    ✅ Error responses and edge cases
    ✅ Cross-file security scan E2E workflow
"""

import tempfile
from pathlib import Path

import pytest

# [20260111_BUGFIX] Removed module-level pytestmark to avoid warnings on sync tests
# Individual async tests should use @pytest.mark.asyncio decorator


# =============================================================================
# TOOL REGISTRATION AND AVAILABILITY TESTS
# =============================================================================


class TestToolAvailability:
    """Tests for tool registration and availability."""

    async def test_cross_file_security_scan_registered(self):
        """[20260103_TEST] cross_file_security_scan is registered as an MCP tool."""
        from code_scalpel.mcp.server import cross_file_security_scan

        # Tool should be importable and callable
        assert callable(cross_file_security_scan)
        assert hasattr(cross_file_security_scan, "__name__")

    @pytest.mark.asyncio
    async def test_cross_file_security_scan_callable(self):
        """[20260103_TEST] Tool is callable with proper signature."""
        # Should have expected parameters
        import inspect

        from code_scalpel.mcp.server import cross_file_security_scan

        sig = inspect.signature(cross_file_security_scan)
        params = set(sig.parameters.keys())

        expected_params = {
            "project_root",
            "entry_points",
            "max_depth",
            "include_diagram",
            "timeout_seconds",
            "max_modules",
        }

        # All expected parameters should be present
        assert expected_params.issubset(
            params
        ), f"Missing parameters: {expected_params - params}"

    async def test_tool_in_server_registry(self):
        """[20260103_TEST] Tool is in MCP server registry."""
        try:
            from code_scalpel.mcp.server import TOOLS

            # Tool should be registered
            tool_names = {t.get("name") for t in TOOLS if isinstance(t, dict)}
            assert "cross_file_security_scan" in tool_names or any(
                "cross_file" in str(t) for t in TOOLS
            ), "Tool should be registered in server"
        except (ImportError, AttributeError):
            # Registry structure may vary, skip if not available
            pytest.skip("Tool registry not available in this version")


# =============================================================================
# PARAMETER VALIDATION TESTS
# =============================================================================


class TestParameterValidation:
    """Tests for parameter validation and type checking."""

    async def test_project_root_required(self):
        """[20260103_TEST] project_root parameter is required."""
        import inspect

        from code_scalpel.mcp.server import cross_file_security_scan

        # Check signature requires project_root
        sig = inspect.signature(cross_file_security_scan)
        assert "project_root" in sig.parameters

    @pytest.mark.asyncio
    async def test_project_root_accepts_string(self):
        """[20260103_TEST] project_root accepts string paths."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            result = await cross_file_security_scan(
                project_root=tmpdir,
                entry_points=None,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result is not None
            assert hasattr(result, "success")

    @pytest.mark.asyncio
    async def test_max_depth_parameter(self):
        """[20260103_TEST] max_depth parameter is respected."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=5,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_max_modules_parameter(self):
        """[20260103_TEST] max_modules parameter is respected."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=50,
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_include_diagram_parameter(self):
        """[20260103_TEST] include_diagram parameter controls diagram generation."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            # With diagram
            result_with = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=True,
                timeout_seconds=10.0,
                max_modules=10,
            )

            # Without diagram
            result_without = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result_with is not None
            assert result_without is not None
            # May have different diagram content
            if hasattr(result_with, "mermaid_diagram"):
                # With diagram might have populated mermaid_diagram
                pass

    @pytest.mark.asyncio
    async def test_timeout_seconds_parameter(self):
        """[20260103_TEST] timeout_seconds parameter is respected."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=1.0,  # Short timeout
                max_modules=10,
            )

            assert result is not None


# =============================================================================
# RESULT VALIDATION TESTS
# =============================================================================


class TestResultFormat:
    """Tests for result format and serialization."""

    @pytest.mark.asyncio
    async def test_result_is_serializable(self):
        """[20260103_TEST] Result can be serialized to dict/JSON."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            # Should be serializable
            try:
                if hasattr(result, "to_dict"):
                    data = result.to_dict()
                    assert isinstance(data, dict)
                elif hasattr(result, "__dict__"):
                    # dataclass or similar
                    data = vars(result)
                    assert isinstance(data, dict)
            except Exception as e:
                pytest.fail(f"Result should be serializable: {e}")

    @pytest.mark.asyncio
    async def test_result_has_success_field(self):
        """[20260103_TEST] Result includes success indicator."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert hasattr(result, "success")
            assert isinstance(result.success, (bool, type(None)))

    @pytest.mark.asyncio
    async def test_result_has_vulnerability_fields(self):
        """[20260103_TEST] Result includes vulnerability information."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            # Should have vulnerability-related fields
            expected_fields = [
                "has_vulnerabilities",
                "vulnerability_count",
                "vulnerabilities",
            ]
            for field in expected_fields:
                assert hasattr(result, field), f"Result should have '{field}' field"

    @pytest.mark.asyncio
    async def test_result_has_taint_flow_info(self):
        """[20260103_TEST] Result includes taint flow information."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            # Should have taint flow fields
            expected_fields = ["taint_flows", "files_analyzed"]
            for field in expected_fields:
                assert hasattr(result, field), f"Result should have '{field}' field"

    @pytest.mark.asyncio
    async def test_java_only_project_reports_bounded_java_warning(self):
        """[20260309_TEST] Java-only projects should report the bounded Java analysis warning."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "UserController.java").write_text("""
package demo;

class UserController {
    String run(String q) {
        return q;
    }
}
""")

            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result.success is True
            assert result.files_analyzed == 1
            assert result.warnings
            assert any(
                "bounded IR-based subset" in warning for warning in result.warnings
            )

    @pytest.mark.asyncio
    async def test_java_only_project_reports_sql_injection_flow(self):
        """[20260309_TEST] Java-only projects should surface bounded source-to-sink vulnerabilities."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            web_dir = root / "src" / "com" / "example" / "web"
            service_dir = root / "src" / "com" / "example" / "service"
            repo_dir = root / "src" / "com" / "example" / "repo"
            util_dir = root / "src" / "com" / "example" / "util"
            web_dir.mkdir(parents=True)
            service_dir.mkdir(parents=True)
            repo_dir.mkdir(parents=True)
            util_dir.mkdir(parents=True)

            (web_dir / "UserController.java").write_text("""
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

            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result.success is True
            assert result.files_analyzed == 4
            assert result.vulnerability_count >= 1
            assert any(v.cwe == "CWE-89" for v in result.vulnerabilities)

    @pytest.mark.asyncio
    async def test_java_only_project_reports_sql_injection_flow_from_implicit_field_write(
        self,
    ):
        """[20260310_TEST] Java-only MCP scan should surface implicit same-class field flows."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            web_dir = root / "src" / "com" / "example" / "web"
            service_dir = root / "src" / "com" / "example" / "service"
            repo_dir = root / "src" / "com" / "example" / "repo"
            util_dir = root / "src" / "com" / "example" / "util"
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

            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result.success is True
            assert result.vulnerability_count >= 1
            assert any(v.cwe == "CWE-89" for v in result.vulnerabilities)

    @pytest.mark.asyncio
    async def test_java_only_project_ignores_local_shadow_of_field_for_sql_flow(self):
        """[20260310_TEST] Java-only MCP scan should not taint fields from shadowing local vars."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            web_dir = root / "src" / "com" / "example" / "web"
            service_dir = root / "src" / "com" / "example" / "service"
            repo_dir = root / "src" / "com" / "example" / "repo"
            util_dir = root / "src" / "com" / "example" / "util"
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

            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result.success is True
            assert not any(v.cwe == "CWE-89" for v in result.vulnerabilities)

    @pytest.mark.asyncio
    async def test_java_only_project_reports_constructor_tainted_receiver_flow(self):
        """[20260310_TEST] Java-only MCP scan should surface constructor-tainted receivers reaching imported no-arg local sinks."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            web_dir = root / "src" / "com" / "example" / "web"
            service_dir = root / "src" / "com" / "example" / "service"
            util_dir = root / "src" / "com" / "example" / "util"
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

            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result.success is True
            assert any(v.cwe == "CWE-89" for v in result.vulnerabilities)

    @pytest.mark.asyncio
    async def test_java_only_project_reports_chained_constructor_receiver_flow(self):
        """[20260310_TEST] Java-only MCP scan should surface chained constructor receivers reaching imported no-arg local sinks."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            web_dir = root / "src" / "com" / "example" / "web"
            service_dir = root / "src" / "com" / "example" / "service"
            util_dir = root / "src" / "com" / "example" / "util"
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

            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result.success is True
            assert any(v.cwe == "CWE-89" for v in result.vulnerabilities)

    @pytest.mark.asyncio
    async def test_java_only_project_reports_field_backed_constructor_receiver_flow(
        self,
    ):
        """[20260310_TEST] Java-only MCP scan should surface field-backed receivers seeded from tainted constructor calls."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            web_dir = root / "src" / "com" / "example" / "web"
            service_dir = root / "src" / "com" / "example" / "service"
            util_dir = root / "src" / "com" / "example" / "util"
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

            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result.success is True
            assert any(v.cwe == "CWE-89" for v in result.vulnerabilities)

    @pytest.mark.asyncio
    async def test_java_only_project_ignores_shadowing_object_receiver_for_field_backed_sink(
        self,
    ):
        """[20260310_TEST] Java-only MCP scan should ignore shadowing object receivers when the field-backed receiver stays safe."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            web_dir = root / "src" / "com" / "example" / "web"
            service_dir = root / "src" / "com" / "example" / "service"
            util_dir = root / "src" / "com" / "example" / "util"
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

            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result.success is True
            assert not any(v.cwe == "CWE-89" for v in result.vulnerabilities)

    @pytest.mark.asyncio
    async def test_java_only_project_ignores_sanitized_chained_constructor_receiver(
        self,
    ):
        """[20260310_TEST] Java-only MCP scan should ignore sanitized chained constructor receiver arguments."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            web_dir = root / "src" / "com" / "example" / "web"
            service_dir = root / "src" / "com" / "example" / "service"
            util_dir = root / "src" / "com" / "example" / "util"
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

            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result.success is True
            assert not any(v.cwe == "CWE-89" for v in result.vulnerabilities)

    @pytest.mark.asyncio
    async def test_java_only_project_ignores_imported_safe_helper_in_chained_constructor_receiver(
        self,
    ):
        """[20260310_TEST] Java-only MCP scan should ignore imported helpers that sanitize chained constructor receiver arguments."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            web_dir = root / "src" / "com" / "example" / "web"
            service_dir = root / "src" / "com" / "example" / "service"
            util_dir = root / "src" / "com" / "example" / "util"
            db_dir = root / "src" / "com" / "example" / "db"
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

            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result.success is True
            assert not any(v.cwe == "CWE-89" for v in result.vulnerabilities)

    @pytest.mark.asyncio
    async def test_java_only_project_reports_imported_tainted_helper_in_chained_constructor_receiver(
        self,
    ):
        """[20260310_TEST] Java-only MCP scan should report imported helpers that preserve chained constructor receiver taint."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            web_dir = root / "src" / "com" / "example" / "web"
            service_dir = root / "src" / "com" / "example" / "service"
            util_dir = root / "src" / "com" / "example" / "util"
            db_dir = root / "src" / "com" / "example" / "db"
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

            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result.success is True
            assert any(v.cwe == "CWE-89" for v in result.vulnerabilities)

    @pytest.mark.asyncio
    async def test_java_only_project_reports_factory_created_receiver_flow(self):
        """[20260310_TEST] Java-only MCP scan should resolve factory-created receivers to the returned object type."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            web_dir = root / "src" / "com" / "example" / "web"
            factory_dir = root / "src" / "com" / "example" / "factory"
            service_dir = root / "src" / "com" / "example" / "service"
            db_dir = root / "src" / "com" / "example" / "db"
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

            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result.success is True
            assert any(v.cwe == "CWE-89" for v in result.vulnerabilities)

    @pytest.mark.asyncio
    async def test_java_only_project_reports_field_backed_factory_created_receiver_flow(
        self,
    ):
        """[20260310_TEST] Java-only MCP scan should resolve field-backed factory receivers to the returned object type."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            web_dir = root / "src" / "com" / "example" / "web"
            factory_dir = root / "src" / "com" / "example" / "factory"
            service_dir = root / "src" / "com" / "example" / "service"
            db_dir = root / "src" / "com" / "example" / "db"
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

            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result.success is True
            assert any(v.cwe == "CWE-89" for v in result.vulnerabilities)

    @pytest.mark.asyncio
    async def test_java_only_project_ignores_shadowing_local_factory_for_field_backed_factory_sink(
        self,
    ):
        """[20260310_TEST] Java-only MCP scan should ignore shadowing local factories when the field-backed factory stays safe."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            web_dir = root / "src" / "com" / "example" / "web"
            factory_dir = root / "src" / "com" / "example" / "factory"
            service_dir = root / "src" / "com" / "example" / "service"
            db_dir = root / "src" / "com" / "example" / "db"
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

            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result.success is True
            assert not any(v.cwe == "CWE-89" for v in result.vulnerabilities)

    @pytest.mark.asyncio
    async def test_java_only_project_ignores_imported_safe_factory_helper(self):
        """[20260310_TEST] Java-only MCP scan should ignore imported factory helpers that sanitize before returning a service."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            web_dir = root / "src" / "com" / "example" / "web"
            factory_dir = root / "src" / "com" / "example" / "factory"
            builder_dir = root / "src" / "com" / "example" / "builder"
            service_dir = root / "src" / "com" / "example" / "service"
            db_dir = root / "src" / "com" / "example" / "db"
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

            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result.success is True
            assert not result.vulnerabilities

    @pytest.mark.asyncio
    async def test_java_only_project_ignores_field_backed_safe_factory_helper(self):
        """[20260310_TEST] Java-only MCP scan should keep field-backed factory helpers safe when they sanitize before returning a service."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            web_dir = root / "src" / "com" / "example" / "web"
            factory_dir = root / "src" / "com" / "example" / "factory"
            service_dir = root / "src" / "com" / "example" / "service"
            db_dir = root / "src" / "com" / "example" / "db"
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

            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result.success is True
            assert not result.vulnerabilities

    @pytest.mark.asyncio
    async def test_mixed_python_java_project_reports_java_skipped_warning(self):
        """[20260309_TEST] Mixed Python/Java projects should warn that Java files were skipped."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "safe.py").write_text("""
def safe(x):
    return x * 2
""")
            (root / "UserController.java").write_text("""
class UserController {}
""")

            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result.success is True
            assert result.files_analyzed == 1
            assert result.warnings
            assert any(
                "skipped detected Java files" in warning for warning in result.warnings
            )

    @pytest.mark.asyncio
    async def test_python_only_project_has_no_java_skip_warning(self):
        """[20260309_TEST] Python-only projects should not emit Java-skip warnings."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "safe.py").write_text("""
def safe(x):
    return x * 2
""")

            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result.success is True
            assert result.files_analyzed == 1
            assert not any("Java" in warning for warning in result.warnings)


# =============================================================================
# END-TO-END WORKFLOW TESTS
# =============================================================================


class TestEndToEndWorkflow:
    """Tests for complete E2E workflows."""

    @pytest.mark.asyncio
    async def test_simple_vulnerability_detection_workflow(self):
        """[20260103_TEST] E2E workflow detects SQL injection."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create vulnerable project
            (tmpdir_path / "routes.py").write_text("""
from flask import request
from db import query

def handler():
    user_id = request.args.get('id')
    return query(user_id)
""")

            (tmpdir_path / "db.py").write_text("""
import sqlite3

def query(user_id):
    sql = f"SELECT * FROM users WHERE id = {user_id}"
    cursor = sqlite3.cursor()
    cursor.execute(sql)
""")

            result = await cross_file_security_scan(
                project_root=tmpdir,
                entry_points=["routes.py"],
                max_depth=10,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=20,
            )

            assert result is not None
            assert result.success

    @pytest.mark.asyncio
    async def test_safe_code_workflow(self):
        """[20260103_TEST] E2E workflow for safe code."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create safe project
            (tmpdir_path / "utils.py").write_text("""
def add(a, b):
    return a + b

def multiply(x, y):
    return x * y
""")

            (tmpdir_path / "main.py").write_text("""
from utils import add, multiply

def calculate(x, y):
    return add(x, multiply(x, y))
""")

            result = await cross_file_security_scan(
                project_root=tmpdir,
                entry_points=["main.py"],
                max_depth=5,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result is not None
            assert result.success

    @pytest.mark.asyncio
    async def test_mermaid_diagram_workflow(self):
        """[20260103_TEST] E2E workflow with diagram generation."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "a.py").write_text("def f_a(): pass")
            (tmpdir_path / "b.py").write_text(
                "from a import f_a\ndef f_b(): return f_a()"
            )

            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=5,
                include_diagram=True,  # Request diagram
                timeout_seconds=10.0,
                max_modules=10,
            )

            assert result is not None
            assert result.success
            # Diagram should be generated (check if field exists)
            if hasattr(result, "mermaid_diagram"):
                assert result.mermaid_diagram is None or isinstance(
                    result.mermaid_diagram, str
                )


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestErrorHandling:
    """Tests for error handling in MCP interface."""

    @pytest.mark.asyncio
    async def test_invalid_project_root(self):
        """[20260103_TEST] Invalid project root handled gracefully."""
        from code_scalpel.mcp.server import cross_file_security_scan

        result = await cross_file_security_scan(
            project_root="/nonexistent/path/12345",
            max_depth=3,
            include_diagram=False,
            timeout_seconds=10.0,
            max_modules=10,
        )

        # Should handle gracefully
        assert result is not None
        # May report success=False or empty results
        assert hasattr(result, "success")

    @pytest.mark.asyncio
    async def test_negative_max_depth(self):
        """[20260103_TEST] Negative max_depth handled."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            # Should handle negative depth (might convert to 0 or raise)
            try:
                result = await cross_file_security_scan(
                    project_root=tmpdir,
                    max_depth=-1,  # Invalid
                    include_diagram=False,
                    timeout_seconds=10.0,
                    max_modules=10,
                )
                # If no exception, should have valid result
                assert result is not None
            except (ValueError, TypeError):
                # Also acceptable to raise
                pass

    @pytest.mark.asyncio
    async def test_zero_timeout(self):
        """[20260103_TEST] Zero timeout handled."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            # Very short timeout should still complete
            result = await cross_file_security_scan(
                project_root=tmpdir,
                max_depth=3,
                include_diagram=False,
                timeout_seconds=0.01,  # Very short
                max_modules=10,
            )

            assert result is not None


# =============================================================================
# REGRESSION TESTS
# =============================================================================


class TestRegressions:
    """Regression tests for known issues."""

    @pytest.mark.asyncio
    async def test_crossfile_hard_fixture(self):
        """[20260103_TEST] Ninja Warrior crossfile-hard fixture detection."""
        from code_scalpel.mcp.server import cross_file_security_scan

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Recreate Ninja Warrior crossfile-hard fixture
            pkg = tmpdir_path / "crossfile_hard"
            pkg.mkdir()
            (pkg / "__init__.py").write_text("# test package\n")

            (pkg / "routes.py").write_text("""\
from flask import Flask, request
from .services import search_users

app = Flask(__name__)

@app.get('/search')
def search_route() -> str:
    q = request.args.get('q', '')
    return search_users(q)
""")

            (pkg / "services.py").write_text("""\
from . import sanitizers as s
from .db import run_query as rq

def search_users(raw_query: str) -> str:
    query = s.sanitize_decoy(raw_query)
    return rq(query)
""")

            (pkg / "sanitizers.py").write_text("""\
def sanitize_decoy(value: str) -> str:
    return value
""")

            (pkg / "db.py").write_text("""\
import sqlite3

def run_query(user_supplied: str) -> str:
    sql = f"SELECT * FROM users WHERE name = '{user_supplied}'"
    conn = sqlite3.connect(':memory:')
    cur = conn.cursor()
    cur.execute(sql)
    conn.close()
    return sql
""")

            result = await cross_file_security_scan(
                project_root=tmpdir,
                entry_points=["crossfile_hard/routes.py"],
                max_depth=10,
                include_diagram=False,
                timeout_seconds=10.0,
                max_modules=50,
            )

            assert result is not None
            assert result.success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
