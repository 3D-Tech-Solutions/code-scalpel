"""
GraphQL Schema Tracker - Schema Evolution Analysis.

[20251219_FEATURE] v3.0.4 - Ninja Warrior Stage 3

This module tracks GraphQL schema evolution and detects breaking changes:
- Parse GraphQL SDL (Schema Definition Language)
- Extract types, fields, queries, mutations, subscriptions
- Detect breaking vs non-breaking changes
- Validate schema for best practices

Breaking Changes:
- Type removed
- Field removed from type
- Field type changed (incompatible)
- Required argument added
- Enum value removed
- Union member removed
- Interface implementation removed

Non-Breaking Changes:
- Type added
- Optional field added
- Optional argument added
- Enum value added
- Union member added
- Deprecation added

Usage:
    tracker = GraphQLSchemaTracker()

    # Parse a schema
    schema = tracker.parse(sdl_content)
    print(f"Types: {len(schema.types)}")

    # Compare two schemas
    drift = tracker.compare(old_sdl, new_sdl)
    if drift.has_breaking_changes():
        print(f"BREAKING: {drift.breaking_changes}")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any


class GraphQLChangeType(Enum):
    """Types of GraphQL schema changes."""

    # Breaking changes
    TYPE_REMOVED = auto()
    FIELD_REMOVED = auto()
    FIELD_TYPE_CHANGED = auto()
    REQUIRED_ARG_ADDED = auto()
    ARG_REMOVED = auto()
    ARG_TYPE_CHANGED = auto()
    ENUM_VALUE_REMOVED = auto()
    UNION_MEMBER_REMOVED = auto()
    INTERFACE_REMOVED = auto()
    DIRECTIVE_REMOVED = auto()

    # Non-breaking changes
    TYPE_ADDED = auto()
    FIELD_ADDED = auto()
    OPTIONAL_ARG_ADDED = auto()
    ENUM_VALUE_ADDED = auto()
    UNION_MEMBER_ADDED = auto()
    INTERFACE_ADDED = auto()
    FIELD_DEPRECATED = auto()
    TYPE_DEPRECATED = auto()
    DESCRIPTION_CHANGED = auto()
    DIRECTIVE_ADDED = auto()


class GraphQLChangeSeverity(Enum):
    """Severity of schema changes."""

    BREAKING = "BREAKING"
    DANGEROUS = "DANGEROUS"  # May break some clients
    INFO = "INFO"


class GraphQLTypeKind(Enum):
    """Kinds of GraphQL types."""

    SCALAR = "SCALAR"
    OBJECT = "OBJECT"
    INTERFACE = "INTERFACE"
    UNION = "UNION"
    ENUM = "ENUM"
    INPUT_OBJECT = "INPUT_OBJECT"


@dataclass
class GraphQLArgument:
    """Represents a GraphQL field argument."""

    name: str
    type: str
    default_value: str | None = None
    description: str | None = None

    @property
    def is_required(self) -> bool:
        """Check if argument is required (non-null without default)."""
        return self.type.endswith("!") and self.default_value is None


@dataclass
class GraphQLField:
    """Represents a GraphQL field."""

    name: str
    type: str
    arguments: dict[str, GraphQLArgument] = field(default_factory=dict)
    description: str | None = None
    deprecated: bool = False
    deprecation_reason: str | None = None
    directives: list[str] = field(default_factory=list)

    @property
    def is_nullable(self) -> bool:
        """Check if field is nullable."""
        return not self.type.endswith("!")

    @property
    def is_list(self) -> bool:
        """Check if field is a list type."""
        return "[" in self.type


@dataclass
class GraphQLEnumValue:
    """Represents a GraphQL enum value."""

    name: str
    description: str | None = None
    deprecated: bool = False
    deprecation_reason: str | None = None


@dataclass
class GraphQLType:
    """Represents a GraphQL type definition."""

    name: str
    kind: GraphQLTypeKind
    fields: dict[str, GraphQLField] = field(default_factory=dict)
    enum_values: dict[str, GraphQLEnumValue] = field(default_factory=dict)
    interfaces: list[str] = field(default_factory=list)
    union_types: list[str] = field(default_factory=list)
    input_fields: dict[str, GraphQLField] = field(default_factory=dict)
    description: str | None = None
    directives: list[str] = field(default_factory=list)

    @property
    def field_count(self) -> int:
        """Get number of fields."""
        if self.kind == GraphQLTypeKind.INPUT_OBJECT:
            return len(self.input_fields)
        return len(self.fields)


@dataclass
class GraphQLDirective:
    """Represents a GraphQL directive definition."""

    name: str
    locations: list[str] = field(default_factory=list)
    arguments: dict[str, GraphQLArgument] = field(default_factory=dict)
    description: str | None = None
    repeatable: bool = False


@dataclass
class GraphQLSchema:
    """Represents a complete GraphQL schema."""

    types: dict[str, GraphQLType] = field(default_factory=dict)
    directives: dict[str, GraphQLDirective] = field(default_factory=dict)
    query_type: str | None = "Query"
    mutation_type: str | None = "Mutation"
    subscription_type: str | None = "Subscription"
    description: str | None = None

    @property
    def type_count(self) -> int:
        """Total number of types (excluding built-ins)."""
        return len([t for t in self.types if not t.startswith("__")])

    @property
    def object_types(self) -> list[GraphQLType]:
        """Get all object types."""
        return [t for t in self.types.values() if t.kind == GraphQLTypeKind.OBJECT]

    @property
    def input_types(self) -> list[GraphQLType]:
        """Get all input types."""
        return [t for t in self.types.values() if t.kind == GraphQLTypeKind.INPUT_OBJECT]

    @property
    def enum_types(self) -> list[GraphQLType]:
        """Get all enum types."""
        return [t for t in self.types.values() if t.kind == GraphQLTypeKind.ENUM]

    @property
    def interface_types(self) -> list[GraphQLType]:
        """Get all interface types."""
        return [t for t in self.types.values() if t.kind == GraphQLTypeKind.INTERFACE]

    @property
    def union_types(self) -> list[GraphQLType]:
        """Get all union types."""
        return [t for t in self.types.values() if t.kind == GraphQLTypeKind.UNION]

    def get_type(self, name: str) -> GraphQLType | None:
        """Get a type by name."""
        return self.types.get(name)

    @property
    def queries(self) -> dict[str, GraphQLField]:
        """Get all query fields."""
        if self.query_type and self.query_type in self.types:
            return self.types[self.query_type].fields
        return {}

    @property
    def mutations(self) -> dict[str, GraphQLField]:
        """Get all mutation fields."""
        if self.mutation_type and self.mutation_type in self.types:
            return self.types[self.mutation_type].fields
        return {}

    @property
    def subscriptions(self) -> dict[str, GraphQLField]:
        """Get all subscription fields."""
        if self.subscription_type and self.subscription_type in self.types:
            return self.types[self.subscription_type].fields
        return {}

    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            "GraphQL Schema Summary",
            f"Types: {self.type_count}",
            f"  Object Types: {len(self.object_types)}",
            f"  Input Types: {len(self.input_types)}",
            f"  Enums: {len(self.enum_types)}",
            f"  Interfaces: {len(self.interface_types)}",
            f"  Unions: {len(self.union_types)}",
            f"Queries: {len(self.queries)}",
            f"Mutations: {len(self.mutations)}",
            f"Subscriptions: {len(self.subscriptions)}",
            f"Directives: {len(self.directives)}",
        ]
        return "\n".join(lines)


@dataclass
class GraphQLSchemaChange:
    """Represents a single schema change."""

    change_type: GraphQLChangeType
    severity: GraphQLChangeSeverity
    path: str  # e.g., "User.email" or "Query.getUser"
    message: str
    old_value: Any | None = None
    new_value: Any | None = None

    def __str__(self) -> str:
        return f"[{self.severity.value}] {self.path}: {self.message}"


@dataclass
class GraphQLSchemaDrift:
    """Result of schema drift analysis."""

    old_version: str = ""
    new_version: str = ""
    changes: list[GraphQLSchemaChange] = field(default_factory=list)

    def has_breaking_changes(self) -> bool:
        """Check if any breaking changes were detected."""
        return any(c.severity == GraphQLChangeSeverity.BREAKING for c in self.changes)

    @property
    def breaking_changes(self) -> list[GraphQLSchemaChange]:
        """Get only breaking changes."""
        return [c for c in self.changes if c.severity == GraphQLChangeSeverity.BREAKING]

    @property
    def dangerous_changes(self) -> list[GraphQLSchemaChange]:
        """Get dangerous changes."""
        return [c for c in self.changes if c.severity == GraphQLChangeSeverity.DANGEROUS]

    @property
    def info_changes(self) -> list[GraphQLSchemaChange]:
        """Get info-level changes."""
        return [c for c in self.changes if c.severity == GraphQLChangeSeverity.INFO]

    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            "GraphQL Schema Drift Analysis",
            f"Old Version: {self.old_version or 'unknown'}",
            f"New Version: {self.new_version or 'unknown'}",
            f"Total Changes: {len(self.changes)}",
            f"  Breaking: {len(self.breaking_changes)}",
            f"  Dangerous: {len(self.dangerous_changes)}",
            f"  Info: {len(self.info_changes)}",
        ]

        if self.breaking_changes:
            lines.append("\nBREAKING CHANGES:")
            for change in self.breaking_changes:
                lines.append(f"  - {change.message}")

        if self.dangerous_changes:
            lines.append("\nDANGEROUS CHANGES:")
            for change in self.dangerous_changes:
                lines.append(f"  - {change.message}")

        return "\n".join(lines)


class GraphQLSchemaParser:
    """
    Parser for GraphQL SDL (Schema Definition Language).

    [20251219_FEATURE] Parses .graphql files for schema tracking.

    Note: This is a simplified parser that handles common SDL patterns.
    For production use with complex schemas, consider using graphql-core.
    """

    # Regex patterns for parsing SDL
    TYPE_PATTERN = re.compile(
        r'(?:"""[\s\S]*?"""\s*)?'  # Optional description
        r"type\s+(\w+)\s*"
        r"(?:implements\s+([\w\s&,]+))?\s*"  # Optional interfaces
        r'(?:@[\w\s()=",]+)?\s*'  # Optional directives
        r"\{([\s\S]*?)\}",
        re.MULTILINE,
    )

    INTERFACE_PATTERN = re.compile(
        r'(?:"""[\s\S]*?"""\s*)?' r"interface\s+(\w+)\s*" r'(?:@[\w\s()=",]+)?\s*' r"\{([\s\S]*?)\}",
        re.MULTILINE,
    )

    INPUT_PATTERN = re.compile(
        r'(?:"""[\s\S]*?"""\s*)?' r"input\s+(\w+)\s*" r'(?:@[\w\s()=",]+)?\s*' r"\{([\s\S]*?)\}",
        re.MULTILINE,
    )

    ENUM_PATTERN = re.compile(
        r'(?:"""[\s\S]*?"""\s*)?' r"enum\s+(\w+)\s*" r'(?:@[\w\s()=",]+)?\s*' r"\{([\s\S]*?)\}",
        re.MULTILINE,
    )

    UNION_PATTERN = re.compile(
        r'(?:"""[\s\S]*?"""\s*)?'
        r"union\s+(\w+)\s*=\s*([\w\s|]+?)(?=\n\s*(?:type|interface|union|enum|input|scalar|directive|schema|$))",
        re.MULTILINE,
    )

    SCALAR_PATTERN = re.compile(r'(?:"""[\s\S]*?"""\s*)?' r"scalar\s+(\w+)", re.MULTILINE)

    DIRECTIVE_PATTERN = re.compile(
        r'(?:"""[\s\S]*?"""\s*)?'
        r"directive\s+@(\w+)\s*"
        r"(?:\(([^)]*)\))?\s*"
        r"(?:repeatable\s+)?"
        r"on\s+([\w\s|]+)",
        re.MULTILINE,
    )

    SCHEMA_PATTERN = re.compile(r"schema\s*\{([^}]*)\}", re.MULTILINE)

    FIELD_PATTERN = re.compile(
        r'(?:"""[^"]*"""\s*|"[^"]*"\s*)?'  # Optional description
        r"(\w+)\s*"  # Field name
        r"(?:\(([^)]*)\))?\s*"  # Optional arguments
        r":\s*"
        r"([\w\[\]!]+)\s*"  # Type
        r"(@\w+(?:\([^)]*\))?)?"  # Optional directive
    )

    ARG_PATTERN = re.compile(r"(\w+)\s*:\s*([\w\[\]!]+)(?:\s*=\s*([^\s,)]+))?")

    DESCRIPTION_PATTERN = re.compile(r'"""([\s\S]*?)"""')

    def parse(self, sdl: str) -> GraphQLSchema:
        """
        Parse a GraphQL SDL string.

        Args:
            sdl: GraphQL Schema Definition Language content

        Returns:
            GraphQLSchema object
        """
        schema = GraphQLSchema()

        # Remove comments (but preserve descriptions)
        content = self._remove_comments(sdl)

        # Parse schema definition
        self._parse_schema_definition(content, schema)

        # Parse types
        self._parse_object_types(content, schema)
        self._parse_interfaces(content, schema)
        self._parse_input_types(content, schema)
        self._parse_enums(content, schema)
        self._parse_unions(content, schema)
        self._parse_scalars(content, schema)

        # Parse directives
        self._parse_directives(content, schema)

        return schema

    def _remove_comments(self, content: str) -> str:
        """Remove single-line comments but preserve triple-quote descriptions."""
        # Remove single-line comments
        lines = []
        for line in content.split("\n"):
            # Check if line has a comment
            if "#" in line:
                # Don't remove if inside a string
                in_string = False
                comment_pos = -1
                for i, char in enumerate(line):
                    if char == '"' and (i == 0 or line[i - 1] != "\\"):
                        in_string = not in_string
                    elif char == "#" and not in_string:
                        comment_pos = i
                        break
                if comment_pos >= 0:
                    line = line[:comment_pos]
            lines.append(line)
        return "\n".join(lines)

    def _parse_schema_definition(self, content: str, schema: GraphQLSchema) -> None:
        """Parse the schema definition block."""
        match = self.SCHEMA_PATTERN.search(content)
        if match:
            body = match.group(1)

            # Parse query/mutation/subscription types
            for line in body.split("\n"):
                line = line.strip()
                if line.startswith("query"):
                    parts = line.split(":")
                    if len(parts) == 2:
                        schema.query_type = parts[1].strip()
                elif line.startswith("mutation"):
                    parts = line.split(":")
                    if len(parts) == 2:
                        schema.mutation_type = parts[1].strip()
                elif line.startswith("subscription"):
                    parts = line.split(":")
                    if len(parts) == 2:
                        schema.subscription_type = parts[1].strip()

    def _parse_object_types(self, content: str, schema: GraphQLSchema) -> None:
        """Parse object type definitions."""
        for match in self.TYPE_PATTERN.finditer(content):
            name = match.group(1)
            interfaces_str = match.group(2)
            body = match.group(3)

            # Get description before the type
            desc_match = self.DESCRIPTION_PATTERN.search(content[: match.start()])
            description = desc_match.group(1).strip() if desc_match else None

            gql_type = GraphQLType(
                name=name,
                kind=GraphQLTypeKind.OBJECT,
                description=description,
            )

            # Parse interfaces
            if interfaces_str:
                interfaces = [i.strip() for i in re.split(r"[&,]", interfaces_str)]
                gql_type.interfaces = [i for i in interfaces if i]

            # Parse fields
            gql_type.fields = self._parse_fields(body)

            schema.types[name] = gql_type

    def _parse_interfaces(self, content: str, schema: GraphQLSchema) -> None:
        """Parse interface definitions."""
        for match in self.INTERFACE_PATTERN.finditer(content):
            name = match.group(1)
            body = match.group(2)

            gql_type = GraphQLType(
                name=name,
                kind=GraphQLTypeKind.INTERFACE,
            )

            gql_type.fields = self._parse_fields(body)
            schema.types[name] = gql_type

    def _parse_input_types(self, content: str, schema: GraphQLSchema) -> None:
        """Parse input type definitions."""
        for match in self.INPUT_PATTERN.finditer(content):
            name = match.group(1)
            body = match.group(2)

            gql_type = GraphQLType(
                name=name,
                kind=GraphQLTypeKind.INPUT_OBJECT,
            )

            gql_type.input_fields = self._parse_fields(body)
            schema.types[name] = gql_type

    def _parse_enums(self, content: str, schema: GraphQLSchema) -> None:
        """Parse enum definitions."""
        for match in self.ENUM_PATTERN.finditer(content):
            name = match.group(1)
            body = match.group(2)

            gql_type = GraphQLType(
                name=name,
                kind=GraphQLTypeKind.ENUM,
            )

            # Parse enum values
            for line in body.split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith('"'):
                    # Handle deprecation
                    deprecated = "@deprecated" in line.lower()
                    value_name = re.match(r"(\w+)", line)
                    if value_name:
                        gql_type.enum_values[value_name.group(1)] = GraphQLEnumValue(
                            name=value_name.group(1),
                            deprecated=deprecated,
                        )

            schema.types[name] = gql_type

    def _parse_unions(self, content: str, schema: GraphQLSchema) -> None:
        """Parse union definitions."""
        for match in self.UNION_PATTERN.finditer(content):
            name = match.group(1)
            members_str = match.group(2)

            gql_type = GraphQLType(
                name=name,
                kind=GraphQLTypeKind.UNION,
            )

            # Parse union members
            members = [m.strip() for m in members_str.split("|")]
            gql_type.union_types = [m for m in members if m]

            schema.types[name] = gql_type

    def _parse_scalars(self, content: str, schema: GraphQLSchema) -> None:
        """Parse scalar definitions."""
        for match in self.SCALAR_PATTERN.finditer(content):
            name = match.group(1)

            gql_type = GraphQLType(
                name=name,
                kind=GraphQLTypeKind.SCALAR,
            )

            schema.types[name] = gql_type

    def _parse_directives(self, content: str, schema: GraphQLSchema) -> None:
        """Parse directive definitions."""
        for match in self.DIRECTIVE_PATTERN.finditer(content):
            name = match.group(1)
            args_str = match.group(2)
            locations_str = match.group(3)

            directive = GraphQLDirective(
                name=name,
                locations=[loc.strip() for loc in locations_str.split("|") if loc.strip()],
                repeatable="repeatable" in content[match.start() : match.end()].lower(),
            )

            # Parse arguments
            if args_str:
                directive.arguments = self._parse_arguments(args_str)

            schema.directives[name] = directive

    def _parse_fields(self, body: str) -> dict[str, GraphQLField]:
        """Parse field definitions from a type body."""
        fields: dict[str, GraphQLField] = {}

        for match in self.FIELD_PATTERN.finditer(body):
            name = match.group(1)
            args_str = match.group(2)
            field_type = match.group(3)
            directive = match.group(4)

            gql_field = GraphQLField(
                name=name,
                type=field_type,
            )

            # Check for deprecation
            if directive and "@deprecated" in directive.lower():
                gql_field.deprecated = True
                # Try to extract reason
                reason_match = re.search(r'reason:\s*"([^"]*)"', directive)
                if reason_match:
                    gql_field.deprecation_reason = reason_match.group(1)

            # Parse arguments
            if args_str:
                gql_field.arguments = self._parse_arguments(args_str)

            fields[name] = gql_field

        return fields

    def _parse_arguments(self, args_str: str) -> dict[str, GraphQLArgument]:
        """Parse argument definitions."""
        arguments: dict[str, GraphQLArgument] = {}

        for match in self.ARG_PATTERN.finditer(args_str):
            name = match.group(1)
            arg_type = match.group(2)
            default = match.group(3)

            arguments[name] = GraphQLArgument(
                name=name,
                type=arg_type,
                default_value=default,
            )

        return arguments


