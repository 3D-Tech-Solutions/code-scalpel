# [20260106_TEST] Multi-language support via file_path extension detection
from __future__ import annotations

import textwrap

import pytest

pytestmark = pytest.mark.asyncio


async def test_javascript_dom_xss_via_file_path(tmp_path):
    js_code = textwrap.dedent("""
        function render(userInput) {
          document.getElementById('t').innerHTML = userInput;
          document.write(userInput);
          const el = document.getElementById('c');
          el.insertAdjacentHTML('beforeend', userInput);
        }
        """).strip() + "\n"
    js_file = tmp_path / "sample.js"
    js_file.write_text(js_code, encoding="utf-8")

    from code_scalpel.mcp.server import security_scan

    result = await security_scan(file_path=str(js_file))

    assert result.success is True
    assert result.vulnerability_count >= 1
    assert any(v.cwe == "CWE-79" or "xss" in v.type.lower() for v in result.vulnerabilities)


# [20260107_TEST] TypeScript language support tests
async def test_typescript_dom_xss(tmp_path):
    """TypeScript innerHTML XSS detection."""
    ts_code = textwrap.dedent("""
        function renderUser(name: string): void {
          const userDiv = document.getElementById('user');
          if (userDiv) {
            userDiv.innerHTML = name; // XSS vulnerability
          }
        }
        """).strip() + "\n"
    ts_file = tmp_path / "app.ts"
    ts_file.write_text(ts_code, encoding="utf-8")

    from code_scalpel.mcp.server import security_scan

    result = await security_scan(file_path=str(ts_file))

    assert result.success is True
    assert result.vulnerability_count >= 1
    assert any(v.cwe == "CWE-79" or "xss" in v.type.lower() for v in result.vulnerabilities)


@pytest.mark.skip(
    reason="TypeScript SQL injection pattern not yet supported - requires TS-specific template literal parser"
)
async def test_typescript_sql_injection(tmp_path):
    """TypeScript SQL injection via template strings."""
    ts_code = textwrap.dedent("""
        async function getUser(id: string): Promise<any> {
          const query = `SELECT * FROM users WHERE id=${id}`;  // SQL injection
          return await database.query(query);
        }
        """).strip() + "\n"
    ts_file = tmp_path / "db.ts"
    ts_file.write_text(ts_code, encoding="utf-8")

    from code_scalpel.mcp.server import security_scan

    result = await security_scan(file_path=str(ts_file))

    assert result.success is True
    assert result.vulnerability_count >= 1
    assert any(v.cwe == "CWE-89" or "sql" in v.type.lower() for v in result.vulnerabilities)


@pytest.mark.skip(
    reason="TypeScript command injection via template literals not yet supported - requires TS parser enhancement"
)
async def test_typescript_command_injection(tmp_path):
    """TypeScript command injection via child_process."""
    ts_code = textwrap.dedent("""
        import { exec } from 'child_process';
        function runCommand(userCmd: string): void {
          exec(`ls -la ${userCmd}`);  // Command injection
        }
        """).strip() + "\n"
    ts_file = tmp_path / "cmd.ts"
    ts_file.write_text(ts_code, encoding="utf-8")

    from code_scalpel.mcp.server import security_scan

    result = await security_scan(file_path=str(ts_file))

    assert result.success is True
    assert result.vulnerability_count >= 1
    assert any(v.cwe == "CWE-78" or "command" in v.type.lower() for v in result.vulnerabilities)


# [20260107_TEST] Java language support tests
async def test_java_sql_injection_spring(tmp_path):
    """Java Spring SQL injection detection."""
    java_code = textwrap.dedent("""
        @GetMapping("/user")
        public User getUser(@RequestParam String id) {
          String query = "SELECT * FROM users WHERE id=" + id;  // SQL injection
          return jdbcTemplate.queryForObject(query, User.class);
        }
        """).strip() + "\n"
    java_file = tmp_path / "UserController.java"
    java_file.write_text(java_code, encoding="utf-8")

    from code_scalpel.mcp.server import security_scan

    result = await security_scan(file_path=str(java_file))

    assert result.success is True
    assert result.vulnerability_count >= 1
    assert any(v.cwe == "CWE-89" or "sql" in v.type.lower() for v in result.vulnerabilities)


@pytest.mark.skip(reason="Java JNDI injection patterns not yet implemented - requires Java-specific semantic analysis")
async def test_java_jndi_injection(tmp_path):
    """Java JNDI injection detection (Log4Shell variant)."""
    java_code = textwrap.dedent("""
        public void logUserInput(String input) {
          Context context = new InitialContext();
          context.lookup(input);  // JNDI injection vulnerability
        }
        """).strip() + "\n"
    java_file = tmp_path / "Logger.java"
    java_file.write_text(java_code, encoding="utf-8")

    from code_scalpel.mcp.server import security_scan

    result = await security_scan(file_path=str(java_file))

    assert result.success is True
    # JNDI may be flagged as code injection (CWE-94) or detected via pattern matching
    assert result.vulnerability_count >= 1


@pytest.mark.skip(reason="JSP XSS patterns not yet supported - requires JSP/servlet parser")
async def test_java_xss_jsp(tmp_path):
    """Java JSP XSS detection."""
    java_code = textwrap.dedent("""
        <%
        String userName = request.getParameter("name");
        out.println("<div>" + userName + "</div>");  // XSS
        %>
        """).strip() + "\n"
    jsp_file = tmp_path / "user.jsp"
    jsp_file.write_text(java_code, encoding="utf-8")

    from code_scalpel.mcp.server import security_scan

    result = await security_scan(file_path=str(jsp_file))

    assert result.success is True
    assert result.vulnerability_count >= 1
    assert any(v.cwe == "CWE-79" or "xss" in v.type.lower() for v in result.vulnerabilities)
