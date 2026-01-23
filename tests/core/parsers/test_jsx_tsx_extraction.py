"""
Tests for JSX/TSX extraction feature.

[20251216_FEATURE] v2.0.2 - Tests for React component extraction,
Server Component detection, and Server Action detection.
"""

import pytest

# Mark entire module as async
pytestmark = pytest.mark.asyncio


class TestJSXExtractionBasic:
    """Tests for basic JSX component extraction."""

    async def test_extract_functional_component(self):
        """Test extracting a functional React component."""
        from code_scalpel.mcp.server import extract_code

        code = """
export function UserCard({ user }) {
  return (
    <div className="card">
      <h2>{user.name}</h2>
      <p>{user.email}</p>
    </div>
  );
}
"""
        result = await extract_code(
            target_type="function",
            target_name="UserCard",
            code=code,
            language="jsx",
        )

        assert result.success is True
        assert "UserCard" in result.target_code
        assert result.jsx_normalized is True
        assert result.component_type == "functional"
        assert result.is_server_component is False

    async def test_extract_tsx_component(self):
        """Test extracting a TypeScript React component."""
        from code_scalpel.mcp.server import extract_code

        code = """
interface User {
  name: string;
  email: string;
}

export function UserCard({ user }: { user: User }) {
  return (
    <div className="card">
      <h2>{user.name}</h2>
      <p>{user.email}</p>
    </div>
  );
}
"""
        result = await extract_code(
            target_type="function",
            target_name="UserCard",
            code=code,
            language="tsx",
        )

        assert result.success is True
        assert "UserCard" in result.target_code
        assert result.jsx_normalized is True
        assert result.component_type == "functional"

    async def test_extract_class_component(self):
        """Test extracting a class-based React component."""
        from code_scalpel.mcp.server import extract_code

        code = """
import React from 'react';

export class UserProfile extends React.Component {
  render() {
    return (
      <div>
        <h1>{this.props.name}</h1>
      </div>
    );
  }
}
"""
        result = await extract_code(
            target_type="class",
            target_name="UserProfile",
            code=code,
            language="jsx",
        )

        assert result.success is True
        assert "UserProfile" in result.target_code
        assert result.jsx_normalized is True
        # assert result.component_type == "class"


class TestServerComponentDetection:
    """Tests for Next.js Server Component detection."""

    async def test_detect_server_component(self):
        """Test detecting an async Server Component."""
        from code_scalpel.mcp.server import extract_code

        code = """
async function UserList() {
  const users = await fetchUsers();
  return (
    <div>
      {users.map(u => <UserCard key={u.id} user={u} />)}
    </div>
  );
}
"""
        result = await extract_code(
            target_type="function",
            target_name="UserList",
            code=code,
            language="tsx",
        )

        assert result.success is True
        assert "UserList" in result.target_code
        assert result.jsx_normalized is True
        assert result.is_server_component is True, "Should detect async component"
        assert result.component_type == "functional"

    async def test_non_server_component(self):
        """Test that non-async components are not marked as Server Components."""
        from code_scalpel.mcp.server import extract_code

        code = """
function RegularComponent() {
  return <div>Hello</div>;
}
"""
        result = await extract_code(
            target_type="function",
            target_name="RegularComponent",
            code=code,
            language="tsx",
        )

        assert result.success is True
        assert result.is_server_component is False


class TestServerActionDetection:
    """Tests for Next.js Server Action detection."""

    async def test_detect_server_action(self):
        """Test detecting a Server Action with 'use server' directive."""
        from code_scalpel.mcp.server import extract_code

        code = """
async function updateUser(formData) {
  'use server';
  const id = formData.get('id');
  await db.users.update({ id }, formData);
}
"""
        result = await extract_code(
            target_type="function",
            target_name="updateUser",
            code=code,
            language="tsx",
        )

        assert result.success is True
        assert "updateUser" in result.target_code
        assert result.is_server_action is True, "Should detect 'use server' directive"

    async def test_server_action_with_double_quotes(self):
        """Test detecting Server Action with double quotes."""
        from code_scalpel.mcp.server import extract_code

        code = """
async function deleteUser(id) {
  "use server";
  await db.users.delete(id);
}
"""
        result = await extract_code(
            target_type="function",
            target_name="deleteUser",
            code=code,
            language="tsx",
        )

        assert result.success is True
        assert result.is_server_action is True

    async def test_non_server_action(self):
        """Test that regular functions are not marked as Server Actions."""
        from code_scalpel.mcp.server import extract_code

        code = """
function regularFunction() {
  return "hello";
}
"""
        result = await extract_code(
            target_type="function",
            target_name="regularFunction",
            code=code,
            language="tsx",
        )

        assert result.success is True
        assert result.is_server_action is False


class TestJSXNormalization:
    """Tests for JSX syntax normalization."""

    async def test_jsx_detected_and_normalized(self):
        """Test that JSX syntax is detected and normalized."""
        from code_scalpel.mcp.server import extract_code

        code = """
function App() {
  return (
    <div>
      <Header />
      <Content />
      <Footer />
    </div>
  );
}
"""
        result = await extract_code(
            target_type="function",
            target_name="App",
            code=code,
            language="jsx",
        )

        assert result.success is True
        assert result.jsx_normalized is True
        # Verify JSX is present in extracted code
        assert "<div>" in result.target_code
        assert "<Header />" in result.target_code

    async def test_non_jsx_not_normalized(self):
        """Test that non-JSX code is not marked as normalized."""
        from code_scalpel.mcp.server import extract_code

        code = """
function add(a, b) {
  return a + b;
}
"""
        result = await extract_code(
            target_type="function",
            target_name="add",
            code=code,
            language="javascript",
        )

        assert result.success is True
        assert result.jsx_normalized is False
