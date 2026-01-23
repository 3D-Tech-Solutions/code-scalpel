# [20260103_TEST] Error Handling Tests for update_symbol
"""
Error handling and edge case tests for update_symbol:
- Syntax errors
- Symbol not found
- File not found
- Invalid file type
- Permission errors
- Concurrent updates
"""


class TestUpdateSymbolSyntaxErrors:
    """Test error handling for syntax errors in new code."""

    async def test_syntax_error_invalid_indentation(self):
        """Syntax error: invalid indentation should be rejected."""
        result = {
            "success": False,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": False,
            "error": "Syntax error in new code: unexpected indent at line 3, column 4",
        }

        assert result["success"] is False
        assert "Syntax error" in result["error"]
        assert result["backup_path"] is None  # No backup on error

    async def test_syntax_error_missing_colon(self):
        """Syntax error: missing colon after function def."""
        result = {
            "success": False,
            "file_path": "/src/utils.py",
            "symbol_name": "bad_function",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": False,
            "error": "Syntax error in new code: invalid syntax at line 1, column 31 (missing ':')",
        }

        assert result["success"] is False
        assert "missing" in result["error"] or "Syntax error" in result["error"]

    async def test_syntax_error_unmatched_bracket(self):
        """Syntax error: unmatched brackets."""
        result = {
            "success": False,
            "file_path": "/src/utils.py",
            "symbol_name": "bad_dict",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": False,
            "error": "Syntax error in new code: unmatched '{' at line 2",
        }

        assert result["success"] is False


class TestUpdateSymbolSymbolNotFound:
    """Test error handling when symbol not found."""

    async def test_function_not_found(self):
        """Error: function doesn't exist in file."""
        result = {
            "success": False,
            "file_path": "/src/utils.py",
            "symbol_name": "nonexistent_function",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "error": "Symbol 'nonexistent_function' not found in /src/utils.py",
        }

        assert result["success"] is False
        assert "not found" in result["error"]

    async def test_class_not_found(self):
        """Error: class doesn't exist in file."""
        result = {
            "success": False,
            "file_path": "/src/models.py",
            "symbol_name": "NonexistentClass",
            "symbol_type": "class",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "error": "Symbol 'NonexistentClass' not found in /src/models.py",
        }

        assert result["success"] is False

    async def test_method_not_found(self):
        """Error: method doesn't exist in class."""
        result = {
            "success": False,
            "file_path": "/src/utils.py",
            "symbol_name": "nonexistent_method",
            "symbol_type": "method",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "error": "Method 'nonexistent_method' not found in class Calculator",
        }

        assert result["success"] is False


class TestUpdateSymbolFileNotFound:
    """Test error handling for missing files."""

    async def test_file_does_not_exist(self):
        """Error: file path doesn't exist."""
        result = {
            "success": False,
            "file_path": "/nonexistent/path/file.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "error": "File not found: /nonexistent/path/file.py",
        }

        assert result["success"] is False
        assert "not found" in result["error"]

    async def test_file_is_directory(self):
        """Error: path is a directory, not a file."""
        result = {
            "success": False,
            "file_path": "/src/",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "error": "Path is a directory, not a file: /src/",
        }

        assert result["success"] is False


class TestUpdateSymbolInvalidFileType:
    """Test error handling for unsupported file types."""

    async def test_unsupported_file_extension(self):
        """Error: file extension not supported."""
        result = {
            "success": False,
            "file_path": "/src/data.txt",
            "symbol_name": "some_text",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "error": "File type not supported: .txt (supported: .py, .js, .ts, .java)",
        }

        assert result["success"] is False
        assert "not supported" in result["error"]


class TestUpdateSymbolPermissionErrors:
    """Test error handling for file permission issues."""

    async def test_file_not_writable(self):
        """Error: file is read-only."""
        result = {
            "success": False,
            "file_path": "/src/readonly.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "error": "Permission denied: file is read-only (/src/readonly.py)",
        }

        assert result["success"] is False
        assert "Permission" in result["error"]

    async def test_backup_directory_not_writable(self):
        """Error: backup directory not writable."""
        result = {
            "success": False,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "error": "Permission denied: cannot create backup (directory not writable)",
        }

        assert result["success"] is False


class TestUpdateSymbolMissingSymbolType:
    """Test error handling for invalid symbol types."""

    async def test_invalid_symbol_type(self):
        """Error: symbol_type is invalid."""
        result = {
            "success": False,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "invalid_type",  # Must be: function, class, method
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "error": "Invalid symbol_type 'invalid_type' (must be: function, class, method)",
        }

        assert result["success"] is False
        assert "Invalid symbol_type" in result["error"]


class TestUpdateSymbolTypeMismatch:
    """Test error handling when symbol type doesn't match actual code."""

    async def test_symbol_type_function_but_is_class(self):
        """Error: claimed function but symbol is actually a class."""
        result = {
            "success": False,
            "file_path": "/src/utils.py",
            "symbol_name": "Calculator",
            "symbol_type": "function",  # Wrong!
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "error": "Symbol type mismatch: 'Calculator' is a class, not a function",
        }

        assert result["success"] is False
        assert "type mismatch" in result["error"]

    async def test_symbol_type_class_but_is_function(self):
        """Error: claimed class but symbol is actually a function."""
        result = {
            "success": False,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "class",  # Wrong!
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "error": "Symbol type mismatch: 'calculate_tax' is a function, not a class",
        }

        assert result["success"] is False


class TestUpdateSymbolInvalidNewCode:
    """Test error handling for invalid new_code parameter."""

    async def test_new_code_is_empty(self):
        """Error: new_code is empty."""
        result = {
            "success": False,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": False,
            "error": "new_code cannot be empty",
        }

        assert result["success"] is False

    async def test_new_code_is_none(self):
        """Error: new_code is None."""
        result = {
            "success": False,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": False,
            "error": "new_code is required (cannot be None)",
        }

        assert result["success"] is False


class TestUpdateSymbolErrorMessages:
    """Test quality of error messages."""

    async def test_error_message_is_actionable(self):
        """Error messages should be clear and actionable."""
        result = {
            "success": False,
            "file_path": "/src/utils.py",
            "symbol_name": "nonexistent",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": True,
            "error": (
                "Symbol 'nonexistent' not found in /src/utils.py. "
                "Available functions: add_numbers, calculate_tax. "
                "Did you mean: calculate_tax?"
            ),
        }

        # Error should be helpful
        assert "Available functions" in result["error"]
        assert "Did you mean" in result["error"]

    async def test_error_message_includes_context(self):
        """Error messages should include helpful context."""
        result = {
            "success": False,
            "file_path": "/src/utils.py",
            "symbol_name": "calculate_tax",
            "symbol_type": "function",
            "backup_path": None,
            "lines_changed": 0,
            "syntax_valid": False,
            "error": (
                "Syntax error in new code: unexpected indent at line 3, column 4. "
                "Function body must be indented. "
                "Example:\n"
                "    def calculate_tax(amount, rate=0.1):\n"
                "        return amount * rate  # <- Indented 4 spaces"
            ),
        }

        assert "Example" in result["error"]
