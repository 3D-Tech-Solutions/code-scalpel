# [20251215_TEST] Cover TypeScript parser/analyzer stub paths to raise coverage
import textwrap
from pathlib import Path

from code_scalpel.polyglot.typescript.analyzer import TypeScriptAnalyzer
from code_scalpel.polyglot.typescript.parser import TypeScriptParser


def _ts_sample_code() -> str:
    return textwrap.dedent("""
        import { Router, Request } from 'express';
        import type { User } from './models';

        export async function fetchUser(id: string) {
            if (id) {
                return `user-${id}`;
            }
        }

        export const arrowFetch = async (id) => {
            return id ?? 'missing';
        };

        export class UserController {
            constructor() {}
        }

        export default function defaultHelper(name: string) {
            return name;
        }
        """).strip()


def test_parse_with_fallback_extracts_structures():
    parser = TypeScriptParser(language="typescript")
    result = parser.parse(_ts_sample_code(), filename="example.ts")

    assert result.success is True
    assert len(result.functions) == 3  # fetchUser, arrowFetch, defaultHelper
    assert len(result.classes) == 1
    assert len(result.imports) == 2
    func_names = {f["name"] for f in result.functions}
    assert {"fetchUser", "arrowFetch", "defaultHelper"} <= func_names

    class_names = {c["name"] for c in result.classes}
    assert class_names == {"UserController"}

    # Verify export metadata captured
    assert all(f.get("is_exported") for f in result.functions)
    assert all(c.get("is_exported") for c in result.classes)


def test_parse_file_sets_language_and_handles_missing(tmp_path: Path):
    ts_path = tmp_path / "sample.ts"
    ts_path.write_text(_ts_sample_code())

    parser = TypeScriptParser()
    result = parser.parse_file(ts_path)
    assert result.success is True
    assert result.language == "typescript"

    missing = parser.parse_file(tmp_path / "missing.ts")
    assert missing.success is False
    assert "File not found" in missing.errors[0]


def test_analyzer_metrics_and_security(tmp_path: Path):
    analyzer = TypeScriptAnalyzer(language="javascript")
    code = textwrap.dedent("""
        export function risky(input) {
            eval(input);
            const el = document.getElementById('root');
            el.innerHTML = input;
            return el;
        }
        """).strip()

    result = analyzer.analyze(code, filename="demo.js")
    assert result.success is True
    assert result.language == "javascript"
    assert result.num_functions == 1
    assert result.lines_of_code >= 4
    assert result.cyclomatic_complexity >= 1
    assert result.max_nesting_depth >= 1

    issue_types = {issue["type"] for issue in result.security_issues}
    assert {"eval-usage", "innerhtml-xss"} <= issue_types

    # Exercise analyze_file to ensure IO path is covered
    js_path = tmp_path / "demo.js"
    js_path.write_text(code)
    from_file = analyzer.analyze_file(js_path)
    assert from_file.success is True
    assert from_file.num_functions == 1


def test_parse_empty_code_returns_error():
    parser = TypeScriptParser()
    result = parser.parse("   \n  ")
    assert result.success is False
    assert result.errors
