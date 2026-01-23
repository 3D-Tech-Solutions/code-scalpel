"""
Schema Drift Detector - API Contract Evolution Analysis.

[20251219_FEATURE] v3.0.4 - Ninja Warrior Stage 3

This module detects breaking changes when API schemas evolve:
- Protobuf (.proto) field changes
- JSON Schema property changes
- OpenAPI/Swagger specification changes

CRITICAL CONCEPT: Breaking vs Non-Breaking Changes
==================================================

Breaking Changes (will break clients):
- Field/property removed
- Field/property type changed
- Required field added
- Enum value removed
- Field number changed (Protobuf)

Non-Breaking Changes (backward compatible):
- Optional field added
- Enum value added
- Field deprecated (but not removed)
- Description/comment changed

Usage:
    detector = SchemaDriftDetector()

    # Compare two Protobuf schemas
    drift = detector.compare_protobuf(old_proto, new_proto)

    # Compare two JSON schemas
    drift = detector.compare_json_schema(old_schema, new_schema)

    if drift.has_breaking_changes():
        print(f"BREAKING: {drift.breaking_changes}")
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, cast


class ChangeType(Enum):
    """Types of schema changes."""

    # Breaking changes
    FIELD_REMOVED = auto()
    FIELD_TYPE_CHANGED = auto()
    REQUIRED_FIELD_ADDED = auto()
    ENUM_VALUE_REMOVED = auto()
    FIELD_NUMBER_CHANGED = auto()  # Protobuf-specific
    FIELD_MADE_REQUIRED = auto()

    # Non-breaking changes
    OPTIONAL_FIELD_ADDED = auto()
    ENUM_VALUE_ADDED = auto()
    FIELD_DEPRECATED = auto()
    DESCRIPTION_CHANGED = auto()
    DEFAULT_VALUE_CHANGED = auto()
    FIELD_MADE_OPTIONAL = auto()


class ChangeSeverity(Enum):
    """Severity of schema changes."""

    BREAKING = "BREAKING"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class SchemaChange:
    """Represents a single schema change."""

    change_type: ChangeType
    severity: ChangeSeverity
    path: str  # JSON path to the changed element
    field_name: str
    message: str
    old_value: Any | None = None
    new_value: Any | None = None

    def __str__(self) -> str:
        return f"[{self.severity.value}] {self.path}: {self.message}"


@dataclass
class SchemaDriftResult:
    """Result of schema drift analysis."""

    old_version: str = ""
    new_version: str = ""
    schema_type: str = ""  # "protobuf", "json_schema", "openapi"
    changes: list[SchemaChange] = field(default_factory=list)

    def has_breaking_changes(self) -> bool:
        """Check if any breaking changes were detected."""
        return any(c.severity == ChangeSeverity.BREAKING for c in self.changes)

    @property
    def breaking_changes(self) -> list[SchemaChange]:
        """Get only breaking changes."""
        return [c for c in self.changes if c.severity == ChangeSeverity.BREAKING]

    @property
    def warnings(self) -> list[SchemaChange]:
        """Get warning-level changes."""
        return [c for c in self.changes if c.severity == ChangeSeverity.WARNING]

    @property
    def info_changes(self) -> list[SchemaChange]:
        """Get info-level changes."""
        return [c for c in self.changes if c.severity == ChangeSeverity.INFO]

    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Schema Drift Analysis: {self.schema_type}",
            f"Old Version: {self.old_version or 'unknown'}",
            f"New Version: {self.new_version or 'unknown'}",
            f"Total Changes: {len(self.changes)}",
            f"  Breaking: {len(self.breaking_changes)}",
            f"  Warnings: {len(self.warnings)}",
            f"  Info: {len(self.info_changes)}",
        ]

        if self.breaking_changes:
            lines.append("\nBREAKING CHANGES:")
            for change in self.breaking_changes:
                lines.append(f"  - {change.message}")

        if self.warnings:
            lines.append("\nWARNINGS:")
            for change in self.warnings:
                lines.append(f"  - {change.message}")

        return "\n".join(lines)


@dataclass
class ProtobufField:
    """Represents a Protobuf field."""

    name: str
    number: int
    type: str
    label: str = "optional"  # optional, required, repeated
    default: str | None = None
    deprecated: bool = False
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProtobufEnum:
    """Represents a Protobuf enum."""

    name: str
    values: dict[str, int] = field(default_factory=dict)  # name -> number


@dataclass
class ProtobufMessage:
    """Represents a Protobuf message."""

    name: str
    fields: dict[str, ProtobufField] = field(default_factory=dict)
    nested_messages: dict[str, ProtobufMessage] = field(default_factory=dict)
    nested_enums: dict[str, ProtobufEnum] = field(default_factory=dict)


@dataclass
class ProtobufSchema:
    """Represents a parsed Protobuf schema."""

    syntax: str = "proto3"
    package: str = ""
    messages: dict[str, ProtobufMessage] = field(default_factory=dict)
    enums: dict[str, ProtobufEnum] = field(default_factory=dict)
    services: dict[str, dict[str, tuple[str, str]]] = field(
        default_factory=dict
    )  # service -> {rpc_name: (request, response)}


class ProtobufParser:
    """
    Simple Protobuf schema parser.

    [20251219_FEATURE] Parses .proto files for drift detection.

    Note: This is a simplified parser that handles common cases.
    For production use, consider using protobuf compiler (protoc).
    """

    # Regex patterns for parsing
    SYNTAX_PATTERN = re.compile(r'syntax\s*=\s*["\'](\w+)["\']')
    PACKAGE_PATTERN = re.compile(r"package\s+([\w.]+)\s*;")
    MESSAGE_PATTERN = re.compile(r"message\s+(\w+)\s*\{")
    ENUM_PATTERN = re.compile(r"enum\s+(\w+)\s*\{")
    FIELD_PATTERN = re.compile(
        r"(optional|required|repeated)?\s*" r"(\w+)\s+" r"(\w+)\s*=\s*" r"(\d+)\s*" r"(?:\[(.*?)\])?\s*;"
    )
    ENUM_VALUE_PATTERN = re.compile(r"(\w+)\s*=\s*(-?\d+)\s*;")
    SERVICE_PATTERN = re.compile(r"service\s+(\w+)\s*\{")
    RPC_PATTERN = re.compile(r"rpc\s+(\w+)\s*\(\s*(\w+)\s*\)\s*returns\s*\(\s*(\w+)\s*\)")

    def parse(self, proto_content: str) -> ProtobufSchema:
        """
        Parse a Protobuf schema from string content.

        Args:
            proto_content: Content of .proto file

        Returns:
            ProtobufSchema object
        """
        schema = ProtobufSchema()

        # Remove comments
        content = self._remove_comments(proto_content)

        # Parse syntax
        syntax_match = self.SYNTAX_PATTERN.search(content)
        if syntax_match:
            schema.syntax = syntax_match.group(1)

        # Parse package
        package_match = self.PACKAGE_PATTERN.search(content)
        if package_match:
            schema.package = package_match.group(1)

        # Parse messages
        schema.messages = self._parse_messages(content)

        # Parse top-level enums
        schema.enums = self._parse_top_level_enums(content)

        # Parse services
        schema.services = self._parse_services(content)

        return schema

    def _remove_comments(self, content: str) -> str:
        """Remove single-line and multi-line comments."""
        # Remove multi-line comments
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        # Remove single-line comments
        content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)
        return content

    def _parse_messages(self, content: str) -> dict[str, ProtobufMessage]:
        """Parse all message definitions."""
        messages: dict[str, ProtobufMessage] = {}

        # Find all message blocks
        for match in self.MESSAGE_PATTERN.finditer(content):
            name = match.group(1)
            start = match.end()

            # Find matching closing brace
            brace_count = 1
            end = start
            while brace_count > 0 and end < len(content):
                if content[end] == "{":
                    brace_count += 1
                elif content[end] == "}":
                    brace_count -= 1
                end += 1

            message_body = content[start : end - 1]
            message = self._parse_message_body(name, message_body)
            messages[name] = message

        return messages

    def _parse_message_body(self, name: str, body: str) -> ProtobufMessage:
        """Parse the body of a message definition."""
        message = ProtobufMessage(name=name)

        # Parse fields
        for match in self.FIELD_PATTERN.finditer(body):
            label = match.group(1) or "optional"  # proto3 default
            field_type = match.group(2)
            field_name = match.group(3)
            field_number = int(match.group(4))
            options_str = match.group(5)

            field = ProtobufField(
                name=field_name,
                number=field_number,
                type=field_type,
                label=label,
            )

            # Parse options
            if options_str:
                if "deprecated" in options_str.lower():
                    field.deprecated = True
                if "default" in options_str:
                    default_match = re.search(r"default\s*=\s*(\S+)", options_str)
                    if default_match:
                        field.default = default_match.group(1)

            message.fields[field_name] = field

        # Parse nested enums
        for enum_match in self.ENUM_PATTERN.finditer(body):
            enum_name = enum_match.group(1)
            enum_start = enum_match.end()

            # Find closing brace
            brace_count = 1
            enum_end = enum_start
            while brace_count > 0 and enum_end < len(body):
                if body[enum_end] == "{":
                    brace_count += 1
                elif body[enum_end] == "}":
                    brace_count -= 1
                enum_end += 1

            enum_body = body[enum_start : enum_end - 1]
            enum = self._parse_enum_body(enum_name, enum_body)
            message.nested_enums[enum_name] = enum

        return message

    def _parse_enum_body(self, name: str, body: str) -> ProtobufEnum:
        """Parse the body of an enum definition."""
        enum = ProtobufEnum(name=name)

        for match in self.ENUM_VALUE_PATTERN.finditer(body):
            value_name = match.group(1)
            value_number = int(match.group(2))
            enum.values[value_name] = value_number

        return enum

    def _parse_top_level_enums(self, content: str) -> dict[str, ProtobufEnum]:
        """Parse top-level enum definitions (not nested in messages)."""
        enums: dict[str, ProtobufEnum] = {}

        # This is simplified - would need to exclude enums inside messages
        for match in self.ENUM_PATTERN.finditer(content):
            name = match.group(1)
            start = match.end()

            brace_count = 1
            end = start
            while brace_count > 0 and end < len(content):
                if content[end] == "{":
                    brace_count += 1
                elif content[end] == "}":
                    brace_count -= 1
                end += 1

            enum_body = content[start : end - 1]
            enum = self._parse_enum_body(name, enum_body)
            enums[name] = enum

        return enums

    def _parse_services(self, content: str) -> dict[str, dict[str, tuple[str, str]]]:
        """Parse service definitions."""
        services: dict[str, dict[str, tuple[str, str]]] = {}

        for match in self.SERVICE_PATTERN.finditer(content):
            service_name = match.group(1)
            start = match.end()

            brace_count = 1
            end = start
            while brace_count > 0 and end < len(content):
                if content[end] == "{":
                    brace_count += 1
                elif content[end] == "}":
                    brace_count -= 1
                end += 1

            service_body = content[start : end - 1]
            rpcs: dict[str, tuple[str, str]] = {}

            for rpc_match in self.RPC_PATTERN.finditer(service_body):
                rpc_name = rpc_match.group(1)
                request_type = rpc_match.group(2)
                response_type = rpc_match.group(3)
                rpcs[rpc_name] = (request_type, response_type)

            services[service_name] = rpcs

        return services


class SchemaDriftDetector:
    """
    Detects breaking changes between schema versions.

    [20251219_FEATURE] v3.0.4 - Schema Drift Detection

    Supports:
    - Protobuf (.proto) schemas
    - JSON Schema
    - OpenAPI/Swagger (planned)

    Usage:
        detector = SchemaDriftDetector()
        result = detector.compare_protobuf(old_proto, new_proto)
        if result.has_breaking_changes():
            for change in result.breaking_changes:
                print(f"BREAKING: {change}")
    """

    def __init__(self) -> None:
        """Initialize the detector."""
        self._proto_parser = ProtobufParser()

    def compare_protobuf(
        self,
        old_proto: str,
        new_proto: str,
        old_version: str = "",
        new_version: str = "",
    ) -> SchemaDriftResult:
        """
        Compare two Protobuf schemas for breaking changes.

        Args:
            old_proto: Old .proto file content
            new_proto: New .proto file content
            old_version: Version label for old schema
            new_version: Version label for new schema

        Returns:
            SchemaDriftResult with detected changes
        """
        result = SchemaDriftResult(
            old_version=old_version,
            new_version=new_version,
            schema_type="protobuf",
        )

        old_schema = self._proto_parser.parse(old_proto)
        new_schema = self._proto_parser.parse(new_proto)

        # Compare messages
        self._compare_protobuf_messages(old_schema, new_schema, result)

        # Compare top-level enums
        self._compare_protobuf_enums(old_schema.enums, new_schema.enums, "", result)

        # Compare services
        self._compare_protobuf_services(old_schema, new_schema, result)

        return result

    def _compare_protobuf_messages(
        self,
        old_schema: ProtobufSchema,
        new_schema: ProtobufSchema,
        result: SchemaDriftResult,
    ) -> None:
        """Compare message definitions."""
        old_messages = set(old_schema.messages.keys())
        new_messages = set(new_schema.messages.keys())

        # Removed messages
        for name in old_messages - new_messages:
            result.changes.append(
                SchemaChange(
                    change_type=ChangeType.FIELD_REMOVED,
                    severity=ChangeSeverity.BREAKING,
                    path=name,
                    field_name=name,
                    message=f"Message '{name}' was removed",
                )
            )

        # Added messages (non-breaking)
        for name in new_messages - old_messages:
            result.changes.append(
                SchemaChange(
                    change_type=ChangeType.OPTIONAL_FIELD_ADDED,
                    severity=ChangeSeverity.INFO,
                    path=name,
                    field_name=name,
                    message=f"Message '{name}' was added",
                )
            )

        # Compare common messages
        for name in old_messages & new_messages:
            old_msg = old_schema.messages[name]
            new_msg = new_schema.messages[name]
            self._compare_protobuf_fields(old_msg, new_msg, name, result)
            self._compare_protobuf_enums(old_msg.nested_enums, new_msg.nested_enums, name, result)

    def _compare_protobuf_fields(
        self,
        old_msg: ProtobufMessage,
        new_msg: ProtobufMessage,
        path: str,
        result: SchemaDriftResult,
    ) -> None:
        """Compare fields within a message."""
        old_fields = set(old_msg.fields.keys())
        new_fields = set(new_msg.fields.keys())

        # Removed fields (BREAKING)
        for name in old_fields - new_fields:
            old_field = old_msg.fields[name]
            result.changes.append(
                SchemaChange(
                    change_type=ChangeType.FIELD_REMOVED,
                    severity=ChangeSeverity.BREAKING,
                    path=f"{path}.{name}",
                    field_name=name,
                    message=f"Field '{name}' (number {old_field.number}) was removed from '{path}'",
                    old_value=f"{old_field.type} {name} = {old_field.number}",
                )
            )

        # Added fields
        for name in new_fields - old_fields:
            new_field = new_msg.fields[name]
            severity = ChangeSeverity.INFO
            change_type = ChangeType.OPTIONAL_FIELD_ADDED

            # Required fields are breaking changes
            if new_field.label == "required":
                severity = ChangeSeverity.BREAKING
                change_type = ChangeType.REQUIRED_FIELD_ADDED

            result.changes.append(
                SchemaChange(
                    change_type=change_type,
                    severity=severity,
                    path=f"{path}.{name}",
                    field_name=name,
                    message=f"{'Required' if new_field.label == 'required' else 'Optional'} field '{name}' was added to '{path}'",
                    new_value=f"{new_field.type} {name} = {new_field.number}",
                )
            )

        # Compare common fields
        for name in old_fields & new_fields:
            old_field = old_msg.fields[name]
            new_field = new_msg.fields[name]

            # Type changed (BREAKING)
            if old_field.type != new_field.type:
                result.changes.append(
                    SchemaChange(
                        change_type=ChangeType.FIELD_TYPE_CHANGED,
                        severity=ChangeSeverity.BREAKING,
                        path=f"{path}.{name}",
                        field_name=name,
                        message=f"Field '{name}' type changed from '{old_field.type}' to '{new_field.type}'",
                        old_value=old_field.type,
                        new_value=new_field.type,
                    )
                )

            # Field number changed (BREAKING - wire format incompatibility)
            if old_field.number != new_field.number:
                result.changes.append(
                    SchemaChange(
                        change_type=ChangeType.FIELD_NUMBER_CHANGED,
                        severity=ChangeSeverity.BREAKING,
                        path=f"{path}.{name}",
                        field_name=name,
                        message=f"Field '{name}' number changed from {old_field.number} to {new_field.number}",
                        old_value=old_field.number,
                        new_value=new_field.number,
                    )
                )

            # Label changed (optional -> required is BREAKING)
            if old_field.label != new_field.label:
                if old_field.label == "optional" and new_field.label == "required":
                    result.changes.append(
                        SchemaChange(
                            change_type=ChangeType.FIELD_MADE_REQUIRED,
                            severity=ChangeSeverity.BREAKING,
                            path=f"{path}.{name}",
                            field_name=name,
                            message=f"Field '{name}' changed from optional to required",
                            old_value=old_field.label,
                            new_value=new_field.label,
                        )
                    )
                else:
                    result.changes.append(
                        SchemaChange(
                            change_type=ChangeType.FIELD_MADE_OPTIONAL,
                            severity=ChangeSeverity.INFO,
                            path=f"{path}.{name}",
                            field_name=name,
                            message=f"Field '{name}' label changed from '{old_field.label}' to '{new_field.label}'",
                            old_value=old_field.label,
                            new_value=new_field.label,
                        )
                    )

            # Deprecated changed
            if not old_field.deprecated and new_field.deprecated:
                result.changes.append(
                    SchemaChange(
                        change_type=ChangeType.FIELD_DEPRECATED,
                        severity=ChangeSeverity.WARNING,
                        path=f"{path}.{name}",
                        field_name=name,
                        message=f"Field '{name}' was marked as deprecated",
                    )
                )

    def _compare_protobuf_enums(
        self,
        old_enums: dict[str, ProtobufEnum],
        new_enums: dict[str, ProtobufEnum],
        parent_path: str,
        result: SchemaDriftResult,
    ) -> None:
        """Compare enum definitions."""
        old_names = set(old_enums.keys())
        new_names = set(new_enums.keys())

        prefix = f"{parent_path}." if parent_path else ""

        # Removed enums (BREAKING)
        for name in old_names - new_names:
            result.changes.append(
                SchemaChange(
                    change_type=ChangeType.FIELD_REMOVED,
                    severity=ChangeSeverity.BREAKING,
                    path=f"{prefix}{name}",
                    field_name=name,
                    message=f"Enum '{name}' was removed",
                )
            )

        # Added enums (non-breaking)
        for name in new_names - old_names:
            result.changes.append(
                SchemaChange(
                    change_type=ChangeType.OPTIONAL_FIELD_ADDED,
                    severity=ChangeSeverity.INFO,
                    path=f"{prefix}{name}",
                    field_name=name,
                    message=f"Enum '{name}' was added",
                )
            )

        # Compare common enums
        for name in old_names & new_names:
            old_enum = old_enums[name]
            new_enum = new_enums[name]

            old_values = set(old_enum.values.keys())
            new_values = set(new_enum.values.keys())

            # Removed enum values (BREAKING)
            for value in old_values - new_values:
                result.changes.append(
                    SchemaChange(
                        change_type=ChangeType.ENUM_VALUE_REMOVED,
                        severity=ChangeSeverity.BREAKING,
                        path=f"{prefix}{name}.{value}",
                        field_name=value,
                        message=f"Enum value '{value}' was removed from '{name}'",
                        old_value=old_enum.values[value],
                    )
                )

            # Added enum values (non-breaking)
            for value in new_values - old_values:
                result.changes.append(
                    SchemaChange(
                        change_type=ChangeType.ENUM_VALUE_ADDED,
                        severity=ChangeSeverity.INFO,
                        path=f"{prefix}{name}.{value}",
                        field_name=value,
                        message=f"Enum value '{value}' was added to '{name}'",
                        new_value=new_enum.values[value],
                    )
                )

    def _compare_protobuf_services(
        self,
        old_schema: ProtobufSchema,
        new_schema: ProtobufSchema,
        result: SchemaDriftResult,
    ) -> None:
        """Compare service definitions."""
        old_services = set(old_schema.services.keys())
        new_services = set(new_schema.services.keys())

        # Removed services (BREAKING)
        for name in old_services - new_services:
            result.changes.append(
                SchemaChange(
                    change_type=ChangeType.FIELD_REMOVED,
                    severity=ChangeSeverity.BREAKING,
                    path=f"service.{name}",
                    field_name=name,
                    message=f"Service '{name}' was removed",
                )
            )

        # Added services (non-breaking)
        for name in new_services - old_services:
            result.changes.append(
                SchemaChange(
                    change_type=ChangeType.OPTIONAL_FIELD_ADDED,
                    severity=ChangeSeverity.INFO,
                    path=f"service.{name}",
                    field_name=name,
                    message=f"Service '{name}' was added",
                )
            )

        # Compare RPCs in common services
        for name in old_services & new_services:
            old_rpcs = old_schema.services[name]
            new_rpcs = new_schema.services[name]

            old_rpc_names = set(old_rpcs.keys())
            new_rpc_names = set(new_rpcs.keys())

            # Removed RPCs (BREAKING)
            for rpc in old_rpc_names - new_rpc_names:
                result.changes.append(
                    SchemaChange(
                        change_type=ChangeType.FIELD_REMOVED,
                        severity=ChangeSeverity.BREAKING,
                        path=f"service.{name}.{rpc}",
                        field_name=rpc,
                        message=f"RPC '{rpc}' was removed from service '{name}'",
                    )
                )

            # Compare common RPCs
            for rpc in old_rpc_names & new_rpc_names:
                old_req, old_resp = old_rpcs[rpc]
                new_req, new_resp = new_rpcs[rpc]

                if old_req != new_req:
                    result.changes.append(
                        SchemaChange(
                            change_type=ChangeType.FIELD_TYPE_CHANGED,
                            severity=ChangeSeverity.BREAKING,
                            path=f"service.{name}.{rpc}.request",
                            field_name=rpc,
                            message=f"RPC '{rpc}' request type changed from '{old_req}' to '{new_req}'",
                            old_value=old_req,
                            new_value=new_req,
                        )
                    )

                if old_resp != new_resp:
                    result.changes.append(
                        SchemaChange(
                            change_type=ChangeType.FIELD_TYPE_CHANGED,
                            severity=ChangeSeverity.BREAKING,
                            path=f"service.{name}.{rpc}.response",
                            field_name=rpc,
                            message=f"RPC '{rpc}' response type changed from '{old_resp}' to '{new_resp}'",
                            old_value=old_resp,
                            new_value=new_resp,
                        )
                    )

    def compare_json_schema(
        self,
        old_schema: str | dict,
        new_schema: str | dict,
        old_version: str = "",
        new_version: str = "",
    ) -> SchemaDriftResult:
        """
        Compare two JSON Schemas for breaking changes.

        Args:
            old_schema: Old JSON Schema (string or dict)
            new_schema: New JSON Schema (string or dict)
            old_version: Version label for old schema
            new_version: Version label for new schema

        Returns:
            SchemaDriftResult with detected changes
        """
        result = SchemaDriftResult(
            old_version=old_version,
            new_version=new_version,
            schema_type="json_schema",
        )

        # Parse if strings
        if isinstance(old_schema, str):
            old_schema = json.loads(old_schema)
        if isinstance(new_schema, str):
            new_schema = json.loads(new_schema)

        # Cast to Dict after parsing to satisfy type checker
        old_schema = cast(dict[str, Any], old_schema)
        new_schema = cast(dict[str, Any], new_schema)

        # Compare schemas
        self._compare_json_schema_recursive(old_schema, new_schema, "#", result)

        return result

    def _compare_json_schema_recursive(
        self,
        old: dict[str, Any],
        new: dict[str, Any],
        path: str,
        result: SchemaDriftResult,
    ) -> None:
        """Recursively compare JSON Schema objects."""

        # Compare type
        old_type = old.get("type")
        new_type = new.get("type")

        if old_type != new_type and old_type is not None and new_type is not None:
            result.changes.append(
                SchemaChange(
                    change_type=ChangeType.FIELD_TYPE_CHANGED,
                    severity=ChangeSeverity.BREAKING,
                    path=path,
                    field_name=path.split("/")[-1],
                    message=f"Type changed from '{old_type}' to '{new_type}' at {path}",
                    old_value=old_type,
                    new_value=new_type,
                )
            )

        # Compare properties (for objects)
        old_props = old.get("properties", {})
        new_props = new.get("properties", {})
        old_required = set(old.get("required", []))
        new_required = set(new.get("required", []))

        old_prop_names = set(old_props.keys())
        new_prop_names = set(new_props.keys())

        # Removed properties (BREAKING)
        for prop in old_prop_names - new_prop_names:
            result.changes.append(
                SchemaChange(
                    change_type=ChangeType.FIELD_REMOVED,
                    severity=ChangeSeverity.BREAKING,
                    path=f"{path}/properties/{prop}",
                    field_name=prop,
                    message=f"Property '{prop}' was removed",
                )
            )

        # Added properties
        for prop in new_prop_names - old_prop_names:
            is_required = prop in new_required
            severity = ChangeSeverity.BREAKING if is_required else ChangeSeverity.INFO
            change_type = ChangeType.REQUIRED_FIELD_ADDED if is_required else ChangeType.OPTIONAL_FIELD_ADDED

            result.changes.append(
                SchemaChange(
                    change_type=change_type,
                    severity=severity,
                    path=f"{path}/properties/{prop}",
                    field_name=prop,
                    message=f"{'Required' if is_required else 'Optional'} property '{prop}' was added",
                )
            )

        # Compare common properties
        for prop in old_prop_names & new_prop_names:
            self._compare_json_schema_recursive(
                old_props[prop],
                new_props[prop],
                f"{path}/properties/{prop}",
                result,
            )

        # Check for new required fields (BREAKING)
        newly_required = new_required - old_required
        for prop in newly_required:
            if prop in old_prop_names:  # Existing field made required
                result.changes.append(
                    SchemaChange(
                        change_type=ChangeType.FIELD_MADE_REQUIRED,
                        severity=ChangeSeverity.BREAKING,
                        path=f"{path}/properties/{prop}",
                        field_name=prop,
                        message=f"Property '{prop}' was made required",
                    )
                )

        # Check for enum changes
        old_enum = old.get("enum", [])
        new_enum = new.get("enum", [])

        if old_enum or new_enum:
            old_enum_set = set(str(v) for v in old_enum)
            new_enum_set = set(str(v) for v in new_enum)

            # Removed enum values (BREAKING)
            for value in old_enum_set - new_enum_set:
                result.changes.append(
                    SchemaChange(
                        change_type=ChangeType.ENUM_VALUE_REMOVED,
                        severity=ChangeSeverity.BREAKING,
                        path=f"{path}/enum",
                        field_name="enum",
                        message=f"Enum value '{value}' was removed",
                        old_value=value,
                    )
                )

            # Added enum values (non-breaking)
            for value in new_enum_set - old_enum_set:
                result.changes.append(
                    SchemaChange(
                        change_type=ChangeType.ENUM_VALUE_ADDED,
                        severity=ChangeSeverity.INFO,
                        path=f"{path}/enum",
                        field_name="enum",
                        message=f"Enum value '{value}' was added",
                        new_value=value,
                    )
                )

        # Compare items (for arrays)
        if "items" in old and "items" in new:
            self._compare_json_schema_recursive(
                old["items"],
                new["items"],
                f"{path}/items",
                result,
            )


def compare_protobuf_files(
    old_path: str | Path,
    new_path: str | Path,
) -> SchemaDriftResult:
    """
    Convenience function to compare two .proto files.

    Args:
        old_path: Path to old .proto file
        new_path: Path to new .proto file

    Returns:
        SchemaDriftResult with detected changes
    """
    old_path = Path(old_path)
    new_path = Path(new_path)

    old_content = old_path.read_text()
    new_content = new_path.read_text()

    detector = SchemaDriftDetector()
    return detector.compare_protobuf(
        old_content,
        new_content,
        old_version=old_path.name,
        new_version=new_path.name,
    )


def compare_json_schema_files(
    old_path: str | Path,
    new_path: str | Path,
) -> SchemaDriftResult:
    """
    Convenience function to compare two JSON Schema files.

    Args:
        old_path: Path to old JSON Schema file
        new_path: Path to new JSON Schema file

    Returns:
        SchemaDriftResult with detected changes
    """
    old_path = Path(old_path)
    new_path = Path(new_path)

    old_content = json.loads(old_path.read_text())
    new_content = json.loads(new_path.read_text())

    detector = SchemaDriftDetector()
    return detector.compare_json_schema(
        old_content,
        new_content,
        old_version=old_path.name,
        new_version=new_path.name,
    )


# [20251225_FEATURE] Export public API for type checkers
__all__ = [
    "SchemaDriftDetector",
    "SchemaDriftResult",
    "SchemaChange",
    "ChangeType",
    "ChangeSeverity",
    "ProtobufParser",
    "compare_protobuf_files",
    "compare_json_schema_files",
]