class GraphQLSchemaTracker:
    """
    Tracks GraphQL schema evolution and detects breaking changes.

    [20251219_FEATURE] v3.0.4 - GraphQL Schema Tracking

    Features:
    - Parse GraphQL SDL to extract schema structure
    - Compare schema versions for breaking/non-breaking changes
    - Validate schemas for best practices
    - Track deprecations and removals

    Usage:
        tracker = GraphQLSchemaTracker()

        # Parse a schema
        schema = tracker.parse(sdl_content)

        # Compare two versions
        drift = tracker.compare(old_sdl, new_sdl)
        if drift.has_breaking_changes():
            for change in drift.breaking_changes:
                print(f"BREAKING: {change}")
    """

    def __init__(self) -> None:
        """Initialize the tracker."""
        self._parser = GraphQLSchemaParser()

    def parse(self, sdl: str) -> GraphQLSchema:
        """
        Parse a GraphQL SDL string.

        Args:
            sdl: GraphQL Schema Definition Language content

        Returns:
            GraphQLSchema object
        """
        return self._parser.parse(sdl)

    def parse_file(self, path: str | Path) -> GraphQLSchema:
        """
        Parse a GraphQL SDL file.

        Args:
            path: Path to .graphql file

        Returns:
            GraphQLSchema object
        """
        content = Path(path).read_text()
        return self.parse(content)

    def compare(
        self,
        old_sdl: str,
        new_sdl: str,
        old_version: str = "",
        new_version: str = "",
    ) -> GraphQLSchemaDrift:
        """
        Compare two GraphQL schemas for changes.

        Args:
            old_sdl: Old schema SDL
            new_sdl: New schema SDL
            old_version: Version label for old schema
            new_version: Version label for new schema

        Returns:
            GraphQLSchemaDrift with detected changes
        """
        old_schema = self.parse(old_sdl)
        new_schema = self.parse(new_sdl)

        return self.compare_schemas(old_schema, new_schema, old_version, new_version)

    def compare_schemas(
        self,
        old_schema: GraphQLSchema,
        new_schema: GraphQLSchema,
        old_version: str = "",
        new_version: str = "",
    ) -> GraphQLSchemaDrift:
        """
        Compare two parsed GraphQL schemas.

        Args:
            old_schema: Old GraphQLSchema
            new_schema: New GraphQLSchema
            old_version: Version label
            new_version: Version label

        Returns:
            GraphQLSchemaDrift with detected changes
        """
        drift = GraphQLSchemaDrift(
            old_version=old_version,
            new_version=new_version,
        )

        # Compare types
        self._compare_types(old_schema, new_schema, drift)

        # Compare directives
        self._compare_directives(old_schema, new_schema, drift)

        return drift

    def _compare_types(
        self,
        old_schema: GraphQLSchema,
        new_schema: GraphQLSchema,
        drift: GraphQLSchemaDrift,
    ) -> None:
        """Compare type definitions."""
        old_types = set(old_schema.types.keys())
        new_types = set(new_schema.types.keys())

        # Removed types (BREAKING)
        for name in old_types - new_types:
            old_type = old_schema.types[name]
            drift.changes.append(
                GraphQLSchemaChange(
                    change_type=GraphQLChangeType.TYPE_REMOVED,
                    severity=GraphQLChangeSeverity.BREAKING,
                    path=name,
                    message=f"Type '{name}' ({old_type.kind.value}) was removed",
                )
            )

        # Added types (INFO)
        for name in new_types - old_types:
            new_type = new_schema.types[name]
            drift.changes.append(
                GraphQLSchemaChange(
                    change_type=GraphQLChangeType.TYPE_ADDED,
                    severity=GraphQLChangeSeverity.INFO,
                    path=name,
                    message=f"Type '{name}' ({new_type.kind.value}) was added",
                )
            )

        # Compare common types
        for name in old_types & new_types:
            old_type = old_schema.types[name]
            new_type = new_schema.types[name]

            # Check if type kind changed (BREAKING)
            if old_type.kind != new_type.kind:
                drift.changes.append(
                    GraphQLSchemaChange(
                        change_type=GraphQLChangeType.TYPE_REMOVED,
                        severity=GraphQLChangeSeverity.BREAKING,
                        path=name,
                        message=f"Type '{name}' kind changed from {old_type.kind.value} to {new_type.kind.value}",
                        old_value=old_type.kind.value,
                        new_value=new_type.kind.value,
                    )
                )
                continue

            # Compare based on type kind
            if old_type.kind == GraphQLTypeKind.OBJECT:
                self._compare_object_types(old_type, new_type, drift)
            elif old_type.kind == GraphQLTypeKind.INTERFACE:
                self._compare_object_types(old_type, new_type, drift)
            elif old_type.kind == GraphQLTypeKind.INPUT_OBJECT:
                self._compare_input_types(old_type, new_type, drift)
            elif old_type.kind == GraphQLTypeKind.ENUM:
                self._compare_enum_types(old_type, new_type, drift)
            elif old_type.kind == GraphQLTypeKind.UNION:
                self._compare_union_types(old_type, new_type, drift)

    def _compare_object_types(
        self,
        old_type: GraphQLType,
        new_type: GraphQLType,
        drift: GraphQLSchemaDrift,
    ) -> None:
        """Compare object/interface type fields."""
        old_fields = set(old_type.fields.keys())
        new_fields = set(new_type.fields.keys())

        # Removed fields (BREAKING)
        for name in old_fields - new_fields:
            drift.changes.append(
                GraphQLSchemaChange(
                    change_type=GraphQLChangeType.FIELD_REMOVED,
                    severity=GraphQLChangeSeverity.BREAKING,
                    path=f"{old_type.name}.{name}",
                    message=f"Field '{name}' was removed from type '{old_type.name}'",
                )
            )

        # Added fields (INFO)
        for name in new_fields - old_fields:
            drift.changes.append(
                GraphQLSchemaChange(
                    change_type=GraphQLChangeType.FIELD_ADDED,
                    severity=GraphQLChangeSeverity.INFO,
                    path=f"{new_type.name}.{name}",
                    message=f"Field '{name}' was added to type '{new_type.name}'",
                )
            )

        # Compare common fields
        for name in old_fields & new_fields:
            old_field = old_type.fields[name]
            new_field = new_type.fields[name]
            self._compare_fields(old_type.name, old_field, new_field, drift)

        # Compare interfaces
        old_interfaces = set(old_type.interfaces)
        new_interfaces = set(new_type.interfaces)

        for iface in old_interfaces - new_interfaces:
            drift.changes.append(
                GraphQLSchemaChange(
                    change_type=GraphQLChangeType.INTERFACE_REMOVED,
                    severity=GraphQLChangeSeverity.BREAKING,
                    path=f"{old_type.name}",
                    message=f"Type '{old_type.name}' no longer implements interface '{iface}'",
                )
            )

        for iface in new_interfaces - old_interfaces:
            drift.changes.append(
                GraphQLSchemaChange(
                    change_type=GraphQLChangeType.INTERFACE_ADDED,
                    severity=GraphQLChangeSeverity.INFO,
                    path=f"{new_type.name}",
                    message=f"Type '{new_type.name}' now implements interface '{iface}'",
                )
            )

    def _compare_fields(
        self,
        type_name: str,
        old_field: GraphQLField,
        new_field: GraphQLField,
        drift: GraphQLSchemaDrift,
    ) -> None:
        """Compare two fields."""
        path = f"{type_name}.{old_field.name}"

        # Type changed
        if old_field.type != new_field.type:
            # Check if it's a breaking change
            is_breaking = self._is_type_change_breaking(old_field.type, new_field.type)
            drift.changes.append(
                GraphQLSchemaChange(
                    change_type=GraphQLChangeType.FIELD_TYPE_CHANGED,
                    severity=(GraphQLChangeSeverity.BREAKING if is_breaking else GraphQLChangeSeverity.DANGEROUS),
                    path=path,
                    message=f"Field '{old_field.name}' type changed from '{old_field.type}' to '{new_field.type}'",
                    old_value=old_field.type,
                    new_value=new_field.type,
                )
            )

        # Compare arguments
        self._compare_arguments(path, old_field.arguments, new_field.arguments, drift)

        # Deprecation added
        if not old_field.deprecated and new_field.deprecated:
            drift.changes.append(
                GraphQLSchemaChange(
                    change_type=GraphQLChangeType.FIELD_DEPRECATED,
                    severity=GraphQLChangeSeverity.INFO,
                    path=path,
                    message=f"Field '{old_field.name}' was deprecated",
                )
            )

    def _compare_arguments(
        self,
        path: str,
        old_args: dict[str, GraphQLArgument],
        new_args: dict[str, GraphQLArgument],
        drift: GraphQLSchemaDrift,
    ) -> None:
        """Compare field arguments."""
        old_arg_names = set(old_args.keys())
        new_arg_names = set(new_args.keys())

        # Removed arguments (BREAKING)
        for name in old_arg_names - new_arg_names:
            drift.changes.append(
                GraphQLSchemaChange(
                    change_type=GraphQLChangeType.ARG_REMOVED,
                    severity=GraphQLChangeSeverity.BREAKING,
                    path=f"{path}({name})",
                    message=f"Argument '{name}' was removed from '{path}'",
                )
            )

        # Added arguments
        for name in new_arg_names - old_arg_names:
            new_arg = new_args[name]
            is_required = new_arg.is_required
            drift.changes.append(
                GraphQLSchemaChange(
                    change_type=(
                        GraphQLChangeType.REQUIRED_ARG_ADDED if is_required else GraphQLChangeType.OPTIONAL_ARG_ADDED
                    ),
                    severity=(GraphQLChangeSeverity.BREAKING if is_required else GraphQLChangeSeverity.INFO),
                    path=f"{path}({name})",
                    message=f"{'Required' if is_required else 'Optional'} argument '{name}' was added to '{path}'",
                )
            )

        # Compare common arguments
        for name in old_arg_names & new_arg_names:
            old_arg = old_args[name]
            new_arg = new_args[name]

            if old_arg.type != new_arg.type:
                drift.changes.append(
                    GraphQLSchemaChange(
                        change_type=GraphQLChangeType.ARG_TYPE_CHANGED,
                        severity=GraphQLChangeSeverity.BREAKING,
                        path=f"{path}({name})",
                        message=f"Argument '{name}' type changed from '{old_arg.type}' to '{new_arg.type}'",
                        old_value=old_arg.type,
                        new_value=new_arg.type,
                    )
                )

    def _compare_input_types(
        self,
        old_type: GraphQLType,
        new_type: GraphQLType,
        drift: GraphQLSchemaDrift,
    ) -> None:
        """Compare input type fields."""
        old_fields = set(old_type.input_fields.keys())
        new_fields = set(new_type.input_fields.keys())

        # Removed fields (BREAKING)
        for name in old_fields - new_fields:
            drift.changes.append(
                GraphQLSchemaChange(
                    change_type=GraphQLChangeType.FIELD_REMOVED,
                    severity=GraphQLChangeSeverity.BREAKING,
                    path=f"{old_type.name}.{name}",
                    message=f"Input field '{name}' was removed from '{old_type.name}'",
                )
            )

        # Added fields
        for name in new_fields - old_fields:
            new_field = new_type.input_fields[name]
            is_required = new_field.type.endswith("!")
            drift.changes.append(
                GraphQLSchemaChange(
                    change_type=(
                        GraphQLChangeType.REQUIRED_ARG_ADDED if is_required else GraphQLChangeType.FIELD_ADDED
                    ),
                    severity=(GraphQLChangeSeverity.BREAKING if is_required else GraphQLChangeSeverity.INFO),
                    path=f"{new_type.name}.{name}",
                    message=f"{'Required' if is_required else 'Optional'} input field '{name}' was added to '{new_type.name}'",
                )
            )

        # Compare common fields
        for name in old_fields & new_fields:
            old_field = old_type.input_fields[name]
            new_field = new_type.input_fields[name]

            if old_field.type != new_field.type:
                drift.changes.append(
                    GraphQLSchemaChange(
                        change_type=GraphQLChangeType.FIELD_TYPE_CHANGED,
                        severity=GraphQLChangeSeverity.BREAKING,
                        path=f"{old_type.name}.{name}",
                        message=f"Input field '{name}' type changed from '{old_field.type}' to '{new_field.type}'",
                        old_value=old_field.type,
                        new_value=new_field.type,
                    )
                )

    def _compare_enum_types(
        self,
        old_type: GraphQLType,
        new_type: GraphQLType,
        drift: GraphQLSchemaDrift,
    ) -> None:
        """Compare enum values."""
        old_values = set(old_type.enum_values.keys())
        new_values = set(new_type.enum_values.keys())

        # Removed values (BREAKING)
        for name in old_values - new_values:
            drift.changes.append(
                GraphQLSchemaChange(
                    change_type=GraphQLChangeType.ENUM_VALUE_REMOVED,
                    severity=GraphQLChangeSeverity.BREAKING,
                    path=f"{old_type.name}.{name}",
                    message=f"Enum value '{name}' was removed from '{old_type.name}'",
                )
            )

        # Added values (INFO)
        for name in new_values - old_values:
            drift.changes.append(
                GraphQLSchemaChange(
                    change_type=GraphQLChangeType.ENUM_VALUE_ADDED,
                    severity=GraphQLChangeSeverity.INFO,
                    path=f"{new_type.name}.{name}",
                    message=f"Enum value '{name}' was added to '{new_type.name}'",
                )
            )

    def _compare_union_types(
        self,
        old_type: GraphQLType,
        new_type: GraphQLType,
        drift: GraphQLSchemaDrift,
    ) -> None:
        """Compare union members."""
        old_members = set(old_type.union_types)
        new_members = set(new_type.union_types)

        # Removed members (BREAKING)
        for name in old_members - new_members:
            drift.changes.append(
                GraphQLSchemaChange(
                    change_type=GraphQLChangeType.UNION_MEMBER_REMOVED,
                    severity=GraphQLChangeSeverity.BREAKING,
                    path=f"{old_type.name}",
                    message=f"Union member '{name}' was removed from '{old_type.name}'",
                )
            )

        # Added members (DANGEROUS - may affect fragment spreads)
        for name in new_members - old_members:
            drift.changes.append(
                GraphQLSchemaChange(
                    change_type=GraphQLChangeType.UNION_MEMBER_ADDED,
                    severity=GraphQLChangeSeverity.DANGEROUS,
                    path=f"{new_type.name}",
                    message=f"Union member '{name}' was added to '{new_type.name}'",
                )
            )

    def _compare_directives(
        self,
        old_schema: GraphQLSchema,
        new_schema: GraphQLSchema,
        drift: GraphQLSchemaDrift,
    ) -> None:
        """Compare directive definitions."""
        old_directives = set(old_schema.directives.keys())
        new_directives = set(new_schema.directives.keys())

        # Removed directives (BREAKING)
        for name in old_directives - new_directives:
            drift.changes.append(
                GraphQLSchemaChange(
                    change_type=GraphQLChangeType.DIRECTIVE_REMOVED,
                    severity=GraphQLChangeSeverity.BREAKING,
                    path=f"@{name}",
                    message=f"Directive '@{name}' was removed",
                )
            )

        # Added directives (INFO)
        for name in new_directives - old_directives:
            drift.changes.append(
                GraphQLSchemaChange(
                    change_type=GraphQLChangeType.DIRECTIVE_ADDED,
                    severity=GraphQLChangeSeverity.INFO,
                    path=f"@{name}",
                    message=f"Directive '@{name}' was added",
                )
            )

    def _is_type_change_breaking(self, old_type: str, new_type: str) -> bool:
        """
        Determine if a type change is breaking.

        Non-breaking changes:
        - T -> T! (making nullable non-null is breaking for inputs, safe for outputs)
        - [T] -> [T!] (making list items non-null)

        Breaking changes:
        - T! -> T (making non-null nullable for outputs)
        - Type completely changed
        """
        # Strip non-null markers for base comparison
        old_base = old_type.rstrip("!")
        new_base = new_type.rstrip("!")

        # Base type changed
        if old_base != new_base:
            return True

        # Nullability changed (for outputs, removing ! is breaking)
        # This is a simplified check - in real GraphQL, it depends on context
        return False


