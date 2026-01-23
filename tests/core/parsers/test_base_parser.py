import os
import sys
import unittest

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from code_scalpel.code_parsers.base_parser import (
    CodeParser,
    Language,
    ParseResult,
    PreprocessorConfig,
)


class TestCodeParser(unittest.TestCase):
    def setUp(self):
        self.parser = CodeParser()

    def test_parse_python_code(self):
        code = "def foo():\n    return 42"
        result = self.parser.parse_code(code, Language.PYTHON)
        self.assertIsInstance(result, ParseResult)
        self.assertEqual(result.language, Language.PYTHON)
        self.assertIsNotNone(result.ast)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.tokens, [])
        self.assertIsInstance(result.metrics, dict)

    def test_parse_javascript_code(self):
        code = "function foo() { return 42; }"
        result = self.parser.parse_code(code, Language.JAVASCRIPT)
        self.assertIsInstance(result, ParseResult)
        self.assertEqual(result.language, Language.JAVASCRIPT)
        self.assertIsNotNone(result.ast)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.tokens, [])
        self.assertIsInstance(result.metrics, dict)

    def test_parse_java_code(self):
        code = "public class Foo { public int foo() { return 42; } }"
        result = self.parser.parse_code(code, Language.JAVA)
        self.assertIsInstance(result, ParseResult)
        self.assertEqual(result.language, Language.JAVA)
        self.assertIsNotNone(result.ast)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.tokens, [])
        self.assertIsInstance(result.metrics, dict)

    def test_parse_cpp_code(self):
        code = "int foo() { return 42; }"
        result = self.parser.parse_code(code, Language.CPP)
        self.assertIsInstance(result, ParseResult)
        self.assertEqual(result.language, Language.CPP)
        self.assertIsNotNone(result.ast)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.tokens, [])
        self.assertIsInstance(result.metrics, dict)

    def test_preprocess_code_remove_comments(self):
        code = "int foo() { // comment\n return 42; }"
        config = PreprocessorConfig(remove_comments=True)
        preprocessed_code = self.parser._preprocess_code(code, Language.CPP, config)
        self.assertNotIn("// comment", preprocessed_code)

    def test_preprocess_code_normalize_whitespace(self):
        code = "int    foo() { return  42; }"
        config = PreprocessorConfig(normalize_whitespace=True)
        preprocessed_code = self.parser._preprocess_code(code, Language.CPP, config)
        self.assertNotIn("  ", preprocessed_code)


# [20251214_TEST] Added syntax error and preprocessing coverage.
class TestCodeParserAdditional(unittest.TestCase):
    def setUp(self):
        self.parser = CodeParser()

    def test_parse_python_syntax_error(self):
        code = "def broken(:\n    return 42"
        result = self.parser.parse_code(code, Language.PYTHON)
        self.assertEqual(result.ast, None)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0]["type"], "SyntaxError")

    def test_remove_comments_python_string_protected(self):
        code = "value = '# not a comment'\n# real comment\nvalue2 = 2"
        cleaned = self.parser._remove_comments(code, Language.PYTHON)
        self.assertIn("# not a comment", cleaned)
        self.assertNotIn("# real comment", cleaned)

    def test_normalize_whitespace_preserves_indent(self):
        code = "def f():\n    x  =  1\n      y   =   2"
        normalized = self.parser._normalize_whitespace(code)
        lines = normalized.split("\n")
        self.assertTrue(lines[1].startswith("    x"))
        self.assertTrue(lines[2].startswith("      y"))

    def test_parse_code_invalid_language(self):
        with self.assertRaises(ValueError):
            self.parser.parse_code("", "not-a-language")


if __name__ == "__main__":
    unittest.main()
