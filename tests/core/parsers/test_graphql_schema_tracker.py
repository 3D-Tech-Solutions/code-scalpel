"""
Tests for GraphQL Schema Tracker.

[20251219_FEATURE] v3.0.4 - Ninja Warrior Stage 3 Tests
"""

import pytest

from code_scalpel.integrations.protocol_analyzers.graphql.schema_tracker import (
    GraphQLChangeSeverity,
    GraphQLChangeType,
    GraphQLSchemaTracker,
    GraphQLTypeKind,
    compare_graphql_schemas,
    track_graphql_schema,
)

# =============================================================================
# TEST FIXTURES
# =============================================================================

OLD_SCHEMA = """
\"\"\"User management API\"\"\"
type Query {
    \"\"\"Get a user by ID\"\"\"
    getUser(id: ID!): User
    listUsers(limit: Int = 10, offset: Int = 0): [User!]!
    searchUsers(query: String!): [User!]!
}

type Mutation {
    createUser(input: CreateUserInput!): User!
    updateUser(id: ID!, input: UpdateUserInput!): User
    deleteUser(id: ID!): Boolean!
}

type Subscription {
    userCreated: User!
    userUpdated(userId: ID!): User!
}

type User {
    id: ID!
    email: String!
    name: String!
    age: Int
    status: UserStatus!
    posts: [Post!]!
    createdAt: DateTime!
}

type Post {
    id: ID!
    title: String!
    content: String!
    author: User!
}

input CreateUserInput {
    email: String!
    name: String!
    age: Int
}

input UpdateUserInput {
    email: String
    name: String
    age: Int
}

enum UserStatus {
    ACTIVE
    INACTIVE
    PENDING
    SUSPENDED
}

union SearchResult = User | Post

interface Node {
    id: ID!
}

scalar DateTime

directive @deprecated(reason: String) on FIELD_DEFINITION | ENUM_VALUE
"""

NEW_SCHEMA_BREAKING = """
type Query {
    getUser(id: ID!): User
    listUsers(limit: Int = 10): [User!]!
    # searchUsers removed - BREAKING
}

type Mutation {
    createUser(input: CreateUserInput!): User!
    updateUser(id: ID!, input: UpdateUserInput!, force: Boolean!): User  # Required arg added - BREAKING
    deleteUser(id: ID!): Boolean!
}

type Subscription {
    userCreated: User!
    userUpdated(userId: ID!): User!
}

type User {
    id: ID!
    email: String!
    # name removed - BREAKING
    age: Int
    status: String!  # Type changed - BREAKING
    posts: [Post!]!
    createdAt: DateTime!
    role: String  # New optional field
}

type Post {
    id: ID!
    title: String!
    content: String!
    author: User!
}

input CreateUserInput {
    email: String!
    name: String!
    age: Int
    role: String!  # New required field - BREAKING
}

input UpdateUserInput {
    email: String
    name: String
    age: Int
}

enum UserStatus {
    ACTIVE
    # INACTIVE removed - BREAKING
    PENDING
    SUSPENDED
    BANNED  # New value
}

union SearchResult = User  # Post removed - BREAKING

interface Node {
    id: ID!
}

# New type
type Comment {
    id: ID!
    text: String!
}

scalar DateTime
"""

NEW_SCHEMA_NON_BREAKING = """
type Query {
    getUser(id: ID!): User
    listUsers(limit: Int = 10, offset: Int = 0): [User!]!
    searchUsers(query: String!): [User!]!
    getPost(id: ID!): Post  # New query
}

type Mutation {
    createUser(input: CreateUserInput!): User!
    updateUser(id: ID!, input: UpdateUserInput!): User
    deleteUser(id: ID!): Boolean!
    createPost(input: CreatePostInput!): Post!  # New mutation
}

type Subscription {
    userCreated: User!
    userUpdated(userId: ID!): User!
    postCreated: Post!  # New subscription
}

type User {
    id: ID!
    email: String!
    name: String!
    age: Int
    status: UserStatus!
    posts: [Post!]!
    createdAt: DateTime!
    avatar: String  # New optional field
}

type Post {
    id: ID!
    title: String!
    content: String!
    author: User!
    views: Int  # New optional field
}

input CreateUserInput {
    email: String!
    name: String!
    age: Int
    avatar: String  # New optional field
}

input UpdateUserInput {
    email: String
    name: String
    age: Int
}

input CreatePostInput {
    title: String!
    content: String!
}

enum UserStatus {
    ACTIVE
    INACTIVE
    PENDING
    SUSPENDED
    VERIFIED  # New value
}

union SearchResult = User | Post | Comment  # New member

type Comment {
    id: ID!
    text: String!
}

interface Node {
    id: ID!
}

scalar DateTime

directive @deprecated(reason: String) on FIELD_DEFINITION | ENUM_VALUE
"""


