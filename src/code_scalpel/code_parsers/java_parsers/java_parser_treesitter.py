"""
Tree-sitter Java Parser - Fast native Java code parsing.

Uses tree-sitter for high-performance AST parsing of Java source code.
Extracts comprehensive structural information including methods, classes,
fields, annotations, enums, and calculates method-level complexity.

Implemented Features:
- Package declaration extraction
- Field declarations with types and modifiers
- Interface implementations and extends relationships
- Annotations (class-level, method-level, field-level)
- Enum declarations and constants
- Method-level cyclomatic complexity
- Javadoc comment extraction
- Lambda expressions and method references
- Inner/nested class detection
- Generic type parameters
- Exception types from throws clauses
- Java modules (module-info.java) support
- Incremental parsing for large files
- Static initializer block detection
- Record class support (Java 14+)
- Sealed class support (Java 17+)

"""

import hashlib
from dataclasses import dataclass, field

import tree_sitter_java
from tree_sitter import Language, Parser


@dataclass
class JavaAnnotation:
    """Represents a Java annotation."""

    name: str
    arguments: str | None = None
    line: int = 0


@dataclass
class JavaField:
    """Represents a Java field declaration."""

    name: str
    field_type: str
    modifiers: list[str] = field(default_factory=list)
    annotations: list[JavaAnnotation] = field(default_factory=list)
    initial_value: str | None = None
    line: int = 0
    javadoc: str | None = None


@dataclass
class JavaParameter:
    """Represents a method parameter."""

    name: str
    param_type: str
    annotations: list[JavaAnnotation] = field(default_factory=list)
    is_varargs: bool = False


@dataclass
class JavaMethod:
    """Represents a Java method declaration."""

    name: str
    return_type: str | None = None
    parameters: list[JavaParameter] = field(default_factory=list)
    modifiers: list[str] = field(default_factory=list)
    annotations: list[JavaAnnotation] = field(default_factory=list)
    throws: list[str] = field(default_factory=list)
    type_parameters: list[str] = field(default_factory=list)
    line: int = 0
    end_line: int = 0
    complexity: int = 1
    javadoc: str | None = None
    is_constructor: bool = False
    lambda_count: int = 0
    method_reference_count: int = 0


@dataclass
class JavaEnumConstant:
    """Represents an enum constant."""

    name: str
    arguments: str | None = None
    line: int = 0


@dataclass
class JavaEnum:
    """Represents a Java enum declaration."""

    name: str
    constants: list[JavaEnumConstant] = field(default_factory=list)
    modifiers: list[str] = field(default_factory=list)
    annotations: list[JavaAnnotation] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)
    line: int = 0
    javadoc: str | None = None


@dataclass
class JavaInterface:
    """Represents a Java interface declaration."""

    name: str
    extends: list[str] = field(default_factory=list)
    modifiers: list[str] = field(default_factory=list)
    annotations: list[JavaAnnotation] = field(default_factory=list)
    type_parameters: list[str] = field(default_factory=list)
    line: int = 0
    javadoc: str | None = None


@dataclass
class JavaStaticInitializer:
    """Represents a static initializer block."""

    line: int = 0
    end_line: int = 0
    complexity: int = 1


@dataclass
class JavaRecordComponent:
    """Represents a record component (parameter in record declaration)."""

    name: str
    component_type: str
    annotations: list[JavaAnnotation] = field(default_factory=list)


@dataclass
class JavaRecord:
    """Represents a Java record declaration (Java 14+)."""

    name: str
    components: list[JavaRecordComponent] = field(default_factory=list)
    modifiers: list[str] = field(default_factory=list)
    annotations: list[JavaAnnotation] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)
    type_parameters: list[str] = field(default_factory=list)
    methods: list[JavaMethod] = field(default_factory=list)
    line: int = 0
    javadoc: str | None = None


