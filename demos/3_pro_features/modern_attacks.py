"""
Modern Attack Vectors Demo
For Code Scalpel Pro Tier Security Scanning

These vulnerabilities are detected by Pro tier but NOT by Community tier.
Demonstrates the value of upgrading for modern security coverage.
"""

# ==============================================================================
# NoSQL INJECTION EXAMPLES (Pro Tier Only)
# ==============================================================================


def nosql_login_vulnerable(username: str, password: str) -> dict:
    """
    MongoDB authentication with NoSQL injection vulnerability.

    VULNERABILITY: NoSQL injection via $where operator
    CWE-943: Improper Neutralization of Special Elements in Data Query Logic
    DETECTED BY: Pro tier only
    """
    from pymongo import MongoClient

    client = MongoClient("mongodb://localhost:27017/")
    db = client["myapp"]

    # VULNERABLE: User input in $where clause
    # Attack: password = "'; return true; //"
    query = {"username": username, "$where": f"this.password == '{password}'"}

    user = db.users.find_one(query)
    return user


def nosql_search_vulnerable(search_query: dict) -> list:
    """
    MongoDB search with object injection.

    VULNERABILITY: Accepting untrusted objects in queries
    ATTACK: {"$gt": ""} bypasses authentication
    DETECTED BY: Pro tier only
    """
    from pymongo import MongoClient

    client = MongoClient("mongodb://localhost:27017/")
    db = client["myapp"]

    # VULNERABLE: Passing user-controlled dict directly
    # Attack: search_query = {"$ne": null} returns all documents
    results = db.products.find(search_query)
    return list(results)


# ==============================================================================
# LDAP INJECTION EXAMPLES (Pro Tier Only)
# ==============================================================================


def ldap_authenticate(username: str, password: str) -> bool:
    """
    LDAP authentication with injection vulnerability.

    VULNERABILITY: LDAP injection in filter
    CWE-90: Improper Neutralization of Special Elements in LDAP Queries
    DETECTED BY: Pro tier only
    """
    import ldap

    # VULNERABLE: User input in LDAP filter
    # Attack: username = "*)(uid=*))(|(uid=*"
    search_filter = f"(&(uid={username})(password={password}))"

    ldap_conn = ldap.initialize("ldap://localhost:389")

    try:
        results = ldap_conn.search_s("dc=example,dc=com", ldap.SCOPE_SUBTREE, search_filter)
        return len(results) > 0
    except Exception:
        return False


def ldap_search_users(department: str) -> list:
    """
    LDAP user search with injection.

    VULNERABILITY: LDAP injection
    ATTACK: department = "*)(&(uid=admin)" bypasses filters
    DETECTED BY: Pro tier only
    """
    import ldap

    # VULNERABLE: Unescaped user input
    search_filter = f"(department={department})"

    ldap_conn = ldap.initialize("ldap://localhost:389")
    results = ldap_conn.search_s(
        "ou=users,dc=example,dc=com",
        ldap.SCOPE_SUBTREE,
        search_filter,
        ["uid", "cn", "mail"],
    )

    return results


# ==============================================================================
# HARDCODED SECRETS (Pro Tier Only)
# ==============================================================================

# VULNERABILITY: AWS credentials hardcoded
# DETECTED BY: Pro tier secret detection
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# VULNERABILITY: Database password in code
# DETECTED BY: Pro tier secret detection
DATABASE_URL = "postgresql://admin:SuperSecret123!@prod-db.example.com:5432/maindb"

# VULNERABILITY: API keys hardcoded
# DETECTED BY: Pro tier secret detection
STRIPE_SECRET_KEY = "sk_live_51HvGqLJK9m8..."
SENDGRID_API_KEY = "SG.xxxxxxxxxxxxxxxxxxx.yyyyyyyyyyyyyyyyyyyyyyyyyyyy"
TWILIO_AUTH_TOKEN = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"

# VULNERABILITY: Private key in source
# DETECTED BY: Pro tier secret detection
PRIVATE_KEY = """
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA1234567890abcdefghijklmnop...
-----END RSA PRIVATE KEY-----
"""

