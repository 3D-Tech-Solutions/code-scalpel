"""
Tests for Schema Drift Detector.

[20251219_FEATURE] v3.0.4 - Ninja Warrior Stage 3 Tests
"""

import json

import pytest

from code_scalpel.integrations.protocol_analyzers.schema import (
    ChangeType,
    ProtobufParser,
    SchemaDriftDetector,
)

# =============================================================================
# PROTOBUF TEST FIXTURES
# =============================================================================

OLD_PROTO = """
syntax = "proto3";

package example.api.v1;

// User service for managing users
service UserService {
    rpc GetUser(GetUserRequest) returns (GetUserResponse);
    rpc CreateUser(CreateUserRequest) returns (CreateUserResponse);
    rpc DeleteUser(DeleteUserRequest) returns (DeleteUserResponse);
}

enum UserStatus {
    USER_STATUS_UNKNOWN = 0;
    USER_STATUS_ACTIVE = 1;
    USER_STATUS_INACTIVE = 2;
    USER_STATUS_SUSPENDED = 3;
}

message User {
    string id = 1;
    string email = 2;
    string name = 3;
    UserStatus status = 4;
    int64 created_at = 5;
    optional string phone = 6;
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
    optional string phone = 3;
}

message CreateUserResponse {
    User user = 1;
}

message DeleteUserRequest {
    string user_id = 1;
}

message DeleteUserResponse {
    bool success = 1;
}
"""

NEW_PROTO_BREAKING = """
syntax = "proto3";

package example.api.v2;

// User service for managing users - MODIFIED
service UserService {
    rpc GetUser(GetUserRequest) returns (GetUserResponse);
    rpc CreateUser(CreateUserRequest) returns (CreateUserResponse);
    // DeleteUser RPC removed - BREAKING
}

enum UserStatus {
    USER_STATUS_UNKNOWN = 0;
    USER_STATUS_ACTIVE = 1;
    // USER_STATUS_INACTIVE removed - BREAKING
    USER_STATUS_SUSPENDED = 3;
    USER_STATUS_BANNED = 4;  // New value - non-breaking
}

message User {
    string id = 1;
    string email = 2;
    // name field removed - BREAKING
    UserStatus status = 4;
    int64 created_at = 5;
    optional string phone = 6;
    int32 age = 7;  // New optional field - non-breaking
}

message GetUserRequest {
    string user_id = 1;
    optional bool include_profile = 2;  // New optional field
}

message GetUserResponse {
    User user = 1;
    optional string cached_at = 2;  // New optional field
}

message CreateUserRequest {
    string email = 1;
    // name field is now required - was optional before
    string name = 2;
    required string password = 3;  // New required field - BREAKING
}

message CreateUserResponse {
    User user = 1;
}

// New message - non-breaking
message UpdateUserRequest {
    string user_id = 1;
    optional string email = 2;
    optional string name = 3;
}
"""

NEW_PROTO_NON_BREAKING = """
syntax = "proto3";

package example.api.v1;

service UserService {
    rpc GetUser(GetUserRequest) returns (GetUserResponse);
    rpc CreateUser(CreateUserRequest) returns (CreateUserResponse);
    rpc DeleteUser(DeleteUserRequest) returns (DeleteUserResponse);
    rpc UpdateUser(UpdateUserRequest) returns (UpdateUserResponse);  // New RPC
}

enum UserStatus {
    USER_STATUS_UNKNOWN = 0;
    USER_STATUS_ACTIVE = 1;
    USER_STATUS_INACTIVE = 2;
    USER_STATUS_SUSPENDED = 3;
    USER_STATUS_BANNED = 4;  // New value
}

message User {
    string id = 1;
    string email = 2;
    string name = 3;
    UserStatus status = 4;
    int64 created_at = 5;
    optional string phone = 6;
    optional string avatar_url = 7;  // New optional field
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
    optional string phone = 3;
}

message CreateUserResponse {
    User user = 1;
}

message DeleteUserRequest {
    string user_id = 1;
}

message DeleteUserResponse {
    bool success = 1;
}

// New message
message UpdateUserRequest {
    string user_id = 1;
    optional string email = 2;
}

// New message
message UpdateUserResponse {
    User user = 1;
}
"""


