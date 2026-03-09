"""
Unified Security Sink Detector - Polyglot vulnerability detection with confidence scoring.

This module provides a unified approach to security sink detection across multiple languages
(Python, Java, TypeScript, JavaScript) with explicit confidence scoring for each pattern.

Key Features:
- Language-agnostic sink definitions with confidence scores
- OWASP Top 10 2021 complete coverage
- Context-aware vulnerability assessment
- Sanitizer detection and validation
- Parameterization detection

[20251216_FEATURE] v2.3.0 - Unified polyglot sink detection with confidence scoring
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, TypedDict


class CoverageReportDict(TypedDict, total=False):
    """Coverage report for security sinks."""

    total_patterns: int
    by_language: dict[str, int]
    by_vulnerability: dict[str, dict[str, int]]
    owasp_coverage: dict[str, dict[str, Any]]


# [20260102_REFACTOR] Keep imports below to allow type declarations before heavy modules.
# ruff: noqa: E402
from .taint_tracker import SecuritySink, TaintInfo, TaintLevel


class Language(Enum):
    """Supported languages for unified sink detection."""

    PYTHON = "python"
    JAVA = "java"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    RUST = "rust"  # [20260305_FEATURE] Rust language support


@dataclass
class SinkDefinition:
    """
    Definition of a security sink with confidence scoring.

    Attributes:
        pattern: Function/method pattern to match (e.g., "cursor.execute")
        confidence: Confidence score 0.0-1.0 (1.0 = definitely vulnerable)
        sink_type: Type of security sink (SQL_QUERY, XSS, etc.)
        description: Human-readable description
    """

    pattern: str
    confidence: float
    sink_type: SecuritySink
    description: str = ""

    def __post_init__(self):
        """Validate confidence score."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            )


@dataclass
class DetectedSink:
    """
    A detected security sink in code.

    Attributes:
        pattern: The matched pattern
        sink_type: Type of security sink
        confidence: Confidence score for this detection
        line: Line number in source code
        column: Column number in source code
        code_snippet: The actual code that matched
        vulnerability_type: OWASP category or CWE identifier
    """

    pattern: str
    sink_type: SecuritySink
    confidence: float
    line: int
    column: int
    code_snippet: str
    vulnerability_type: str = ""

    @property
    def name(self) -> str:
        """[20251228_BUGFIX] Backwards-compatible alias for sink name."""
        return self.pattern.rsplit(".", 1)[-1]


# [20251216_FEATURE] Unified sink registry with confidence scores across all languages

