"""Test fixtures for exercising all 22 MCP tools.

These fixtures provide diverse code samples to validate each tool's functionality.
"""

# Python test code - complex enough to exercise all tools
PYTHON_CODE_BASIC = '''
def greet(name: str) -> str:
    """Return a greeting message."""
    return f"Hello, {name}!"

def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two numbers."""
    return a + b

class Calculator:
    """A simple calculator class."""

    def __init__(self, initial_value: float = 0):
        self.value = initial_value

    def add(self, x: float) -> float:
        """Add x to the current value."""
        self.value += x
        return self.value

    def multiply(self, x: float) -> float:
        """Multiply current value by x."""
        self.value *= x
        return self.value
'''

PYTHON_CODE_COMPLEX = '''
import os
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class User:
    """User data class."""
    id: int
    name: str
    email: str
    active: bool = True

def process_users(users: List[User]) -> Dict[int, User]:
    """Process a list of users into a dictionary."""
    result = {}
    for user in users:
        if user.active:
            if user.email.endswith('@company.com'):
                result[user.id] = user
            elif user.name.startswith('Admin'):
                result[user.id] = user
    return result

class UserService:
    """Service for managing users."""

    def __init__(self, db_connection):
        self.db = db_connection
        self._cache = {}

    def get_user(self, user_id: int) -> Optional[User]:
        """Get a user by ID."""
        if user_id in self._cache:
            return self._cache[user_id]
        user = self.db.query(User).filter(id=user_id).first()
        if user:
            self._cache[user_id] = user
        return user

    def create_user(self, name: str, email: str) -> User:
        """Create a new user."""
        user = User(id=self._generate_id(), name=name, email=email)
        self.db.add(user)
        self.db.commit()
        return user

    def _generate_id(self) -> int:
        """Generate a unique ID."""
        return int(os.urandom(4).hex(), 16)
'''

# Python code with security vulnerabilities for security_scan
PYTHON_CODE_VULNERABLE = '''
import os
import pickle
import sqlite3
from flask import Flask, request

app = Flask(__name__)

@app.route('/user/<user_id>')
def get_user(user_id):
    """Vulnerable to SQL injection."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE id = {user_id}"  # SQL Injection!
    cursor.execute(query)
    return str(cursor.fetchone())

@app.route('/search')
def search():
    """Vulnerable to XSS."""
    query = request.args.get('q', '')
    return f"<h1>Search results for: {query}</h1>"  # XSS!

@app.route('/run')
def run_command():
    """Vulnerable to command injection."""
    cmd = request.args.get('cmd', 'echo hello')
    result = os.system(cmd)  # Command Injection!
    return str(result)

@app.route('/load')
def load_data():
    """Vulnerable to insecure deserialization."""
    data = request.get_data()
    obj = pickle.loads(data)  # Insecure Deserialization!
    return str(obj)

API_KEY = "sk-1234567890abcdef"  # Hardcoded Secret!
'''

# JavaScript code for polyglot testing
JAVASCRIPT_CODE = """
import { useState, useEffect } from 'react';

export function useUserData(userId) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        async function fetchUser() {
            try {
                const response = await fetch(`/api/users/${userId}`);
                if (!response.ok) throw new Error('Failed to fetch');
                const data = await response.json();
                setUser(data);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }

        if (userId) {
            fetchUser();
        }
    }, [userId]);

    return { user, loading, error };
}

export class UserService {
    constructor(apiBase) {
        this.apiBase = apiBase;
    }

    async getUser(id) {
        const response = await fetch(`${this.apiBase}/users/${id}`);
        return response.json();
    }

    async createUser(userData) {
        const response = await fetch(`${this.apiBase}/users`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        });
        return response.json();
    }
}
"""

# TypeScript code with type evaporation issues
TYPESCRIPT_CODE_FRONTEND = """
interface User {
    id: number;
    name: string;
    email: string;
}

async function fetchUser(id: number): Promise<User> {
    const response = await fetch(`/api/users/${id}`);
    const data = await response.json();  // Type evaporation: any
    return data;  // No runtime validation!
}

function processUserData(data: any): User {
    // Implicit any -> User conversion
    return {
        id: data.id,
        name: data.name,
        email: data.email
    };
}

export async function getUserEmail(userId: number): Promise<string> {
    const user = await fetchUser(userId);
    return user.email;  // Could be undefined at runtime!
}
"""