# VULNERABILITY: GitHub token
# DETECTED BY: Pro tier secret detection
GITHUB_TOKEN = "ghp_1234567890abcdefghijklmnopqrstuv"


def connect_to_aws():
    """
    Uses hardcoded AWS credentials.

    VULNERABILITY: Exposes credentials if code is public/leaked
    DETECTED BY: Pro tier only
    """
    import boto3

    # VULNERABLE: Using hardcoded credentials
    client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )

    return client


# ==============================================================================
# JWT/TOKEN VULNERABILITIES (Pro Tier Only)
# ==============================================================================


def create_jwt_insecure(user_id: int) -> str:
    """
    Creates JWT with weak secret.

    VULNERABILITY: Weak JWT secret
    CWE-326: Inadequate Encryption Strength
    DETECTED BY: Pro tier only
    """
    import jwt

    # VULNERABLE: Weak secret key
    secret = "secret"  # Easily guessable

    payload = {"user_id": user_id, "role": "user"}

    token = jwt.encode(payload, secret, algorithm="HS256")
    return token


def verify_jwt_no_signature(token: str) -> dict:
    """
    Verifies JWT without checking signature.

    VULNERABILITY: JWT signature bypass
    CWE-347: Improper Verification of Cryptographic Signature
    DETECTED BY: Pro tier only
    """
    import jwt

    # VULNERABLE: verify_signature=False allows tampering
    payload = jwt.decode(token, options={"verify_signature": False})

    return payload


# ==============================================================================
# REGEX DENIAL OF SERVICE (ReDoS) (Pro Tier Only)
# ==============================================================================


def validate_email_redos(email: str) -> bool:
    """
    Email validation with ReDoS vulnerability.

    VULNERABILITY: Catastrophic backtracking
    CWE-1333: Inefficient Regular Expression Complexity
    DETECTED BY: Pro tier only
    """
    import re

    # VULNERABLE: Nested quantifiers cause exponential backtracking
    # Attack: "a" * 50 + "@" causes CPU spike
    pattern = r"^([a-zA-Z0-9])*([a-zA-Z0-9])*@[a-zA-Z0-9]+\.[a-zA-Z0-9]+$"

    return re.match(pattern, email) is not None


# ==============================================================================
# PROTOTYPE POLLUTION (JavaScript) (Pro Tier Only)
# ==============================================================================


def merge_objects_prototype_pollution(target: dict, source: dict) -> dict:
    """
    Deep merge with prototype pollution.

    VULNERABILITY: Allows __proto__ pollution
    CWE-1321: Improperly Controlled Modification of Object Prototype
    DETECTED BY: Pro tier only (for Python dict merges)
    """
    # VULNERABLE: No protection against __proto__ or constructor
    # Attack: source = {"__proto__": {"isAdmin": true}}
    for key, value in source.items():
        if isinstance(value, dict) and key in target:
            target[key] = merge_objects_prototype_pollution(target[key], value)
        else:
            target[key] = value  # Allows __proto__ assignment

    return target


# ==============================================================================
# TIMING ATTACKS (Pro Tier Only)
# ==============================================================================


def compare_tokens_insecure(user_token: str, valid_token: str) -> bool:
    """
    Token comparison vulnerable to timing attacks.

    VULNERABILITY: Timing side-channel
    CWE-208: Observable Timing Discrepancy
    DETECTED BY: Pro tier only
    """
    # VULNERABLE: String comparison returns early on mismatch
    # Attacker can brute-force by measuring response time
    return user_token == valid_token


def compare_passwords_insecure(input_password: str, stored_hash: str) -> bool:
    """
    Password comparison with timing vulnerability.

    VULNERABILITY: Early return on length mismatch
    DETECTED BY: Pro tier only
    """
    import hashlib

    input_hash = hashlib.sha256(input_password.encode()).hexdigest()

    # VULNERABLE: Length check reveals information
    if len(input_hash) != len(stored_hash):
        return False

    # VULNERABLE: Character-by-character comparison
    for i in range(len(input_hash)):
        if input_hash[i] != stored_hash[i]:
            return False

    return True


