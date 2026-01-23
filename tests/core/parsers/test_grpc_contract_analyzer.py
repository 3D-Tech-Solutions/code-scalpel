"""
Tests for gRPC Contract Analyzer.

[20251219_FEATURE] v3.0.4 - Ninja Warrior Stage 3 Tests
"""

import pytest

from code_scalpel.integrations.protocol_analyzers.grpc.contract_analyzer import (
    GrpcContractAnalyzer,
    IssueSeverity,
    RpcMethod,
    StreamingType,
    analyze_grpc_contract,
    validate_grpc_contract,
)

# =============================================================================
# TEST FIXTURES
# =============================================================================

SIMPLE_PROTO = """
syntax = "proto3";

package example.api.v1;

import "google/protobuf/empty.proto";
import "google/protobuf/timestamp.proto";

option java_package = "com.example.api.v1";
option go_package = "github.com/example/api/v1";

// User management service
service UserService {
    // Get a user by ID
    rpc GetUser(GetUserRequest) returns (GetUserResponse);

    // Create a new user
    rpc CreateUser(CreateUserRequest) returns (CreateUserResponse);

    // Delete a user
    rpc DeleteUser(DeleteUserRequest) returns (google.protobuf.Empty);

    // List all users with server streaming
    rpc ListUsers(ListUsersRequest) returns (stream User);

    // Bulk create with client streaming
    rpc BulkCreateUsers(stream CreateUserRequest) returns (BulkCreateResponse);

    // Chat with bidirectional streaming
    rpc Chat(stream ChatMessage) returns (stream ChatMessage);
}

message User {
    string id = 1;
    string email = 2;
    string name = 3;
    UserStatus status = 4;
}

enum UserStatus {
    USER_STATUS_UNKNOWN = 0;
    USER_STATUS_ACTIVE = 1;
    USER_STATUS_INACTIVE = 2;
}

message GetUserRequest {
    string user_id = 1;
}

message GetUserResponse {
    User user = 1;
}

message CreateUserRequest {
    string email = 1;
    string name = 2;
}

message CreateUserResponse {
    User user = 1;
}

message DeleteUserRequest {
    string user_id = 1;
}

message ListUsersRequest {
    int32 page_size = 1;
    string page_token = 2;
}

message BulkCreateResponse {
    int32 created_count = 1;
    repeated string user_ids = 2;
}

message ChatMessage {
    string sender_id = 1;
    string content = 2;
}
"""

PROTO_WITH_ISSUES = """
syntax = "proto2";

// No package defined

service EmptyService {
    // No methods
}

service BadNamingService {
    rpc getUser(Request) returns (Response);
    rpc CreateUser(UnknownRequest) returns (UnknownResponse);
}

message Request {
    string id = 1;
}

message Response {
    string data = 1;
}

message UnusedMessage {
    string unused = 1;
}
"""

DEPRECATED_PROTO = """
syntax = "proto3";

package deprecated.api;

service LegacyService {
    rpc OldMethod(OldRequest) returns (OldResponse) [deprecated = true];
    rpc NewMethod(NewRequest) returns (NewResponse);
}

message OldRequest {
    string id = 1;
}

message OldResponse {
    string data = 1;
}

message NewRequest {
    string id = 1;
}

message NewResponse {
    string data = 1;
}
"""


# =============================================================================
# BASIC PARSING TESTS
# =============================================================================