@dataclass
class JavaModuleDirective:
    """Represents a directive in a module declaration."""

    directive_type: str  # "requires", "exports", "opens", "uses", "provides"
    module_or_package: str
    modifiers: list[str] = field(default_factory=list)  # "transitive", "static"
    to_modules: list[str] = field(default_factory=list)  # for "exports...to" or "opens...to"
    with_implementations: list[str] = field(default_factory=list)  # for "provides...with"


@dataclass
class JavaModule:
    """Represents a Java module declaration (module-info.java)."""

    name: str
    is_open: bool = False
    directives: list[JavaModuleDirective] = field(default_factory=list)
    annotations: list[JavaAnnotation] = field(default_factory=list)
    line: int = 0


@dataclass
class JavaClass:
    """Represents a Java class declaration."""

    name: str
    superclass: str | None = None
    interfaces: list[str] = field(default_factory=list)
    modifiers: list[str] = field(default_factory=list)
    annotations: list[JavaAnnotation] = field(default_factory=list)
    type_parameters: list[str] = field(default_factory=list)
    fields: list[JavaField] = field(default_factory=list)
    methods: list[JavaMethod] = field(default_factory=list)
    inner_classes: list["JavaClass"] = field(default_factory=list)
    static_initializers: list[JavaStaticInitializer] = field(default_factory=list)
    inner_records: list["JavaRecord"] = field(default_factory=list)
    inner_enums: list[JavaEnum] = field(default_factory=list)
    line: int = 0
    javadoc: str | None = None
    is_inner: bool = False
    is_static: bool = False
    is_abstract: bool = False
    # Sealed class support (Java 17+)
    is_sealed: bool = False
    is_non_sealed: bool = False
    is_final: bool = False
    permitted_subclasses: list[str] = field(default_factory=list)


@dataclass
class JavaParseResult:
    """Complete parse result for a Java file."""

    package: str | None = None
    imports: list[str] = field(default_factory=list)
    static_imports: list[str] = field(default_factory=list)
    classes: list[JavaClass] = field(default_factory=list)
    interfaces: list[JavaInterface] = field(default_factory=list)
    enums: list[JavaEnum] = field(default_factory=list)
    records: list[JavaRecord] = field(default_factory=list)
    module: JavaModule | None = None  # For module-info.java
    total_complexity: int = 1
    lines_of_code: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    lambda_count: int = 0
    method_reference_count: int = 0
    static_initializer_count: int = 0
    # Incremental parsing support
    _source_hash: str | None = field(default=None, repr=False)