TYPESCRIPT_CODE_BACKEND = """
from pydantic import BaseModel
from fastapi import FastAPI

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    created_at: str  # Extra field not in frontend interface!

app = FastAPI()

@app.get("/api/users/{user_id}")
def get_user(user_id: int) -> UserResponse:
    return UserResponse(
        id=user_id,
        name="John Doe",
        email="john@example.com",
        created_at="2025-01-01T00:00:00Z"
    )
"""

# Java code for polyglot testing
JAVA_CODE = """
package com.example.service;

import java.util.List;
import java.util.Optional;

public class UserRepository {
    private final Database database;

    public UserRepository(Database database) {
        this.database = database;
    }

    public Optional<User> findById(Long id) {
        String query = "SELECT * FROM users WHERE id = ?";
        return database.querySingle(query, id);
    }

    public List<User> findByStatus(String status) {
        String query = "SELECT * FROM users WHERE status = ?";
        return database.queryList(query, status);
    }

    public void save(User user) {
        if (user.getId() == null) {
            database.insert("users", user);
        } else {
            database.update("users", user);
        }
    }

    public void delete(Long id) {
        database.delete("users", id);
    }
}

class User {
    private Long id;
    private String name;
    private String email;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
}
"""

# Code with symbolic execution targets
SYMBOLIC_EXECUTION_CODE = '''
def calculate_discount(price: float, quantity: int, is_premium: bool) -> float:
    """Calculate discount based on purchase conditions."""
    if price <= 0:
        raise ValueError("Price must be positive")

    discount = 0.0

    if quantity >= 100:
        discount = 0.20  # 20% bulk discount
    elif quantity >= 50:
        discount = 0.10  # 10% medium bulk
    elif quantity >= 10:
        discount = 0.05  # 5% small bulk

    if is_premium:
        discount += 0.05  # Additional 5% for premium

    if discount > 0.25:
        discount = 0.25  # Cap at 25%

    return price * quantity * (1 - discount)


def loan_approval(credit_score: int, income: float, debt: float) -> str:
    """Determine loan approval status."""
    if credit_score < 300 or credit_score > 850:
        return "INVALID_SCORE"

    if credit_score < 500:
        return "REJECT"

    debt_ratio = debt / income if income > 0 else float('inf')

    if credit_score >= 750 and debt_ratio < 0.3:
        return "INSTANT_APPROVE"

    if credit_score >= 650 and debt_ratio < 0.4:
        return "APPROVE"

    if credit_score >= 600 and debt_ratio < 0.35:
        return "CONDITIONAL"

    return "MANUAL_REVIEW"
'''

# Cross-file dependency structure (simulated as strings)
CROSS_FILE_MODULE_A = '''
# module_a.py
from module_b import helper_function

def main_function(data):
    """Main entry point."""
    processed = preprocess(data)
    result = helper_function(processed)
    return postprocess(result)

def preprocess(data):
    """Preprocess input data."""
    return data.strip().lower()

def postprocess(result):
    """Postprocess output data."""
    return f"Result: {result}"
'''

CROSS_FILE_MODULE_B = '''
# module_b.py
from module_c import utility

def helper_function(data):
    """Helper function using utility."""
    validated = validate(data)
    return utility(validated)

def validate(data):
    """Validate input data."""
    if not data:
        raise ValueError("Empty data")
    return data
'''

CROSS_FILE_MODULE_C = '''
# module_c.py

def utility(data):
    """Utility function."""
    return data.upper()

def unused_function():
    """This function is never called."""
    pass
'''

# Test cases dictionary for easy access
TEST_FIXTURES = {
    "python_basic": PYTHON_CODE_BASIC,
    "python_complex": PYTHON_CODE_COMPLEX,
    "python_vulnerable": PYTHON_CODE_VULNERABLE,
    "javascript": JAVASCRIPT_CODE,
    "typescript_frontend": TYPESCRIPT_CODE_FRONTEND,
    "typescript_backend": TYPESCRIPT_CODE_BACKEND,
    "java": JAVA_CODE,
    "symbolic_execution": SYMBOLIC_EXECUTION_CODE,
    "cross_file_a": CROSS_FILE_MODULE_A,
    "cross_file_b": CROSS_FILE_MODULE_B,
    "cross_file_c": CROSS_FILE_MODULE_C,
}

if __name__ == "__main__":
    print("Test fixtures loaded successfully!")
    for name, code in TEST_FIXTURES.items():
        lines = len(code.strip().split("\n"))
        print(f"  - {name}: {lines} lines")
