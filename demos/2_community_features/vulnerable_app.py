"""
Intentionally Vulnerable Web Application
For Code Scalpel Security Scanning Demo

WARNING: This code contains intentional security vulnerabilities.
DO NOT use in production. For educational purposes only.
"""

import os
import sqlite3
import subprocess
from typing import Any

from flask import Flask, request

app = Flask(__name__)


# VULNERABILITY 1: SQL Injection (High Severity)
def get_user_by_id(user_id: str) -> dict[str, Any]:
    """
    Fetch user from database by ID.

    VULNERABILITY: SQL injection via string formatting
    CWE-89: Improper Neutralization of Special Elements used in an SQL Command
    """
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # BAD: User input directly in SQL query
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)

    result = cursor.fetchone()
    conn.close()

    return {"id": result[0], "name": result[1]} if result else None


# VULNERABILITY 2: SQL Injection via format() (High Severity)
def login_user(username: str, password: str) -> bool:
    """
    Authenticate user login.

    VULNERABILITY: SQL injection via .format()
    CWE-89: SQL Injection
    """
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # BAD: Using .format() with user input
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    cursor.execute(query)

    result = cursor.fetchone()
    conn.close()

    return result is not None


# VULNERABILITY 3: Command Injection (Critical Severity)
def ping_host(hostname: str) -> str:
    """
    Ping a hostname to check connectivity.

    VULNERABILITY: Command injection via shell execution
    CWE-78: OS Command Injection
    """
    # BAD: User input in shell command
    command = f"ping -c 4 {hostname}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout


# VULNERABILITY 4: Path Traversal (High Severity)
def read_user_file(filename: str) -> str:
    """
    Read a user-uploaded file.

    VULNERABILITY: Path traversal
    CWE-22: Path Traversal
    """
    # BAD: No path validation
    base_dir = "/var/www/uploads/"
    file_path = base_dir + filename  # User can use ../../../etc/passwd

    with open(file_path) as f:
        return f.read()


# VULNERABILITY 5: XSS - Reflected (Medium Severity)
@app.route("/welcome")
def welcome():
    """
    Welcome page showing username.

    VULNERABILITY: Reflected XSS
    CWE-79: Cross-site Scripting
    """
    username = request.args.get("name", "Guest")

    # BAD: Unescaped user input in HTML
    html = f"<h1>Welcome {username}!</h1>"
    return html


# VULNERABILITY 6: XSS - Stored (High Severity)
def save_comment(comment: str, user_id: int) -> None:
    """
    Save user comment to database.

    VULNERABILITY: Stored XSS
    CWE-79: Cross-site Scripting
    """
    conn = sqlite3.connect("comments.db")
    cursor = conn.cursor()

    # BAD: Storing unescaped user input
    cursor.execute(
        "INSERT INTO comments (user_id, comment) VALUES (?, ?)",
        (user_id, comment),  # Comment not sanitized
    )
    conn.commit()
    conn.close()


def display_comments() -> str:
    """
    Display all comments.

    VULNERABILITY: Outputs unsanitized stored data
    """
    conn = sqlite3.connect("comments.db")
    cursor = conn.cursor()
    cursor.execute("SELECT comment FROM comments")
    comments = cursor.fetchall()
    conn.close()

    # BAD: Rendering unescaped comments
    html = "<div>"
    for comment in comments:
        html += f"<p>{comment[0]}</p>"  # XSS here
    html += "</div>"

    return html


# VULNERABILITY 7: Hardcoded Secrets (High Severity)
API_KEY = "sk-1234567890abcdef"  # BAD: Hardcoded API key
DATABASE_PASSWORD = "admin123"  # BAD: Hardcoded password
SECRET_KEY = "my-secret-key-123"  # BAD: Hardcoded secret


def connect_to_api():
    """
    Connect to external API.

    VULNERABILITY: Hardcoded credentials
    CWE-798: Use of Hard-coded Credentials
    """
    import requests

    headers = {"Authorization": f"Bearer {API_KEY}"}
    return requests.get("https://api.example.com/data", headers=headers)


# VULNERABILITY 8: Insecure Deserialization (Critical Severity)
def load_user_session(session_data: str) -> dict:
    """
    Load user session from cookie.

    VULNERABILITY: Insecure deserialization
    CWE-502: Deserialization of Untrusted Data
    """
    import pickle

    # BAD: Unpickling untrusted data
    session = pickle.loads(session_data.encode())
    return session


# VULNERABILITY 9: Weak Cryptography (Medium Severity)
def hash_password(password: str) -> str:
    """
    Hash user password.

    VULNERABILITY: Weak hashing algorithm
    CWE-327: Use of a Broken or Risky Cryptographic Algorithm
    """
    import hashlib

    # BAD: MD5 is cryptographically broken
    return hashlib.md5(password.encode()).hexdigest()