# [20251216_FEATURE] Unified sink registry with confidence scores across all languages
UNIFIED_SINKS: Dict[str, Dict[str, List[SinkDefinition]]] = {
    # ==========================================================================
    # A03:2021 – Injection - SQL Injection
    # ==========================================================================
    "sql_injection": {
        "python": [
            SinkDefinition(
                "cursor.execute", 0.5, SecuritySink.SQL_QUERY, "Raw SQL execution"
            ),
            SinkDefinition(
                "connection.execute",
                0.5,
                SecuritySink.SQL_QUERY,
                "Direct connection execute",
            ),
            SinkDefinition(
                "session.execute",
                0.5,
                SecuritySink.SQL_QUERY,
                "SQLAlchemy session execute",
            ),
            SinkDefinition(
                "engine.execute",
                0.5,
                SecuritySink.SQL_QUERY,
                "SQLAlchemy engine execute",
            ),
            SinkDefinition(
                "db.execute", 0.5, SecuritySink.SQL_QUERY, "Generic database execute"
            ),
            SinkDefinition(
                "cursor.executemany", 0.5, SecuritySink.SQL_QUERY, "Batch SQL execution"
            ),
            SinkDefinition("RawSQL", 0.5, SecuritySink.SQL_QUERY, "Django raw SQL"),
            SinkDefinition(
                "QuerySet.extra", 0.5, SecuritySink.SQL_QUERY, "Django QuerySet extra"
            ),
            SinkDefinition(
                "sqlalchemy.text", 0.5, SecuritySink.SQL_QUERY, "SQLAlchemy text query"
            ),
        ],
        "java": [
            SinkDefinition(
                "Statement.executeQuery",
                0.9,
                SecuritySink.SQL_QUERY,
                "JDBC Statement query",
            ),
            SinkDefinition(
                "Statement.executeUpdate",
                0.9,
                SecuritySink.SQL_QUERY,
                "JDBC Statement update",
            ),
            SinkDefinition(
                "Statement.execute",
                0.9,
                SecuritySink.SQL_QUERY,
                "JDBC Statement execute",
            ),
            SinkDefinition(
                "PreparedStatement.executeQuery",
                0.9,
                SecuritySink.SQL_QUERY,
                "PreparedStatement (safer if used correctly)",
            ),
            SinkDefinition(
                "entityManager.createQuery",
                0.9,
                SecuritySink.SQL_QUERY,
                "JPA JPQL query",
            ),
            SinkDefinition(
                "entityManager.createNativeQuery",
                0.9,
                SecuritySink.SQL_QUERY,
                "JPA native SQL",
            ),
            SinkDefinition(
                "jdbcTemplate.query",
                0.9,
                SecuritySink.SQL_QUERY,
                "Spring JdbcTemplate query",
            ),
            SinkDefinition(
                "jdbcTemplate.update",
                0.9,
                SecuritySink.SQL_QUERY,
                "Spring JdbcTemplate update",
            ),
        ],
        "typescript": [
            SinkDefinition(
                "connection.query", 0.5, SecuritySink.SQL_QUERY, "Direct SQL query"
            ),
            SinkDefinition(
                "pool.query", 0.5, SecuritySink.SQL_QUERY, "Connection pool query"
            ),
            SinkDefinition("knex.raw", 0.5, SecuritySink.SQL_QUERY, "Knex raw SQL"),
            SinkDefinition(
                "knex.whereRaw", 0.5, SecuritySink.SQL_QUERY, "Knex raw where clause"
            ),
            SinkDefinition(
                "sequelize.query", 0.5, SecuritySink.SQL_QUERY, "Sequelize raw query"
            ),
            SinkDefinition(
                "prisma.$queryRaw", 0.5, SecuritySink.SQL_QUERY, "Prisma raw query"
            ),
            SinkDefinition(
                "typeorm.query", 0.5, SecuritySink.SQL_QUERY, "TypeORM raw query"
            ),
        ],
        "javascript": [
            SinkDefinition(
                "db.query", 0.5, SecuritySink.SQL_QUERY, "Generic database query"
            ),
            SinkDefinition(
                "sequelize.query", 0.8, SecuritySink.SQL_QUERY, "Sequelize query"
            ),
            SinkDefinition(
                "mysql.query", 0.95, SecuritySink.SQL_QUERY, "MySQL driver query"
            ),
            SinkDefinition(
                "pg.query", 0.95, SecuritySink.SQL_QUERY, "PostgreSQL driver query"
            ),
            SinkDefinition(
                "Model.find", 0.7, SecuritySink.SQL_QUERY, "MongoDB/Mongoose find"
            ),
        ],
        # [20260305_FEATURE] Polyglot SQL injection sinks - Go/C/C++/C#/Kotlin/PHP/Ruby/Swift
        "go": [
            SinkDefinition("db.Query", 0.95, SecuritySink.SQL_QUERY, "sql.DB Query"),
            SinkDefinition("db.QueryRow", 0.95, SecuritySink.SQL_QUERY, "sql.DB QueryRow"),
            SinkDefinition("db.Exec", 0.9, SecuritySink.SQL_QUERY, "sql.DB Exec"),
            SinkDefinition("sqlx.Get", 0.9, SecuritySink.SQL_QUERY, "sqlx Get"),
            SinkDefinition("sqlx.Select", 0.9, SecuritySink.SQL_QUERY, "sqlx Select"),
            SinkDefinition(".QueryContext", 0.9, SecuritySink.SQL_QUERY, "Context query"),
        ],
        "c": [
            SinkDefinition("sqlite3_exec", 0.95, SecuritySink.SQL_QUERY, "SQLite3 exec"),
            SinkDefinition("sqlite3_prepare", 0.9, SecuritySink.SQL_QUERY, "SQLite3 prepare"),
            SinkDefinition("PQexec", 0.95, SecuritySink.SQL_QUERY, "libpq PQexec"),
            SinkDefinition("mysql_query", 0.95, SecuritySink.SQL_QUERY, "MySQL C API query"),
        ],
        "cpp": [
            SinkDefinition("sqlite3_exec", 0.95, SecuritySink.SQL_QUERY, "SQLite3 exec"),
            SinkDefinition("sqlite3_prepare_v2", 0.9, SecuritySink.SQL_QUERY, "SQLite3 prepare"),
            SinkDefinition("execute(", 0.8, SecuritySink.SQL_QUERY, "ORM execute"),
        ],
        "csharp": [
            SinkDefinition("SqlCommand", 0.95, SecuritySink.SQL_QUERY, "ADO.NET SqlCommand"),
            SinkDefinition("ExecuteReader", 0.9, SecuritySink.SQL_QUERY, "ADO.NET ExecuteReader"),
            SinkDefinition("ExecuteNonQuery", 0.9, SecuritySink.SQL_QUERY, "ADO.NET ExecuteNonQuery"),
            SinkDefinition("ExecuteScalar", 0.9, SecuritySink.SQL_QUERY, "ADO.NET ExecuteScalar"),
            SinkDefinition("DbCommand", 0.85, SecuritySink.SQL_QUERY, "ADO.NET DbCommand"),
            SinkDefinition(".FromSqlRaw", 0.95, SecuritySink.SQL_QUERY, "EF Core raw SQL"),
            SinkDefinition(".ExecuteSqlRaw", 0.95, SecuritySink.SQL_QUERY, "EF Core execute raw SQL"),
        ],
        "kotlin": [
            SinkDefinition("jdbcTemplate.queryForObject", 0.9, SecuritySink.SQL_QUERY, "Spring JdbcTemplate"),
            SinkDefinition("jdbcTemplate.query", 0.9, SecuritySink.SQL_QUERY, "Spring JdbcTemplate query"),
            SinkDefinition("createQuery", 0.85, SecuritySink.SQL_QUERY, "JPA createQuery"),
            SinkDefinition("rawQuery", 0.95, SecuritySink.SQL_QUERY, "Android SQLite rawQuery"),
            SinkDefinition("execSQL", 0.9, SecuritySink.SQL_QUERY, "Android SQLite execSQL"),
        ],
        "php": [
            SinkDefinition("mysql_query", 0.95, SecuritySink.SQL_QUERY, "MySQL legacy query"),
            SinkDefinition("mysqli_query", 0.95, SecuritySink.SQL_QUERY, "MySQLi query"),
            SinkDefinition("->query", 0.85, SecuritySink.SQL_QUERY, "PDO/MySQLi query"),
            SinkDefinition("PDO::query", 0.9, SecuritySink.SQL_QUERY, "PDO query"),
            SinkDefinition("->exec", 0.9, SecuritySink.SQL_QUERY, "PDO exec"),
            SinkDefinition("pg_query", 0.95, SecuritySink.SQL_QUERY, "PostgreSQL query"),
        ],
        "ruby": [
            SinkDefinition(".execute", 0.9, SecuritySink.SQL_QUERY, "ActiveRecord execute"),
            SinkDefinition("find_by_sql", 0.95, SecuritySink.SQL_QUERY, "ActiveRecord find_by_sql"),
            SinkDefinition("ActiveRecord::Base.connection.execute", 1.0, SecuritySink.SQL_QUERY, "Direct AR connection execute"),
            SinkDefinition("sanitize_sql", 0.7, SecuritySink.SQL_QUERY, "AR sanitize_sql - check usage"),
        ],
        "swift": [
            SinkDefinition("sqlite3_exec", 0.95, SecuritySink.SQL_QUERY, "SQLite3 exec"),
            SinkDefinition("sqlite3_prepare_v2", 0.9, SecuritySink.SQL_QUERY, "SQLite3 prepare"),
            SinkDefinition(".execute", 0.8, SecuritySink.SQL_QUERY, "ORM execute"),
        ],
        # [20260305_FEATURE] Rust SQL injection sinks
        "rust": [
            SinkDefinition(".execute(", 0.95, SecuritySink.SQL_QUERY, "sqlx/diesel execute"),
            SinkDefinition(".query(", 0.9, SecuritySink.SQL_QUERY, "sqlx/diesel query"),
            SinkDefinition(".query_as(", 0.9, SecuritySink.SQL_QUERY, "sqlx query_as"),
            SinkDefinition("diesel::sql_query(", 0.95, SecuritySink.SQL_QUERY, "Diesel raw SQL"),
            SinkDefinition(".fetch_all(", 0.85, SecuritySink.SQL_QUERY, "sqlx fetch_all"),
        ],
    },
    # ==========================================================================
    # A03:2021 – Injection - Command Injection
    # ==========================================================================
    "command_injection": {
        "python": [
            SinkDefinition(
                "os.system", 1.0, SecuritySink.SHELL_COMMAND, "Direct shell execution"
            ),
            SinkDefinition(
                "subprocess.call", 0.9, SecuritySink.SHELL_COMMAND, "Subprocess call"
            ),
            SinkDefinition(
                "subprocess.run", 0.9, SecuritySink.SHELL_COMMAND, "Subprocess run"
            ),
            SinkDefinition(
                "subprocess.Popen", 0.9, SecuritySink.SHELL_COMMAND, "Subprocess Popen"
            ),
            SinkDefinition("os.popen", 1.0, SecuritySink.SHELL_COMMAND, "OS popen"),
            SinkDefinition(
                "eval", 1.0, SecuritySink.EVAL, "Python eval - code injection"
            ),
            SinkDefinition(
                "exec", 1.0, SecuritySink.EVAL, "Python exec - code injection"
            ),
        ],
        "java": [
            SinkDefinition(
                "Runtime.getRuntime().exec",
                1.0,
                SecuritySink.SHELL_COMMAND,
                "Runtime exec",
            ),
            SinkDefinition(
                "ProcessBuilder.command",
                0.9,
                SecuritySink.SHELL_COMMAND,
                "ProcessBuilder command",
            ),
            SinkDefinition(
                "ProcessBuilder.start",
                0.9,
                SecuritySink.SHELL_COMMAND,
                "ProcessBuilder start",
            ),
        ],
        "typescript": [
            SinkDefinition(
                "child_process.exec",
                1.0,
                SecuritySink.SHELL_COMMAND,
                "Child process exec",
            ),
            SinkDefinition(
                "child_process.spawn",
                0.9,
                SecuritySink.SHELL_COMMAND,
                "Child process spawn",
            ),
            SinkDefinition(
                "child_process.execSync",
                1.0,
                SecuritySink.SHELL_COMMAND,
                "Synchronous exec",
            ),
            SinkDefinition(
                "child_process.execFile", 0.85, SecuritySink.SHELL_COMMAND, "Exec file"
            ),
            SinkDefinition("eval", 1.0, SecuritySink.EVAL, "JavaScript eval"),
            SinkDefinition("Function", 1.0, SecuritySink.EVAL, "Function constructor"),
        ],
        "javascript": [
            SinkDefinition("exec", 1.0, SecuritySink.SHELL_COMMAND, "Shell exec"),
            SinkDefinition("spawn", 0.9, SecuritySink.SHELL_COMMAND, "Process spawn"),
            SinkDefinition("eval", 1.0, SecuritySink.EVAL, "JavaScript eval"),
            SinkDefinition(
                "setTimeout", 0.8, SecuritySink.EVAL, "setTimeout with string"
            ),
            SinkDefinition(
                "setInterval", 0.8, SecuritySink.EVAL, "setInterval with string"
            ),
        ],
        # [20260305_FEATURE] Polyglot command injection sinks - Go/C/C++/C#/Kotlin/PHP/Ruby/Swift
        "go": [
            SinkDefinition("exec.Command", 1.0, SecuritySink.SHELL_COMMAND, "os/exec Command"),
            SinkDefinition("syscall.Exec", 1.0, SecuritySink.SHELL_COMMAND, "syscall Exec"),
            SinkDefinition("syscall.ForkExec", 1.0, SecuritySink.SHELL_COMMAND, "syscall ForkExec"),
        ],
        "c": [
            SinkDefinition("system(", 1.0, SecuritySink.SHELL_COMMAND, "C stdlib system"),
            SinkDefinition("popen(", 1.0, SecuritySink.SHELL_COMMAND, "C popen"),
            SinkDefinition("execve(", 1.0, SecuritySink.SHELL_COMMAND, "POSIX execve"),
            SinkDefinition("execl(", 1.0, SecuritySink.SHELL_COMMAND, "POSIX execl"),
            SinkDefinition("execvp(", 1.0, SecuritySink.SHELL_COMMAND, "POSIX execvp"),
        ],
        "cpp": [
            SinkDefinition("system(", 1.0, SecuritySink.SHELL_COMMAND, "C++ stdlib system"),
            SinkDefinition("popen(", 1.0, SecuritySink.SHELL_COMMAND, "C++ popen"),
            SinkDefinition("execve(", 1.0, SecuritySink.SHELL_COMMAND, "POSIX execve"),
            SinkDefinition("boost::process::child", 0.9, SecuritySink.SHELL_COMMAND, "Boost.Process child"),
        ],
        "csharp": [
            SinkDefinition("Process.Start", 1.0, SecuritySink.SHELL_COMMAND, "System.Diagnostics Process.Start"),
            SinkDefinition("ProcessStartInfo", 0.9, SecuritySink.SHELL_COMMAND, "ProcessStartInfo"),
            SinkDefinition("new Process", 0.85, SecuritySink.SHELL_COMMAND, "System.Diagnostics Process"),
        ],
        "kotlin": [
            SinkDefinition("Runtime.getRuntime().exec", 1.0, SecuritySink.SHELL_COMMAND, "Java Runtime exec"),
            SinkDefinition("ProcessBuilder", 0.9, SecuritySink.SHELL_COMMAND, "Java ProcessBuilder"),
        ],
        "php": [
            SinkDefinition("exec(", 1.0, SecuritySink.SHELL_COMMAND, "PHP exec"),
            SinkDefinition("system(", 1.0, SecuritySink.SHELL_COMMAND, "PHP system"),
            SinkDefinition("shell_exec(", 1.0, SecuritySink.SHELL_COMMAND, "PHP shell_exec"),
            SinkDefinition("passthru(", 1.0, SecuritySink.SHELL_COMMAND, "PHP passthru"),
            SinkDefinition("popen(", 0.9, SecuritySink.SHELL_COMMAND, "PHP popen"),
            SinkDefinition("proc_open(", 0.9, SecuritySink.SHELL_COMMAND, "PHP proc_open"),
            SinkDefinition("eval(", 1.0, SecuritySink.EVAL, "PHP eval"),
        ],
        "ruby": [
            SinkDefinition("system(", 1.0, SecuritySink.SHELL_COMMAND, "Ruby Kernel#system"),
            SinkDefinition("exec(", 1.0, SecuritySink.SHELL_COMMAND, "Ruby Kernel#exec"),
            SinkDefinition("IO.popen", 1.0, SecuritySink.SHELL_COMMAND, "Ruby IO.popen"),
            SinkDefinition("`", 0.9, SecuritySink.SHELL_COMMAND, "Ruby backtick shell"),
            SinkDefinition("%x{", 0.9, SecuritySink.SHELL_COMMAND, "Ruby %x shell"),
            SinkDefinition("spawn(", 0.9, SecuritySink.SHELL_COMMAND, "Ruby Kernel#spawn"),
        ],
        "swift": [
            SinkDefinition("Process()", 1.0, SecuritySink.SHELL_COMMAND, "Foundation Process"),
            SinkDefinition("NSTask()", 1.0, SecuritySink.SHELL_COMMAND, "Foundation NSTask"),
        ],
        # [20260305_FEATURE] Rust command injection sinks
        "rust": [
            SinkDefinition("Command::new(", 1.0, SecuritySink.SHELL_COMMAND, "std::process::Command"),
            SinkDefinition(".arg(", 0.8, SecuritySink.SHELL_COMMAND, "Command arg - check if user-controlled"),
            SinkDefinition(".args(", 0.8, SecuritySink.SHELL_COMMAND, "Command args slice"),
            SinkDefinition(".spawn(", 0.9, SecuritySink.SHELL_COMMAND, "Command spawn"),
            SinkDefinition(".output(", 0.85, SecuritySink.SHELL_COMMAND, "Command output"),
        ],
    },
    # ==========================================================================
    # A03:2021 – Injection - Cross-Site Scripting (XSS)
    # ==========================================================================
    "xss": {
        "typescript": [
            SinkDefinition(
                "innerHTML", 1.0, SecuritySink.DOM_XSS, "Direct HTML injection"
            ),
            SinkDefinition(
                "outerHTML", 1.0, SecuritySink.DOM_XSS, "Outer HTML injection"
            ),
            SinkDefinition(
                "dangerouslySetInnerHTML",
                1.0,
                SecuritySink.DOM_XSS,
                "React dangerous HTML",
            ),
            SinkDefinition(
                "document.write", 1.0, SecuritySink.DOM_XSS, "Document write"
            ),
            SinkDefinition(
                "insertAdjacentHTML", 0.95, SecuritySink.DOM_XSS, "Insert adjacent HTML"
            ),
            SinkDefinition("v-html", 1.0, SecuritySink.DOM_XSS, "Vue v-html directive"),
            SinkDefinition(
                "[innerHTML]", 1.0, SecuritySink.DOM_XSS, "Angular innerHTML binding"
            ),
        ],
        "javascript": [
            SinkDefinition(
                "document.write", 1.0, SecuritySink.DOM_XSS, "Document write"
            ),
            SinkDefinition(
                "element.innerHTML", 1.0, SecuritySink.DOM_XSS, "Element innerHTML"
            ),
            SinkDefinition("outerHTML", 1.0, SecuritySink.DOM_XSS, "Outer HTML"),
            SinkDefinition(
                "jQuery.html", 0.95, SecuritySink.DOM_XSS, "jQuery HTML method"
            ),
            SinkDefinition(
                "$.html", 0.95, SecuritySink.DOM_XSS, "jQuery shorthand HTML"
            ),
        ],
        "python": [
            SinkDefinition(
                "render_template_string",
                1.0,
                SecuritySink.SSTI,
                "Flask template string rendering",
            ),
            SinkDefinition(
                "jinja2.Template", 1.0, SecuritySink.SSTI, "Jinja2 template injection"
            ),
            SinkDefinition(
                "Markup", 0.8, SecuritySink.HTML_OUTPUT, "MarkupSafe Markup"
            ),
        ],
        "java": [
            SinkDefinition(
                "response.getWriter().write",
                0.8,
                SecuritySink.HTML_OUTPUT,
                "Servlet response write",
            ),
            SinkDefinition(
                "PrintWriter.println",
                0.7,
                SecuritySink.HTML_OUTPUT,
                "PrintWriter output",
            ),
            SinkDefinition(
                "HttpServletResponse.getWriter",
                0.75,
                SecuritySink.HTML_OUTPUT,
                "Servlet writer",
            ),
        ],
        # [20260305_FEATURE] Polyglot XSS sinks - Go/C#/Kotlin/PHP/Ruby
        "go": [
            SinkDefinition("template.HTML(", 0.95, SecuritySink.HTML_OUTPUT, "Go unsafe HTML in template"),
            SinkDefinition("fmt.Fprintf(w", 0.75, SecuritySink.HTML_OUTPUT, "Unescaped write to ResponseWriter"),
            SinkDefinition("w.Write(", 0.7, SecuritySink.HTML_OUTPUT, "Raw write to ResponseWriter"),
        ],
        "csharp": [
            SinkDefinition("Response.Write(", 0.9, SecuritySink.HTML_OUTPUT, "ASP.NET Response.Write"),
            SinkDefinition("Html.Raw(", 1.0, SecuritySink.HTML_OUTPUT, "ASP.NET MVC Html.Raw"),
            SinkDefinition("@Html.Raw(", 1.0, SecuritySink.HTML_OUTPUT, "Razor @Html.Raw"),
            SinkDefinition("HttpResponse.Write(", 0.9, SecuritySink.HTML_OUTPUT, "HttpResponse.Write"),
        ],
        "kotlin": [
            SinkDefinition("response.writer.print(", 0.85, SecuritySink.HTML_OUTPUT, "Servlet response print"),
            SinkDefinition("PrintWriter.println(", 0.8, SecuritySink.HTML_OUTPUT, "PrintWriter output"),
        ],
        "php": [
            SinkDefinition("echo ", 0.75, SecuritySink.HTML_OUTPUT, "PHP echo"),
            SinkDefinition("print(", 0.75, SecuritySink.HTML_OUTPUT, "PHP print"),
            SinkDefinition("printf(", 0.75, SecuritySink.HTML_OUTPUT, "PHP printf"),
            SinkDefinition("<?=", 0.75, SecuritySink.HTML_OUTPUT, "PHP short echo tag"),
            SinkDefinition("header(\"Location:", 0.9, SecuritySink.REDIRECT, "PHP redirect XSS"),
        ],
        "ruby": [
            SinkDefinition("render html:", 0.9, SecuritySink.HTML_OUTPUT, "Rails render raw HTML"),
            SinkDefinition("raw(", 0.95, SecuritySink.HTML_OUTPUT, "Rails raw helper"),
            SinkDefinition(".html_safe", 0.9, SecuritySink.HTML_OUTPUT, "Rails html_safe"),
        ],
        # [20260305_FEATURE] Rust XSS sinks (server-side template injection)
        "rust": [
            SinkDefinition("minijinja::render!", 0.85, SecuritySink.HTML_OUTPUT, "MiniJinja template render"),
            SinkDefinition("tera.render(", 0.85, SecuritySink.HTML_OUTPUT, "Tera template render"),
            SinkDefinition("handlebars.render(", 0.85, SecuritySink.HTML_OUTPUT, "Handlebars template render"),
            SinkDefinition(".render(", 0.7, SecuritySink.HTML_OUTPUT, "Template render - check if user-controlled"),
        ],
    },
    # ==========================================================================
    # A01:2021 – Broken Access Control - Path Traversal
    # ==========================================================================
    "path_traversal": {
        "python": [
            SinkDefinition(
                "open", 0.8, SecuritySink.FILE_PATH, "File open - context dependent"
            ),
            SinkDefinition(
                "os.path.join", 0.6, SecuritySink.FILE_PATH, "Path join - can be safe"
            ),
            SinkDefinition(
                "pathlib.Path", 0.7, SecuritySink.FILE_PATH, "Path construction"
            ),
            SinkDefinition(
                "shutil.copy", 0.85, SecuritySink.FILE_PATH, "File copy operation"
            ),
        ],
        "java": [
            SinkDefinition("new File", 0.8, SecuritySink.FILE_PATH, "File constructor"),
            SinkDefinition(
                "Files.readString", 0.8, SecuritySink.FILE_PATH, "Read file as string"
            ),
            SinkDefinition(
                "Files.readAllBytes", 0.8, SecuritySink.FILE_PATH, "Read file bytes"
            ),
            SinkDefinition(
                "FileInputStream", 0.9, SecuritySink.FILE_PATH, "File input stream"
            ),
            SinkDefinition(
                "FileOutputStream", 0.9, SecuritySink.FILE_PATH, "File output stream"
            ),
        ],
        "typescript": [
            SinkDefinition("fs.readFile", 0.8, SecuritySink.FILE_PATH, "Read file"),
            SinkDefinition(
                "fs.readFileSync", 0.8, SecuritySink.FILE_PATH, "Synchronous read"
            ),
            SinkDefinition("fs.writeFile", 0.85, SecuritySink.FILE_PATH, "Write file"),
            SinkDefinition(
                "fs.createReadStream", 0.8, SecuritySink.FILE_PATH, "Create read stream"
            ),
            SinkDefinition("require", 0.7, SecuritySink.FILE_PATH, "Dynamic require"),
        ],
        "javascript": [
            SinkDefinition("fs.readFile", 0.8, SecuritySink.FILE_PATH, "File read"),
            SinkDefinition("fs.writeFile", 0.85, SecuritySink.FILE_PATH, "File write"),
            SinkDefinition("path.join", 0.6, SecuritySink.FILE_PATH, "Path join"),
        ],
        # [20260305_FEATURE] Polyglot path traversal sinks - Go/C/C++/C#/Kotlin/PHP/Ruby/Swift
        "go": [
            SinkDefinition("os.Open(", 0.85, SecuritySink.FILE_PATH, "os.Open"),
            SinkDefinition("os.ReadFile(", 0.85, SecuritySink.FILE_PATH, "os.ReadFile"),
            SinkDefinition("ioutil.ReadFile(", 0.85, SecuritySink.FILE_PATH, "ioutil.ReadFile"),
            SinkDefinition("filepath.Join(", 0.7, SecuritySink.FILE_PATH, "filepath.Join"),
            SinkDefinition("os.Create(", 0.85, SecuritySink.FILE_PATH, "os.Create"),
        ],
        "c": [
            SinkDefinition("fopen(", 0.9, SecuritySink.FILE_PATH, "C stdio fopen"),
            SinkDefinition("open(", 0.8, SecuritySink.FILE_PATH, "POSIX open"),
            SinkDefinition("freopen(", 0.9, SecuritySink.FILE_PATH, "C stdio freopen"),
        ],
        "cpp": [
            SinkDefinition("fopen(", 0.9, SecuritySink.FILE_PATH, "C++ fopen"),
            SinkDefinition("std::ifstream", 0.85, SecuritySink.FILE_PATH, "C++ ifstream"),
            SinkDefinition("std::ofstream", 0.85, SecuritySink.FILE_PATH, "C++ ofstream"),
            SinkDefinition("std::fstream", 0.85, SecuritySink.FILE_PATH, "C++ fstream"),
        ],
        "csharp": [
            SinkDefinition("File.ReadAllText(", 0.9, SecuritySink.FILE_PATH, "System.IO File.ReadAllText"),
            SinkDefinition("File.WriteAllText(", 0.9, SecuritySink.FILE_PATH, "System.IO File.WriteAllText"),
            SinkDefinition("new FileStream(", 0.9, SecuritySink.FILE_PATH, "System.IO FileStream"),
            SinkDefinition("Directory.GetFiles(", 0.8, SecuritySink.FILE_PATH, "System.IO Directory.GetFiles"),
            SinkDefinition("File.Open(", 0.9, SecuritySink.FILE_PATH, "System.IO File.Open"),
        ],
        "kotlin": [
            SinkDefinition("File(", 0.8, SecuritySink.FILE_PATH, "java.io.File"),
            SinkDefinition("Files.readAllBytes(", 0.85, SecuritySink.FILE_PATH, "java.nio Files"),
            SinkDefinition("FileInputStream(", 0.9, SecuritySink.FILE_PATH, "java.io FileInputStream"),
            SinkDefinition("FileOutputStream(", 0.9, SecuritySink.FILE_PATH, "java.io FileOutputStream"),
        ],
        "php": [
            SinkDefinition("include(", 0.9, SecuritySink.FILE_PATH, "PHP include"),
            SinkDefinition("require(", 0.9, SecuritySink.FILE_PATH, "PHP require"),
            SinkDefinition("include_once(", 0.9, SecuritySink.FILE_PATH, "PHP include_once"),
            SinkDefinition("fopen(", 0.9, SecuritySink.FILE_PATH, "PHP fopen"),
            SinkDefinition("file_get_contents(", 0.8, SecuritySink.FILE_PATH, "PHP file_get_contents"),
            SinkDefinition("readfile(", 0.85, SecuritySink.FILE_PATH, "PHP readfile"),
        ],
        "ruby": [
            SinkDefinition("File.read(", 0.9, SecuritySink.FILE_PATH, "Ruby File.read"),
            SinkDefinition("File.open(", 0.85, SecuritySink.FILE_PATH, "Ruby File.open"),
            SinkDefinition("IO.read(", 0.9, SecuritySink.FILE_PATH, "Ruby IO.read"),
            SinkDefinition("Pathname.new(", 0.75, SecuritySink.FILE_PATH, "Ruby Pathname"),
        ],
        "swift": [
            SinkDefinition("FileManager.default.contents(", 0.9, SecuritySink.FILE_PATH, "NSFileManager contents"),
            SinkDefinition("String(contentsOfFile:", 0.9, SecuritySink.FILE_PATH, "String contentsOfFile"),
            SinkDefinition("URL(fileURLWithPath:", 0.8, SecuritySink.FILE_PATH, "URL fileURLWithPath"),
        ],
        # [20260305_FEATURE] Rust path traversal sinks
        "rust": [
            SinkDefinition("File::open(", 0.85, SecuritySink.FILE_PATH, "std::fs::File::open"),
            SinkDefinition("fs::read(", 0.85, SecuritySink.FILE_PATH, "std::fs::read"),
            SinkDefinition("fs::read_to_string(", 0.85, SecuritySink.FILE_PATH, "std::fs::read_to_string"),
            SinkDefinition("fs::write(", 0.9, SecuritySink.FILE_PATH, "std::fs::write"),
            SinkDefinition("Path::new(", 0.7, SecuritySink.FILE_PATH, "std::path::Path construction"),
            SinkDefinition("PathBuf::from(", 0.7, SecuritySink.FILE_PATH, "std::path::PathBuf construction"),
        ],
    },
    # ==========================================================================
    # A10:2021 – Server-Side Request Forgery (SSRF)
    # ==========================================================================
    "ssrf": {
        "python": [
            SinkDefinition("requests.get", 0.9, SecuritySink.SSRF, "HTTP GET request"),
            SinkDefinition(
                "requests.post", 0.9, SecuritySink.SSRF, "HTTP POST request"
            ),
            SinkDefinition(
                "urllib.request.urlopen", 0.95, SecuritySink.SSRF, "URL open"
            ),
            SinkDefinition("httpx.get", 0.9, SecuritySink.SSRF, "HTTPX GET"),
            SinkDefinition(
                "aiohttp.ClientSession.get", 0.9, SecuritySink.SSRF, "Aiohttp GET"
            ),
        ],
        "java": [
            SinkDefinition(
                "URL.openConnection", 1.0, SecuritySink.SSRF, "URL connection open"
            ),
            SinkDefinition(
                "HttpURLConnection", 0.95, SecuritySink.SSRF, "HTTP URL connection"
            ),
            SinkDefinition(
                "RestTemplate.getForObject",
                0.85,
                SecuritySink.SSRF,
                "Spring RestTemplate GET",
            ),
            SinkDefinition(
                "RestTemplate.exchange",
                0.85,
                SecuritySink.SSRF,
                "Spring RestTemplate exchange",
            ),
            SinkDefinition(
                "WebClient.get", 0.85, SecuritySink.SSRF, "Spring WebFlux WebClient"
            ),
        ],
        "typescript": [
            SinkDefinition("fetch", 0.9, SecuritySink.SSRF, "Fetch API"),
            SinkDefinition("axios.get", 0.9, SecuritySink.SSRF, "Axios GET"),
            SinkDefinition("axios.post", 0.9, SecuritySink.SSRF, "Axios POST"),
            SinkDefinition("http.get", 0.95, SecuritySink.SSRF, "HTTP get"),
            SinkDefinition("https.get", 0.95, SecuritySink.SSRF, "HTTPS get"),
        ],
        "javascript": [
            SinkDefinition("fetch", 0.9, SecuritySink.SSRF, "Fetch API"),
            SinkDefinition("axios", 0.9, SecuritySink.SSRF, "Axios library"),
            SinkDefinition(
                "request.get", 0.9, SecuritySink.SSRF, "Request library GET"
            ),
        ],
        # [20260305_FEATURE] Polyglot SSRF sinks - Go/C/C++/C#/Kotlin/PHP/Ruby/Swift
        "go": [
            SinkDefinition("http.Get(", 0.9, SecuritySink.SSRF, "net/http GET"),
            SinkDefinition("http.Post(", 0.9, SecuritySink.SSRF, "net/http POST"),
            SinkDefinition("http.NewRequest(", 0.85, SecuritySink.SSRF, "net/http NewRequest"),
            SinkDefinition("http.DefaultClient.Do(", 0.9, SecuritySink.SSRF, "net/http client Do"),
        ],
        "c": [
            SinkDefinition("curl_easy_setopt(", 0.85, SecuritySink.SSRF, "libcurl setopt with URL"),
            SinkDefinition("curl_easy_perform(", 0.9, SecuritySink.SSRF, "libcurl perform"),
        ],
        "cpp": [
            SinkDefinition("curl_easy_setopt(", 0.85, SecuritySink.SSRF, "libcurl setopt"),
            SinkDefinition("curl_easy_perform(", 0.9, SecuritySink.SSRF, "libcurl perform"),
            SinkDefinition("beast::http::get(", 0.9, SecuritySink.SSRF, "Boost.Beast HTTP GET"),
        ],
        "csharp": [
            SinkDefinition("HttpClient.GetAsync(", 0.9, SecuritySink.SSRF, "System.Net.Http GetAsync"),
            SinkDefinition("HttpClient.PostAsync(", 0.9, SecuritySink.SSRF, "System.Net.Http PostAsync"),
            SinkDefinition("WebClient.DownloadString(", 0.9, SecuritySink.SSRF, "System.Net WebClient"),
            SinkDefinition("WebRequest.Create(", 0.9, SecuritySink.SSRF, "System.Net WebRequest"),
        ],
        "kotlin": [
            SinkDefinition("URL(", 0.8, SecuritySink.SSRF, "java.net.URL"),
            SinkDefinition("HttpURLConnection", 0.85, SecuritySink.SSRF, "java.net.HttpURLConnection"),
            SinkDefinition("OkHttpClient", 0.85, SecuritySink.SSRF, "OkHttp3 client"),
            SinkDefinition("Fuel.get(", 0.9, SecuritySink.SSRF, "Fuel HTTP GET"),
        ],
        "php": [
            SinkDefinition("curl_exec(", 0.9, SecuritySink.SSRF, "PHP cURL exec"),
            SinkDefinition("file_get_contents(", 0.75, SecuritySink.SSRF, "PHP file_get_contents with URL"),
            SinkDefinition("fsockopen(", 0.9, SecuritySink.SSRF, "PHP fsockopen"),
        ],
        "ruby": [
            SinkDefinition("Net::HTTP.get(", 0.9, SecuritySink.SSRF, "Ruby Net::HTTP GET"),
            SinkDefinition("Net::HTTP.post(", 0.9, SecuritySink.SSRF, "Ruby Net::HTTP POST"),
            SinkDefinition("open(", 0.75, SecuritySink.SSRF, "Ruby open-uri"),
            SinkDefinition("URI.open(", 0.8, SecuritySink.SSRF, "Ruby URI.open"),
            SinkDefinition("Faraday.get(", 0.9, SecuritySink.SSRF, "Faraday HTTP GET"),
        ],
        "swift": [
            SinkDefinition("URLSession.shared.dataTask(", 0.9, SecuritySink.SSRF, "Foundation URLSession"),
            SinkDefinition("URLSession.shared.data(", 0.9, SecuritySink.SSRF, "Foundation URLSession async"),
            SinkDefinition("URLRequest(", 0.8, SecuritySink.SSRF, "Foundation URLRequest"),
        ],
        # [20260305_FEATURE] Rust SSRF sinks
        "rust": [
            SinkDefinition("reqwest::get(", 0.9, SecuritySink.SSRF, "reqwest GET"),
            SinkDefinition("reqwest::Client::new(", 0.85, SecuritySink.SSRF, "reqwest Client"),
            SinkDefinition(".get(", 0.75, SecuritySink.SSRF, "HTTP GET - check if URL is user-controlled"),
            SinkDefinition(".post(", 0.75, SecuritySink.SSRF, "HTTP POST - check if URL is user-controlled"),
            SinkDefinition("hyper::Client::", 0.85, SecuritySink.SSRF, "hyper HTTP client"),
            SinkDefinition("ureq::get(", 0.9, SecuritySink.SSRF, "ureq GET"),
        ],
    },
    # ==========================================================================
    # [20251229_FEATURE] v3.0.4 - A02:2021 – Cryptographic Failures (Weak Crypto)
    # ==========================================================================
    "weak_crypto": {
        "python": [
            SinkDefinition(
                "hashlib.md5",
                0.95,
                SecuritySink.WEAK_CRYPTO,
                "MD5 hash - cryptographically broken",
            ),
            SinkDefinition(
                "hashlib.sha1",
                0.85,
                SecuritySink.WEAK_CRYPTO,
                "SHA1 hash - deprecated for security",
            ),
            SinkDefinition(
                "Crypto.Cipher.DES",
                1.0,
                SecuritySink.WEAK_CRYPTO,
                "DES cipher - broken",
            ),
            SinkDefinition(
                "Crypto.Hash.MD5", 0.95, SecuritySink.WEAK_CRYPTO, "PyCryptodome MD5"
            ),
        ],
        "java": [
            SinkDefinition(
                'MessageDigest.getInstance("MD5")',
                0.95,
                SecuritySink.WEAK_CRYPTO,
                "MD5 digest",
            ),
            SinkDefinition(
                'MessageDigest.getInstance("SHA-1")',
                0.85,
                SecuritySink.WEAK_CRYPTO,
                "SHA1 digest",
            ),
            SinkDefinition(
                'Cipher.getInstance("DES")', 1.0, SecuritySink.WEAK_CRYPTO, "DES cipher"
            ),
            SinkDefinition(
                'Cipher.getInstance("DESede")',
                0.9,
                SecuritySink.WEAK_CRYPTO,
                "3DES cipher - weak",
            ),
        ],
        "typescript": [
            SinkDefinition(
                "crypto.createHash('md5')",
                0.95,
                SecuritySink.WEAK_CRYPTO,
                "MD5 hash - broken",
            ),
            SinkDefinition(
                "crypto.createHash('sha1')",
                0.85,
                SecuritySink.WEAK_CRYPTO,
                "SHA1 hash - deprecated",
            ),
            SinkDefinition(
                "crypto.createCipheriv('des')",
                1.0,
                SecuritySink.WEAK_CRYPTO,
                "DES cipher - broken",
            ),
            SinkDefinition(
                "crypto.createCipheriv('des-ede')",
                0.9,
                SecuritySink.WEAK_CRYPTO,
                "3DES - weak",
            ),
            SinkDefinition(
                "CryptoJS.MD5", 0.95, SecuritySink.WEAK_CRYPTO, "CryptoJS MD5"
            ),
            SinkDefinition(
                "CryptoJS.SHA1", 0.85, SecuritySink.WEAK_CRYPTO, "CryptoJS SHA1"
            ),
            SinkDefinition(
                "CryptoJS.DES", 1.0, SecuritySink.WEAK_CRYPTO, "CryptoJS DES"
            ),
            SinkDefinition("md5(", 0.95, SecuritySink.WEAK_CRYPTO, "MD5 function call"),
            SinkDefinition(
                "sha1(", 0.85, SecuritySink.WEAK_CRYPTO, "SHA1 function call"
            ),
        ],
        "javascript": [
            SinkDefinition(
                "crypto.createHash('md5')",
                0.95,
                SecuritySink.WEAK_CRYPTO,
                "MD5 hash - broken",
            ),
            SinkDefinition(
                "crypto.createHash('sha1')",
                0.85,
                SecuritySink.WEAK_CRYPTO,
                "SHA1 hash - deprecated",
            ),
            SinkDefinition(
                "CryptoJS.MD5", 0.95, SecuritySink.WEAK_CRYPTO, "CryptoJS MD5"
            ),
            SinkDefinition(
                "CryptoJS.SHA1", 0.85, SecuritySink.WEAK_CRYPTO, "CryptoJS SHA1"
            ),
            SinkDefinition(
                "CryptoJS.DES", 1.0, SecuritySink.WEAK_CRYPTO, "CryptoJS DES"
            ),
            SinkDefinition("md5(", 0.95, SecuritySink.WEAK_CRYPTO, "MD5 function call"),
        ],
        # [20260305_FEATURE] Polyglot weak crypto sinks - Go/C/C++/C#/Kotlin/PHP/Ruby/Swift
        "go": [
            SinkDefinition("md5.New()", 0.95, SecuritySink.WEAK_CRYPTO, "Go crypto/md5"),
            SinkDefinition("sha1.New()", 0.85, SecuritySink.WEAK_CRYPTO, "Go crypto/sha1"),
            SinkDefinition("des.NewCipher(", 1.0, SecuritySink.WEAK_CRYPTO, "Go crypto/des"),
            SinkDefinition("rc4.NewCipher(", 1.0, SecuritySink.WEAK_CRYPTO, "Go crypto/rc4"),
        ],
        "c": [
            SinkDefinition("MD5_Init(", 0.95, SecuritySink.WEAK_CRYPTO, "OpenSSL MD5"),
            SinkDefinition("SHA1_Init(", 0.85, SecuritySink.WEAK_CRYPTO, "OpenSSL SHA1"),
            SinkDefinition("DES_set_key(", 1.0, SecuritySink.WEAK_CRYPTO, "OpenSSL DES"),
        ],
        "cpp": [
            SinkDefinition("MD5_Init(", 0.95, SecuritySink.WEAK_CRYPTO, "OpenSSL MD5"),
            SinkDefinition("SHA1_Init(", 0.85, SecuritySink.WEAK_CRYPTO, "OpenSSL SHA1"),
            SinkDefinition("EVP_des_cbc(", 1.0, SecuritySink.WEAK_CRYPTO, "OpenSSL DES CBC"),
        ],
        "csharp": [
            SinkDefinition("MD5.Create(", 0.95, SecuritySink.WEAK_CRYPTO, "System.Security.Cryptography MD5"),
            SinkDefinition("SHA1.Create(", 0.85, SecuritySink.WEAK_CRYPTO, "System.Security.Cryptography SHA1"),
            SinkDefinition("DESCryptoServiceProvider(", 1.0, SecuritySink.WEAK_CRYPTO, "DES cipher"),
            SinkDefinition("new MD5CryptoServiceProvider(", 0.95, SecuritySink.WEAK_CRYPTO, "MD5 provider"),
            SinkDefinition("TripleDESCryptoServiceProvider(", 0.9, SecuritySink.WEAK_CRYPTO, "3DES - weak"),
        ],
        "kotlin": [
            SinkDefinition('MessageDigest.getInstance("MD5")', 0.95, SecuritySink.WEAK_CRYPTO, "Java MD5"),
            SinkDefinition('MessageDigest.getInstance("SHA-1")', 0.85, SecuritySink.WEAK_CRYPTO, "Java SHA-1"),
            SinkDefinition('Cipher.getInstance("DES")', 1.0, SecuritySink.WEAK_CRYPTO, "Java DES cipher"),
        ],
        "php": [
            SinkDefinition("md5(", 0.95, SecuritySink.WEAK_CRYPTO, "PHP md5"),
            SinkDefinition("sha1(", 0.85, SecuritySink.WEAK_CRYPTO, "PHP sha1"),
            SinkDefinition("crc32(", 0.8, SecuritySink.WEAK_CRYPTO, "PHP crc32 - not cryptographic"),
            SinkDefinition("mcrypt_encrypt(", 1.0, SecuritySink.WEAK_CRYPTO, "PHP mcrypt (deprecated)"),
        ],
        "ruby": [
            SinkDefinition("Digest::MD5.hexdigest(", 0.95, SecuritySink.WEAK_CRYPTO, "Ruby Digest MD5"),
            SinkDefinition("Digest::SHA1.hexdigest(", 0.85, SecuritySink.WEAK_CRYPTO, "Ruby Digest SHA1"),
            SinkDefinition('OpenSSL::Cipher.new("DES")', 1.0, SecuritySink.WEAK_CRYPTO, "Ruby OpenSSL DES"),
        ],
        "swift": [
            SinkDefinition("CC_MD5(", 0.95, SecuritySink.WEAK_CRYPTO, "CommonCrypto MD5"),
            SinkDefinition("CC_SHA1(", 0.85, SecuritySink.WEAK_CRYPTO, "CommonCrypto SHA1"),
            SinkDefinition("kCCAlgorithmDES", 1.0, SecuritySink.WEAK_CRYPTO, "CommonCrypto DES"),
        ],
        # [20260305_FEATURE] Rust weak crypto sinks
        "rust": [
            SinkDefinition("md5::compute(", 0.95, SecuritySink.WEAK_CRYPTO, "md5 crate compute"),
            SinkDefinition("Md5::new(", 0.95, SecuritySink.WEAK_CRYPTO, "RustCrypto MD5"),
            SinkDefinition("Sha1::new(", 0.85, SecuritySink.WEAK_CRYPTO, "RustCrypto SHA1"),
            SinkDefinition("sha1::Sha1::", 0.85, SecuritySink.WEAK_CRYPTO, "sha1 crate"),
            SinkDefinition("Des::new(", 1.0, SecuritySink.WEAK_CRYPTO, "RustCrypto DES"),
            SinkDefinition("Rc4::new(", 1.0, SecuritySink.WEAK_CRYPTO, "RustCrypto RC4 (broken)"),
        ],
    },
    # ==========================================================================
    # [20251229_FEATURE] v3.0.4 - A05:2021 – Security Misconfiguration (XXE)
    # ==========================================================================
    "xxe": {
        "python": [
            SinkDefinition(
                "xml.etree.ElementTree.parse",
                0.9,
                SecuritySink.XXE,
                "ElementTree parse",
            ),
            SinkDefinition(
                "xml.etree.ElementTree.fromstring",
                0.9,
                SecuritySink.XXE,
                "ElementTree fromstring",
            ),
            SinkDefinition(
                "lxml.etree.parse",
                0.95,
                SecuritySink.XXE,
                "lxml parse - XXE by default",
            ),
            SinkDefinition(
                "xml.dom.minidom.parse", 0.9, SecuritySink.XXE, "minidom parse"
            ),
            SinkDefinition("xml.sax.parse", 0.9, SecuritySink.XXE, "SAX parse"),
        ],
        "java": [
            SinkDefinition(
                "DocumentBuilderFactory.newInstance",
                0.95,
                SecuritySink.XXE,
                "DOM parser factory",
            ),
            SinkDefinition(
                "SAXParserFactory.newInstance",
                0.95,
                SecuritySink.XXE,
                "SAX parser factory",
            ),
            SinkDefinition(
                "XMLInputFactory.newInstance",
                0.95,
                SecuritySink.XXE,
                "StAX parser factory",
            ),
            SinkDefinition(
                "Unmarshaller.unmarshal", 0.9, SecuritySink.XXE, "JAXB unmarshal"
            ),
        ],
        "typescript": [
            SinkDefinition("DOMParser", 0.85, SecuritySink.XXE, "Browser DOMParser"),
            SinkDefinition(
                "new DOMParser().parseFromString",
                0.85,
                SecuritySink.XXE,
                "DOMParser parseFromString",
            ),
            SinkDefinition(
                "xml2js.parseString", 0.9, SecuritySink.XXE, "xml2js parser"
            ),
            SinkDefinition(
                "xml2js.Parser", 0.9, SecuritySink.XXE, "xml2js Parser class"
            ),
            SinkDefinition(
                "fast-xml-parser", 0.85, SecuritySink.XXE, "fast-xml-parser"
            ),
            SinkDefinition("XMLParser", 0.85, SecuritySink.XXE, "XMLParser"),
            SinkDefinition("xmldom", 0.9, SecuritySink.XXE, "xmldom library"),
            SinkDefinition(
                "libxmljs", 0.95, SecuritySink.XXE, "libxmljs - XXE vulnerable"
            ),
            SinkDefinition("sax.parser", 0.85, SecuritySink.XXE, "SAX parser"),
        ],
        "javascript": [
            SinkDefinition("DOMParser", 0.85, SecuritySink.XXE, "Browser DOMParser"),
            SinkDefinition(
                "xml2js.parseString", 0.9, SecuritySink.XXE, "xml2js parser"
            ),
            SinkDefinition(
                "fast-xml-parser", 0.85, SecuritySink.XXE, "fast-xml-parser"
            ),
            SinkDefinition("xmldom", 0.9, SecuritySink.XXE, "xmldom library"),
            SinkDefinition(
                "libxmljs", 0.95, SecuritySink.XXE, "libxmljs - XXE vulnerable"
            ),
        ],
        # [20260305_FEATURE] Polyglot XXE sinks - Go/C/C++/C#/Kotlin/PHP/Ruby/Swift
        "go": [
            SinkDefinition("xml.NewDecoder(", 0.85, SecuritySink.XXE, "encoding/xml Decoder"),
            SinkDefinition("xml.Unmarshal(", 0.85, SecuritySink.XXE, "encoding/xml Unmarshal"),
            SinkDefinition("etree.ReadFrom(", 0.9, SecuritySink.XXE, "etree ReadFrom"),
        ],
        "c": [
            SinkDefinition("xmlParseDoc(", 0.9, SecuritySink.XXE, "libxml2 xmlParseDoc"),
            SinkDefinition("xmlReadFile(", 0.9, SecuritySink.XXE, "libxml2 xmlReadFile"),
            SinkDefinition("xmlSAXParseDoc(", 0.9, SecuritySink.XXE, "libxml2 SAX parse"),
        ],
        "cpp": [
            SinkDefinition("xmlParseDoc(", 0.9, SecuritySink.XXE, "libxml2 xmlParseDoc"),
            SinkDefinition("xmlReadFile(", 0.9, SecuritySink.XXE, "libxml2 xmlReadFile"),
            SinkDefinition("TiXmlDocument", 0.85, SecuritySink.XXE, "TinyXML document"),
        ],
        "csharp": [
            SinkDefinition("XmlReader.Create(", 0.9, SecuritySink.XXE, "System.Xml XmlReader"),
            SinkDefinition("XmlDocument.Load(", 0.9, SecuritySink.XXE, "System.Xml XmlDocument"),
            SinkDefinition("XDocument.Load(", 0.85, SecuritySink.XXE, "System.Xml.Linq XDocument"),
            SinkDefinition("XmlTextReader(", 0.9, SecuritySink.XXE, "System.Xml XmlTextReader (legacy)"),
        ],
        "kotlin": [
            SinkDefinition("DocumentBuilderFactory.newInstance(", 0.95, SecuritySink.XXE, "Java DOM parser"),
            SinkDefinition("SAXParserFactory.newInstance(", 0.95, SecuritySink.XXE, "Java SAX parser"),
            SinkDefinition("XmlPullParserFactory.newInstance(", 0.9, SecuritySink.XXE, "Android XmlPullParser"),
        ],
        "php": [
            SinkDefinition("simplexml_load_string(", 0.9, SecuritySink.XXE, "PHP SimpleXML"),
            SinkDefinition("simplexml_load_file(", 0.9, SecuritySink.XXE, "PHP SimpleXML file"),
            SinkDefinition("DOMDocument::loadXML(", 0.9, SecuritySink.XXE, "PHP DOMDocument loadXML"),
            SinkDefinition("DOMDocument::load(", 0.9, SecuritySink.XXE, "PHP DOMDocument load"),
        ],
        "ruby": [
            SinkDefinition("Nokogiri::XML(", 0.9, SecuritySink.XXE, "Nokogiri XML parser"),
            SinkDefinition("REXML::Document.new(", 0.85, SecuritySink.XXE, "Ruby REXML"),
            SinkDefinition("LibXML::XML::Document.file(", 0.9, SecuritySink.XXE, "Ruby LibXML"),
        ],
        "swift": [
            SinkDefinition("XMLParser(", 0.85, SecuritySink.XXE, "Foundation XMLParser"),
            SinkDefinition("XMLDocument(", 0.85, SecuritySink.XXE, "Foundation XMLDocument"),
        ],
        # [20260305_FEATURE] Rust XXE sinks
        "rust": [
            SinkDefinition("roxmltree::Document::parse(", 0.85, SecuritySink.XXE, "roxmltree parser"),
            SinkDefinition("minidom::Element::from_reader(", 0.85, SecuritySink.XXE, "minidom reader"),
            SinkDefinition("xml::reader::EventReader::", 0.8, SecuritySink.XXE, "xml-rs EventReader"),
            SinkDefinition("quick_xml::Reader::", 0.8, SecuritySink.XXE, "quick-xml Reader"),
        ],
    },
    # ==========================================================================
    # [20251229_FEATURE] v3.0.4 - A09:2021 – Security Logging and Monitoring Failures
    # ==========================================================================
    "log_injection": {
        "python": [
            SinkDefinition(
                "logging.info", 0.7, SecuritySink.LOG_OUTPUT, "Logging info"
            ),
            SinkDefinition(
                "logging.warning", 0.7, SecuritySink.LOG_OUTPUT, "Logging warning"
            ),
            SinkDefinition(
                "logging.error", 0.7, SecuritySink.LOG_OUTPUT, "Logging error"
            ),
            SinkDefinition(
                "logging.debug", 0.6, SecuritySink.LOG_OUTPUT, "Logging debug"
            ),
            SinkDefinition("logger.info", 0.7, SecuritySink.LOG_OUTPUT, "Logger info"),
            SinkDefinition(
                "logger.error", 0.7, SecuritySink.LOG_OUTPUT, "Logger error"
            ),
        ],
        "java": [
            SinkDefinition("Logger.info", 0.7, SecuritySink.LOG_OUTPUT, "Logger info"),
            SinkDefinition("Logger.warn", 0.7, SecuritySink.LOG_OUTPUT, "Logger warn"),
            SinkDefinition(
                "Logger.error", 0.7, SecuritySink.LOG_OUTPUT, "Logger error"
            ),
            SinkDefinition("log.info", 0.7, SecuritySink.LOG_OUTPUT, "SLF4J log info"),
            SinkDefinition(
                "log.error", 0.7, SecuritySink.LOG_OUTPUT, "SLF4J log error"
            ),
            SinkDefinition(
                "System.out.println", 0.6, SecuritySink.LOG_OUTPUT, "Console output"
            ),
        ],
        "typescript": [
            SinkDefinition(
                "console.log",
                0.65,
                SecuritySink.LOG_OUTPUT,
                "Console log - may leak data",
            ),
            SinkDefinition(
                "console.error", 0.65, SecuritySink.LOG_OUTPUT, "Console error"
            ),
            SinkDefinition(
                "console.warn", 0.65, SecuritySink.LOG_OUTPUT, "Console warn"
            ),
            SinkDefinition(
                "console.info", 0.65, SecuritySink.LOG_OUTPUT, "Console info"
            ),
            SinkDefinition(
                "winston.log", 0.75, SecuritySink.LOG_OUTPUT, "Winston logger"
            ),
            SinkDefinition(
                "winston.info", 0.75, SecuritySink.LOG_OUTPUT, "Winston info"
            ),
            SinkDefinition(
                "winston.error", 0.75, SecuritySink.LOG_OUTPUT, "Winston error"
            ),
            SinkDefinition(
                "pino.info", 0.75, SecuritySink.LOG_OUTPUT, "Pino logger info"
            ),
            SinkDefinition(
                "pino.error", 0.75, SecuritySink.LOG_OUTPUT, "Pino logger error"
            ),
            SinkDefinition(
                "bunyan.info", 0.75, SecuritySink.LOG_OUTPUT, "Bunyan logger info"
            ),
            SinkDefinition(
                "bunyan.error", 0.75, SecuritySink.LOG_OUTPUT, "Bunyan logger error"
            ),
            SinkDefinition(
                "log4js.getLogger", 0.75, SecuritySink.LOG_OUTPUT, "Log4js logger"
            ),
        ],
        "javascript": [
            SinkDefinition("console.log", 0.65, SecuritySink.LOG_OUTPUT, "Console log"),
            SinkDefinition(
                "console.error", 0.65, SecuritySink.LOG_OUTPUT, "Console error"
            ),
            SinkDefinition(
                "winston.log", 0.75, SecuritySink.LOG_OUTPUT, "Winston logger"
            ),
            SinkDefinition("pino.info", 0.75, SecuritySink.LOG_OUTPUT, "Pino logger"),
            SinkDefinition(
                "bunyan.info", 0.75, SecuritySink.LOG_OUTPUT, "Bunyan logger"
            ),
        ],
        # [20260305_FEATURE] Polyglot log injection sinks - Go/C/C++/C#/Kotlin/PHP/Ruby/Swift
        "go": [
            SinkDefinition("log.Print(", 0.65, SecuritySink.LOG_OUTPUT, "Go log Print"),
            SinkDefinition("log.Printf(", 0.65, SecuritySink.LOG_OUTPUT, "Go log Printf"),
            SinkDefinition("log.Println(", 0.65, SecuritySink.LOG_OUTPUT, "Go log Println"),
            SinkDefinition(".Info(", 0.65, SecuritySink.LOG_OUTPUT, "Go logger Info (zap/logrus)"),
            SinkDefinition(".Error(", 0.65, SecuritySink.LOG_OUTPUT, "Go logger Error (zap/logrus)"),
        ],
        "c": [
            SinkDefinition("printf(", 0.6, SecuritySink.LOG_OUTPUT, "C printf"),
            SinkDefinition("fprintf(stderr", 0.65, SecuritySink.LOG_OUTPUT, "C fprintf to stderr"),
            SinkDefinition("syslog(", 0.7, SecuritySink.LOG_OUTPUT, "POSIX syslog"),
        ],
        "cpp": [
            SinkDefinition("printf(", 0.6, SecuritySink.LOG_OUTPUT, "C++ printf"),
            SinkDefinition("std::cout", 0.55, SecuritySink.LOG_OUTPUT, "C++ cout"),
            SinkDefinition("syslog(", 0.7, SecuritySink.LOG_OUTPUT, "POSIX syslog"),
            SinkDefinition("BOOST_LOG_TRIVIAL(", 0.7, SecuritySink.LOG_OUTPUT, "Boost.Log"),
        ],
        "csharp": [
            SinkDefinition("Console.WriteLine(", 0.6, SecuritySink.LOG_OUTPUT, "System Console.WriteLine"),
            SinkDefinition("logger.LogInformation(", 0.7, SecuritySink.LOG_OUTPUT, "ILogger LogInformation"),
            SinkDefinition("logger.LogError(", 0.7, SecuritySink.LOG_OUTPUT, "ILogger LogError"),
            SinkDefinition("logger.LogWarning(", 0.7, SecuritySink.LOG_OUTPUT, "ILogger LogWarning"),
            SinkDefinition("_logger.Log(", 0.7, SecuritySink.LOG_OUTPUT, "ILogger Log"),
        ],
        "kotlin": [
            SinkDefinition("println(", 0.6, SecuritySink.LOG_OUTPUT, "Kotlin println"),
            SinkDefinition("Log.i(", 0.65, SecuritySink.LOG_OUTPUT, "Android Log.i"),
            SinkDefinition("Log.d(", 0.6, SecuritySink.LOG_OUTPUT, "Android Log.d"),
            SinkDefinition("Log.e(", 0.65, SecuritySink.LOG_OUTPUT, "Android Log.e"),
            SinkDefinition("log.info(", 0.7, SecuritySink.LOG_OUTPUT, "SLF4J log.info"),
        ],
        "php": [
            SinkDefinition("error_log(", 0.7, SecuritySink.LOG_OUTPUT, "PHP error_log"),
            SinkDefinition("syslog(", 0.7, SecuritySink.LOG_OUTPUT, "PHP syslog"),
            SinkDefinition("trigger_error(", 0.65, SecuritySink.LOG_OUTPUT, "PHP trigger_error"),
        ],
        "ruby": [
            SinkDefinition("Rails.logger.info", 0.7, SecuritySink.LOG_OUTPUT, "Rails logger"),
            SinkDefinition("logger.info", 0.7, SecuritySink.LOG_OUTPUT, "Ruby Logger info"),
            SinkDefinition("puts ", 0.55, SecuritySink.LOG_OUTPUT, "Ruby puts"),
            SinkDefinition("Syslog.log(", 0.7, SecuritySink.LOG_OUTPUT, "Ruby Syslog"),
        ],
        "swift": [
            SinkDefinition("print(", 0.55, SecuritySink.LOG_OUTPUT, "Swift print"),
            SinkDefinition("NSLog(", 0.65, SecuritySink.LOG_OUTPUT, "Foundation NSLog"),
            SinkDefinition("os_log(", 0.65, SecuritySink.LOG_OUTPUT, "os.log os_log"),
            SinkDefinition("Logger(", 0.65, SecuritySink.LOG_OUTPUT, "os.log Logger"),
        ],
        # [20260305_FEATURE] Rust log injection sinks
        "rust": [
            SinkDefinition("println!(", 0.55, SecuritySink.LOG_OUTPUT, "Rust println macro"),
            SinkDefinition("eprintln!(", 0.6, SecuritySink.LOG_OUTPUT, "Rust eprintln macro"),
            SinkDefinition("log::info!(", 0.65, SecuritySink.LOG_OUTPUT, "log crate info"),
            SinkDefinition("log::warn!(", 0.65, SecuritySink.LOG_OUTPUT, "log crate warn"),
            SinkDefinition("log::error!(", 0.65, SecuritySink.LOG_OUTPUT, "log crate error"),
            SinkDefinition("tracing::info!(", 0.65, SecuritySink.LOG_OUTPUT, "tracing crate info"),
            SinkDefinition("tracing::error!(", 0.65, SecuritySink.LOG_OUTPUT, "tracing crate error"),
        ],
    },
    # ==========================================================================
    # [20251229_FEATURE] v3.0.4 - ReDoS (Regular Expression Denial of Service)
    # ==========================================================================
    "redos": {
        "python": [
            SinkDefinition(
                "re.match",
                0.6,
                SecuritySink.EVAL,
                "Regex match - check for catastrophic backtracking",
            ),
            SinkDefinition("re.search", 0.6, SecuritySink.EVAL, "Regex search"),
            SinkDefinition("re.compile", 0.6, SecuritySink.EVAL, "Regex compile"),
            SinkDefinition("re.findall", 0.6, SecuritySink.EVAL, "Regex findall"),
        ],
        "java": [
            SinkDefinition("Pattern.compile", 0.6, SecuritySink.EVAL, "Regex compile"),
            SinkDefinition("Pattern.matches", 0.6, SecuritySink.EVAL, "Regex matches"),
            SinkDefinition(
                "String.matches", 0.6, SecuritySink.EVAL, "String regex match"
            ),
            SinkDefinition(
                "String.replaceAll", 0.6, SecuritySink.EVAL, "Regex replace"
            ),
        ],
        "typescript": [
            SinkDefinition(
                "new RegExp",
                0.75,
                SecuritySink.EVAL,
                "Dynamic regex - ReDoS risk if user input",
            ),
            SinkDefinition(
                "RegExp(", 0.75, SecuritySink.EVAL, "RegExp constructor with user input"
            ),
            SinkDefinition(
                ".match(", 0.6, SecuritySink.EVAL, "String match with regex"
            ),
            SinkDefinition(
                ".replace(", 0.6, SecuritySink.EVAL, "String replace with regex"
            ),
            SinkDefinition(
                ".search(", 0.6, SecuritySink.EVAL, "String search with regex"
            ),
            SinkDefinition(
                ".split(", 0.5, SecuritySink.EVAL, "String split with regex"
            ),
        ],
        "javascript": [
            SinkDefinition(
                "new RegExp", 0.75, SecuritySink.EVAL, "Dynamic regex - ReDoS risk"
            ),
            SinkDefinition("RegExp(", 0.75, SecuritySink.EVAL, "RegExp constructor"),
            SinkDefinition(".match(", 0.6, SecuritySink.EVAL, "String match"),
            SinkDefinition(".replace(", 0.6, SecuritySink.EVAL, "String replace"),
        ],
        # [20260305_FEATURE] Polyglot ReDoS sinks - Go/C++/C#/Kotlin/PHP/Ruby/Swift
        "go": [
            SinkDefinition("regexp.Compile(", 0.65, SecuritySink.EVAL, "Go regexp.Compile"),
            SinkDefinition("regexp.MustCompile(", 0.65, SecuritySink.EVAL, "Go regexp.MustCompile"),
            SinkDefinition("regexp.MatchString(", 0.6, SecuritySink.EVAL, "Go regexp.MatchString"),
        ],
        "cpp": [
            SinkDefinition("std::regex(", 0.7, SecuritySink.EVAL, "C++ std::regex dynamic"),
            SinkDefinition("regex_match(", 0.6, SecuritySink.EVAL, "C++ regex_match"),
            SinkDefinition("regex_search(", 0.6, SecuritySink.EVAL, "C++ regex_search"),
        ],
        "csharp": [
            SinkDefinition("new Regex(", 0.75, SecuritySink.EVAL, "C# dynamic Regex"),
            SinkDefinition("Regex.Match(", 0.65, SecuritySink.EVAL, "C# Regex.Match"),
            SinkDefinition("Regex.IsMatch(", 0.65, SecuritySink.EVAL, "C# Regex.IsMatch"),
            SinkDefinition("Regex.Replace(", 0.6, SecuritySink.EVAL, "C# Regex.Replace"),
        ],
        "kotlin": [
            SinkDefinition("Regex(", 0.7, SecuritySink.EVAL, "Kotlin Regex"),
            SinkDefinition(".toRegex(", 0.65, SecuritySink.EVAL, "Kotlin toRegex"),
            SinkDefinition("Pattern.compile(", 0.6, SecuritySink.EVAL, "Java Pattern.compile"),
        ],
        "php": [
            SinkDefinition("preg_match(", 0.65, SecuritySink.EVAL, "PHP preg_match"),
            SinkDefinition("preg_replace(", 0.65, SecuritySink.EVAL, "PHP preg_replace"),
            SinkDefinition("preg_match_all(", 0.65, SecuritySink.EVAL, "PHP preg_match_all"),
        ],
        "ruby": [
            SinkDefinition("Regexp.new(", 0.75, SecuritySink.EVAL, "Ruby dynamic Regexp"),
            SinkDefinition(".match(", 0.6, SecuritySink.EVAL, "Ruby String.match"),
            SinkDefinition(".scan(", 0.6, SecuritySink.EVAL, "Ruby String.scan"),
        ],
        "swift": [
            SinkDefinition("NSRegularExpression(", 0.75, SecuritySink.EVAL, "Foundation NSRegularExpression"),
            SinkDefinition("try NSRegularExpression(", 0.75, SecuritySink.EVAL, "Foundation NSRegularExpression throwing init"),
        ],
        # [20260305_FEATURE] Rust ReDoS sinks
        "rust": [
            SinkDefinition("Regex::new(", 0.75, SecuritySink.EVAL, "regex crate dynamic Regex"),
            SinkDefinition("RegexSet::new(", 0.7, SecuritySink.EVAL, "regex crate RegexSet"),
            SinkDefinition("Regex::is_match(", 0.6, SecuritySink.EVAL, "regex crate is_match"),
            SinkDefinition("Regex::find(", 0.6, SecuritySink.EVAL, "regex crate find"),
        ],
    },
}


