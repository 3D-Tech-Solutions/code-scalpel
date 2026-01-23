"""
[20251214_TEST] Coverage for TreeSitterVisitor dispatch, noise filtering, and diagnostics.
"""

import warnings

import pytest

from code_scalpel.ir.normalizers.tree_sitter_visitor import (
    SourceLocation,
    TreeSitterVisitor,
)


class _FakeNode:
    def __init__(self, node_type, text="", children=None, named_children=None):
        self.type = node_type
        self._text = text
        self.children = children or []
        self.named_children = named_children or []
        self.start_point = (0, 0)
        self.end_point = (0, len(text))


class _Visitor(TreeSitterVisitor[_FakeNode]):
    language = "dummy"

    def _get_node_type(self, node: _FakeNode) -> str:
        return node.type

    def _get_children(self, node: _FakeNode):
        return node.children

    def _get_named_children(self, node: _FakeNode):
        return node.named_children

    def _get_text(self, node: _FakeNode) -> str:
        return node._text

    def _get_location(self, node: _FakeNode) -> SourceLocation:
        return SourceLocation(line=1, column=0, end_line=1, end_column=len(node._text), filename="<mem>")

    def _get_child_by_field(self, node: _FakeNode, field_name: str):
        return None

    def _get_children_by_field(self, node: _FakeNode, field_name: str):
        return []

    def visit_special(self, node: _FakeNode):
        return self.make_location(node)


def test_visit_dispatch_and_generic_visit_collects_children():
    visitor = _Visitor()
    leaf = _FakeNode("leaf", text="x")
    special = _FakeNode("special", text="y")
    root = _FakeNode("root", children=[leaf, special], named_children=[leaf, special])

    result = visitor.visit(root)

    assert isinstance(result, list)
    assert any(isinstance(item, SourceLocation) for item in result)


def test_noise_filter_and_debug_node_output():
    visitor = _Visitor()
    noise = _FakeNode(";", text=";")
    assert visitor.is_noise(noise) is True

    described = visitor.debug_node(_FakeNode("token", text="value"))
    assert "token" in described


def test_warn_and_error_helpers(recwarn):
    visitor = _Visitor()
    node = _FakeNode("token", text="value")

    warnings.simplefilter("always")
    visitor.warn("caution", node)

    assert any("caution" in str(w.message) for w in recwarn)

    with pytest.raises(ValueError):
        visitor.error("boom", node)


# [20251214_TEST] Exercise helper utilities and child finders.
def test_visit_children_and_find_helpers():
    visitor = _Visitor()
    child_a = _FakeNode("alpha", text="a")
    child_b = _FakeNode("beta", text="b")
    parent = _FakeNode("parent", children=[child_a, child_b], named_children=[child_a, child_b])

    assert visitor.visit_children(parent) == []
    assert visitor.find_child_by_type(parent, "beta") is child_b
    assert visitor.find_children_by_type(parent, "alpha") == [child_a]
    assert visitor.get_child_by_field(parent, "name") is None
    assert visitor.get_children_by_field(parent, "params") == []
    assert isinstance(visitor.make_location(child_a), SourceLocation)


# [20251214_TEST] Debug output truncates long text.
def test_debug_node_truncates_long_text():
    visitor = _Visitor()
    long = _FakeNode("token", text="x" * 60)

    output = visitor.debug_node(long)
    assert "..." in output
