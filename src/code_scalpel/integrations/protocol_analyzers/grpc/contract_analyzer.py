"""
gRPC Contract Analyzer - Service Definition Analysis.

[20251219_FEATURE] v3.0.4 - Ninja Warrior Stage 3

This module analyzes gRPC service contracts defined in .proto files:
- Service and RPC method extraction
- Request/Response message analysis
- Streaming pattern detection (unary, server, client, bidirectional)
- Contract validation and best practice checks
- Breaking change detection between contract versions

Usage:
    analyzer = GrpcContractAnalyzer()

    # Analyze a single .proto file
    contract = analyzer.analyze(proto_content)
    print(f"Services: {[s.name for s in contract.services]}")

    # Validate contract for issues
    issues = analyzer.validate(contract)
    for issue in issues:
        print(f"[{issue.severity}] {issue.message}")

    # Compare two versions for breaking changes
    from .schema_drift_detector import SchemaDriftDetector
    detector = SchemaDriftDetector()
    drift = detector.compare_protobuf(old_proto, new_proto)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# [20251225_REFACTOR] Updated import path after protocol_analyzers reorganization
from ..schema.drift_detector import (
    ProtobufEnum,
    ProtobufMessage,
    ProtobufParser,
    SchemaDriftDetector,
    SchemaDriftResult,
)


class StreamingType(Enum):
    """gRPC streaming patterns."""

    UNARY = "unary"  # Single request, single response
    SERVER_STREAMING = "server_stream"  # Single request, stream response
    CLIENT_STREAMING = "client_stream"  # Stream request, single response
    BIDIRECTIONAL = "bidi_stream"  # Stream request, stream response


class IssueSeverity(Enum):
    """Severity of contract issues."""

    ERROR = "ERROR"  # Must fix - will break clients
    WARNING = "WARNING"  # Should fix - potential problems
    INFO = "INFO"  # Best practice suggestion


@dataclass
class RpcMethod:
    """Represents a gRPC RPC method."""

    name: str
    request_type: str
    response_type: str
    client_streaming: bool = False
    server_streaming: bool = False
    deprecated: bool = False
    options: dict[str, Any] = field(default_factory=dict)

    @property
    def streaming_type(self) -> StreamingType:
        """Get the streaming pattern for this RPC."""
        if self.client_streaming and self.server_streaming:
            return StreamingType.BIDIRECTIONAL
        elif self.server_streaming:
            return StreamingType.SERVER_STREAMING
        elif self.client_streaming:
            return StreamingType.CLIENT_STREAMING
        else:
            return StreamingType.UNARY

    @property
    def full_signature(self) -> str:
        """Get the full RPC signature."""
        req = f"stream {self.request_type}" if self.client_streaming else self.request_type
        resp = f"stream {self.response_type}" if self.server_streaming else self.response_type
        return f"rpc {self.name}({req}) returns ({resp})"


@dataclass
class GrpcService:
    """Represents a gRPC service definition."""

    name: str
    methods: dict[str, RpcMethod] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)
    deprecated: bool = False

    @property
    def method_count(self) -> int:
        """Number of RPC methods."""
        return len(self.methods)

    @property
    def streaming_methods(self) -> list[RpcMethod]:
        """Get all streaming methods."""
        return [m for m in self.methods.values() if m.streaming_type != StreamingType.UNARY]

    @property
    def unary_methods(self) -> list[RpcMethod]:
        """Get all unary methods."""
        return [m for m in self.methods.values() if m.streaming_type == StreamingType.UNARY]


@dataclass
class GrpcContract:
    """
    Represents a complete gRPC contract from a .proto file.

    Contains all information needed to understand the API surface.
    """

    # File metadata
    syntax: str = "proto3"
    package: str = ""
    imports: list[str] = field(default_factory=list)
    options: dict[str, Any] = field(default_factory=dict)

    # Service definitions
    services: list[GrpcService] = field(default_factory=list)

    # Message definitions
    messages: dict[str, ProtobufMessage] = field(default_factory=dict)

    # Enum definitions
    enums: dict[str, ProtobufEnum] = field(default_factory=dict)

    # Source file (if known)
    source_file: str | None = None

    @property
    def service_count(self) -> int:
        """Number of services defined."""
        return len(self.services)

    @property
    def total_rpc_count(self) -> int:
        """Total number of RPC methods across all services."""
        return sum(s.method_count for s in self.services)

    @property
    def all_message_types(self) -> set[str]:
        """Get all message type names used in the contract."""
        types = set(self.messages.keys())
        for service in self.services:
            for method in service.methods.values():
                types.add(method.request_type)
                types.add(method.response_type)
        return types

    def get_service(self, name: str) -> GrpcService | None:
        """Get a service by name."""
        for service in self.services:
            if service.name == name:
                return service
        return None

    def get_message(self, name: str) -> ProtobufMessage | None:
        """Get a message by name."""
        return self.messages.get(name)

    def summary(self) -> str:
        """Generate a human-readable summary."""
        lines = [
            f"gRPC Contract: {self.package or '(no package)'}",
            f"Syntax: {self.syntax}",
            f"Services: {self.service_count}",
            f"Total RPCs: {self.total_rpc_count}",
            f"Messages: {len(self.messages)}",
            f"Enums: {len(self.enums)}",
        ]

        if self.services:
            lines.append("\nServices:")
            for service in self.services:
                lines.append(f"  {service.name}:")
                for method in service.methods.values():
                    streaming = (
                        f" [{method.streaming_type.value}]" if method.streaming_type != StreamingType.UNARY else ""
                    )
                    lines.append(f"    - {method.name}({method.request_type}) → {method.response_type}{streaming}")

        return "\n".join(lines)


@dataclass
class ContractIssue:
    """Represents an issue found during contract validation."""

    severity: IssueSeverity
    code: str
    message: str
    location: str = ""  # e.g., "UserService.GetUser"
    suggestion: str = ""

    def __str__(self) -> str:
        loc = f" at {self.location}" if self.location else ""
        return f"[{self.severity.value}] {self.code}{loc}: {self.message}"


class GrpcContractAnalyzer:
    """
    Analyzes gRPC service contracts from .proto files.

    [20251219_FEATURE] v3.0.4 - gRPC Contract Analysis

    Features:
    - Parse .proto files to extract service definitions
    - Analyze RPC methods, request/response types
    - Detect streaming patterns (unary, server, client, bidi)
    - Validate contracts for common issues
    - Compare contracts for breaking changes

    Usage:
        analyzer = GrpcContractAnalyzer()
        contract = analyzer.analyze(proto_content)

        # Get all services
        for service in contract.services:
            print(f"Service: {service.name}")
            for method in service.methods.values():
                print(f"  RPC: {method.full_signature}")

        # Validate for issues
        issues = analyzer.validate(contract)
        for issue in issues:
            print(issue)
    """

    # Extended regex patterns for gRPC-specific parsing
    IMPORT_PATTERN = re.compile(r'import\s+["\']([^"\']+)["\']')
    OPTION_PATTERN = re.compile(r'option\s+(\w+)\s*=\s*["\']?([^"\';\s]+)["\']?\s*;')
    SERVICE_PATTERN = re.compile(r"service\s+(\w+)\s*\{")
    RPC_PATTERN = re.compile(r"rpc\s+(\w+)\s*\(\s*(stream\s+)?([\w.]+)\s*\)\s*returns\s*\(\s*(stream\s+)?([\w.]+)\s*\)")
    DEPRECATED_PATTERN = re.compile(r"\[deprecated\s*=\s*true\]", re.IGNORECASE)

    def __init__(self) -> None:
        """Initialize the analyzer."""
        self._proto_parser = ProtobufParser()
        self._drift_detector = SchemaDriftDetector()

    def analyze(self, proto_content: str, source_file: str | None = None) -> GrpcContract:
        """
        Analyze a .proto file and extract the gRPC contract.

        Args:
            proto_content: Content of the .proto file
            source_file: Optional source file path for reference

        Returns:
            GrpcContract with all extracted information
        """
        # Use the base parser for messages/enums
        base_schema = self._proto_parser.parse(proto_content)

        # Remove comments for cleaner parsing
        clean_content = self._remove_comments(proto_content)

        # Create contract from base schema
        contract = GrpcContract(
            syntax=base_schema.syntax,
            package=base_schema.package,
            messages=base_schema.messages,
            enums=base_schema.enums,
            source_file=source_file,
        )

        # Parse imports
        contract.imports = self._parse_imports(clean_content)

        # Parse file-level options
        contract.options = self._parse_options(clean_content)

        # Parse services with full RPC details
        contract.services = self._parse_services(clean_content)

        return contract

    def analyze_file(self, proto_path: str | Path) -> GrpcContract:
        """
        Analyze a .proto file from disk.

        Args:
            proto_path: Path to the .proto file

        Returns:
            GrpcContract with all extracted information
        """
        path = Path(proto_path)
        content = path.read_text()
        return self.analyze(content, source_file=str(path))

    def validate(self, contract: GrpcContract) -> list[ContractIssue]:
        """
        Validate a contract for common issues and best practices.

        Args:
            contract: The contract to validate

        Returns:
            List of ContractIssue objects
        """
        issues: list[ContractIssue] = []

        # Check for missing package
        if not contract.package:
            issues.append(
                ContractIssue(
                    severity=IssueSeverity.WARNING,
                    code="GRPC001",
                    message="No package defined - may cause naming conflicts",
                    suggestion="Add 'package your.service.name;' to the .proto file",
                )
            )

        # Check for proto3 syntax
        if contract.syntax != "proto3":
            issues.append(
                ContractIssue(
                    severity=IssueSeverity.INFO,
                    code="GRPC002",
                    message=f"Using {contract.syntax} syntax - proto3 is recommended",
                    suggestion="Consider migrating to proto3 for better defaults",
                )
            )

        # Check each service
        for service in contract.services:
            issues.extend(self._validate_service(service, contract))

        # Check for unused messages
        used_messages = set()
        for service in contract.services:
            for method in service.methods.values():
                used_messages.add(method.request_type)
                used_messages.add(method.response_type)

        # Add messages referenced in other messages
        for msg in contract.messages.values():
            for msg_field in msg.fields.values():
                if msg_field.type in contract.messages:
                    used_messages.add(msg_field.type)

        unused = set(contract.messages.keys()) - used_messages
        for msg_name in unused:
            issues.append(
                ContractIssue(
                    severity=IssueSeverity.INFO,
                    code="GRPC010",
                    message=f"Message '{msg_name}' is not used by any RPC method",
                    location=msg_name,
                    suggestion="Consider removing unused messages or marking as reserved",
                )
            )

        return issues

    def _validate_service(self, service: GrpcService, contract: GrpcContract) -> list[ContractIssue]:
        """Validate a single service."""
        issues: list[ContractIssue] = []

        # Check for empty service
        if not service.methods:
            issues.append(
                ContractIssue(
                    severity=IssueSeverity.WARNING,
                    code="GRPC003",
                    message=f"Service '{service.name}' has no RPC methods",
                    location=service.name,
                )
            )

        # Check each RPC method
        for method in service.methods.values():
            location = f"{service.name}.{method.name}"

            # Check if request/response types exist
            if method.request_type not in contract.messages:
                # Check if it's a well-known type
                if not self._is_well_known_type(method.request_type):
                    issues.append(
                        ContractIssue(
                            severity=IssueSeverity.ERROR,
                            code="GRPC004",
                            message=f"Request type '{method.request_type}' not found in contract",
                            location=location,
                            suggestion=f"Define message {method.request_type} or check for typos",
                        )
                    )

            if method.response_type not in contract.messages:
                if not self._is_well_known_type(method.response_type):
                    issues.append(
                        ContractIssue(
                            severity=IssueSeverity.ERROR,
                            code="GRPC005",
                            message=f"Response type '{method.response_type}' not found in contract",
                            location=location,
                            suggestion=f"Define message {method.response_type} or check for typos",
                        )
                    )

            # Check for generic request/response names
            if method.request_type.lower() in ("request", "req"):
                issues.append(
                    ContractIssue(
                        severity=IssueSeverity.WARNING,
                        code="GRPC006",
                        message="Generic request type name - use descriptive names",
                        location=location,
                        suggestion=f"Rename to {method.name}Request",
                    )
                )

            if method.response_type.lower() in ("response", "resp"):
                issues.append(
                    ContractIssue(
                        severity=IssueSeverity.WARNING,
                        code="GRPC007",
                        message="Generic response type name - use descriptive names",
                        location=location,
                        suggestion=f"Rename to {method.name}Response",
                    )
                )

            # Check naming conventions
            if not method.name[0].isupper():
                issues.append(
                    ContractIssue(
                        severity=IssueSeverity.INFO,
                        code="GRPC008",
                        message="RPC method names should start with uppercase (PascalCase)",
                        location=location,
                    )
                )

            # Warn about deprecated methods
            if method.deprecated:
                issues.append(
                    ContractIssue(
                        severity=IssueSeverity.INFO,
                        code="GRPC009",
                        message=f"RPC method '{method.name}' is deprecated",
                        location=location,
                    )
                )

        return issues

    def _is_well_known_type(self, type_name: str) -> bool:
        """Check if a type is a Protobuf well-known type."""
        well_known = {
            # Wrappers
            "google.protobuf.DoubleValue",
            "google.protobuf.FloatValue",
            "google.protobuf.Int64Value",
            "google.protobuf.UInt64Value",
            "google.protobuf.Int32Value",
            "google.protobuf.UInt32Value",
            "google.protobuf.BoolValue",
            "google.protobuf.StringValue",
            "google.protobuf.BytesValue",
            # Common types
            "google.protobuf.Any",
            "google.protobuf.Empty",
            "google.protobuf.Timestamp",
            "google.protobuf.Duration",
            "google.protobuf.Struct",
            "google.protobuf.Value",
            "google.protobuf.ListValue",
            "google.protobuf.FieldMask",
            # Simple names (without package)
            "Empty",
            "Any",
            "Timestamp",
            "Duration",
        }
        return type_name in well_known

    def compare_contracts(
        self,
        old_contract: GrpcContract,
        new_contract: GrpcContract,
    ) -> SchemaDriftResult:
        """
        Compare two contracts for breaking changes.

        This is a convenience wrapper around SchemaDriftDetector.
        For detailed drift analysis, use SchemaDriftDetector directly.

        Args:
            old_contract: Previous version of the contract
            new_contract: New version of the contract

        Returns:
            SchemaDriftResult with detected changes
        """
        # Reconstruct proto content for comparison
        # This is a simplified approach - for full fidelity, compare raw .proto files
        old_proto = self._contract_to_proto(old_contract)
        new_proto = self._contract_to_proto(new_contract)

        return self._drift_detector.compare_protobuf(
            old_proto,
            new_proto,
            old_version=old_contract.source_file or "old",
            new_version=new_contract.source_file or "new",
        )

    def _contract_to_proto(self, contract: GrpcContract) -> str:
        """Convert a contract back to proto format for comparison."""
        lines = [f'syntax = "{contract.syntax}";']

        if contract.package:
            lines.append(f"package {contract.package};")

        lines.append("")

        # Messages
        for msg in contract.messages.values():
            lines.append(f"message {msg.name} {{")
            for msg_field in msg.fields.values():
                lines.append(f"  {msg_field.type} {msg_field.name} = {msg_field.number};")
            lines.append("}")
            lines.append("")

        # Services
        for service in contract.services:
            lines.append(f"service {service.name} {{")
            for method in service.methods.values():
                req = f"stream {method.request_type}" if method.client_streaming else method.request_type
                resp = f"stream {method.response_type}" if method.server_streaming else method.response_type
                lines.append(f"  rpc {method.name}({req}) returns ({resp});")
            lines.append("}")

        return "\n".join(lines)

    def _remove_comments(self, content: str) -> str:
        """Remove single-line and multi-line comments."""
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)
        return content

    def _parse_imports(self, content: str) -> list[str]:
        """Parse import statements."""
        return self.IMPORT_PATTERN.findall(content)

    def _parse_options(self, content: str) -> dict[str, Any]:
        """Parse file-level options."""
        options = {}
        for match in self.OPTION_PATTERN.finditer(content):
            name = match.group(1)
            value = match.group(2)
            options[name] = value
        return options

    def _parse_services(self, content: str) -> list[GrpcService]:
        """Parse all service definitions with full RPC details."""
        services: list[GrpcService] = []

        for match in self.SERVICE_PATTERN.finditer(content):
            service_name = match.group(1)
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

            service_body = content[start : end - 1]
            service = self._parse_service_body(service_name, service_body)
            services.append(service)

        return services

    def _parse_service_body(self, name: str, body: str) -> GrpcService:
        """Parse the body of a service definition."""
        service = GrpcService(name=name)

        # Check for deprecated service
        if self.DEPRECATED_PATTERN.search(body):
            service.deprecated = True

        # Parse RPC methods
        for match in self.RPC_PATTERN.finditer(body):
            method_name = match.group(1)
            client_streaming = match.group(2) is not None
            request_type = match.group(3)
            server_streaming = match.group(4) is not None
            response_type = match.group(5)

            # Check if this specific method is deprecated
            # Look for deprecated option near this RPC
            method_start = match.start()
            method_section = body[max(0, method_start - 50) : match.end() + 50]
            deprecated = bool(self.DEPRECATED_PATTERN.search(method_section))

            method = RpcMethod(
                name=method_name,
                request_type=request_type,
                response_type=response_type,
                client_streaming=client_streaming,
                server_streaming=server_streaming,
                deprecated=deprecated,
            )

            service.methods[method_name] = method

        return service

    def get_streaming_stats(self, contract: GrpcContract) -> dict[str, int]:
        """
        Get statistics about streaming patterns in a contract.

        Returns:
            Dict with counts for each streaming type
        """
        stats = {
            StreamingType.UNARY.value: 0,
            StreamingType.SERVER_STREAMING.value: 0,
            StreamingType.CLIENT_STREAMING.value: 0,
            StreamingType.BIDIRECTIONAL.value: 0,
        }

        for service in contract.services:
            for method in service.methods.values():
                stats[method.streaming_type.value] += 1

        return stats

    def extract_dependencies(self, contract: GrpcContract) -> dict[str, set[str]]:
        """
        Extract message dependencies for each RPC method.

        Returns:
            Dict mapping RPC names to their dependent message types
        """
        dependencies: dict[str, set[str]] = {}

        for service in contract.services:
            for method in service.methods.values():
                key = f"{service.name}.{method.name}"
                deps = {method.request_type, method.response_type}

                # Recursively find nested dependencies
                self._collect_message_deps(method.request_type, contract, deps)
                self._collect_message_deps(method.response_type, contract, deps)

                dependencies[key] = deps

        return dependencies

    def _collect_message_deps(
        self,
        msg_name: str,
        contract: GrpcContract,
        deps: set[str],
    ) -> None:
        """Recursively collect message dependencies."""
        if msg_name not in contract.messages:
            return

        msg = contract.messages[msg_name]
        for msg_field in msg.fields.values():
            if msg_field.type in contract.messages and msg_field.type not in deps:
                deps.add(msg_field.type)
                self._collect_message_deps(msg_field.type, contract, deps)


def analyze_grpc_contract(proto_content: str) -> GrpcContract:
    """
    Convenience function to analyze a .proto file.

    Args:
        proto_content: Content of the .proto file

    Returns:
        GrpcContract with all extracted information
    """
    analyzer = GrpcContractAnalyzer()
    return analyzer.analyze(proto_content)


def validate_grpc_contract(proto_content: str) -> list[ContractIssue]:
    """
    Convenience function to validate a .proto file.

    Args:
        proto_content: Content of the .proto file

    Returns:
        List of validation issues
    """
    analyzer = GrpcContractAnalyzer()
    contract = analyzer.analyze(proto_content)
    return analyzer.validate(contract)


def analyze_grpc_file(proto_path: str | Path) -> GrpcContract:
    """
    Convenience function to analyze a .proto file from disk.

    Args:
        proto_path: Path to the .proto file

    Returns:
        GrpcContract with all extracted information
    """
    analyzer = GrpcContractAnalyzer()
    return analyzer.analyze_file(proto_path)


# [20251225_FEATURE] Export public API for type checkers
__all__ = [
    "GrpcContractAnalyzer",
    "GrpcContract",
    "GrpcService",
    "RpcMethod",
    "StreamingType",
    "ContractIssue",
    "IssueSeverity",
    "analyze_grpc_contract",
    "validate_grpc_contract",
    "analyze_grpc_file",
]