class TestGrpcContractAnalyzer:
    """Tests for GrpcContractAnalyzer parsing."""

    def test_parse_syntax(self):
        """Test parsing syntax declaration."""
        analyzer = GrpcContractAnalyzer()
        contract = analyzer.analyze(SIMPLE_PROTO)
        assert contract.syntax == "proto3"

    def test_parse_package(self):
        """Test parsing package declaration."""
        analyzer = GrpcContractAnalyzer()
        contract = analyzer.analyze(SIMPLE_PROTO)
        assert contract.package == "example.api.v1"

    def test_parse_imports(self):
        """Test parsing import statements."""
        analyzer = GrpcContractAnalyzer()
        contract = analyzer.analyze(SIMPLE_PROTO)
        assert "google/protobuf/empty.proto" in contract.imports
        assert "google/protobuf/timestamp.proto" in contract.imports

    def test_parse_options(self):
        """Test parsing file-level options."""
        analyzer = GrpcContractAnalyzer()
        contract = analyzer.analyze(SIMPLE_PROTO)
        assert "java_package" in contract.options
        assert contract.options["java_package"] == "com.example.api.v1"

    def test_parse_services(self):
        """Test parsing service definitions."""
        analyzer = GrpcContractAnalyzer()
        contract = analyzer.analyze(SIMPLE_PROTO)

        assert contract.service_count == 1
        assert contract.services[0].name == "UserService"

    def test_parse_rpc_methods(self):
        """Test parsing RPC method definitions."""
        analyzer = GrpcContractAnalyzer()
        contract = analyzer.analyze(SIMPLE_PROTO)

        service = contract.get_service("UserService")
        assert service is not None
        assert "GetUser" in service.methods
        assert "CreateUser" in service.methods
        assert "DeleteUser" in service.methods

        get_user = service.methods["GetUser"]
        assert get_user.request_type == "GetUserRequest"
        assert get_user.response_type == "GetUserResponse"

    def test_parse_messages(self):
        """Test parsing message definitions."""
        analyzer = GrpcContractAnalyzer()
        contract = analyzer.analyze(SIMPLE_PROTO)

        assert "User" in contract.messages
        assert "GetUserRequest" in contract.messages

        user = contract.messages["User"]
        assert "id" in user.fields
        assert "email" in user.fields

    def test_parse_enums(self):
        """Test parsing enum definitions."""
        analyzer = GrpcContractAnalyzer()
        contract = analyzer.analyze(SIMPLE_PROTO)

        assert "UserStatus" in contract.enums
        user_status = contract.enums["UserStatus"]
        assert "USER_STATUS_ACTIVE" in user_status.values


# =============================================================================
# STREAMING PATTERN TESTS
# =============================================================================


class TestStreamingPatterns:
    """Tests for streaming pattern detection."""

    def test_unary_rpc(self):
        """Test detection of unary RPC."""
        analyzer = GrpcContractAnalyzer()
        contract = analyzer.analyze(SIMPLE_PROTO)

        service = contract.get_service("UserService")
        get_user = service.methods["GetUser"]

        assert get_user.streaming_type == StreamingType.UNARY
        assert not get_user.client_streaming
        assert not get_user.server_streaming

    def test_server_streaming_rpc(self):
        """Test detection of server streaming RPC."""
        analyzer = GrpcContractAnalyzer()
        contract = analyzer.analyze(SIMPLE_PROTO)

        service = contract.get_service("UserService")
        list_users = service.methods["ListUsers"]

        assert list_users.streaming_type == StreamingType.SERVER_STREAMING
        assert not list_users.client_streaming
        assert list_users.server_streaming

    def test_client_streaming_rpc(self):
        """Test detection of client streaming RPC."""
        analyzer = GrpcContractAnalyzer()
        contract = analyzer.analyze(SIMPLE_PROTO)

        service = contract.get_service("UserService")
        bulk_create = service.methods["BulkCreateUsers"]

        assert bulk_create.streaming_type == StreamingType.CLIENT_STREAMING
        assert bulk_create.client_streaming
        assert not bulk_create.server_streaming

    def test_bidirectional_streaming_rpc(self):
        """Test detection of bidirectional streaming RPC."""
        analyzer = GrpcContractAnalyzer()
        contract = analyzer.analyze(SIMPLE_PROTO)

        service = contract.get_service("UserService")
        chat = service.methods["Chat"]

        assert chat.streaming_type == StreamingType.BIDIRECTIONAL
        assert chat.client_streaming
        assert chat.server_streaming

    def test_streaming_stats(self):
        """Test streaming statistics calculation."""
        analyzer = GrpcContractAnalyzer()
        contract = analyzer.analyze(SIMPLE_PROTO)

        stats = analyzer.get_streaming_stats(contract)

        assert stats["unary"] == 3  # GetUser, CreateUser, DeleteUser
        assert stats["server_stream"] == 1  # ListUsers
        assert stats["client_stream"] == 1  # BulkCreateUsers
        assert stats["bidi_stream"] == 1  # Chat


