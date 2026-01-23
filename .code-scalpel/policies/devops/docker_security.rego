package code_scalpel.devops

# Dockerfile Security Policy
# Enforces Docker container security best practices
#
# Rules:
# 1. No secrets in Dockerfile
# 2. No root user (use USER directive)
# 3. Use specific image tags (not :latest)
# 4. Minimize layers
# 5. Use multi-stage builds for production
# 6. Set health checks
# 7. Use .dockerignore

import future.keywords.if
import future.keywords.in

# Check for secrets in Dockerfile
has_secrets(content) if {
    # Check for common secret patterns
    regex.match("(?i)(password|api[_-]?key|secret|token|credential)\\s*=", content)
}

has_hardcoded_secrets(content) if {
    # Check for actual secret values
    regex.match("(AWS|AKIA|ghp_|sk-)[A-Za-z0-9+/]{20,}", content)
}

# Check for root user
uses_root_user(lines) if {
    # No USER directive found
    not any([line | 
        line := lines[_]
        startswith(line, "USER ")
    ])
}

uses_root_user(lines) if {
    # USER root explicitly set
    some line in lines
    line == "USER root"
}

# Check for :latest tag
uses_latest_tag(lines) if {
    some line in lines
    startswith(line, "FROM ")
    contains(line, ":latest")
}

uses_no_tag(lines) if {
    some line in lines
    startswith(line, "FROM ")
    not contains(line, ":")
}

# Check for multi-stage builds
is_multistage(lines) if {
    from_count := count([line | 
        line := lines[_]
        startswith(line, "FROM ")
    ])
    from_count > 1
}

# Check for HEALTHCHECK
has_healthcheck(lines) if {
    some line in lines
    startswith(line, "HEALTHCHECK ")
}

# Violations
violation[{"msg": msg, "severity": "CRITICAL"}] if {
    file := input.files[_]
    endswith(file.path, "Dockerfile")
    has_secrets(file.content)
    msg := sprintf("Dockerfile '%s' contains potential secrets. Use build args or environment variables.", [file.path])
}

violation[{"msg": msg, "severity": "CRITICAL"}] if {
    file := input.files[_]
    endswith(file.path, "Dockerfile")
    has_hardcoded_secrets(file.content)
    msg := sprintf("Dockerfile '%s' contains hardcoded secrets (AWS keys, GitHub tokens, etc.). Remove immediately!", [file.path])
}

violation[{"msg": msg, "severity": "HIGH"}] if {
    file := input.files[_]
    endswith(file.path, "Dockerfile")
    lines := split(file.content, "\n")
    uses_root_user(lines)
    msg := sprintf("Dockerfile '%s' runs as root user. Add 'USER <non-root-user>' directive.", [file.path])
}

violation[{"msg": msg, "severity": "MEDIUM"}] if {
    file := input.files[_]
    endswith(file.path, "Dockerfile")
    lines := split(file.content, "\n")
    uses_latest_tag(lines)
    msg := sprintf("Dockerfile '%s' uses ':latest' tag. Pin to specific version for reproducibility.", [file.path])
}

violation[{"msg": msg, "severity": "MEDIUM"}] if {
    file := input.files[_]
    endswith(file.path, "Dockerfile")
    lines := split(file.content, "\n")
    uses_no_tag(lines)
    msg := sprintf("Dockerfile '%s' uses no tag (defaults to :latest). Pin to specific version.", [file.path])
}

violation[{"msg": msg, "severity": "LOW"}] if {
    file := input.files[_]
    endswith(file.path, "Dockerfile")
    lines := split(file.content, "\n")
    not is_multistage(lines)
    # Only warn for production
    contains(file.path, "prod")
    msg := sprintf("Dockerfile '%s' should use multi-stage builds for production to minimize image size.", [file.path])
}

violation[{"msg": msg, "severity": "LOW"}] if {
    file := input.files[_]
    endswith(file.path, "Dockerfile")
    lines := split(file.content, "\n")
    not has_healthcheck(lines)
    msg := sprintf("Dockerfile '%s' missing HEALTHCHECK. Add health check for monitoring.", [file.path])
}

# Check for excessive layers (too many RUN commands)
violation[{"msg": msg, "severity": "LOW"}] if {
    file := input.files[_]
    endswith(file.path, "Dockerfile")
    lines := split(file.content, "\n")
    run_count := count([line | 
        line := lines[_]
        startswith(line, "RUN ")
    ])
    run_count > 10
    msg := sprintf("Dockerfile '%s' has %d RUN commands. Consider combining them to reduce layers.", [file.path, run_count])
}

# Check for .dockerignore
dockerignore_exists if {
    some file in input.files
    endswith(file.path, ".dockerignore")
}

violation[{"msg": msg, "severity": "MEDIUM"}] if {
    # Has Dockerfile but no .dockerignore
    some file in input.files
    endswith(file.path, "Dockerfile")
    not dockerignore_exists
    msg := "Missing .dockerignore file. Create one to exclude unnecessary files from build context."
}

allow if {
    count(violation) == 0
}

deny[msg] if {
    v := violation[_]
    msg := v.msg
}