# [20251216_FEATURE] OWASP Top 10 2021 complete mapping
# [20251229_UPDATE] v3.0.4 - Added weak_crypto, xxe, log_injection, redos patterns
OWASP_COVERAGE: Dict[str, List[str]] = {
    "A01:2021 – Broken Access Control": [
        "path_traversal",
        "unauthorized_file_access",
    ],
    "A02:2021 – Cryptographic Failures": [
        "weak_crypto",  # MD5, SHA1, DES, etc.
        "hardcoded_secrets",
        "insecure_random",
    ],
    "A03:2021 – Injection": [
        "sql_injection",
        "nosql_injection",
        "command_injection",
        "ldap_injection",
        "xpath_injection",
        "xss",
        "ssti",
        "xxe",
        "redos",  # ReDoS via regex injection
    ],
    "A04:2021 – Insecure Design": [
        "missing_rate_limiting",
        "insecure_defaults",
        "type_evaporation",  # v3.0.4 - TypeScript type system evaporation
    ],
    "A05:2021 – Security Misconfiguration": [
        "debug_mode_enabled",
        "verbose_errors",
        "default_credentials",
        "xxe",  # XXE is also a misconfiguration issue
    ],
    "A06:2021 – Vulnerable and Outdated Components": [
        "outdated_dependencies",  # Via scan_dependencies MCP tool
    ],
    "A07:2021 – Identification and Authentication Failures": [
        "weak_password_policy",
        "missing_mfa",
        "session_fixation",
    ],
    "A08:2021 – Software and Data Integrity Failures": [
        "unsigned_code",
        "deserialization",
    ],
    "A09:2021 – Security Logging and Monitoring Failures": [
        "log_injection",  # v3.0.4 - Log injection patterns
        "missing_audit_log",
        "insufficient_logging",
    ],
    "A10:2021 – Server-Side Request Forgery": [
        "ssrf",
        "unvalidated_redirect",
    ],
}