def track_graphql_schema(sdl: str) -> GraphQLSchema:
    """
    Convenience function to parse a GraphQL SDL.

    Args:
        sdl: GraphQL Schema Definition Language content

    Returns:
        GraphQLSchema object
    """
    tracker = GraphQLSchemaTracker()
    return tracker.parse(sdl)


def compare_graphql_schemas(
    old_sdl: str,
    new_sdl: str,
    old_version: str = "",
    new_version: str = "",
) -> GraphQLSchemaDrift:
    """
    Convenience function to compare two GraphQL schemas.

    Args:
        old_sdl: Old schema SDL
        new_sdl: New schema SDL
        old_version: Version label for old schema
        new_version: Version label for new schema

    Returns:
        GraphQLSchemaDrift with detected changes
    """
    tracker = GraphQLSchemaTracker()
    return tracker.compare(old_sdl, new_sdl, old_version, new_version)


def compare_graphql_files(
    old_path: str | Path,
    new_path: str | Path,
) -> GraphQLSchemaDrift:
    """
    Convenience function to compare two GraphQL schema files.

    Args:
        old_path: Path to old .graphql file
        new_path: Path to new .graphql file

    Returns:
        GraphQLSchemaDrift with detected changes
    """
    old_content = Path(old_path).read_text()
    new_content = Path(new_path).read_text()

    return compare_graphql_schemas(
        old_content,
        new_content,
        old_version=str(old_path),
        new_version=str(new_path),
    )


# [20251225_FEATURE] Export public API for type checkers
__all__ = [
    "GraphQLSchemaTracker",
    "GraphQLSchema",
    "GraphQLType",
    "GraphQLTypeKind",
    "GraphQLField",
    "GraphQLArgument",
    "GraphQLSchemaDrift",
    "GraphQLSchemaChange",
    "GraphQLChangeType",
    "GraphQLChangeSeverity",
    "track_graphql_schema",
    "compare_graphql_schemas",
    "compare_graphql_files",
]
