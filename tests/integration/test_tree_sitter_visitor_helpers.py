import warnings

import pytest

from code_scalpel.ir.nodes import SourceLocation
from code_scalpel.ir.normalizers.tree_sitter_visitor import TreeSitterVisitor


class DummyNode:
    def __init__(self, node_type: str, text: str = "", children=None, named=None):
        self.node_type = node_type
        self.text = text
        self.children = children or []
        self.named_children = named or self.children
        self.fields = {}

    def set_field(self, name, value):
        self.fields[name] = value


class DummyVisitor(TreeSitterVisitor[DummyNode]):
    language = "dummy"

    def _get_node_type(self, node: DummyNode) -> str:
        return node.node_type

    def _get_children(self, node: DummyNode):
        return node.children

    def _get_named_children(self, node: DummyNode):
        return node.named_children

    def _get_text(self, node: DummyNode) -> str:
        return node.text

    def _get_location(self, node: DummyNode) -> SourceLocation:
        return SourceLocation(filename="file.py", line=1, column=0)

    def _get_child_by_field(self, node: DummyNode, field_name: str):
        return node.fields.get(field_name)

    def _get_children_by_field(self, node: DummyNode, field_name: str):
        val = node.fields.get(field_name, [])
        return val if isinstance(val, list) else [val]

    def visit_leaf(self, node: DummyNode):
        return node.text


def test_noise_detection_and_error_warning(caplog):
    visitor = DummyVisitor()
    noise = DummyNode(",")
    assert visitor.is_noise(noise)

    target = DummyNode("leaf", text="value")
    with pytest.raises(ValueError):
        visitor.error("boom", target)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        visitor.warn("heads up", target)
        assert any("heads up" in str(w.message) for w in caught)


def test_visit_and_child_helpers():
    child1 = DummyNode("leaf", text="a")
    child2 = DummyNode("leaf", text="b")
    parent = DummyNode("parent", children=[child1, child2])

    visitor = DummyVisitor()
    assert visitor.visit(parent) == ["a", "b"]
    assert visitor.visit_children(parent) == ["a", "b"]

    # Field helpers
    field_child = DummyNode("leaf", text="field")
    parent.set_field("name", field_child)
    assert visitor.get_child_by_field(parent, "name") is field_child
    parent.set_field("items", [field_child])
    assert visitor.get_children_by_field(parent, "items") == [field_child]


def test_debug_node_truncates_and_formats():
    long_text = "x" * 60
    node = DummyNode("leaf", text=long_text, children=[DummyNode("leaf", text="c")])
    visitor = DummyVisitor()
    debug = visitor.debug_node(node)
    assert "leaf" in debug
    assert "..." in debug  # truncated