class UnifiedSinkDetector:
    """
    Polyglot security sink detection with confidence scoring.

    This detector provides unified vulnerability detection across multiple
    programming languages with explicit confidence scoring for each pattern.

    Features:
    - Multi-language support (Python, Java, TypeScript, JavaScript)
    - Confidence-based detection (filters by minimum threshold)
    - Data flow analysis integration
    - Sanitizer detection
    - Parameterization detection

    Example:
        detector = UnifiedSinkDetector()
        sinks = detector.detect_sinks(code, "python", min_confidence=0.8)

        for sink in sinks:
            print(f"Found {sink.sink_type} at line {sink.line} (confidence: {sink.confidence})")
    """

    def __init__(self):
        """Initialize the unified sink detector."""
        self.sinks = UNIFIED_SINKS
        self.owasp_map = OWASP_COVERAGE

    def detect_sinks(
        self, code: str, language: str, min_confidence: float = 0.8
    ) -> List[DetectedSink]:
        """
        Detect security sinks with confidence scores.

        Only returns sinks that meet or exceed the minimum confidence threshold.

        Args:
            code: Source code to analyze
            language: Programming language (python, java, typescript, javascript)
            min_confidence: Minimum confidence threshold (0.0-1.0)

        Returns:
            List of detected sinks that meet the confidence threshold

        Raises:
            ValueError: If language is not supported
        """
        # [20260304_FEATURE] Languages without defined sink patterns return [] gracefully.
        # Sink patterns for go, c, cpp, csharp, kotlin, php, ruby, swift will be
        # added incrementally; unknown languages are not rejected at this layer.

        # [20251228_BUGFIX] Return a list-like object with `.sinks` for compatibility.
        class _DetectedSinkList(list):
            @property
            def sinks(self):  # type: ignore[override]
                return self

        # For Python, we can use AST parsing
        if language == "python":
            return _DetectedSinkList(self._detect_python_sinks(code, min_confidence))

        # For other languages, pattern-based detection
        # This would require tree-sitter or similar for full AST support
        return _DetectedSinkList(
            self._detect_pattern_sinks(code, language, min_confidence)
        )

    def _detect_python_sinks(
        self, code: str, min_confidence: float
    ) -> List[DetectedSink]:
        """Detect sinks in Python code using AST and Taint Tracking."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        # [20260115_FEATURE] 1.3 Confidence Calibration & Taint Integration
        # Run full security analysis to identify high-confidence vulnerabilities
        from .security_analyzer import SecurityAnalyzer

        verified_locs = set()
        try:
            analyzer = SecurityAnalyzer()
            result = analyzer.analyze(code)

            # Map valid vulnerability locations (Match + Taint + No Sanitizer)
            for vuln in result.vulnerabilities:
                if vuln.sink_location:
                    verified_locs.add(vuln.sink_location)
        except Exception:
            # Fallback to pure AST matching if analysis fails
            pass

        detected = []

        for vuln_type, lang_sinks in self.sinks.items():
            if "python" not in lang_sinks:
                continue

            for sink_def in lang_sinks["python"]:
                # [20260115_FEATURE] Re-calibrate confidence
                # Pure AST pattern match = 0.5 (Base)
                base_confidence = 0.5

                # Find matches in AST
                matches = self._find_ast_matches(tree, sink_def.pattern)

                for match in matches:
                    line_no = getattr(match, "lineno", None) or 0
                    col_offset = getattr(match, "col_offset", None) or 0

                    # Determine confidence score
                    current_confidence = base_confidence

                    if (line_no, col_offset) in verified_locs:
                        # Match + taint + NO sanitizer = 0.95 confidence
                        current_confidence = 0.95

                    # Filter by requested threshold
                    if current_confidence < min_confidence:
                        continue

                    detected.append(
                        DetectedSink(
                            pattern=sink_def.pattern,
                            sink_type=sink_def.sink_type,
                            confidence=current_confidence,
                            line=line_no,
                            column=col_offset,
                            code_snippet=(
                                self._extract_snippet(code, line_no) if line_no else ""
                            ),
                            vulnerability_type=vuln_type,
                        )
                    )

        return detected

    def _find_ast_matches(self, tree: ast.AST, pattern: str) -> List[ast.AST]:
        """Find AST nodes matching a pattern."""
        matches = []

        class PatternFinder(ast.NodeVisitor):
            def visit_Call(self, node):
                # Extract function name from call
                func_name = self._get_call_name(node)
                # [20240613_BUGFIX] Ensure pattern matches only at proper boundaries (exact or dot-qualified)
                if func_name == pattern or func_name.endswith("." + pattern):
                    matches.append(node)
                self.generic_visit(node)

            def _get_call_name(self, node: ast.Call) -> str:
                """Extract the full qualified name of a function call."""
                if isinstance(node.func, ast.Name):
                    return node.func.id
                elif isinstance(node.func, ast.Attribute):
                    parts = []
                    current = node.func
                    while isinstance(current, ast.Attribute):
                        parts.append(current.attr)
                        current = current.value
                    if isinstance(current, ast.Name):
                        parts.append(current.id)
                    return ".".join(reversed(parts))
                return ""

        finder = PatternFinder()
        finder.visit(tree)
        return matches

    def _detect_pattern_sinks(
        self, code: str, language: str, min_confidence: float
    ) -> List[DetectedSink]:
        """Detect sinks using simple pattern matching (fallback for non-Python)."""
        detected = []
        lines = code.split("\n")

        for vuln_type, lang_sinks in self.sinks.items():
            if language not in lang_sinks:
                continue

            for sink_def in lang_sinks[language]:
                if sink_def.confidence < min_confidence:
                    continue

                # Simple pattern matching in code
                for line_no, line in enumerate(lines, start=1):
                    if sink_def.pattern in line:
                        detected.append(
                            DetectedSink(
                                pattern=sink_def.pattern,
                                sink_type=sink_def.sink_type,
                                confidence=sink_def.confidence,
                                line=line_no,
                                column=line.find(sink_def.pattern),
                                code_snippet=line.strip(),
                                vulnerability_type=vuln_type,
                            )
                        )

        return detected

    def _extract_snippet(self, code: str, line_no: int, context: int = 0) -> str:
        """
        [20240613_BUGFIX] Implement context-aware snippet extraction for vulnerability reporting.

        Extract code snippet around a line number, including `context` lines before and after.

        Args:
            code: The full source code as a string.
            line_no: 1-based line number to center the snippet on.
            context: Number of lines before and after to include (default: 0).

        Returns:
            String containing the snippet, or empty string if line_no is out of range.
        """
        lines = code.split("\n")
        n_lines = len(lines)
        if not (1 <= line_no <= n_lines):
            return ""
        # Calculate start and end indices (0-based, inclusive)
        start = max(0, line_no - 1 - context)
        end = min(n_lines, line_no + context)
        snippet_lines = lines[start:end]
        return "\n".join(snippet_lines).strip()

    def is_vulnerable(
        self, sink: DetectedSink, taint_info: Optional[TaintInfo] = None
    ) -> Tuple[bool, str]:
        """
        Determine if a sink is vulnerable based on taint analysis.

        Args:
            sink: The detected sink
            taint_info: Taint information for data flowing to sink

        Returns:
            Tuple of (is_vulnerable, explanation)
        """
        # If no taint info provided, assume potentially vulnerable
        if taint_info is None:
            return True, f"Sink at line {sink.line} requires manual review"

        # Check if tainted data reaches this sink
        if taint_info.level == TaintLevel.NONE:
            return False, "No tainted data reaches this sink"

        # Check if taint is dangerous for this specific sink type
        if not taint_info.is_dangerous_for(sink.sink_type):
            sanitizers = ", ".join(taint_info.sanitizers_applied)
            return False, f"Data sanitized by: {sanitizers}"

        # Check confidence threshold
        if sink.confidence < 0.7:
            return True, f"Possible vulnerability (low confidence: {sink.confidence})"

        return True, f"Tainted data flows to {sink.pattern} at line {sink.line}"

    def get_owasp_category(self, vuln_type: str) -> Optional[str]:
        """
        Get OWASP Top 10 category for a vulnerability type.

        Args:
            vuln_type: Vulnerability type (e.g., "sql_injection")

        Returns:
            OWASP category string or None if not found
        """
        for category, types in self.owasp_map.items():
            if vuln_type in types:
                return category
        return None

    def get_coverage_report(self) -> CoverageReportDict:
        """
        Generate a coverage report showing all supported patterns.

        Returns:
            Dictionary with coverage statistics and details
        """
        report: CoverageReportDict = {
            "total_patterns": 0,
            "by_language": {},
            "by_vulnerability": {},
            "owasp_coverage": {},
        }

        for vuln_type, lang_sinks in self.sinks.items():
            report["by_vulnerability"][vuln_type] = {}

            for language, sink_defs in lang_sinks.items():
                count = len(sink_defs)
                report["total_patterns"] += count

                if language not in report["by_language"]:
                    report["by_language"][language] = 0
                report["by_language"][language] += count

                report["by_vulnerability"][vuln_type][language] = count

        # OWASP coverage
        for category, vuln_types in self.owasp_map.items():
            covered = sum(1 for vt in vuln_types if vt in self.sinks)
            report["owasp_coverage"][category] = {
                "total": len(vuln_types),
                "covered": covered,
                "percentage": (covered / len(vuln_types) * 100) if vuln_types else 0,
            }

        return report