# =============================================================================
# VALIDATION TESTS
# =============================================================================


class TestContractValidation:
    """Tests for contract validation."""

    def test_validate_good_contract(self):
        """Test validation of a well-formed contract."""
        analyzer = GrpcContractAnalyzer()
        contract = analyzer.analyze(SIMPLE_PROTO)
        issues = analyzer.validate(contract)

        # Should have few or no issues for a well-formed contract
        errors = [i for i in issues if i.severity == IssueSeverity.ERROR]
        assert len(errors) == 0

    def test_detect_missing_package(self):
        """Test detection of missing package."""
        issues = validate_grpc_contract(PROTO_WITH_ISSUES)

        package_issues = [i for i in issues if i.code == "GRPC001"]
        assert len(package_issues) == 1
        assert "No package" in package_issues[0].message

    def test_detect_proto2_syntax(self):
        """Test detection of proto2 syntax."""
        issues = validate_grpc_contract(PROTO_WITH_ISSUES)

        syntax_issues = [i for i in issues if i.code == "GRPC002"]
        assert len(syntax_issues) == 1
        assert "proto2" in syntax_issues[0].message

    def test_detect_empty_service(self):
        """Test detection of empty service."""
        issues = validate_grpc_contract(PROTO_WITH_ISSUES)

        empty_issues = [i for i in issues if i.code == "GRPC003"]
        assert len(empty_issues) == 1
        assert "EmptyService" in empty_issues[0].location

    def test_detect_missing_request_type(self):
        """Test detection of undefined request type."""
        issues = validate_grpc_contract(PROTO_WITH_ISSUES)

        missing_req = [i for i in issues if i.code == "GRPC004"]
        assert len(missing_req) >= 1
        assert any("UnknownRequest" in i.message for i in missing_req)

    def test_detect_missing_response_type(self):
        """Test detection of undefined response type."""
        issues = validate_grpc_contract(PROTO_WITH_ISSUES)

        missing_resp = [i for i in issues if i.code == "GRPC005"]
        assert len(missing_resp) >= 1
        assert any("UnknownResponse" in i.message for i in missing_resp)

    def test_detect_generic_type_names(self):
        """Test detection of generic type names."""
        issues = validate_grpc_contract(PROTO_WITH_ISSUES)

        generic_req = [i for i in issues if i.code == "GRPC006"]
        generic_resp = [i for i in issues if i.code == "GRPC007"]

        assert len(generic_req) >= 1
        assert len(generic_resp) >= 1

    def test_detect_naming_convention_violation(self):
        """Test detection of naming convention violations."""
        issues = validate_grpc_contract(PROTO_WITH_ISSUES)

        naming_issues = [i for i in issues if i.code == "GRPC008"]
        assert len(naming_issues) >= 1
        assert any("getUser" in i.location for i in naming_issues)

    def test_detect_deprecated_method(self):
        """Test detection of deprecated methods."""
        issues = validate_grpc_contract(DEPRECATED_PROTO)

        deprecated_issues = [i for i in issues if i.code == "GRPC009"]
        assert len(deprecated_issues) >= 1
        assert any("OldMethod" in i.message for i in deprecated_issues)

    def test_detect_unused_messages(self):
        """Test detection of unused messages."""
        issues = validate_grpc_contract(PROTO_WITH_ISSUES)

        unused_issues = [i for i in issues if i.code == "GRPC010"]
        assert len(unused_issues) >= 1
        assert any("UnusedMessage" in i.location for i in unused_issues)


# =============================================================================
# RPC METHOD TESTS
# =============================================================================


