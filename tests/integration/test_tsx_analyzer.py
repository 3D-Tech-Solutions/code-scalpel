from __future__ import annotations

from code_scalpel.ir.nodes import IRClassDef, IRFunctionDef
from code_scalpel.polyglot.tsx_analyzer import (
    detect_server_directive,
    has_jsx_syntax,
    is_react_component,
)

# [20251216_TEST] Cover JSX detection and component classification paths


def test_detect_server_directives() -> None:
    assert detect_server_directive("'use client'") == "use client"
    assert detect_server_directive('"use server"') == "use server"
    assert detect_server_directive("const x = 1;") is None


def test_has_jsx_fragments_and_ignore_comparisons() -> None:
    assert has_jsx_syntax("<>hello</>")
    assert not has_jsx_syntax("a < b && b > c")


def test_is_react_component_function_and_class() -> None:
    fn_node = IRFunctionDef(name="Widget", is_async=True)
    fn_code = "async function Widget(){ 'use server'; return <div/>; }"
    fn_info = is_react_component(fn_node, fn_code)
    assert fn_info.component_type == "functional"
    assert fn_info.is_server_component
    assert fn_info.is_server_action

    cls_node = IRClassDef(name="Panel", bases=["React.Component"])
    cls_code = "class Panel extends React.Component { render(){ return <div/>; } }"
    cls_info = is_react_component(cls_node, cls_code)
    assert cls_info.component_type == "class"
    assert cls_info.has_jsx