# =============================================================================
# JSON SCHEMA TEST FIXTURES
# =============================================================================

OLD_JSON_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "email": {"type": "string", "format": "email"},
        "name": {"type": "string"},
        "age": {"type": "integer", "minimum": 0},
        "status": {"type": "string", "enum": ["active", "inactive", "pending"]},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["id", "email"],
}

NEW_JSON_SCHEMA_BREAKING = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "id": {"type": "integer"},  # Type changed - BREAKING
        "email": {"type": "string", "format": "email"},
        # name field removed - BREAKING
        "age": {"type": "integer", "minimum": 0},
        "status": {
            "type": "string",
            "enum": ["active", "pending", "banned"],  # "inactive" removed - BREAKING
        },
        "tags": {"type": "array", "items": {"type": "string"}},
        "profile": {"type": "object"},  # New optional field
    },
    "required": ["id", "email", "age"],  # age now required - BREAKING
}


# =============================================================================
# PROTOBUF PARSER TESTS
# =============================================================================


class TestProtobufParser:
    """Tests for ProtobufParser."""

    def test_parse_syntax(self):
        """Test parsing syntax declaration."""
        parser = ProtobufParser()
        schema = parser.parse(OLD_PROTO)
        assert schema.syntax == "proto3"

    def test_parse_package(self):
        """Test parsing package declaration."""
        parser = ProtobufParser()
        schema = parser.parse(OLD_PROTO)
        assert schema.package == "example.api.v1"

    def test_parse_messages(self):
        """Test parsing message definitions."""
        parser = ProtobufParser()
        schema = parser.parse(OLD_PROTO)

        assert "User" in schema.messages
        assert "GetUserRequest" in schema.messages
        assert "GetUserResponse" in schema.messages

        user_msg = schema.messages["User"]
        assert "id" in user_msg.fields
        assert "email" in user_msg.fields
        assert "name" in user_msg.fields

        assert user_msg.fields["id"].number == 1
        assert user_msg.fields["id"].type == "string"

    def test_parse_enums(self):
        """Test parsing enum definitions."""
        parser = ProtobufParser()
        schema = parser.parse(OLD_PROTO)

        assert "UserStatus" in schema.enums
        user_status = schema.enums["UserStatus"]

        assert "USER_STATUS_UNKNOWN" in user_status.values
        assert "USER_STATUS_ACTIVE" in user_status.values
        assert user_status.values["USER_STATUS_UNKNOWN"] == 0
        assert user_status.values["USER_STATUS_ACTIVE"] == 1

    def test_parse_services(self):
        """Test parsing service definitions."""
        parser = ProtobufParser()
        schema = parser.parse(OLD_PROTO)

        assert "UserService" in schema.services
        service = schema.services["UserService"]

        assert "GetUser" in service
        assert service["GetUser"] == ("GetUserRequest", "GetUserResponse")

        assert "CreateUser" in service
        assert "DeleteUser" in service

    def test_parse_field_labels(self):
        """Test parsing field labels (optional, required, repeated)."""
        parser = ProtobufParser()
        schema = parser.parse(OLD_PROTO)

        user_msg = schema.messages["User"]
        # In proto3, fields without explicit label are optional by default
        assert user_msg.fields["phone"].label == "optional"


# =============================================================================
# SCHEMA DRIFT DETECTOR TESTS - PROTOBUF
# =============================================================================


