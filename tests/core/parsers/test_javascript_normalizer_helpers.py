import warnings

import pytest

from code_scalpel.ir.normalizers.javascript_normalizer import JavaScriptNormalizer


# [20251214_TEST] Exercise JavaScript normalizer helpers with fake CST nodes to raise coverage without tree-sitter.
class FakeNode:
    def __init__(
        self,
        node_type: str,
        *,
        children=None,
        is_named: bool = True,
        text: str = "",
        fields=None,
        start=(0, 0),
        end=(0, 0),
    ):
        self.type = node_type
        self.children = children or []
        self.is_named = is_named
        self.text = text
        self._fields = fields or {}
        self.start_point = start
        self.end_point = end
        self.start_byte = 0
        self.end_byte = len(text)

    def child_by_field_name(self, name: str):
        return self._fields.get(name)


@pytest.fixture()
def normalizer():
    normalizer = JavaScriptNormalizer()
    normalizer._get_text = lambda node: getattr(node, "text", "")  # type: ignore[attr-defined]
    return normalizer


@pytest.mark.filterwarnings("ignore:JavaScript CST node type")
def test_binary_and_unary_expressions_cover_unknown_and_default_ops(normalizer):
    left = FakeNode("identifier", text="a")
    right = FakeNode("identifier", text="b")
    unknown_op = FakeNode("op", is_named=False, text="@@")
    binary = FakeNode(
        "binary_expression",
        children=[left, unknown_op, right],
        fields={"left": left, "right": right},
        start=(0, 0),
        end=(0, 1),
    )

    result = normalizer.normalize_node(binary)
    assert result.op.name == "ADD"

    unary_arg = FakeNode("identifier", text="x")
    unary_node = FakeNode(
        "unary_expression",
        children=[FakeNode("op", is_named=False, text="~"), unary_arg],
        fields={"argument": unary_arg},
    )
    unary_result = normalizer.normalize_node(unary_node)
    assert unary_result.op.name == "INVERT"


def test_update_and_augmented_assignments_cover_op_selection(normalizer):
    arg = FakeNode("identifier", text="counter")
    update = FakeNode(
        "update_expression",
        children=[FakeNode("op", is_named=False, text="++"), arg],
        fields={"argument": arg},
    )
    update_result = normalizer.normalize_node(update)
    assert update_result.op.name == "ADD"

    left = FakeNode("identifier", text="total")
    right = FakeNode("number", text="5")
    aug = FakeNode(
        "augmented_assignment_expression",
        children=[left, FakeNode("op", is_named=False, text="^="), right],
        fields={"left": left, "right": right},
    )
    aug_result = normalizer.normalize_node(aug)
    assert aug_result.op.name == "BIT_XOR"


def test_member_and_subscript_expressions(normalizer):
    obj = FakeNode("identifier", text="foo")
    prop = FakeNode("identifier", text="bar")
    bracket = FakeNode("[", is_named=False, text="[")
    member = FakeNode(
        "member_expression",
        children=[obj, bracket, prop],
        fields={"object": obj, "property": prop},
    )

    subscript = normalizer.normalize_node(member)
    assert subscript.slice.id == "bar"

    bare_member = FakeNode(
        "member_expression",
        children=[obj, prop],
        fields={"object": obj, "property": prop},
    )
    attribute = normalizer.normalize_node(bare_member)
    assert attribute.attr == "bar"

    subscript_expr = FakeNode(
        "subscript_expression",
        children=[obj, prop],
        fields={"object": obj, "index": prop},
    )
    subscript_direct = normalizer.normalize_node(subscript_expr)
    assert subscript_direct.slice.id == "bar"


def test_literals_and_objects(normalizer):
    number_node = FakeNode("number", text="0x10")
    string_node = FakeNode("string", text='"hello"')
    template_node = FakeNode("template_string", text="`tmpl`")

    assert normalizer.normalize_node(number_node).value == 16
    assert normalizer.normalize_node(string_node).value == "hello"
    assert normalizer.normalize_node(template_node).value == "tmpl"

    true_val = normalizer.normalize_node(FakeNode("true"))
    false_val = normalizer.normalize_node(FakeNode("false"))
    null_val = normalizer.normalize_node(FakeNode("null"))
    undefined_val = normalizer.normalize_node(FakeNode("undefined"))

    assert (true_val.value, false_val.value, null_val.value, undefined_val.value) == (
        True,
        False,
        None,
        None,
    )

    elem = FakeNode("identifier", text="x")
    array_node = FakeNode("array", children=[elem])
    array_ir = normalizer.normalize_node(array_node)
    assert len(array_ir.elements) == 1

    pair_key = FakeNode("identifier", text="k")
    pair_val = FakeNode("number", text="3")
    pair = FakeNode(
        "pair",
        fields={"key": pair_key, "value": pair_val},
        children=[pair_key, pair_val],
    )
    shorthand = FakeNode("shorthand_property_identifier", text="shorty")
    obj_node = FakeNode("object", children=[pair, shorthand])
    obj_ir = normalizer.normalize_node(obj_node)
    assert [key.value for key in obj_ir.keys] == ["k", "shorty"]


