#!/usr/bin/env python
"""
Docker Container Tool Testing Script for Code Scalpel v2.0.0

[20251215_TEST] Tests the new and updated MCP tools via HTTP transport
against the running Docker container.
"""

import json
import sys

import requests

BASE_URL = "http://localhost:8593"
MCP_URL = f"{BASE_URL}/mcp"


def call_tool(tool_name: str, arguments: dict) -> dict:
    """Call an MCP tool via HTTP."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }

    response = requests.post(MCP_URL, json=payload, timeout=60)
    return response.json()


def test_extract_code_python():
    """Test Python extraction."""
    print("\n[TEST] extract_code - Python")
    code = '''
def calculate_tax(amount, rate=0.1):
    """Calculate tax on amount."""
    return amount * rate

class Calculator:
    def add(self, a, b):
        return a + b
'''
    result = call_tool(
        "extract_code",
        {"code": code, "target_type": "function", "target_name": "calculate_tax"},
    )

    if "result" in result:
        content = result["result"].get("content", [{}])[0].get("text", "")
        data = json.loads(content) if content else {}
        if data.get("success"):
            print(f"  ✓ Python function extracted: {data.get('target_code', '')[:50]}...")
            return True
        else:
            print(f"  ✗ Failed: {data.get('error')}")
    else:
        print(f"  ✗ Error: {result.get('error')}")
    return False


def test_extract_code_typescript():
    """Test TypeScript extraction."""
    print("\n[TEST] extract_code - TypeScript")
    code = """
function calculateTax(amount: number, rate: number = 0.1): number {
    return amount * rate;
}

class Calculator {
    add(a: number, b: number): number {
        return a + b;
    }
}
"""
    result = call_tool(
        "extract_code",
        {
            "code": code,
            "target_type": "function",
            "target_name": "calculateTax",
            "language": "typescript",
        },
    )

    if "result" in result:
        content = result["result"].get("content", [{}])[0].get("text", "")
        data = json.loads(content) if content else {}
        if data.get("success"):
            print(f"  ✓ TypeScript function extracted: {data.get('target_code', '')[:50]}...")
            return True
        else:
            print(f"  ✗ Failed: {data.get('error')}")
    else:
        print(f"  ✗ Error: {result.get('error')}")
    return False


def test_extract_code_javascript():
    """Test JavaScript extraction."""
    print("\n[TEST] extract_code - JavaScript")
    code = """
function processData(input) {
    return input.map(x => x * 2);
}

class DataHandler {
    constructor() {
        this.data = [];
    }
    
    process() {
        return this.data;
    }
}
"""
    result = call_tool(
        "extract_code",
        {
            "code": code,
            "target_type": "class",
            "target_name": "DataHandler",
            "language": "javascript",
        },
    )

    if "result" in result:
        content = result["result"].get("content", [{}])[0].get("text", "")
        data = json.loads(content) if content else {}
        if data.get("success"):
            print(f"  ✓ JavaScript class extracted: {data.get('target_code', '')[:50]}...")
            return True
        else:
            print(f"  ✗ Failed: {data.get('error')}")
    else:
        print(f"  ✗ Error: {result.get('error')}")
    return False


def test_extract_code_java():
    """Test Java extraction."""
    print("\n[TEST] extract_code - Java")
    code = """
public class UserService {
    private UserRepository repository;
    
    public User findById(Long id) {
        return repository.findById(id);
    }
    
    public void saveUser(User user) {
        repository.save(user);
    }
}
"""
    result = call_tool(
        "extract_code",
        {
            "code": code,
            "target_type": "method",
            "target_name": "UserService.findById",
            "language": "java",
        },
    )

    if "result" in result:
        content = result["result"].get("content", [{}])[0].get("text", "")
        data = json.loads(content) if content else {}
        if data.get("success"):
            print(f"  ✓ Java method extracted: {data.get('target_code', '')[:50]}...")
            return True
        else:
            print(f"  ✗ Failed: {data.get('error')}")
    else:
        print(f"  ✗ Error: {result.get('error')}")
    return False


def test_security_scan():
    """Test security scanning."""
    print("\n[TEST] security_scan - SQL Injection")
    code = """
import sqlite3

def get_user(user_id):
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE id={user_id}"
    cursor.execute(query)
    return cursor.fetchone()
