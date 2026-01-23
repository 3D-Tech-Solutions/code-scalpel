"""
JSX/TSX Extraction Example

[20251216_FEATURE] v2.0.2 - Demonstrates React component extraction,
Server Component detection, and Server Action detection.

This example shows how to use Code Scalpel to extract React components
from JSX/TSX files with full metadata about component types, Server
Components, and Server Actions.
"""

import asyncio

from code_scalpel.mcp.server import extract_code


async def example_functional_component():
    """Extract a functional React component."""
    print("=" * 60)
    print("Example 1: Functional React Component")
    print("=" * 60)

    jsx_code = """
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
        code=jsx_code,
        language="jsx",
    )

    print(f"✓ Success: {result.success}")
    print(f"✓ Component Type: {result.component_type}")
    print(f"✓ JSX Normalized: {result.jsx_normalized}")
    print(f"✓ Code:\n{result.target_code}")
    print()


async def example_server_component():
    """Extract a Next.js Server Component."""
    print("=" * 60)
    print("Example 2: Next.js Server Component")
    print("=" * 60)

    tsx_code = """
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
        code=tsx_code,
        language="tsx",
    )

    print(f"✓ Success: {result.success}")
    print(f"✓ Component Type: {result.component_type}")
    print(f"✓ Is Server Component: {result.is_server_component}")
    print(f"✓ JSX Normalized: {result.jsx_normalized}")
    print(f"✓ Code:\n{result.target_code}")
    print()


async def example_server_action():
    """Extract a Next.js Server Action."""
    print("=" * 60)
    print("Example 3: Next.js Server Action")
    print("=" * 60)

    tsx_code = """
async function updateUser(formData) {
  'use server';
  const id = formData.get('id');
  await db.users.update({ id }, formData);
  revalidatePath('/users');
}
"""

    result = await extract_code(
        target_type="function",
        target_name="updateUser",
        code=tsx_code,
        language="tsx",
    )

    print(f"✓ Success: {result.success}")
    print(f"✓ Is Server Action: {result.is_server_action}")
    print(f"✓ Code:\n{result.target_code}")
    print()


async def example_typescript_component():
    """Extract a TypeScript React component with types."""
    print("=" * 60)
    print("Example 4: TypeScript React Component")
    print("=" * 60)

    tsx_code = """
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
        code=tsx_code,
        language="tsx",
    )

    print(f"✓ Success: {result.success}")
    print(f"✓ Component Type: {result.component_type}")
    print(f"✓ JSX Normalized: {result.jsx_normalized}")
    print(f"✓ Lines: {result.line_start} - {result.line_end}")
    print(f"✓ Code:\n{result.target_code}")
    print()


async def main():
    """Run all examples."""
    print("\nCode Scalpel v2.0.2 - JSX/TSX Extraction Examples\n")

    await example_functional_component()
    await example_server_component()
    await example_server_action()
    await example_typescript_component()

    print("=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
