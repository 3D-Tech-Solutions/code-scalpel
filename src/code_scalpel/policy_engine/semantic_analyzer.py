"""
Semantic Analyzer - Advanced pattern detection for policy enforcement.

[20251216_FEATURE] v2.5.0 Guardian - Semantic code analysis

This module provides semantic analysis for policy enforcement, detecting
security issues through code pattern analysis rather than simple text matching.

Key Features:
- SQL injection detection via string concatenation
- SQL injection via StringBuilder/StringBuffer patterns
- SQL injection via f-strings/template literals
- SQL injection via string.format()

Example:
    analyzer = SemanticAnalyzer()

    # Detects SQL via concatenation
    code = 'query = "SELECT * FROM users WHERE id=" + user_id'
    has_sql = analyzer.contains_sql_sink(code, "python")

    # Detects SQL via f-string
    code = 'query = f"SELECT * FROM {table} WHERE id={user_id}"'
    has_sql = analyzer.contains_sql_sink(code, "python")
"""

from __future__ import annotations

import ast
import re


class SemanticAnalyzer:
    """
    Semantic analysis for policy enforcement.

    [20251216_FEATURE] v2.5.0 Guardian - Detect security issues semantically

    This analyzer goes beyond simple pattern matching to understand the
    semantic meaning of code, detecting vulnerabilities even when syntax varies.
    """

    # SQL keywords that indicate database operations
    SQL_KEYWORDS = {
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "CREATE",
        "ALTER",
        "TRUNCATE",
        "REPLACE",
        "MERGE",
        "GRANT",
        "REVOKE",
    }

    # [20240613_REFACTOR] Removed empty __init__ method; default constructor is sufficient.
    def contains_sql_sink(self, code: str, language: str) -> bool:
        """
        Detect SQL operations semantically, not just syntactically.

        [20251216_FEATURE] Comprehensive SQL injection detection

        Examples that must be caught:
        - Direct: cursor.execute("SELECT * FROM users WHERE id=" + user_id)
        - StringBuilder: query = new StringBuilder(); query.append("SELECT * FROM users WHERE id="); query.append(userId);
        - Concatenation: sql = f"SELECT * FROM {table} WHERE id={user_id}"
        - String format: sql = "SELECT * FROM users WHERE id=%s" % user_id

        Args:
            code: Source code to analyze
            language: Programming language (python, java, javascript, typescript)

        Returns:
            True if SQL operation detected
        """

        if language.lower() in ["python"]:
            return self._detect_python_sql(code)
        elif language.lower() in ["java"]:
            return self._detect_java_sql(code)
        elif language.lower() in ["javascript", "typescript", "js", "ts"]:
            return self._detect_javascript_sql(code)
        else:
            # Fallback to simple text search for unsupported languages
            return self._contains_sql_keywords_text(code)

    def _detect_python_sql(self, code: str) -> bool:
        """
        Detect SQL in Python code.

        [20251216_FEATURE] Python-specific SQL detection

        Detects:
        - String concatenation with +
        - f-strings with SQL keywords
        - .format() with SQL keywords
        - % formatting with SQL keywords

        Args:

            code: Python source code

        Returns:
            True if SQL detected
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # If code doesn't parse, fall back to text search
            return self._contains_sql_keywords_text(code)

        for node in ast.walk(tree):
            # Check string concatenation
            if self._is_string_concatenation(node):
                if self._contains_sql_keywords_in_node(node):
                    return True

            # Check f-strings
            if isinstance(node, ast.JoinedStr):
                if self._contains_sql_keywords_in_node(node):
                    return True

            # Check .format() calls
            if isinstance(node, ast.Call):
                if self._is_format_call(node):
                    if self._contains_sql_keywords_in_node(node):
                        return True

                # Check % formatting

            # Check binary operations with % (old-style formatting)
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
                if isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
                    if any(kw in node.left.value.upper() for kw in self.SQL_KEYWORDS):
                        return True

        return False

    def _detect_java_sql(self, code: str) -> bool:
        """
        Detect SQL in Java code.

        [20251216_FEATURE] Java-specific SQL detection

        Detects:
        - StringBuilder/StringBuffer patterns
        - String concatenation with +

        Args:
            code: Java source code

        Returns:
            True if SQL detected
        """
        # For Java, we'll use text-based analysis since we don't have a Java parser
        # Check for StringBuilder/StringBuffer patterns
        string_builder_pattern = r"(StringBuilder|StringBuffer)\s+\w+\s*=\s*new\s+(StringBuilder|StringBuffer)"
        if re.search(string_builder_pattern, code):
            # Check if appends contain SQL keywords
            append_pattern = r"\.append\s*\([^)]*\)"
            appends = re.findall(append_pattern, code)
            accumulated = " ".join(appends)
            if any(kw in accumulated.upper() for kw in self.SQL_KEYWORDS):
                return True

        # Check for string concatenation with SQL keywords
        return self._contains_sql_keywords_text(code)

    def _detect_javascript_sql(self, code: str) -> bool:
        """
        Detect SQL in JavaScript/TypeScript code.

        [20251216_FEATURE] JavaScript/TypeScript SQL detection

        Detects:
        - Template literals with SQL keywords
        - String concatenation with +

        Args:
            code: JavaScript/TypeScript source code

        Returns:
            True if SQL detected
        """
        # Check for template literals
        template_literal_pattern = r"`[^`]*`"
        templates = re.findall(template_literal_pattern, code)
        for template in templates:
            if any(kw in template.upper() for kw in self.SQL_KEYWORDS):
                return True

        # Check for string concatenation
        return self._contains_sql_keywords_text(code)

    def _is_string_concatenation(self, node: ast.AST) -> bool:
        """
        Check if node is string concatenation.

        [20251216_FEATURE] Detect string + string patterns

        Args:
            node: AST node to check

        Returns:
            True if node is string concatenation
        """
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            # Check if either side is a string constant or contains strings
            return self._contains_string(node.left) or self._contains_string(node.right)
        return False

    def _contains_string(self, node: ast.AST) -> bool:
        """Check if node contains a string constant."""
        if isinstance(node, ast.Constant):
            return isinstance(node.value, str)
        if isinstance(node, ast.JoinedStr):
            return True
        if isinstance(node, ast.BinOp):
            return self._contains_string(node.left) or self._contains_string(node.right)
        return False

    def _contains_sql_keywords_in_node(self, node: ast.AST) -> bool:
        """
        Check if AST node contains SQL keywords.

        [20251216_FEATURE] Walk AST to find SQL keywords in strings

        Args:
            node: AST node to check

        Returns:
            True if SQL keywords found
        """
        for child in ast.walk(node):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                if any(kw in child.value.upper() for kw in self.SQL_KEYWORDS):
                    return True
        return False

    def _is_format_call(self, node: ast.Call) -> bool:
        """Check if node is a .format() call."""
        if isinstance(node.func, ast.Attribute):
            return node.func.attr == "format"
        return False

    def _contains_sql_keywords_text(self, text: str) -> bool:
        """
        Simple text-based SQL keyword detection.

        [20251216_FEATURE] Fallback for unsupported languages

        Args:
            text: Text to search

        Returns:
            True if SQL keywords found
        """
        text_upper = text.upper()
        return any(kw in text_upper for kw in self.SQL_KEYWORDS)

    def has_parameterization(self, code: str, language: str) -> bool:
        """
        Check if code uses parameterized queries.

        [20251216_FEATURE] Detect safe SQL patterns

        Parameterized queries use placeholders instead of string concatenation:
        - Python: cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
        - Python: cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
        - Java: PreparedStatement with setString()

        Args:
            code: Source code to analyze
            language: Programming language

        Returns:
            True if parameterized queries detected
        """
        if language.lower() == "python":
            # Look for execute() with multiple arguments (query + params)
            # Pattern: .execute("...", (...))
            pattern = r"\.execute\s*\([^,)]+,\s*[^)]+\)"
            if re.search(pattern, code):
                return True

            # Look for placeholder characters
            if "?" in code or "%s" in code:
                # Check if these are inside execute() calls
                execute_pattern = r"\.execute\s*\([^)]*[?%s][^)]*\)"
                if re.search(execute_pattern, code):
                    return True

        elif language.lower() == "java":
            # Look for PreparedStatement
            if "PreparedStatement" in code:
                return True
            # Look for setString/setInt calls
            if re.search(r"\.set(String|Int|Long|Double)", code):
                return True

        return False

    def has_annotation(self, code: str, annotation: str) -> bool:
        """
        Check if code has specific annotation.

        [20251216_FEATURE] Java/Python annotation detection

        Args:
            code: Source code
            annotation: Annotation to search for (e.g., "@PreAuthorize")

        Returns:
            True if annotation found
        """
        # Simple text search for annotation
        return annotation in code

    def has_file_operation(self, code: str) -> bool:
        """
        Check if code contains file operations.

        [20251216_FEATURE] Detect file I/O operations

        Args:
            code: Source code

        Returns:
            True if file operations detected
        """
        file_ops = [
            "open(",
            "file(",
            "read(",
            "write(",
            "File(",
            "FileReader",
            "FileWriter",
            "fs.readFile",
            "fs.writeFile",
        ]
        return any(op in code for op in file_ops)

    def tainted_path_input(self, code: str) -> bool:
        """
        Check if file path comes from user input.

        [20251216_FEATURE] Detect path traversal vulnerabilities

        This is a simplified check. In production, this should integrate
        with the TaintTracker for proper data flow analysis.

        Args:
            code: Source code

        Returns:
            True if user-controlled path detected
        """
        # Simple heuristic: check if file operation uses request/input data
        user_input_patterns = [
            "request.",
            "input(",
            "argv",
            "args.",
            "req.",
            "params.",
            "query.",
            "body.",
        ]

        # Check if user input is near file operations
        has_user_input = any(pattern in code for pattern in user_input_patterns)
        has_file_op = self.has_file_operation(code)

        return has_user_input and has_file_op

    # [20251221_FEATURE] Enhanced security detection methods

    def contains_xss_sink(self, code: str, language: str) -> bool:
        """
        Detect XSS (Cross-Site Scripting) vulnerabilities.

        [20251221_FEATURE] Detect unsafe DOM manipulation and output encoding issues

        Detects:
        - innerHTML/outerHTML assignments (JavaScript/TypeScript)
        - dangerouslySetInnerHTML (React)
        - document.write() with user input
        - Response.write() in Java/C# servlets
        - No sanitization checks

        Args:
            code: Source code to analyze
            language: Programming language

        Returns:
            True if XSS vulnerability pattern detected
        """
        language_lower = language.lower()

        # JavaScript/TypeScript DOM manipulation
        if language_lower in ["javascript", "js", "typescript", "ts"]:
            xss_sinks = [
                "innerHTML",
                "outerHTML",
                "dangerouslySetInnerHTML",
                "document.write",
                "insertAdjacentHTML",
            ]

            has_xss_sink = any(sink in code for sink in xss_sinks)

            if has_xss_sink:
                # Check if user input is anywhere in the code (not just right after sink)
                user_input_patterns = [
                    "userInput",
                    "user_input",
                    "event.",
                    "props.",
                    "req.",
                    "request.",
                    "query.",
                    "body.",
                    "args.",
                    "input(",
                ]
                has_user_input = any(pattern in code for pattern in user_input_patterns)
                return has_user_input

        # Java servlet response writing
        elif language_lower == "java":
            if "response.getWriter()" in code or "PrintWriter" in code:
                if any(req_access in code for req_access in ["request.getParameter", "getQueryString"]):
                    return True

        return False

    def contains_command_injection(self, code: str, language: str) -> bool:
        """
        Detect Command Injection vulnerabilities.

        [20251221_FEATURE] Detect unsafe shell command execution

        Detects:
        - os.system() / subprocess.call() with user input
        - Runtime.exec() with command concatenation
        - child_process.exec() with user input
        - shell=True in subprocess calls
        - eval/exec with untrusted code

        Args:
            code: Source code to analyze
            language: Programming language

        Returns:
            True if command injection vulnerability pattern detected
        """
        language_lower = language.lower()

        # Python command execution
        if language_lower == "python":
            dangerous_funcs = [
                "os.system",
                "subprocess.call",
                "subprocess.popen",
                "eval",
                "exec",
            ]

            has_dangerous = any(func in code for func in dangerous_funcs)

            if has_dangerous:
                # Check for shell=True or user input
                if "shell=True" in code:
                    return True
                # Check for user input patterns
                user_input_patterns = [
                    "request.",
                    "input(",
                    "argv",
                    "sys.argv",
                    "environ",
                    "user_",
                    "query",
                    "body",
                    "args",
                ]
                has_user_input = any(pattern in code for pattern in user_input_patterns)
                if has_user_input:
                    return True

        # Java command execution
        elif language_lower == "java":
            if "Runtime.getRuntime().exec" in code or "ProcessBuilder" in code:
                # Check if command uses user input
                if any(
                    user_input in code
                    for user_input in [
                        "request.getParameter",
                        "getQueryString",
                        "args[",
                    ]
                ):
                    return True

        # JavaScript/TypeScript command execution
        elif language_lower in ["javascript", "js", "typescript", "ts"]:
            dangerous_funcs = ["child_process.exec", "child_process.spawn", "eval"]

            has_dangerous = any(func in code for func in dangerous_funcs)

            if has_dangerous:
                # Check for user input
                user_input_patterns = ["req.", "body", "query", "params", "input"]
                has_user_input = any(pattern in code for pattern in user_input_patterns)
                if has_user_input:
                    return True

        return False

    def contains_path_traversal(self, code: str, language: str) -> bool:
        """
        Detect Path Traversal vulnerabilities.

        [20251221_FEATURE] Detect unsafe file path operations

        Detects:
        - File operations with user-controlled paths
        - Lack of path normalization
        - Using ../ or absolute paths
        - No path validation checks

        Args:
            code: Source code to analyze
            language: Programming language

        Returns:
            True if path traversal vulnerability pattern detected
        """
        if not self.has_file_operation(code):
            return False

        # Check for user-controlled paths without validation
        user_input_patterns = [
            "request.getParameter",
            "request.",
            "query.",
            "params.",
            "argv",
            "process.argv",
            "process.env",
            "req.",
            "body.",
            "input(",
        ]

        has_user_input = any(pattern in code for pattern in user_input_patterns)

        if not has_user_input:
            return False

        # Check if there's any path normalization/validation
        validation_patterns = [
            "normalizePath",
            "realpath",
            "abspath",
            "resolve",
            "startswith",
            "allowed_dir",
            "basename",
            "dirname",
        ]

        has_validation = any(pattern in code.lower() for pattern in validation_patterns)

        # If file operation + user input + no validation = vulnerable
        return not has_validation

    def contains_noql_injection(self, code: str) -> bool:
        """
        Detect NoSQL Injection vulnerabilities.

        [20251221_FEATURE] Detect unsafe NoSQL query construction

        Detects MongoDB patterns like:
        - db.collection.find() with user input
        - Query objects built from request parameters
        - No input validation/sanitization

        Args:
            code: Source code

        Returns:
            True if NoSQL injection pattern detected
        """
        nosql_patterns = [
            "db.",
            "collection",
            ".find",
            ".findOne",
            ".updateOne",
            ".deleteOne",
            ".aggregate",
            "mongodb",
            "mongoose",
        ]

        has_nosql = any(pattern in code for pattern in nosql_patterns)

        if not has_nosql:
            return False

        # Check for user input near NoSQL operations
        user_input_patterns = [
            "request.",
            "req.",
            "query.",
            "body.",
            "params.",
            "input(",
            "user_",
            "args.",
        ]

        has_user_input = any(pattern in code for pattern in user_input_patterns)

        return has_user_input

    def contains_ldap_injection(self, code: str) -> bool:
        """
        Detect LDAP Injection vulnerabilities.

        [20251221_FEATURE] Detect unsafe LDAP query construction

        Args:
            code: Source code

        Returns:
            True if LDAP injection pattern detected
        """
        ldap_patterns = [
            "ldap://",
            "InitialDirContext",
            "DirContext",
            "new LdapConnection",
            "ldap_bind",
            "ldap_search",
        ]

        has_ldap = any(pattern in code for pattern in ldap_patterns)

        if not has_ldap:
            return False

        # Check for user input in LDAP queries
        user_input_patterns = [
            "request.",
            "query.",
            "input(",
            "username",
            "user_id",
        ]

        has_user_input = any(pattern in code for pattern in user_input_patterns)

        return has_user_input

    def contains_xxe_injection(self, code: str, language: str) -> bool:
        """
        Detect XXE (XML External Entity) vulnerabilities.

        [20251221_FEATURE] Detect unsafe XML parsing

        Args:
            code: Source code
            language: Programming language

        Returns:
            True if XXE injection pattern detected
        """
        # Python XXE
        if language.lower() == "python":
            xml_parsers = ["xml.etree", "ElementTree", "lxml", "minidom", "pulldom"]
            has_xml = any(parser in code for parser in xml_parsers)

            if has_xml:
                # Check for defusedxml usage (safe)
                if "defusedxml" in code:
                    return False  # Safe

                # Unsafe if using standard XML parsers
                return True

        # Java XXE
        elif language.lower() == "java":
            if "DocumentBuilder" in code or "SAXParser" in code or "XMLInputFactory" in code:
                # Check for XXE prevention patterns
                safe_patterns = [
                    "XMLConstants.ACCESS_EXTERNAL",
                    "setFeature",
                    "XXE",
                ]

                has_safe_config = any(pattern in code for pattern in safe_patterns)
                return not has_safe_config

        return False