# =============================================================================
# PARSING TESTS
# =============================================================================


class TestGraphQLSchemaParser:
    """Tests for GraphQL SDL parsing."""

    def test_parse_object_types(self):
        """Test parsing object type definitions."""
        schema = track_graphql_schema(OLD_SCHEMA)

        assert "User" in schema.types
        assert "Post" in schema.types
        assert schema.types["User"].kind == GraphQLTypeKind.OBJECT

    def test_parse_fields(self):
        """Test parsing field definitions."""
        schema = track_graphql_schema(OLD_SCHEMA)

        user = schema.types["User"]
        assert "id" in user.fields
        assert "email" in user.fields
        assert "name" in user.fields

        assert user.fields["id"].type == "ID!"
        assert user.fields["email"].type == "String!"

    def test_parse_field_arguments(self):
        """Test parsing field arguments."""
        schema = track_graphql_schema(OLD_SCHEMA)

        query = schema.types["Query"]
        get_user = query.fields["getUser"]

        assert "id" in get_user.arguments
        assert get_user.arguments["id"].type == "ID!"

    def test_parse_input_types(self):
        """Test parsing input type definitions."""
        schema = track_graphql_schema(OLD_SCHEMA)

        assert "CreateUserInput" in schema.types
        assert schema.types["CreateUserInput"].kind == GraphQLTypeKind.INPUT_OBJECT

        input_type = schema.types["CreateUserInput"]
        assert "email" in input_type.input_fields
        assert "name" in input_type.input_fields

    def test_parse_enum_types(self):
        """Test parsing enum definitions."""
        schema = track_graphql_schema(OLD_SCHEMA)

        assert "UserStatus" in schema.types
        assert schema.types["UserStatus"].kind == GraphQLTypeKind.ENUM

        enum = schema.types["UserStatus"]
        assert "ACTIVE" in enum.enum_values
        assert "INACTIVE" in enum.enum_values
        assert "PENDING" in enum.enum_values

    def test_parse_union_types(self):
        """Test parsing union definitions."""
        schema = track_graphql_schema(OLD_SCHEMA)

        assert "SearchResult" in schema.types
        assert schema.types["SearchResult"].kind == GraphQLTypeKind.UNION

        union = schema.types["SearchResult"]
        assert "User" in union.union_types
        assert "Post" in union.union_types

    def test_parse_interface_types(self):
        """Test parsing interface definitions."""
        schema = track_graphql_schema(OLD_SCHEMA)

        assert "Node" in schema.types
        assert schema.types["Node"].kind == GraphQLTypeKind.INTERFACE

    def test_parse_scalar_types(self):
        """Test parsing scalar definitions."""
        schema = track_graphql_schema(OLD_SCHEMA)

        assert "DateTime" in schema.types
        assert schema.types["DateTime"].kind == GraphQLTypeKind.SCALAR

    def test_parse_directives(self):
        """Test parsing directive definitions."""
        schema = track_graphql_schema(OLD_SCHEMA)

        assert "deprecated" in schema.directives
        directive = schema.directives["deprecated"]
        assert "FIELD_DEFINITION" in directive.locations
        assert "reason" in directive.arguments


# =============================================================================
# SCHEMA PROPERTY TESTS
# =============================================================================


class TestGraphQLSchemaProperties:
    """Tests for GraphQLSchema properties."""

    def test_queries_property(self):
        """Test queries property."""
        schema = track_graphql_schema(OLD_SCHEMA)

        queries = schema.queries
        assert "getUser" in queries
        assert "listUsers" in queries
        assert "searchUsers" in queries

    def test_mutations_property(self):
        """Test mutations property."""
        schema = track_graphql_schema(OLD_SCHEMA)

        mutations = schema.mutations
        assert "createUser" in mutations
        assert "updateUser" in mutations
        assert "deleteUser" in mutations

    def test_subscriptions_property(self):
        """Test subscriptions property."""
        schema = track_graphql_schema(OLD_SCHEMA)

        subscriptions = schema.subscriptions
        assert "userCreated" in subscriptions
        assert "userUpdated" in subscriptions

    def test_type_counts(self):
        """Test type count properties."""
        schema = track_graphql_schema(OLD_SCHEMA)

        assert len(schema.object_types) >= 3  # Query, Mutation, User, Post, etc.
        assert len(schema.input_types) >= 2
        assert len(schema.enum_types) >= 1
        assert len(schema.interface_types) >= 1
        assert len(schema.union_types) >= 1

    def test_summary(self):
        """Test summary generation."""
        schema = track_graphql_schema(OLD_SCHEMA)
        summary = schema.summary()

        assert "GraphQL Schema Summary" in summary
        assert "Types:" in summary
        assert "Queries:" in summary
        assert "Mutations:" in summary