class TestRpcMethod:
    """Tests for RpcMethod class."""

    def test_full_signature_unary(self):
        """Test full signature for unary RPC."""
        method = RpcMethod(
            name="GetUser",
            request_type="GetUserRequest",
            response_type="GetUserResponse",
        )

        assert method.full_signature == "rpc GetUser(GetUserRequest) returns (GetUserResponse)"

    def test_full_signature_server_streaming(self):
        """Test full signature for server streaming RPC."""
        method = RpcMethod(
            name="ListUsers",
            request_type="ListUsersRequest",
            response_type="User",
            server_streaming=True,
        )

        assert method.full_signature == "rpc ListUsers(ListUsersRequest) returns (stream User)"

    def test_full_signature_client_streaming(self):
        """Test full signature for client streaming RPC."""
        method = RpcMethod(
            name="BulkCreate",
            request_type="CreateRequest",
            response_type="BulkResponse",
            client_streaming=True,
        )

        assert method.full_signature == "rpc BulkCreate(stream CreateRequest) returns (BulkResponse)"

    def test_full_signature_bidirectional(self):
        """Test full signature for bidirectional streaming RPC."""
        method = RpcMethod(
            name="Chat",
            request_type="ChatMessage",
            response_type="ChatMessage",
            client_streaming=True,
            server_streaming=True,
        )

        assert method.full_signature == "rpc Chat(stream ChatMessage) returns (stream ChatMessage)"


# =============================================================================
# CONTRACT TESTS
# =============================================================================


class TestGrpcContract:
    """Tests for GrpcContract class."""

    def test_service_count(self):
        """Test service count property."""
        contract = analyze_grpc_contract(SIMPLE_PROTO)
        assert contract.service_count == 1

    def test_total_rpc_count(self):
        """Test total RPC count property."""
        contract = analyze_grpc_contract(SIMPLE_PROTO)
        assert contract.total_rpc_count == 6

    def test_all_message_types(self):
        """Test all_message_types property."""
        contract = analyze_grpc_contract(SIMPLE_PROTO)
        types = contract.all_message_types

        assert "User" in types
        assert "GetUserRequest" in types
        assert "GetUserResponse" in types

    def test_get_service(self):
        """Test get_service method."""
        contract = analyze_grpc_contract(SIMPLE_PROTO)

        service = contract.get_service("UserService")
        assert service is not None
        assert service.name == "UserService"

        assert contract.get_service("NonExistent") is None

    def test_get_message(self):
        """Test get_message method."""
        contract = analyze_grpc_contract(SIMPLE_PROTO)

        user = contract.get_message("User")
        assert user is not None
        assert user.name == "User"

        assert contract.get_message("NonExistent") is None

    def test_summary(self):
        """Test summary generation."""
        contract = analyze_grpc_contract(SIMPLE_PROTO)
        summary = contract.summary()

        assert "example.api.v1" in summary
        assert "UserService" in summary
        assert "GetUser" in summary
        assert "proto3" in summary


# =============================================================================
# DEPENDENCY ANALYSIS TESTS
# =============================================================================


class TestDependencyAnalysis:
    """Tests for dependency analysis."""

    def test_extract_dependencies(self):
        """Test extracting message dependencies."""
        analyzer = GrpcContractAnalyzer()
        contract = analyzer.analyze(SIMPLE_PROTO)

        deps = analyzer.extract_dependencies(contract)

        # GetUser depends on GetUserRequest, GetUserResponse, and User (nested in response)
        get_user_deps = deps.get("UserService.GetUser", set())
        assert "GetUserRequest" in get_user_deps
        assert "GetUserResponse" in get_user_deps
        assert "User" in get_user_deps


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestIntegration:
    """Integration tests."""

    def test_full_analysis_workflow(self):
        """Test complete analysis workflow."""
        analyzer = GrpcContractAnalyzer()

        # Analyze contract
        contract = analyzer.analyze(SIMPLE_PROTO)

        # Validate
        issues = analyzer.validate(contract)

        # Get streaming stats
        stats = analyzer.get_streaming_stats(contract)

        # Get dependencies
        deps = analyzer.extract_dependencies(contract)

        # All should work without errors
        assert contract.service_count == 1
        assert len(issues) == 0 or all(i.severity != IssueSeverity.ERROR for i in issues)
        assert sum(stats.values()) == 6
        assert len(deps) == 6

    def test_convenience_functions(self):
        """Test convenience functions."""
        contract = analyze_grpc_contract(SIMPLE_PROTO)
        assert contract.service_count == 1

        issues = validate_grpc_contract(PROTO_WITH_ISSUES)
        assert len(issues) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