class TestSchemaDriftDetectorProtobuf:
    """Tests for Protobuf schema drift detection."""

    def test_detect_breaking_changes(self):
        """Test detection of breaking changes."""
        detector = SchemaDriftDetector()
        result = detector.compare_protobuf(OLD_PROTO, NEW_PROTO_BREAKING)

        assert result.has_breaking_changes()
        breaking = result.breaking_changes

        # Should detect removed name field from User
        field_removed = [c for c in breaking if c.change_type == ChangeType.FIELD_REMOVED]
        assert len(field_removed) > 0

        # Should detect removed RPC
        rpc_removed = [c for c in breaking if "DeleteUser" in c.message]
        assert len(rpc_removed) > 0

        # Should detect removed enum value
        enum_removed = [c for c in breaking if c.change_type == ChangeType.ENUM_VALUE_REMOVED]
        assert len(enum_removed) > 0

    def test_detect_required_field_added(self):
        """Test detection of new required field (BREAKING)."""
        detector = SchemaDriftDetector()
        result = detector.compare_protobuf(OLD_PROTO, NEW_PROTO_BREAKING)

        required_added = [c for c in result.breaking_changes if c.change_type == ChangeType.REQUIRED_FIELD_ADDED]
        assert len(required_added) > 0
        assert any("password" in c.field_name for c in required_added)

    def test_non_breaking_changes_only(self):
        """Test schema evolution with only non-breaking changes."""
        detector = SchemaDriftDetector()
        result = detector.compare_protobuf(OLD_PROTO, NEW_PROTO_NON_BREAKING)

        # Should have changes but no breaking changes
        assert len(result.changes) > 0
        assert not result.has_breaking_changes()

        # Should detect new optional fields
        optional_added = [c for c in result.changes if c.change_type == ChangeType.OPTIONAL_FIELD_ADDED]
        assert len(optional_added) > 0

        # Should detect new enum values
        enum_added = [c for c in result.changes if c.change_type == ChangeType.ENUM_VALUE_ADDED]
        assert len(enum_added) > 0

    def test_no_changes(self):
        """Test identical schemas produce no changes."""
        detector = SchemaDriftDetector()
        result = detector.compare_protobuf(OLD_PROTO, OLD_PROTO)

        assert len(result.changes) == 0
        assert not result.has_breaking_changes()

    def test_result_summary(self):
        """Test result summary generation."""
        detector = SchemaDriftDetector()
        result = detector.compare_protobuf(
            OLD_PROTO,
            NEW_PROTO_BREAKING,
            old_version="v1.0",
            new_version="v2.0",
        )

        summary = result.summary()
        assert "v1.0" in summary
        assert "v2.0" in summary
        assert "BREAKING CHANGES" in summary
        assert "protobuf" in summary


# =============================================================================
# SCHEMA DRIFT DETECTOR TESTS - JSON SCHEMA
# =============================================================================


class TestSchemaDriftDetectorJsonSchema:
    """Tests for JSON Schema drift detection."""

    def test_detect_type_change(self):
        """Test detection of type changes (BREAKING)."""
        detector = SchemaDriftDetector()
        result = detector.compare_json_schema(OLD_JSON_SCHEMA, NEW_JSON_SCHEMA_BREAKING)

        type_changes = [c for c in result.breaking_changes if c.change_type == ChangeType.FIELD_TYPE_CHANGED]
        assert len(type_changes) > 0
        # id changed from string to integer
        assert any("id" in c.path for c in type_changes)

    def test_detect_property_removed(self):
        """Test detection of removed property (BREAKING)."""
        detector = SchemaDriftDetector()
        result = detector.compare_json_schema(OLD_JSON_SCHEMA, NEW_JSON_SCHEMA_BREAKING)

        removed = [c for c in result.breaking_changes if c.change_type == ChangeType.FIELD_REMOVED]
        assert len(removed) > 0
        # name was removed
        assert any("name" in c.field_name for c in removed)

    def test_detect_enum_value_removed(self):
        """Test detection of removed enum value (BREAKING)."""
        detector = SchemaDriftDetector()
        result = detector.compare_json_schema(OLD_JSON_SCHEMA, NEW_JSON_SCHEMA_BREAKING)

        enum_removed = [c for c in result.breaking_changes if c.change_type == ChangeType.ENUM_VALUE_REMOVED]
        assert len(enum_removed) > 0
        # "inactive" was removed
        assert any("inactive" in str(c.old_value) for c in enum_removed)

    def test_detect_field_made_required(self):
        """Test detection of optional field made required (BREAKING)."""
        detector = SchemaDriftDetector()
        result = detector.compare_json_schema(OLD_JSON_SCHEMA, NEW_JSON_SCHEMA_BREAKING)

        made_required = [c for c in result.breaking_changes if c.change_type == ChangeType.FIELD_MADE_REQUIRED]
        assert len(made_required) > 0
        # age was made required
        assert any("age" in c.field_name for c in made_required)

    def test_detect_optional_field_added(self):
        """Test detection of optional field added (non-breaking)."""
        detector = SchemaDriftDetector()
        result = detector.compare_json_schema(OLD_JSON_SCHEMA, NEW_JSON_SCHEMA_BREAKING)

        optional_added = [c for c in result.info_changes if c.change_type == ChangeType.OPTIONAL_FIELD_ADDED]
        assert len(optional_added) > 0
        # profile was added
        assert any("profile" in c.field_name for c in optional_added)

    def test_json_string_input(self):
        """Test parsing JSON string input."""
        detector = SchemaDriftDetector()
        result = detector.compare_json_schema(
            json.dumps(OLD_JSON_SCHEMA),
            json.dumps(NEW_JSON_SCHEMA_BREAKING),
        )

        assert result.has_breaking_changes()

    def test_no_changes_identical_schema(self):
        """Test identical schemas produce no changes."""
        detector = SchemaDriftDetector()
        result = detector.compare_json_schema(OLD_JSON_SCHEMA, OLD_JSON_SCHEMA)

        assert len(result.changes) == 0