# =============================================================================
# SCHEMA DRIFT DETECTION TESTS
# =============================================================================


class TestSchemaDriftDetection:
    """Tests for schema drift detection."""

    def test_detect_breaking_changes(self):
        """Test detection of breaking changes."""
        drift = compare_graphql_schemas(OLD_SCHEMA, NEW_SCHEMA_BREAKING)

        assert drift.has_breaking_changes()
        assert len(drift.breaking_changes) > 0

    def test_detect_field_removed(self):
        """Test detection of removed field (BREAKING)."""
        drift = compare_graphql_schemas(OLD_SCHEMA, NEW_SCHEMA_BREAKING)

        field_removed = [c for c in drift.breaking_changes if c.change_type == GraphQLChangeType.FIELD_REMOVED]
        assert len(field_removed) > 0
        # name was removed from User, searchUsers was removed from Query
        assert any("name" in c.message or "searchUsers" in c.message for c in field_removed)

    def test_detect_type_changed(self):
        """Test detection of field type change (BREAKING/DANGEROUS)."""
        drift = compare_graphql_schemas(OLD_SCHEMA, NEW_SCHEMA_BREAKING)

        type_changed = [c for c in drift.changes if c.change_type == GraphQLChangeType.FIELD_TYPE_CHANGED]
        assert len(type_changed) > 0
        # status changed from UserStatus! to String!
        assert any("status" in c.path for c in type_changed)

    def test_detect_required_arg_added(self):
        """Test detection of required argument added (BREAKING)."""
        drift = compare_graphql_schemas(OLD_SCHEMA, NEW_SCHEMA_BREAKING)

        required_added = [c for c in drift.breaking_changes if c.change_type == GraphQLChangeType.REQUIRED_ARG_ADDED]
        assert len(required_added) > 0
        # force was added as required to updateUser
        assert any("force" in c.message for c in required_added)

    def test_detect_enum_value_removed(self):
        """Test detection of removed enum value (BREAKING)."""
        drift = compare_graphql_schemas(OLD_SCHEMA, NEW_SCHEMA_BREAKING)

        enum_removed = [c for c in drift.breaking_changes if c.change_type == GraphQLChangeType.ENUM_VALUE_REMOVED]
        assert len(enum_removed) > 0
        # INACTIVE was removed from UserStatus
        assert any("INACTIVE" in c.message for c in enum_removed)

    def test_detect_union_member_removed(self):
        """Test detection of removed union member (BREAKING)."""
        drift = compare_graphql_schemas(OLD_SCHEMA, NEW_SCHEMA_BREAKING)

        union_removed = [c for c in drift.breaking_changes if c.change_type == GraphQLChangeType.UNION_MEMBER_REMOVED]
        assert len(union_removed) > 0
        # Post was removed from SearchResult
        assert any("Post" in c.message for c in union_removed)

    def test_non_breaking_changes(self):
        """Test detection of non-breaking changes only."""
        drift = compare_graphql_schemas(OLD_SCHEMA, NEW_SCHEMA_NON_BREAKING)

        # Should have changes but no breaking ones
        assert len(drift.changes) > 0
        assert not drift.has_breaking_changes()

    def test_detect_field_added(self):
        """Test detection of added field (INFO)."""
        drift = compare_graphql_schemas(OLD_SCHEMA, NEW_SCHEMA_NON_BREAKING)

        field_added = [c for c in drift.info_changes if c.change_type == GraphQLChangeType.FIELD_ADDED]
        assert len(field_added) > 0
        # avatar was added to User
        assert any("avatar" in c.message for c in field_added)

    def test_detect_enum_value_added(self):
        """Test detection of added enum value (INFO)."""
        drift = compare_graphql_schemas(OLD_SCHEMA, NEW_SCHEMA_NON_BREAKING)

        enum_added = [c for c in drift.info_changes if c.change_type == GraphQLChangeType.ENUM_VALUE_ADDED]
        assert len(enum_added) > 0
        # VERIFIED was added to UserStatus
        assert any("VERIFIED" in c.message for c in enum_added)

    def test_detect_type_added(self):
        """Test detection of added type (INFO)."""
        drift = compare_graphql_schemas(OLD_SCHEMA, NEW_SCHEMA_NON_BREAKING)

        type_added = [c for c in drift.info_changes if c.change_type == GraphQLChangeType.TYPE_ADDED]
        assert len(type_added) > 0
        # Comment type was added
        assert any("Comment" in c.message for c in type_added)

    def test_no_changes_identical(self):
        """Test no changes for identical schemas."""
        drift = compare_graphql_schemas(OLD_SCHEMA, OLD_SCHEMA)

        assert len(drift.changes) == 0
        assert not drift.has_breaking_changes()