class JavaParser:
    """
    Tree-sitter based Java parser for comprehensive structural analysis.

    This parser uses tree-sitter's incremental parsing for high performance.
    It extracts detailed information about Java source files including:
    - Package and imports
    - Classes with inheritance and interfaces
    - Methods with complexity metrics
    - Fields with types and annotations
    - Enums and interfaces
    - Records (Java 14+)
    - Sealed classes (Java 17+)
    - Java modules (module-info.java)
    - Javadoc comments
    - Lambda expressions and method references
    - Static initializer blocks

    Supports incremental parsing for efficient re-parsing of modified files.
    """

    # Node types that increase cyclomatic complexity
    COMPLEXITY_NODES = {
        "if_statement",
        "for_statement",
        "enhanced_for_statement",
        "while_statement",
        "do_statement",
        "switch_expression",
        "case_label",
        "catch_clause",
        "ternary_expression",
        "throw_statement",
    }

    # Binary operators that increase complexity
    COMPLEXITY_OPERATORS = {"&&", "||", "?"}

    def __init__(self):
        self.JAVA_LANGUAGE = Language(tree_sitter_java.language())
        # [20251220_BUGFIX] v3.0.4 - Use new tree-sitter API (Parser(language))
        self.parser = Parser(self.JAVA_LANGUAGE)
        self._code = ""
        self._tree = None

    def _get_text(self, node) -> str:
        """Get the source text for a node."""
        if node is None:
            return ""
        return self._code[node.start_byte : node.end_byte]

    def _get_line(self, node) -> int:
        """Get the 1-based line number for a node."""
        return node.start_point[0] + 1 if node else 0

    def _get_end_line(self, node) -> int:
        """Get the 1-based end line number for a node."""
        return node.end_point[0] + 1 if node else 0

    def _find_children_by_type(self, node, node_type: str) -> list:
        """Find all direct children of a specific type."""
        return [child for child in node.children if child.type == node_type]

    def _find_child_by_type(self, node, node_type: str):
        """Find the first direct child of a specific type."""
        for child in node.children:
            if child.type == node_type:
                return child
        return None

    def _find_descendants_by_type(self, node, node_type: str) -> list:
        """Find all descendants of a specific type (recursive)."""
        results = []
        stack = [node]
        while stack:
            current = stack.pop()
            if current.type == node_type:
                results.append(current)
            stack.extend(current.children)
        return results

    def _get_preceding_javadoc(self, node) -> str | None:
        """Extract Javadoc comment immediately preceding a node."""
        # Look for block_comment that starts with /** before this node
        if node.prev_sibling and node.prev_sibling.type == "block_comment":
            comment = self._get_text(node.prev_sibling)
            if comment.startswith("/**"):
                # Clean up the Javadoc
                return comment
        return None

    def _extract_modifiers(self, node) -> list[str]:
        """Extract modifiers from a declaration node, including sealed/non-sealed."""
        modifiers = []
        for child in node.children:
            if child.type == "modifiers":
                for mod in child.children:
                    if mod.type in (
                        "public",
                        "private",
                        "protected",
                        "static",
                        "final",
                        "abstract",
                        "synchronized",
                        "volatile",
                        "transient",
                        "native",
                        "strictfp",
                        "default",
                        "sealed",
                        "non-sealed",  # Java 17+
                    ):
                        modifiers.append(mod.type)
        return modifiers

    def _extract_annotations(self, node) -> list[JavaAnnotation]:
        """Extract annotations from a declaration node."""
        annotations = []
        for child in node.children:
            if child.type == "modifiers":
                for mod in child.children:
                    if mod.type in ("annotation", "marker_annotation"):
                        name_node = self._find_child_by_type(mod, "identifier")
                        if not name_node:
                            name_node = self._find_child_by_type(mod, "scoped_identifier")
                        name = self._get_text(name_node) if name_node else ""

                        # Get annotation arguments if present
                        args_node = self._find_child_by_type(mod, "annotation_argument_list")
                        args = self._get_text(args_node) if args_node else None

                        annotations.append(
                            JavaAnnotation(
                                name=name.lstrip("@"),
                                arguments=args,
                                line=self._get_line(mod),
                            )
                        )
        return annotations

    def _extract_type_parameters(self, node) -> list[str]:
        """Extract generic type parameters."""
        type_params = []
        type_params_node = self._find_child_by_type(node, "type_parameters")
        if type_params_node:
            for param in self._find_children_by_type(type_params_node, "type_parameter"):
                type_params.append(self._get_text(param))
        return type_params

    def _extract_throws(self, node) -> list[str]:
        """Extract exception types from throws clause."""
        throws = []
        throws_node = self._find_child_by_type(node, "throws")
        if throws_node:
            for child in throws_node.children:
                if child.type in ("type_identifier", "scoped_type_identifier"):
                    throws.append(self._get_text(child))
        return throws

    def _extract_interfaces(self, node) -> list[str]:
        """Extract implemented interfaces from class declaration."""
        interfaces = []
        interfaces_node = self._find_child_by_type(node, "super_interfaces")
        if interfaces_node:
            type_list = self._find_child_by_type(interfaces_node, "type_list")
            if type_list:
                for child in type_list.children:
                    if child.type in (
                        "type_identifier",
                        "scoped_type_identifier",
                        "generic_type",
                    ):
                        interfaces.append(self._get_text(child))
        return interfaces

    def _extract_superclass(self, node) -> str | None:
        """Extract superclass from class declaration."""
        superclass_node = self._find_child_by_type(node, "superclass")
        if superclass_node:
            for child in superclass_node.children:
                if child.type in (
                    "type_identifier",
                    "scoped_type_identifier",
                    "generic_type",
                ):
                    return self._get_text(child)
        return None

    def _calculate_complexity(self, node) -> tuple[int, int, int]:
        """
        Calculate cyclomatic complexity for a method body.
        Returns (complexity, lambda_count, method_reference_count).
        """
        complexity = 1  # Base complexity
        lambda_count = 0
        method_ref_count = 0

        stack = [node]
        while stack:
            current = stack.pop()

            # Count complexity-increasing constructs
            if current.type in self.COMPLEXITY_NODES:
                complexity += 1

            # Count logical operators
            if current.type == "binary_expression":
                operator_node = current.child_by_field_name("operator")
                if operator_node:
                    op = self._get_text(operator_node)
                    if op in self.COMPLEXITY_OPERATORS:
                        complexity += 1

            # Count lambda expressions
            if current.type == "lambda_expression":
                lambda_count += 1

            # Count method references
            if current.type == "method_reference":
                method_ref_count += 1

            stack.extend(current.children)

        return complexity, lambda_count, method_ref_count

    def _extract_parameters(self, node) -> list[JavaParameter]:
        """Extract method parameters."""
        parameters = []
        params_node = self._find_child_by_type(node, "formal_parameters")
        if params_node:
            for param in self._find_children_by_type(params_node, "formal_parameter"):
                # Get parameter type
                type_node = None
                for child in param.children:
                    if child.type in (
                        "type_identifier",
                        "scoped_type_identifier",
                        "generic_type",
                        "array_type",
                        "integral_type",
                        "floating_point_type",
                        "boolean_type",
                        "void_type",
                    ):
                        type_node = child
                        break

                # Get parameter name
                name_node = self._find_child_by_type(param, "identifier")

                # Check for varargs
                is_varargs = any(c.type == "spread_parameter" for c in param.children)

                # Get parameter annotations
                param_annotations = []
                for child in param.children:
                    if child.type in ("annotation", "marker_annotation"):
                        name = self._get_text(self._find_child_by_type(child, "identifier"))
                        param_annotations.append(JavaAnnotation(name=name.lstrip("@")))

                if name_node:
                    parameters.append(
                        JavaParameter(
                            name=self._get_text(name_node),
                            param_type=(self._get_text(type_node) if type_node else "Object"),
                            annotations=param_annotations,
                            is_varargs=is_varargs,
                        )
                    )

            # Handle varargs parameters (spread_parameter)
            for spread in self._find_children_by_type(params_node, "spread_parameter"):
                type_node = None
                for child in spread.children:
                    if child.type in (
                        "type_identifier",
                        "scoped_type_identifier",
                        "generic_type",
                    ):
                        type_node = child
                        break
                name_node = self._find_child_by_type(spread, "identifier")
                if name_node:
                    parameters.append(
                        JavaParameter(
                            name=self._get_text(name_node),
                            param_type=(self._get_text(type_node) if type_node else "Object"),
                            is_varargs=True,
                        )
                    )

        return parameters

    def _extract_method(self, node, is_constructor: bool = False) -> JavaMethod:
        """Extract method information from a method declaration node."""
        name_node = node.child_by_field_name("name")
        name = self._get_text(name_node) if name_node else ""

        # Get return type (not for constructors)
        return_type = None
        if not is_constructor:
            type_node = node.child_by_field_name("type")
            return_type = self._get_text(type_node) if type_node else "void"

        # Get method body for complexity calculation
        body_node = self._find_child_by_type(node, "block")
        if body_node:
            complexity, lambdas, method_refs = self._calculate_complexity(body_node)
        else:
            complexity, lambdas, method_refs = 1, 0, 0

        return JavaMethod(
            name=name,
            return_type=return_type,
            parameters=self._extract_parameters(node),
            modifiers=self._extract_modifiers(node),
            annotations=self._extract_annotations(node),
            throws=self._extract_throws(node),
            type_parameters=self._extract_type_parameters(node),
            line=self._get_line(node),
            end_line=self._get_end_line(node),
            complexity=complexity,
            javadoc=self._get_preceding_javadoc(node),
            is_constructor=is_constructor,
            lambda_count=lambdas,
            method_reference_count=method_refs,
        )

    def _extract_field(self, node) -> list[JavaField]:
        """Extract field information from a field declaration node."""
        fields = []

        # Get type
        type_node = None
        for child in node.children:
            if child.type in (
                "type_identifier",
                "scoped_type_identifier",
                "generic_type",
                "array_type",
                "integral_type",
                "floating_point_type",
                "boolean_type",
            ):
                type_node = child
                break

        field_type = self._get_text(type_node) if type_node else "Object"
        modifiers = self._extract_modifiers(node)
        annotations = self._extract_annotations(node)
        javadoc = self._get_preceding_javadoc(node)

        # Handle multiple declarators (e.g., int x, y, z;)
        for declarator in self._find_children_by_type(node, "variable_declarator"):
            name_node = self._find_child_by_type(declarator, "identifier")
            if name_node:
                # Check for initial value
                init_value = None
                for child in declarator.children:
                    if child.type == "=":
                        # Get everything after =
                        idx = declarator.children.index(child)
                        if idx + 1 < len(declarator.children):
                            init_value = self._get_text(declarator.children[idx + 1])
                        break

                fields.append(
                    JavaField(
                        name=self._get_text(name_node),
                        field_type=field_type,
                        modifiers=modifiers,
                        annotations=annotations,
                        initial_value=init_value,
                        line=self._get_line(node),
                        javadoc=javadoc,
                    )
                )

        return fields

    def _extract_enum(self, node) -> JavaEnum:
        """Extract enum information from an enum declaration node."""
        name_node = node.child_by_field_name("name")
        name = self._get_text(name_node) if name_node else ""

        # Extract constants
        constants = []
        body = self._find_child_by_type(node, "enum_body")
        if body:
            for const in self._find_children_by_type(body, "enum_constant"):
                const_name_node = self._find_child_by_type(const, "identifier")
                const_args_node = self._find_child_by_type(const, "argument_list")
                if const_name_node:
                    constants.append(
                        JavaEnumConstant(
                            name=self._get_text(const_name_node),
                            arguments=(self._get_text(const_args_node) if const_args_node else None),
                            line=self._get_line(const),
                        )
                    )

        return JavaEnum(
            name=name,
            constants=constants,
            modifiers=self._extract_modifiers(node),
            annotations=self._extract_annotations(node),
            interfaces=self._extract_interfaces(node),
            line=self._get_line(node),
            javadoc=self._get_preceding_javadoc(node),
        )

    def _extract_interface(self, node) -> JavaInterface:
        """Extract interface information from an interface declaration node."""
        name_node = node.child_by_field_name("name")
        name = self._get_text(name_node) if name_node else ""

        # Get extends (interfaces can extend multiple interfaces)
        extends = []
        extends_node = self._find_child_by_type(node, "extends_interfaces")
        if extends_node:
            type_list = self._find_child_by_type(extends_node, "type_list")
            if type_list:
                for child in type_list.children:
                    if child.type in (
                        "type_identifier",
                        "scoped_type_identifier",
                        "generic_type",
                    ):
                        extends.append(self._get_text(child))

        return JavaInterface(
            name=name,
            extends=extends,
            modifiers=self._extract_modifiers(node),
            annotations=self._extract_annotations(node),
            type_parameters=self._extract_type_parameters(node),
            line=self._get_line(node),
            javadoc=self._get_preceding_javadoc(node),
        )

    def _extract_class(self, node, is_inner: bool = False) -> JavaClass:
        """Extract class information from a class declaration node."""
        name_node = node.child_by_field_name("name")
        name = self._get_text(name_node) if name_node else ""

        modifiers = self._extract_modifiers(node)

        # Extract permitted subclasses for sealed classes (Java 17+)
        permitted = []
        permits_node = self._find_child_by_type(node, "permits")
        if permits_node:
            type_list = self._find_child_by_type(permits_node, "type_list")
            if type_list:
                for child in type_list.children:
                    if child.type in ("type_identifier", "scoped_type_identifier"):
                        permitted.append(self._get_text(child))

        java_class = JavaClass(
            name=name,
            superclass=self._extract_superclass(node),
            interfaces=self._extract_interfaces(node),
            modifiers=modifiers,
            annotations=self._extract_annotations(node),
            type_parameters=self._extract_type_parameters(node),
            line=self._get_line(node),
            javadoc=self._get_preceding_javadoc(node),
            is_inner=is_inner,
            is_static="static" in modifiers,
            is_abstract="abstract" in modifiers,
            is_sealed="sealed" in modifiers,
            is_non_sealed="non-sealed" in modifiers,
            is_final="final" in modifiers,
            permitted_subclasses=permitted,
        )

        # Extract members from class body
        body = self._find_child_by_type(node, "class_body")
        if body:
            for child in body.children:
                if child.type == "method_declaration":
                    java_class.methods.append(self._extract_method(child))
                elif child.type == "constructor_declaration":
                    java_class.methods.append(self._extract_method(child, is_constructor=True))
                elif child.type == "field_declaration":
                    java_class.fields.extend(self._extract_field(child))
                elif child.type == "class_declaration":
                    java_class.inner_classes.append(self._extract_class(child, is_inner=True))
                elif child.type == "static_initializer":
                    # Static initializer block
                    block = self._find_child_by_type(child, "block")
                    complexity = 1
                    if block:
                        complexity, _, _ = self._calculate_complexity(block)
                    java_class.static_initializers.append(
                        JavaStaticInitializer(
                            line=self._get_line(child),
                            end_line=self._get_end_line(child),
                            complexity=complexity,
                        )
                    )
                elif child.type == "record_declaration":
                    java_class.inner_records.append(self._extract_record(child))
                elif child.type == "enum_declaration":
                    java_class.inner_enums.append(self._extract_enum(child))

        return java_class

    def _extract_record(self, node) -> JavaRecord:
        """Extract record information from a record declaration node (Java 14+)."""
        name_node = node.child_by_field_name("name")
        name = self._get_text(name_node) if name_node else ""

        # Extract record components (the parameters in record header)
        components = []
        params_node = self._find_child_by_type(node, "formal_parameters")
        if params_node:
            for param in self._find_children_by_type(params_node, "formal_parameter"):
                # Get component type
                type_node = None
                for child in param.children:
                    if child.type in (
                        "type_identifier",
                        "scoped_type_identifier",
                        "generic_type",
                        "array_type",
                        "integral_type",
                        "floating_point_type",
                        "boolean_type",
                    ):
                        type_node = child
                        break

                name_node = self._find_child_by_type(param, "identifier")

                # Get component annotations
                comp_annotations = []
                for child in param.children:
                    if child.type in ("annotation", "marker_annotation"):
                        ann_name = self._get_text(self._find_child_by_type(child, "identifier"))
                        comp_annotations.append(JavaAnnotation(name=ann_name.lstrip("@")))

                if name_node:
                    components.append(
                        JavaRecordComponent(
                            name=self._get_text(name_node),
                            component_type=(self._get_text(type_node) if type_node else "Object"),
                            annotations=comp_annotations,
                        )
                    )

        # Extract methods from record body
        methods = []
        body = self._find_child_by_type(node, "class_body")
        if body:
            for child in body.children:
                if child.type == "method_declaration":
                    methods.append(self._extract_method(child))
                elif child.type == "compact_constructor_declaration":
                    # Compact constructor in records
                    methods.append(self._extract_method(child, is_constructor=True))

        return JavaRecord(
            name=name,
            components=components,
            modifiers=self._extract_modifiers(node),
            annotations=self._extract_annotations(node),
            interfaces=self._extract_interfaces(node),
            type_parameters=self._extract_type_parameters(node),
            methods=methods,
            line=self._get_line(node),
            javadoc=self._get_preceding_javadoc(node),
        )

    def _extract_module(self, node) -> JavaModule:
        """Extract module information from a module declaration node."""
        # Check if it's an open module
        is_open = any(child.type == "open" for child in node.children)

        # Get module name
        name_node = None
        for child in node.children:
            if child.type in ("scoped_identifier", "identifier"):
                name_node = child
                break
        name = self._get_text(name_node) if name_node else ""

        # Extract directives from module body
        directives = []
        body = self._find_child_by_type(node, "module_body")
        if body:
            for child in body.children:
                directive = self._extract_module_directive(child)
                if directive:
                    directives.append(directive)

        return JavaModule(
            name=name,
            is_open=is_open,
            directives=directives,
            annotations=self._extract_annotations(node),
            line=self._get_line(node),
        )

    def _extract_module_directive(self, node) -> JavaModuleDirective | None:
        """Extract a single module directive."""
        directive_type = None
        module_or_package = ""
        modifiers = []
        to_modules = []
        with_implementations = []

        if node.type == "requires_directive":
            directive_type = "requires"
            # Check for transitive/static modifiers
            for child in node.children:
                if child.type == "requires_modifier":
                    mod_text = self._get_text(child)
                    if mod_text in ("transitive", "static"):
                        modifiers.append(mod_text)
                elif child.type in ("scoped_identifier", "identifier"):
                    module_or_package = self._get_text(child)

        elif node.type == "exports_directive":
            directive_type = "exports"
            for child in node.children:
                if child.type in ("scoped_identifier", "identifier"):
                    if not module_or_package:
                        module_or_package = self._get_text(child)
                    else:
                        to_modules.append(self._get_text(child))

        elif node.type == "opens_directive":
            directive_type = "opens"
            for child in node.children:
                if child.type in ("scoped_identifier", "identifier"):
                    if not module_or_package:
                        module_or_package = self._get_text(child)
                    else:
                        to_modules.append(self._get_text(child))

        elif node.type == "uses_directive":
            directive_type = "uses"
            for child in node.children:
                if child.type in ("scoped_identifier", "identifier"):
                    module_or_package = self._get_text(child)

        elif node.type == "provides_directive":
            directive_type = "provides"
            seen_with = False
            for child in node.children:
                if child.type == "with":
                    seen_with = True
                elif child.type in ("scoped_identifier", "identifier"):
                    if not seen_with:
                        module_or_package = self._get_text(child)
                    else:
                        with_implementations.append(self._get_text(child))

        if directive_type:
            return JavaModuleDirective(
                directive_type=directive_type,
                module_or_package=module_or_package,
                modifiers=modifiers,
                to_modules=to_modules,
                with_implementations=with_implementations,
            )
        return None

    def _count_lines(self, code: str) -> tuple[int, int, int]:
        """Count lines of code, comment lines, and blank lines."""
        lines = code.splitlines()
        total = len(lines)
        blank = sum(1 for line in lines if not line.strip())

        # Simple comment counting (could be improved)
        comment_lines = 0
        in_block_comment = False
        for line in lines:
            stripped = line.strip()
            if in_block_comment:
                comment_lines += 1
                if "*/" in stripped:
                    in_block_comment = False
            elif stripped.startswith("//"):
                comment_lines += 1
            elif stripped.startswith("/*"):
                comment_lines += 1
                if "*/" not in stripped:
                    in_block_comment = True

        return total, comment_lines, blank

    def parse(self, code: str) -> dict:
        """
        Parse Java source code and return a simple dictionary result.

        This is the legacy interface for backward compatibility.
        Use parse_detailed() for the full JavaParseResult.
        """
        result = self.parse_detailed(code)

        # Flatten to simple format for backward compatibility
        functions = []
        classes = []

        for cls in result.classes:
            classes.append(cls.name)
            for method in cls.methods:
                functions.append(method.name)

        for iface in result.interfaces:
            classes.append(iface.name)

        for enum in result.enums:
            classes.append(enum.name)

        for record in result.records:
            classes.append(record.name)

        return {
            "package": result.package,
            "functions": functions,
            "classes": classes,
            "imports": result.imports,
            "static_imports": result.static_imports,
            "complexity": result.total_complexity,
            "lines_of_code": result.lines_of_code,
            "comment_lines": result.comment_lines,
            "blank_lines": result.blank_lines,
            "lambda_count": result.lambda_count,
            "method_reference_count": result.method_reference_count,
            "static_initializer_count": result.static_initializer_count,
            "module": result.module.name if result.module else None,
            "issues": [],
        }

    def _compute_hash(self, code: str) -> str:
        """Compute a hash of the source code for incremental parsing."""
        return hashlib.sha256(code.encode()).hexdigest()

    def parse_incremental(self, code: str, previous_result: JavaParseResult | None = None) -> JavaParseResult:
        """
        Parse Java source code with incremental parsing support.

        If the code hasn't changed (based on hash), returns the previous result.
        Otherwise performs a full parse.

        Args:
            code: Java source code string
            previous_result: Optional previous parse result for caching

        Returns:
            JavaParseResult with comprehensive parse information
        """
        current_hash = self._compute_hash(code)

        # Check if we can reuse the previous result
        if previous_result is not None and previous_result._source_hash == current_hash:
            return previous_result

        # Perform full parse
        result = self.parse_detailed(code)
        result._source_hash = current_hash
        return result

    def parse_detailed(self, code: str) -> JavaParseResult:
        """
        Parse Java source code and return detailed structural information.

        Args:
            code: Java source code string

        Returns:
            JavaParseResult with comprehensive parse information
        """
        self._code = code
        self._tree = self.parser.parse(bytes(code, "utf8"))
        root_node = self._tree.root_node

        result = JavaParseResult()
        result._source_hash = self._compute_hash(code)

        # Count lines
        result.lines_of_code, result.comment_lines, result.blank_lines = self._count_lines(code)

        # Process top-level nodes
        for child in root_node.children:
            if child.type == "package_declaration":
                # Extract package name
                pkg_name_node = self._find_child_by_type(child, "scoped_identifier")
                if not pkg_name_node:
                    pkg_name_node = self._find_child_by_type(child, "identifier")
                result.package = self._get_text(pkg_name_node) if pkg_name_node else None

            elif child.type == "import_declaration":
                import_text = self._get_text(child)
                import_text = import_text.replace("import ", "").replace(";", "").strip()

                if import_text.startswith("static "):
                    result.static_imports.append(import_text.replace("static ", ""))
                else:
                    result.imports.append(import_text)

            elif child.type == "class_declaration":
                java_class = self._extract_class(child)
                result.classes.append(java_class)

                # Aggregate complexity and counts
                for method in java_class.methods:
                    result.total_complexity += method.complexity - 1  # Don't double-count base
                    result.lambda_count += method.lambda_count
                    result.method_reference_count += method.method_reference_count

                # Count static initializers
                result.static_initializer_count += len(java_class.static_initializers)
                for init in java_class.static_initializers:
                    result.total_complexity += init.complexity - 1

            elif child.type == "interface_declaration":
                result.interfaces.append(self._extract_interface(child))

            elif child.type == "enum_declaration":
                result.enums.append(self._extract_enum(child))

            elif child.type == "record_declaration":
                record = self._extract_record(child)
                result.records.append(record)

                # Aggregate complexity from record methods
                for method in record.methods:
                    result.total_complexity += method.complexity - 1
                    result.lambda_count += method.lambda_count
                    result.method_reference_count += method.method_reference_count

            elif child.type == "module_declaration":
                result.module = self._extract_module(child)

        return result