"""
    result = call_tool("security_scan", {"code": code})

    if "result" in result:
        content = result["result"].get("content", [{}])[0].get("text", "")
        data = json.loads(content) if content else {}
        if data.get("success"):
            vuln_count = data.get("vulnerability_count", 0)
            print(f"  ✓ Security scan completed: {vuln_count} vulnerabilities found")
            return vuln_count > 0
        else:
            print(f"  ✗ Failed: {data.get('error')}")
    else:
        print(f"  ✗ Error: {result.get('error')}")
    return False


def test_get_file_context():
    """Test file context retrieval."""
    print("\n[TEST] get_file_context")
    result = call_tool("get_file_context", {"file_path": "/app/code/src/code_scalpel/mcp/server.py"})

    if "result" in result:
        content = result["result"].get("content", [{}])[0].get("text", "")
        data = json.loads(content) if content else {}
        if data.get("success"):
            print(
                f"  ✓ File context retrieved: {len(data.get('functions', []))} functions, {len(data.get('classes', []))} classes"
            )
            return True
        else:
            print(f"  ✗ Failed: {data.get('error')}")
    else:
        print(f"  ✗ Error: {result.get('error')}")
    return False


def test_validate_paths():
    """Test path validation."""
    print("\n[TEST] validate_paths")
    result = call_tool(
        "validate_paths",
        {"paths": ["/app/code/src/code_scalpel/mcp/server.py", "/nonexistent/file.py"]},
    )

    if "result" in result:
        content = result["result"].get("content", [{}])[0].get("text", "")
        data = json.loads(content) if content else {}
        accessible = len(data.get("accessible", []))
        inaccessible = len(data.get("inaccessible", []))
        print(f"  ✓ Path validation: {accessible} accessible, {inaccessible} inaccessible")
        return accessible > 0
    else:
        print(f"  ✗ Error: {result.get('error')}")
    return False


def test_analyze_code():
    """Test code analysis."""
    print("\n[TEST] analyze_code - Python")
    code = """
def calculate_tax(amount, rate=0.1):
    return amount * rate

class Calculator:
    def add(self, a, b):
        return a + b
"""
    result = call_tool("analyze_code", {"code": code})

    if "result" in result:
        content = result["result"].get("content", [{}])[0].get("text", "")
        data = json.loads(content) if content else {}
        if data.get("success"):
            print(f"  ✓ Code analyzed: {data.get('function_count', 0)} functions, {data.get('class_count', 0)} classes")
            return True
        else:
            print(f"  ✗ Failed: {data.get('error')}")
    else:
        print(f"  ✗ Error: {result.get('error')}")
    return False


def test_crawl_project():
    """Test project crawling."""
    print("\n[TEST] crawl_project")
    result = call_tool("crawl_project", {"root_path": "/app/code/src/code_scalpel"})

    if "result" in result:
        content = result["result"].get("content", [{}])[0].get("text", "")
        data = json.loads(content) if content else {}
        if data.get("success"):
            summary = data.get("summary", {})
            print(
                f"  ✓ Project crawled: {summary.get('total_files', 0)} files, {summary.get('total_functions', 0)} functions"
            )
            return True
        else:
            print(f"  ✗ Failed: {data.get('error')}")
    else:
        print(f"  ✗ Error: {result.get('error')}")
    return False


def main():
    print("=" * 60)
    print("Code Scalpel v2.0.0 Docker Container Tool Tests")
    print("=" * 60)
    print(f"Target: {MCP_URL}")

    # Check server is running
    try:
        response = requests.get(
            f"{BASE_URL}/sse",
            headers={"Accept": "text/event-stream"},
            timeout=5,
            stream=True,
        )
        if response.status_code != 200:
            print(f"Server not responding correctly: {response.status_code}")
            return 1
        print("Server is running ✓")
    except Exception as e:
        print(f"Cannot connect to server: {e}")
        return 1

    # Run tests
    results = []

    # Core extraction tests (v2.0.0 polyglot)
    results.append(("Python extraction", test_extract_code_python()))
    results.append(("TypeScript extraction", test_extract_code_typescript()))
    results.append(("JavaScript extraction", test_extract_code_javascript()))
    results.append(("Java extraction", test_extract_code_java()))

    # Security and analysis
    results.append(("Security scan", test_security_scan()))
    results.append(("Code analysis", test_analyze_code()))

    # Project tools
    results.append(("File context", test_get_file_context()))
    results.append(("Path validation", test_validate_paths()))
    results.append(("Project crawl", test_crawl_project()))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
