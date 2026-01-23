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
from typing import Any, TypedDict


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
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")


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
UNIFIED_SINKS: dict[str, dict[str, list[SinkDefinition]]] = {
    # ==========================================================================
    # A03:2021 – Injection - SQL Injection
    # ==========================================================================
    "sql_injection": {
        "python": [
            SinkDefinition("cursor.execute", 0.5, SecuritySink.SQL_QUERY, "Raw SQL execution"),
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
            SinkDefinition("db.execute", 0.5, SecuritySink.SQL_QUERY, "Generic database execute"),
            SinkDefinition("cursor.executemany", 0.5, SecuritySink.SQL_QUERY, "Batch SQL execution"),
            SinkDefinition("RawSQL", 0.5, SecuritySink.SQL_QUERY, "Django raw SQL"),
            SinkDefinition("QuerySet.extra", 0.5, SecuritySink.SQL_QUERY, "Django QuerySet extra"),
            SinkDefinition("sqlalchemy.text", 0.5, SecuritySink.SQL_QUERY, "SQLAlchemy text query"),
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
            SinkDefinition("connection.query", 0.5, SecuritySink.SQL_QUERY, "Direct SQL query"),
            SinkDefinition("pool.query", 0.5, SecuritySink.SQL_QUERY, "Connection pool query"),
            SinkDefinition("knex.raw", 0.5, SecuritySink.SQL_QUERY, "Knex raw SQL"),
            SinkDefinition("knex.whereRaw", 0.5, SecuritySink.SQL_QUERY, "Knex raw where clause"),
            SinkDefinition("sequelize.query", 0.5, SecuritySink.SQL_QUERY, "Sequelize raw query"),
            SinkDefinition("prisma.$queryRaw", 0.5, SecuritySink.SQL_QUERY, "Prisma raw query"),
            SinkDefinition("typeorm.query", 0.5, SecuritySink.SQL_QUERY, "TypeORM raw query"),
        ],
        "javascript": [
            SinkDefinition("db.query", 0.5, SecuritySink.SQL_QUERY, "Generic database query"),
            SinkDefinition("sequelize.query", 0.8, SecuritySink.SQL_QUERY, "Sequelize query"),
            SinkDefinition("mysql.query", 0.95, SecuritySink.SQL_QUERY, "MySQL driver query"),
            SinkDefinition("pg.query", 0.95, SecuritySink.SQL_QUERY, "PostgreSQL driver query"),
            SinkDefinition("Model.find", 0.7, SecuritySink.SQL_QUERY, "MongoDB/Mongoose find"),
        ],
    },
    # ==========================================================================
    # A03:2021 – Injection - Command Injection
    # ==========================================================================
    "command_injection": {
        "python": [
            SinkDefinition("os.system", 1.0, SecuritySink.SHELL_COMMAND, "Direct shell execution"),
            SinkDefinition("subprocess.call", 0.9, SecuritySink.SHELL_COMMAND, "Subprocess call"),
            SinkDefinition("subprocess.run", 0.9, SecuritySink.SHELL_COMMAND, "Subprocess run"),
            SinkDefinition("subprocess.Popen", 0.9, SecuritySink.SHELL_COMMAND, "Subprocess Popen"),
            SinkDefinition("os.popen", 1.0, SecuritySink.SHELL_COMMAND, "OS popen"),
            SinkDefinition("eval", 1.0, SecuritySink.EVAL, "Python eval - code injection"),
            SinkDefinition("exec", 1.0, SecuritySink.EVAL, "Python exec - code injection"),
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
            SinkDefinition("child_process.execFile", 0.85, SecuritySink.SHELL_COMMAND, "Exec file"),
            SinkDefinition("eval", 1.0, SecuritySink.EVAL, "JavaScript eval"),
            SinkDefinition("Function", 1.0, SecuritySink.EVAL, "Function constructor"),
        ],
        "javascript": [
            SinkDefinition("exec", 1.0, SecuritySink.SHELL_COMMAND, "Shell exec"),
            SinkDefinition("spawn", 0.9, SecuritySink.SHELL_COMMAND, "Process spawn"),
            SinkDefinition("eval", 1.0, SecuritySink.EVAL, "JavaScript eval"),
            SinkDefinition("setTimeout", 0.8, SecuritySink.EVAL, "setTimeout with string"),
            SinkDefinition("setInterval", 0.8, SecuritySink.EVAL, "setInterval with string"),
        ],
    },
    # ==========================================================================
    # A03:2021 – Injection - Cross-Site Scripting (XSS)
    # ==========================================================================
    "xss": {
        "typescript": [
            SinkDefinition("innerHTML", 1.0, SecuritySink.DOM_XSS, "Direct HTML injection"),
            SinkDefinition("outerHTML", 1.0, SecuritySink.DOM_XSS, "Outer HTML injection"),
            SinkDefinition(
                "dangerouslySetInnerHTML",
                1.0,
                SecuritySink.DOM_XSS,
                "React dangerous HTML",
            ),
            SinkDefinition("document.write", 1.0, SecuritySink.DOM_XSS, "Document write"),
            SinkDefinition("insertAdjacentHTML", 0.95, SecuritySink.DOM_XSS, "Insert adjacent HTML"),
            SinkDefinition("v-html", 1.0, SecuritySink.DOM_XSS, "Vue v-html directive"),
            SinkDefinition("[innerHTML]", 1.0, SecuritySink.DOM_XSS, "Angular innerHTML binding"),
        ],
        "javascript": [
            SinkDefinition("document.write", 1.0, SecuritySink.DOM_XSS, "Document write"),
            SinkDefinition("element.innerHTML", 1.0, SecuritySink.DOM_XSS, "Element innerHTML"),
            SinkDefinition("outerHTML", 1.0, SecuritySink.DOM_XSS, "Outer HTML"),
            SinkDefinition("jQuery.html", 0.95, SecuritySink.DOM_XSS, "jQuery HTML method"),
            SinkDefinition("$.html", 0.95, SecuritySink.DOM_XSS, "jQuery shorthand HTML"),
        ],
        "python": [
            SinkDefinition(
                "render_template_string",
                1.0,
                SecuritySink.SSTI,
                "Flask template string rendering",
            ),
            SinkDefinition("jinja2.Template", 1.0, SecuritySink.SSTI, "Jinja2 template injection"),
            SinkDefinition("Markup", 0.8, SecuritySink.HTML_OUTPUT, "MarkupSafe Markup"),
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
    },
    # ==========================================================================
    # A01:2021 – Broken Access Control - Path Traversal
    # ==========================================================================
    "path_traversal": {
        "python": [
            SinkDefinition("open", 0.8, SecuritySink.FILE_PATH, "File open - context dependent"),
            SinkDefinition("os.path.join", 0.6, SecuritySink.FILE_PATH, "Path join - can be safe"),
            SinkDefinition("pathlib.Path", 0.7, SecuritySink.FILE_PATH, "Path construction"),
            SinkDefinition("shutil.copy", 0.85, SecuritySink.FILE_PATH, "File copy operation"),
        ],
        "java": [
            SinkDefinition("new File", 0.8, SecuritySink.FILE_PATH, "File constructor"),
            SinkDefinition("Files.readString", 0.8, SecuritySink.FILE_PATH, "Read file as string"),
            SinkDefinition("Files.readAllBytes", 0.8, SecuritySink.FILE_PATH, "Read file bytes"),
            SinkDefinition("FileInputStream", 0.9, SecuritySink.FILE_PATH, "File input stream"),
            SinkDefinition("FileOutputStream", 0.9, SecuritySink.FILE_PATH, "File output stream"),
        ],
        "typescript": [
            SinkDefinition("fs.readFile", 0.8, SecuritySink.FILE_PATH, "Read file"),
            SinkDefinition("fs.readFileSync", 0.8, SecuritySink.FILE_PATH, "Synchronous read"),
            SinkDefinition("fs.writeFile", 0.85, SecuritySink.FILE_PATH, "Write file"),
            SinkDefinition("fs.createReadStream", 0.8, SecuritySink.FILE_PATH, "Create read stream"),
            SinkDefinition("require", 0.7, SecuritySink.FILE_PATH, "Dynamic require"),
        ],
        "javascript": [
            SinkDefinition("fs.readFile", 0.8, SecuritySink.FILE_PATH, "File read"),
            SinkDefinition("fs.writeFile", 0.85, SecuritySink.FILE_PATH, "File write"),
            SinkDefinition("path.join", 0.6, SecuritySink.FILE_PATH, "Path join"),
        ],
    },
    # ==========================================================================
    # A10:2021 – Server-Side Request Forgery (SSRF)
    # ==========================================================================
    "ssrf": {
        "python": [
            SinkDefinition("requests.get", 0.9, SecuritySink.SSRF, "HTTP GET request"),
            SinkDefinition("requests.post", 0.9, SecuritySink.SSRF, "HTTP POST request"),
            SinkDefinition("urllib.request.urlopen", 0.95, SecuritySink.SSRF, "URL open"),
            SinkDefinition("httpx.get", 0.9, SecuritySink.SSRF, "HTTPX GET"),
            SinkDefinition("aiohttp.ClientSession.get", 0.9, SecuritySink.SSRF, "Aiohttp GET"),
        ],
        "java": [
            SinkDefinition("URL.openConnection", 1.0, SecuritySink.SSRF, "URL connection open"),
            SinkDefinition("HttpURLConnection", 0.95, SecuritySink.SSRF, "HTTP URL connection"),
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
            SinkDefinition("WebClient.get", 0.85, SecuritySink.SSRF, "Spring WebFlux WebClient"),
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
            SinkDefinition("request.get", 0.9, SecuritySink.SSRF, "Request library GET"),
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
            SinkDefinition("Crypto.Hash.MD5", 0.95, SecuritySink.WEAK_CRYPTO, "PyCryptodome MD5"),
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
            SinkDefinition('Cipher.getInstance("DES")', 1.0, SecuritySink.WEAK_CRYPTO, "DES cipher"),
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
            SinkDefinition("CryptoJS.MD5", 0.95, SecuritySink.WEAK_CRYPTO, "CryptoJS MD5"),
            SinkDefinition("CryptoJS.SHA1", 0.85, SecuritySink.WEAK_CRYPTO, "CryptoJS SHA1"),
            SinkDefinition("CryptoJS.DES", 1.0, SecuritySink.WEAK_CRYPTO, "CryptoJS DES"),
            SinkDefinition("md5(", 0.95, SecuritySink.WEAK_CRYPTO, "MD5 function call"),
            SinkDefinition("sha1(", 0.85, SecuritySink.WEAK_CRYPTO, "SHA1 function call"),
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
            SinkDefinition("CryptoJS.MD5", 0.95, SecuritySink.WEAK_CRYPTO, "CryptoJS MD5"),
            SinkDefinition("CryptoJS.SHA1", 0.85, SecuritySink.WEAK_CRYPTO, "CryptoJS SHA1"),
            SinkDefinition("CryptoJS.DES", 1.0, SecuritySink.WEAK_CRYPTO, "CryptoJS DES"),
            SinkDefinition("md5(", 0.95, SecuritySink.WEAK_CRYPTO, "MD5 function call"),
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
            SinkDefinition("xml.dom.minidom.parse", 0.9, SecuritySink.XXE, "minidom parse"),
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
            SinkDefinition("Unmarshaller.unmarshal", 0.9, SecuritySink.XXE, "JAXB unmarshal"),
        ],
        "typescript": [
            SinkDefinition("DOMParser", 0.85, SecuritySink.XXE, "Browser DOMParser"),
            SinkDefinition(
                "new DOMParser().parseFromString",
                0.85,
                SecuritySink.XXE,
                "DOMParser parseFromString",
            ),
            SinkDefinition("xml2js.parseString", 0.9, SecuritySink.XXE, "xml2js parser"),
            SinkDefinition("xml2js.Parser", 0.9, SecuritySink.XXE, "xml2js Parser class"),
            SinkDefinition("fast-xml-parser", 0.85, SecuritySink.XXE, "fast-xml-parser"),
            SinkDefinition("XMLParser", 0.85, SecuritySink.XXE, "XMLParser"),
            SinkDefinition("xmldom", 0.9, SecuritySink.XXE, "xmldom library"),
            SinkDefinition("libxmljs", 0.95, SecuritySink.XXE, "libxmljs - XXE vulnerable"),
            SinkDefinition("sax.parser", 0.85, SecuritySink.XXE, "SAX parser"),
        ],
        "javascript": [
            SinkDefinition("DOMParser", 0.85, SecuritySink.XXE, "Browser DOMParser"),
            SinkDefinition("xml2js.parseString", 0.9, SecuritySink.XXE, "xml2js parser"),
            SinkDefinition("fast-xml-parser", 0.85, SecuritySink.XXE, "fast-xml-parser"),
            SinkDefinition("xmldom", 0.9, SecuritySink.XXE, "xmldom library"),
            SinkDefinition("libxmljs", 0.95, SecuritySink.XXE, "libxmljs - XXE vulnerable"),
        ],
    },
    # ==========================================================================
    # [20251229_FEATURE] v3.0.4 - A09:2021 – Security Logging and Monitoring Failures
    # ==========================================================================
    "log_injection": {
        "python": [
            SinkDefinition("logging.info", 0.7, SecuritySink.LOG_OUTPUT, "Logging info"),
            SinkDefinition("logging.warning", 0.7, SecuritySink.LOG_OUTPUT, "Logging warning"),
            SinkDefinition("logging.error", 0.7, SecuritySink.LOG_OUTPUT, "Logging error"),
            SinkDefinition("logging.debug", 0.6, SecuritySink.LOG_OUTPUT, "Logging debug"),
            SinkDefinition("logger.info", 0.7, SecuritySink.LOG_OUTPUT, "Logger info"),
            SinkDefinition("logger.error", 0.7, SecuritySink.LOG_OUTPUT, "Logger error"),
        ],
        "java": [
            SinkDefinition("Logger.info", 0.7, SecuritySink.LOG_OUTPUT, "Logger info"),
            SinkDefinition("Logger.warn", 0.7, SecuritySink.LOG_OUTPUT, "Logger warn"),
            SinkDefinition("Logger.error", 0.7, SecuritySink.LOG_OUTPUT, "Logger error"),
            SinkDefinition("log.info", 0.7, SecuritySink.LOG_OUTPUT, "SLF4J log info"),
            SinkDefinition("log.error", 0.7, SecuritySink.LOG_OUTPUT, "SLF4J log error"),
            SinkDefinition("System.out.println", 0.6, SecuritySink.LOG_OUTPUT, "Console output"),
        ],
        "typescript": [
            SinkDefinition(
                "console.log",
                0.65,
                SecuritySink.LOG_OUTPUT,
                "Console log - may leak data",
            ),
            SinkDefinition("console.error", 0.65, SecuritySink.LOG_OUTPUT, "Console error"),
            SinkDefinition("console.warn", 0.65, SecuritySink.LOG_OUTPUT, "Console warn"),
            SinkDefinition("console.info", 0.65, SecuritySink.LOG_OUTPUT, "Console info"),
            SinkDefinition("winston.log", 0.75, SecuritySink.LOG_OUTPUT, "Winston logger"),
            SinkDefinition("winston.info", 0.75, SecuritySink.LOG_OUTPUT, "Winston info"),
            SinkDefinition("winston.error", 0.75, SecuritySink.LOG_OUTPUT, "Winston error"),
            SinkDefinition("pino.info", 0.75, SecuritySink.LOG_OUTPUT, "Pino logger info"),
            SinkDefinition("pino.error", 0.75, SecuritySink.LOG_OUTPUT, "Pino logger error"),
            SinkDefinition("bunyan.info", 0.75, SecuritySink.LOG_OUTPUT, "Bunyan logger info"),
            SinkDefinition("bunyan.error", 0.75, SecuritySink.LOG_OUTPUT, "Bunyan logger error"),
            SinkDefinition("log4js.getLogger", 0.75, SecuritySink.LOG_OUTPUT, "Log4js logger"),
        ],
        "javascript": [
            SinkDefinition("console.log", 0.65, SecuritySink.LOG_OUTPUT, "Console log"),
            SinkDefinition("console.error", 0.65, SecuritySink.LOG_OUTPUT, "Console error"),
            SinkDefinition("winston.log", 0.75, SecuritySink.LOG_OUTPUT, "Winston logger"),
            SinkDefinition("pino.info", 0.75, SecuritySink.LOG_OUTPUT, "Pino logger"),
            SinkDefinition("bunyan.info", 0.75, SecuritySink.LOG_OUTPUT, "Bunyan logger"),
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
            SinkDefinition("String.matches", 0.6, SecuritySink.EVAL, "String regex match"),
            SinkDefinition("String.replaceAll", 0.6, SecuritySink.EVAL, "Regex replace"),
        ],
        "typescript": [
            SinkDefinition(
                "new RegExp",
                0.75,
                SecuritySink.EVAL,
                "Dynamic regex - ReDoS risk if user input",
            ),
            SinkDefinition("RegExp(", 0.75, SecuritySink.EVAL, "RegExp constructor with user input"),
            SinkDefinition(".match(", 0.6, SecuritySink.EVAL, "String match with regex"),
            SinkDefinition(".replace(", 0.6, SecuritySink.EVAL, "String replace with regex"),
            SinkDefinition(".search(", 0.6, SecuritySink.EVAL, "String search with regex"),
            SinkDefinition(".split(", 0.5, SecuritySink.EVAL, "String split with regex"),
        ],
        "javascript": [
            SinkDefinition("new RegExp", 0.75, SecuritySink.EVAL, "Dynamic regex - ReDoS risk"),
            SinkDefinition("RegExp(", 0.75, SecuritySink.EVAL, "RegExp constructor"),
            SinkDefinition(".match(", 0.6, SecuritySink.EVAL, "String match"),
            SinkDefinition(".replace(", 0.6, SecuritySink.EVAL, "String replace"),
        ],
    },
}


# [20251216_FEATURE] OWASP Top 10 2021 complete mapping
# [20251229_UPDATE] v3.0.4 - Added weak_crypto, xxe, log_injection, redos patterns
OWASP_COVERAGE: dict[str, list[str]] = {
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

    def detect_sinks(self, code: str, language: str, min_confidence: float = 0.8) -> list[DetectedSink]:
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
        if language not in ["python", "java", "typescript", "javascript"]:
            raise ValueError(f"Unsupported language: {language}")

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
        return _DetectedSinkList(self._detect_pattern_sinks(code, language, min_confidence))

    def _detect_python_sinks(self, code: str, min_confidence: float) -> list[DetectedSink]:
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
                            code_snippet=(self._extract_snippet(code, line_no) if line_no else ""),
                            vulnerability_type=vuln_type,
                        )
                    )

        return detected

    def _find_ast_matches(self, tree: ast.AST, pattern: str) -> list[ast.AST]:
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

    def _detect_pattern_sinks(self, code: str, language: str, min_confidence: float) -> list[DetectedSink]:
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

    def is_vulnerable(self, sink: DetectedSink, taint_info: TaintInfo | None = None) -> tuple[bool, str]:
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

    def get_owasp_category(self, vuln_type: str) -> str | None:
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