def test_class_and_method_definitions(normalizer):
    base = FakeNode("identifier", text="Base")
    name = FakeNode("identifier", text="Child")
    method_name = FakeNode("identifier", text="method")
    method_body = FakeNode("statement_block", children=[])
    method = FakeNode(
        "method_definition",
        fields={
            "name": method_name,
            "parameters": FakeNode("params"),
            "body": method_body,
        },
        children=[method_name, method_body],
    )
    body = FakeNode("class_body", children=[method])
    class_node = FakeNode(
        "class_declaration",
        fields={
            "name": name,
            "heritage": FakeNode("heritage", children=[base]),
            "body": body,
        },
        children=[name, body],
    )

    class_ir = normalizer.normalize_node(class_node)
    assert class_ir.name == "Child"
    assert class_ir.bases[0].id == "Base"
    assert class_ir.body[0].name == "method"


def test_try_and_throw_emit_warnings(normalizer):
    # [20251215_REFACTOR] v2.0.0 - try/throw now properly implemented with IRTry/IRRaise
    # This test now verifies the implementations work correctly rather than stub warnings
    try_node = FakeNode("try_statement", start=(1, 0), end=(1, 5))
    throw_node = FakeNode("throw_statement", start=(2, 0), end=(2, 5))

    # try_statement should now return IRTry (not None with warning)
    from code_scalpel.ir.nodes import IRRaise, IRTry

    try_result = normalizer.normalize_node(try_node)
    assert isinstance(try_result, IRTry), f"Expected IRTry, got {type(try_result)}"

    # throw_statement should now return IRRaise (not None with warning)
    throw_result = normalizer.normalize_node(throw_node)
    assert isinstance(throw_result, IRRaise), f"Expected IRRaise, got {type(throw_result)}"


# [20251214_REFACTOR] Remove duplicate imports and keep helper stubs lint-clean.
class _FakeNode:
    def __init__(self, *, node_type: str, is_named: bool = True, children=None):
        self.type = node_type
        self.is_named = is_named
        self.children = children or []
        self.start_point = (0, 0)
        self.end_point = (0, 3)
        self.start_byte = 0
        self.end_byte = 3

    def child_by_field_name(self, _field):
        return None


# [20260118_TEST] Cover JavaScriptNormalizer helper utilities without tree-sitter dependency.
def test_helper_methods_cover_noise_and_location_logic():
    normalizer = JavaScriptNormalizer.__new__(JavaScriptNormalizer)
    normalizer._filename = "file.js"
    normalizer._source = "abc"

    noise_comment = _FakeNode(node_type="comment")
    noise_anon = _FakeNode(node_type="punct", is_named=False)
    assert normalizer._is_noise(noise_comment) is True
    assert normalizer._is_noise(noise_anon) is True

    loc = normalizer._make_loc(_FakeNode(node_type="id"))
    assert loc.line == 1 and loc.end_line == 1

    extracted = normalizer._get_text(_FakeNode(node_type="id"))
    assert extracted == "abc"


def test_normalize_node_warns_on_unknown_node():
    normalizer = JavaScriptNormalizer.__new__(JavaScriptNormalizer)
    normalizer._filename = "file.js"
    normalizer._source = "abc"

    unknown = _FakeNode(node_type="not_supported")
    with warnings.catch_warnings(record=True) as caught:
        result = normalizer.normalize_node(unknown)
    assert result is None
    assert any("not yet supported" in str(w.message) for w in caught)


def test_normalize_body_flattens_lists():
    normalizer = JavaScriptNormalizer.__new__(JavaScriptNormalizer)

    seq = []

    def fake_normalize(node):
        if node.type == "list":
            return ["a", "b"]
        if node.type == "single":
            return "x"
        return None

    normalizer.normalize_node = fake_normalize
    nodes = [
        _FakeNode(node_type="list"),
        _FakeNode(node_type="single"),
        _FakeNode(node_type="skip"),
    ]
    seq = normalizer._normalize_body(nodes)
    assert seq == ["a", "b", "x"]


def test_get_named_children_filters_anon():
    normalizer = JavaScriptNormalizer.__new__(JavaScriptNormalizer)
    named = _FakeNode(node_type="named", is_named=True)
    anon = _FakeNode(node_type="anon", is_named=False)
    parent = _FakeNode(node_type="parent", children=[named, anon])

    assert normalizer._get_named_children(parent) == [named]
