package code_scalpel.devsecops

# Secret Detection Policy
# Detects hardcoded secrets, API keys, tokens, and credentials
#
# Rules:
# 1. No hardcoded passwords
# 2. No API keys or tokens
# 3. No private keys
# 4. No AWS/Cloud credentials
# 5. No database connection strings with passwords
# 6. Use environment variables or secret managers

import future.keywords.if
import future.keywords.in

# AWS Access Keys
has_aws_key(content) if {
    regex.match("AKIA[0-9A-Z]{16}", content)
}

has_aws_secret(content) if {
    regex.match("[A-Za-z0-9/+=]{40}", content)
    contains(content, "aws")
}

# GitHub Tokens
has_github_token(content) if {
    regex.match("ghp_[A-Za-z0-9]{36}", content)
}

has_github_oauth(content) if {
    regex.match("gho_[A-Za-z0-9]{36}", content)
}

# Generic API Keys
has_api_key(content) if {
    regex.match("(?i)api[_-]?key['\"]?\\s*[:=]\\s*['\"][A-Za-z0-9_\\-]{20,}['\"]", content)
}

has_secret_key(content) if {
    regex.match("(?i)secret[_-]?key['\"]?\\s*[:=]\\s*['\"][A-Za-z0-9_\\-]{20,}['\"]", content)
}

# Private Keys
has_private_key(content) if {
    contains(content, "BEGIN RSA PRIVATE KEY")
}

has_private_key(content) if {
    contains(content, "BEGIN PRIVATE KEY")
}

has_private_key(content) if {
    contains(content, "BEGIN OPENSSH PRIVATE KEY")
}

# Database Credentials
has_db_password(content) if {
    regex.match("(?i)(mysql|postgresql|mongodb|redis)://[^:]+:[^@]+@", content)
}

has_db_connection_string(content) if {
    regex.match("(?i)(server|host)=[^;]+;.*password=[^;]+", content)
}

# OAuth Tokens
has_oauth_token(content) if {
    regex.match("(?i)oauth[_-]?token['\"]?\\s*[:=]\\s*['\"][A-Za-z0-9_\\-]{20,}['\"]", content)
}

# Slack Tokens
has_slack_token(content) if {
    regex.match("xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[A-Za-z0-9]{24,}", content)
}

# Stripe Keys
has_stripe_key(content) if {
    regex.match("sk_live_[A-Za-z0-9]{24,}", content)
}

has_stripe_key(content) if {
    regex.match("rk_live_[A-Za-z0-9]{24,}", content)
}

# JWT Secrets
has_jwt_secret(content) if {
    regex.match("(?i)jwt[_-]?secret['\"]?\\s*[:=]\\s*['\"][A-Za-z0-9_\\-]{20,}['\"]", content)
}

# Generic Password Patterns
has_hardcoded_password(content) if {
    regex.match("(?i)password['\"]?\\s*[:=]\\s*['\"][^'\"]{8,}['\"]", content)
    not contains(content, "password = os.environ")
    not contains(content, "password = config")
    not contains(content, "password=input(")
}

# Violations
violation[{"msg": msg, "severity": "CRITICAL", "type": "aws_key"}] if {
    file := input.files[_]
    has_aws_key(file.content)
    msg := sprintf("AWS Access Key detected in '%s'. Remove immediately and rotate credentials!", [file.path])
}

violation[{"msg": msg, "severity": "CRITICAL", "type": "github_token"}] if {
    file := input.files[_]
    has_github_token(file.content)
    msg := sprintf("GitHub Personal Access Token detected in '%s'. Remove and rotate token!", [file.path])
}

violation[{"msg": msg, "severity": "CRITICAL", "type": "private_key"}] if {
    file := input.files[_]
    has_private_key(file.content)
    msg := sprintf("Private key detected in '%s'. Remove immediately and regenerate keys!", [file.path])
}

violation[{"msg": msg, "severity": "CRITICAL", "type": "api_key"}] if {
    file := input.files[_]
    has_api_key(file.content)
    msg := sprintf("API key detected in '%s'. Use environment variables instead.", [file.path])
}

violation[{"msg": msg, "severity": "CRITICAL", "type": "secret_key"}] if {
    file := input.files[_]
    has_secret_key(file.content)
    msg := sprintf("Secret key detected in '%s'. Use environment variables or secret manager.", [file.path])
}

violation[{"msg": msg, "severity": "HIGH", "type": "db_password"}] if {
    file := input.files[_]
    has_db_password(file.content)
    msg := sprintf("Database password in connection string in '%s'. Use environment variables.", [file.path])
}

violation[{"msg": msg, "severity": "HIGH", "type": "oauth_token"}] if {
    file := input.files[_]
    has_oauth_token(file.content)
    msg := sprintf("OAuth token detected in '%s'. Use secure token storage.", [file.path])
}

violation[{"msg": msg, "severity": "HIGH", "type": "slack_token"}] if {
    file := input.files[_]
    has_slack_token(file.content)
    msg := sprintf("Slack token detected in '%s'. Remove and rotate token.", [file.path])
}

violation[{"msg": msg, "severity": "HIGH", "type": "stripe_key"}] if {
    file := input.files[_]
    has_stripe_key(file.content)
    msg := sprintf("Stripe API key detected in '%s'. Remove and rotate immediately!", [file.path])
}

violation[{"msg": msg, "severity": "HIGH", "type": "jwt_secret"}] if {
    file := input.files[_]
    has_jwt_secret(file.content)
    msg := sprintf("JWT secret detected in '%s'. Use environment variables.", [file.path])
}

violation[{"msg": msg, "severity": "MEDIUM", "type": "password"}] if {
    file := input.files[_]
    has_hardcoded_password(file.content)
    msg := sprintf("Hardcoded password detected in '%s'. Use environment variables or secret manager.", [file.path])
}

# Remediation suggestions
remediation[suggestion] if {
    count(violation) > 0
    suggestion := "Use environment variables: os.environ.get('SECRET_KEY')"
}

remediation[suggestion] if {
    count(violation) > 0
    suggestion := "Use secret managers: AWS Secrets Manager, HashiCorp Vault, Azure Key Vault"
}

remediation[suggestion] if {
    count(violation) > 0
    suggestion := "Add secrets to .gitignore and .env.example"
}

remediation[suggestion] if {
    count(violation) > 0
    suggestion := "Scan git history: git log -S 'AKIA' --all"
}

allow if {
    count(violation) == 0
}

deny[msg] if {
    v := violation[_]
    msg := v.msg
}