# =============================================================================
# EDGE CASES AND ERROR HANDLING
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_proto(self):
        """Test handling of empty proto file."""
        detector = SchemaDriftDetector()
        result = detector.compare_protobuf("", "")

        assert len(result.changes) == 0

    def test_proto_with_comments(self):
        """Test parsing proto with various comment styles."""
        proto_with_comments = """
        syntax = "proto3";

        // Single line comment
        package test;

        /* Multi-line
           comment */
        message Test {
            string id = 1;  // Inline comment
        }
        """

        parser = ProtobufParser()
        schema = parser.parse(proto_with_comments)

        assert "Test" in schema.messages
        assert "id" in schema.messages["Test"].fields

    def test_nested_json_schema(self):
        """Test deeply nested JSON Schema comparison."""
        old_schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "profile": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                        }
                    },
                }
            },
        }

        new_schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "profile": {
                            "type": "object",
                            "properties": {"name": {"type": "integer"}},  # Changed type
                        }
                    },
                }
            },
        }

        detector = SchemaDriftDetector()
        result = detector.compare_json_schema(old_schema, new_schema)

        assert result.has_breaking_changes()
        assert any("name" in c.path for c in result.breaking_changes)

    def test_field_number_change(self):
        """Test detection of protobuf field number change (BREAKING)."""
        old_proto = """
        syntax = "proto3";
        message Test {
            string id = 1;
        }
        """

        new_proto = """
        syntax = "proto3";
        message Test {
            string id = 2;  // Field number changed
        }
        """

        detector = SchemaDriftDetector()
        result = detector.compare_protobuf(old_proto, new_proto)

        assert result.has_breaking_changes()
        number_changed = [c for c in result.breaking_changes if c.change_type == ChangeType.FIELD_NUMBER_CHANGED]
        assert len(number_changed) == 1


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestIntegration:
    """Integration tests for schema drift detection."""

    def test_full_protobuf_workflow(self):
        """Test complete Protobuf drift detection workflow."""
        detector = SchemaDriftDetector()

        # Compare old vs breaking changes
        result = detector.compare_protobuf(
            OLD_PROTO,
            NEW_PROTO_BREAKING,
            old_version="1.0.0",
            new_version="2.0.0",
        )

        # Verify result structure
        assert result.schema_type == "protobuf"
        assert result.old_version == "1.0.0"
        assert result.new_version == "2.0.0"

        # Should have breaking changes
        assert result.has_breaking_changes()

        # Verify categorization
        assert len(result.breaking_changes) > 0

        # Summary should be informative
        summary = result.summary()
        assert "Breaking:" in summary
        assert len(summary) > 100

    def test_full_json_schema_workflow(self):
        """Test complete JSON Schema drift detection workflow."""
        detector = SchemaDriftDetector()

        result = detector.compare_json_schema(
            OLD_JSON_SCHEMA,
            NEW_JSON_SCHEMA_BREAKING,
            old_version="schema-v1",
            new_version="schema-v2",
        )

        assert result.schema_type == "json_schema"
        assert result.has_breaking_changes()

        # Multiple types of breaking changes detected
        change_types = {c.change_type for c in result.breaking_changes}
        assert len(change_types) >= 2  # At least 2 types of breaking changes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
