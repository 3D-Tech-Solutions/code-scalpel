from __future__ import annotations


def test_simulate_refactor_sync_supports_typescript_safe_change() -> None:
    from code_scalpel.mcp.helpers.symbolic_helpers import _simulate_refactor_sync

    original_code = """
export function greet(name: string): string {
    return name;
}
"""
    new_code = """
export function greet(name: string): string {
    return name.trim();
}
"""

    result = _simulate_refactor_sync(original_code=original_code, new_code=new_code)

    assert result.success is True
    assert result.is_safe is True
    assert result.status == "safe"
    assert result.error is None


def test_simulate_refactor_sync_detects_typescript_eval_regression() -> None:
    from code_scalpel.mcp.helpers.symbolic_helpers import _simulate_refactor_sync

    original_code = """
export function parseExpression(input: string): string {
    return input.trim();
}
"""
    new_code = """
export function parseExpression(input: string): unknown {
    return eval(input as string);
}
"""

    result = _simulate_refactor_sync(original_code=original_code, new_code=new_code)

    assert result.success is True
    assert result.is_safe is False
    assert result.status == "unsafe"
    assert any(issue.type == "Code Injection" for issue in result.security_issues)