# VULNERABILITY 10: LDAP Injection (High Severity)
def ldap_search(username: str) -> list:
    """
    Search LDAP directory for user.

    VULNERABILITY: LDAP injection
    CWE-90: LDAP Injection
    """

    # BAD: User input in LDAP filter
    # Example vulnerable filter: f"(uid={username})"
    # This would connect to LDAP server and search
    # Attacker could inject: *)(uid=*))(|(uid=*
    return []


# VULNERABILITY 11: XML External Entity (XXE) (High Severity)
def parse_xml_config(xml_data: str) -> dict:
    """
    Parse XML configuration.

    VULNERABILITY: XML External Entity injection
    CWE-611: XXE
    """
    import xml.etree.ElementTree as ET

    # BAD: Parsing untrusted XML without disabling external entities
    root = ET.fromstring(xml_data)

    config = {}
    for child in root:
        config[child.tag] = child.text

    return config


# VULNERABILITY 12: Server-Side Request Forgery (SSRF) (High Severity)
def fetch_url(url: str) -> str:
    """
    Fetch content from URL.

    VULNERABILITY: SSRF - can access internal resources
    CWE-918: Server-Side Request Forgery
    """
    import requests

    # BAD: No URL validation, can access internal services
    response = requests.get(url)
    return response.text


# VULNERABILITY 13: Insecure Random (Medium Severity)
def generate_password_reset_token() -> str:
    """
    Generate password reset token.

    VULNERABILITY: Cryptographically weak random
    CWE-338: Use of Cryptographically Weak PRNG
    """
    import random
    import string

    # BAD: random.random() is not cryptographically secure
    token = "".join(random.choices(string.ascii_letters + string.digits, k=32))
    return token


# VULNERABILITY 14: Information Exposure (Low Severity)
@app.route("/debug")
def debug_info():
    """
    Debug endpoint.

    VULNERABILITY: Information exposure
    CWE-200: Information Exposure
    """
    # BAD: Exposing sensitive system information
    return {
        "environment": os.environ,  # Exposes all env vars including secrets
        "python_path": os.sys.path,
        "working_dir": os.getcwd(),
    }


# VULNERABILITY 15: Race Condition (Medium Severity)
def transfer_money(from_account: int, to_account: int, amount: float) -> bool:
    """
    Transfer money between accounts.

    VULNERABILITY: Race condition (TOCTOU)
    CWE-362: Time-of-check Time-of-use Race Condition
    """
    # BAD: Check balance and deduct in separate steps
    balance = get_account_balance(from_account)

    if balance >= amount:
        # Race condition window here!
        # Another thread could deduct from same account
        deduct_from_account(from_account, amount)
        add_to_account(to_account, amount)
        return True

    return False


def get_account_balance(account_id: int) -> float:
    """Mock function"""
    return 1000.0


def deduct_from_account(account_id: int, amount: float) -> None:
    """Mock function"""
    pass


def add_to_account(account_id: int, amount: float) -> None:
    """Mock function"""
    pass


# SECURE EXAMPLES (for comparison)


# GOOD: Parameterized query prevents SQL injection
def get_user_by_id_safe(user_id: int) -> dict[str, Any]:
    """Secure version using parameterized query."""
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # GOOD: Using parameterized query
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

    result = cursor.fetchone()
    conn.close()

    return {"id": result[0], "name": result[1]} if result else None


# GOOD: Input validation and safe execution
def ping_host_safe(hostname: str) -> str:
    """Secure version with input validation."""
    import re

    # GOOD: Validate hostname format
    if not re.match(r"^[a-zA-Z0-9.-]+$", hostname):
        raise ValueError("Invalid hostname")

    # GOOD: Using list instead of shell
    result = subprocess.run(
        ["ping", "-c", "4", hostname],
        capture_output=True,
        text=True,
        shell=False,  # No shell = no injection
    )
    return result.stdout


# GOOD: Path validation
def read_user_file_safe(filename: str) -> str:
    """Secure version with path validation."""
    import os.path

    # GOOD: Validate filename
    if ".." in filename or "/" in filename:
        raise ValueError("Invalid filename")

    base_dir = "/var/www/uploads/"
    file_path = os.path.join(base_dir, filename)

    # GOOD: Verify final path is within base_dir
    real_path = os.path.realpath(file_path)
    if not real_path.startswith(os.path.realpath(base_dir)):
        raise ValueError("Path traversal detected")

    with open(file_path) as f:
        return f.read()


if __name__ == "__main__":
    print("Vulnerable application loaded")
    print("This code contains intentional vulnerabilities for demo purposes")
    print("Run Code Scalpel security_scan to find them all!")