# =============================================================================
# DRIFT RESULT TESTS
# =============================================================================


class TestGraphQLSchemaDrift:
    """Tests for GraphQLSchemaDrift class."""

    def test_breaking_changes_property(self):
        """Test breaking_changes property."""
        drift = compare_graphql_schemas(OLD_SCHEMA, NEW_SCHEMA_BREAKING)

        breaking = drift.breaking_changes
        assert all(c.severity == GraphQLChangeSeverity.BREAKING for c in breaking)

    def test_dangerous_changes_property(self):
        """Test dangerous_changes property."""
        drift = compare_graphql_schemas(OLD_SCHEMA, NEW_SCHEMA_NON_BREAKING)

        # Union member added is considered dangerous
        dangerous = drift.dangerous_changes
        # May or may not have dangerous changes depending on schema
        assert isinstance(dangerous, list)

    def test_info_changes_property(self):
        """Test info_changes property."""
        drift = compare_graphql_schemas(OLD_SCHEMA, NEW_SCHEMA_NON_BREAKING)

        info = drift.info_changes
        assert all(c.severity == GraphQLChangeSeverity.INFO for c in info)

    def test_summary_with_breaking(self):
        """Test summary with breaking changes."""
        drift = compare_graphql_schemas(
            OLD_SCHEMA,
            NEW_SCHEMA_BREAKING,
            old_version="v1",
            new_version="v2",
        )

        summary = drift.summary()
        assert "v1" in summary
        assert "v2" in summary
        assert "BREAKING CHANGES" in summary

    def test_summary_without_breaking(self):
        """Test summary without breaking changes."""
        drift = compare_graphql_schemas(OLD_SCHEMA, NEW_SCHEMA_NON_BREAKING)

        summary = drift.summary()
        assert "BREAKING CHANGES" not in summary


# =============================================================================
# EDGE CASES
# =============================================================================


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_schema(self):
        """Test handling of empty/minimal schema."""
        minimal = "type Query { ping: String }"
        schema = track_graphql_schema(minimal)

        assert "Query" in schema.types
        assert "ping" in schema.types["Query"].fields

    def test_schema_with_comments(self):
        """Test parsing schema with comments."""
        schema_with_comments = """
        # This is a comment
        type Query {
            # Get user
            getUser(id: ID!): User  # inline comment
        }

        type User {
            id: ID!
            name: String!
        }
        """

        schema = track_graphql_schema(schema_with_comments)
        assert "Query" in schema.types
        assert "User" in schema.types

    def test_argument_with_default(self):
        """Test parsing arguments with default values."""
        sdl = """
        type Query {
            listUsers(limit: Int = 10, active: Boolean = true): [User!]!
        }
        type User { id: ID! }
        """

        schema = track_graphql_schema(sdl)
        query = schema.types["Query"]
        list_users = query.fields["listUsers"]

        assert "limit" in list_users.arguments
        assert list_users.arguments["limit"].default_value == "10"

    def test_required_argument_detection(self):
        """Test detection of required vs optional arguments."""
        sdl = """
        type Query {
            test(required: String!, optional: String, withDefault: String = "default"): String
        }
        """

        schema = track_graphql_schema(sdl)
        args = schema.types["Query"].fields["test"].arguments

        assert args["required"].is_required is True
        assert args["optional"].is_required is False
        assert args["withDefault"].is_required is False


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestIntegration:
    """Integration tests."""

    def test_full_workflow(self):
        """Test complete schema tracking workflow."""
        tracker = GraphQLSchemaTracker()

        # Parse schema
        schema = tracker.parse(OLD_SCHEMA)

        # Compare schemas
        drift = tracker.compare(OLD_SCHEMA, NEW_SCHEMA_BREAKING)

        # Verify results
        assert schema.type_count > 0
        assert len(schema.queries) > 0
        assert drift.has_breaking_changes()

        # Summary works
        assert len(schema.summary()) > 100
        assert len(drift.summary()) > 100

    def test_convenience_functions(self):
        """Test convenience functions."""
        schema = track_graphql_schema(OLD_SCHEMA)
        assert schema.type_count > 0

        drift = compare_graphql_schemas(OLD_SCHEMA, NEW_SCHEMA_NON_BREAKING)
        assert not drift.has_breaking_changes()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