# ==============================================================================
# SERVER-SIDE TEMPLATE INJECTION (SSTI) (Pro Tier Only)
# ==============================================================================


def render_template_ssti(template_string: str, context: dict) -> str:
    """
    Template rendering with SSTI vulnerability.

    VULNERABILITY: Server-Side Template Injection
    CWE-94: Code Injection
    DETECTED BY: Pro tier only
    """
    from jinja2 import Template

    # VULNERABLE: User-controlled template string
    # Attack: "{{config.items()}}" exposes config
    # Attack: "{{''.__class__.__mro__[1].__subclasses__()}}" can execute code
    template = Template(template_string)
    return template.render(context)


# ==============================================================================
# OPEN REDIRECT (Pro Tier Only)
# ==============================================================================


def redirect_user(next_url: str) -> str:
    """
    Redirect without URL validation.

    VULNERABILITY: Open redirect
    CWE-601: URL Redirection to Untrusted Site
    DETECTED BY: Pro tier only
    """
    # VULNERABLE: No validation of redirect target
    # Attack: next_url = "https://evil.com/phishing"
    return f"Location: {next_url}"


# ==============================================================================
# MASS ASSIGNMENT (Pro Tier Only)
# ==============================================================================


def update_user_profile(user_id: int, update_data: dict) -> dict:
    """
    Update user profile with mass assignment vulnerability.

    VULNERABILITY: Mass assignment
    CWE-915: Improperly Controlled Modification of Dynamically-Determined Object Attributes
    DETECTED BY: Pro tier only
    """
    # VULNERABLE: Accepting arbitrary fields from user input
    # Attack: update_data = {"is_admin": True, "balance": 9999999}

    user = get_user_from_db(user_id)

    # Directly updating all fields without filtering
    for key, value in update_data.items():
        user[key] = value  # Can modify is_admin, balance, etc.

    save_user_to_db(user)
    return user


def get_user_from_db(user_id: int) -> dict:
    """Mock function"""
    return {"id": user_id, "name": "John", "is_admin": False, "balance": 100.0}


def save_user_to_db(user: dict) -> None:
    """Mock function"""
    pass


# ==============================================================================
# SECURE VERSIONS (for comparison)
# ==============================================================================


def nosql_login_secure(username: str, password: str) -> dict:
    """Secure version with parameterized query."""
    import bcrypt
    from pymongo import MongoClient

    client = MongoClient("mongodb://localhost:27017/")
    db = client["myapp"]

    # SECURE: Simple equality check, no $where
    user = db.users.find_one({"username": username})

    if user and bcrypt.checkpw(password.encode(), user["password"]):
        return user

    return None


def ldap_authenticate_secure(username: str, password: str) -> bool:
    """Secure version with LDAP escaping."""

    # SECURE: Escape special LDAP characters
    # Example safe usage:
    # safe_username = ldap.filter.escape_filter_chars(username)
    # safe_password = ldap.filter.escape_filter_chars(password)
    # search_filter = f"(&(uid={safe_username})(password={safe_password}))"
    # ... rest of authentication
    return "LDAP authentication with proper escaping"
    return False


def compare_tokens_secure(user_token: str, valid_token: str) -> bool:
    """Secure version using constant-time comparison."""
    import hmac

    # SECURE: Constant-time comparison prevents timing attacks
    return hmac.compare_digest(user_token, valid_token)


if __name__ == "__main__":
    print("Modern Attack Vectors Demo")
    print("These vulnerabilities are detected by Pro tier:")
    print("- NoSQL injection")
    print("- LDAP injection")
    print("- Hardcoded secrets")
    print("- JWT vulnerabilities")
    print("- ReDoS")
    print("- Timing attacks")
    print("- SSTI")
    print("- Open redirects")
    print("- Mass assignment")
