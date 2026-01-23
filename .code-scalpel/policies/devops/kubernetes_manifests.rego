package code_scalpel.devops

# Kubernetes Manifest Security Policy
# Enforces K8s security best practices
#
# Rules:
# 1. No privileged containers
# 2. Resource limits required
# 3. Security context enforced
# 4. No host network/PID/IPC
# 5. Read-only root filesystem
# 6. Non-root user required
# 7. Secrets properly managed

import future.keywords.if
import future.keywords.in

# Parse YAML (simplified - actual impl would use YAML parser)
is_k8s_manifest(file) if {
    contains(file.content, "apiVersion:")
    contains(file.content, "kind:")
}

# Check for privileged containers
violation[{"msg": msg, "severity": "CRITICAL"}] if {
    file := input.files[_]
    is_k8s_manifest(file)
    contains(file.content, "privileged: true")
    msg := sprintf("K8s manifest '%s' contains privileged container. This is a security risk.", [file.path])
}

# Check for host namespaces
violation[{"msg": msg, "severity": "CRITICAL"}] if {
    file := input.files[_]
    is_k8s_manifest(file)
    regex.match("(?i)hostNetwork:\\s*true", file.content)
    msg := sprintf("K8s manifest '%s' uses hostNetwork. This breaks pod isolation.", [file.path])
}

violation[{"msg": msg, "severity": "CRITICAL"}] if {
    file := input.files[_]
    is_k8s_manifest(file)
    regex.match("(?i)hostPID:\\s*true", file.content)
    msg := sprintf("K8s manifest '%s' uses hostPID. This is a security risk.", [file.path])
}

violation[{"msg": msg, "severity": "CRITICAL"}] if {
    file := input.files[_]
    is_k8s_manifest(file)
    regex.match("(?i)hostIPC:\\s*true", file.content)
    msg := sprintf("K8s manifest '%s' uses hostIPC. This is a security risk.", [file.path])
}

# Check for resource limits
violation[{"msg": msg, "severity": "HIGH"}] if {
    file := input.files[_]
    is_k8s_manifest(file)
    contains(file.content, "kind: Deployment")
    not contains(file.content, "resources:")
    msg := sprintf("K8s manifest '%s' missing resource limits. Add CPU/memory limits.", [file.path])
}

violation[{"msg": msg, "severity": "HIGH"}] if {
    file := input.files[_]
    is_k8s_manifest(file)
    contains(file.content, "resources:")
    not contains(file.content, "limits:")
    msg := sprintf("K8s manifest '%s' has resources but missing limits. Add CPU/memory limits.", [file.path])
}

# Check for security context
violation[{"msg": msg, "severity": "HIGH"}] if {
    file := input.files[_]
    is_k8s_manifest(file)
    contains(file.content, "kind: Deployment")
    not contains(file.content, "securityContext:")
    msg := sprintf("K8s manifest '%s' missing securityContext. Add security context for hardening.", [file.path])
}

# Check for root user
violation[{"msg": msg, "severity": "HIGH"}] if {
    file := input.files[_]
    is_k8s_manifest(file)
    contains(file.content, "runAsUser: 0")
    msg := sprintf("K8s manifest '%s' runs as root (UID 0). Use non-root user.", [file.path])
}

# Check for read-only root filesystem
violation[{"msg": msg, "severity": "MEDIUM"}] if {
    file := input.files[_]
    is_k8s_manifest(file)
    contains(file.content, "securityContext:")
    not contains(file.content, "readOnlyRootFilesystem: true")
    msg := sprintf("K8s manifest '%s' should use read-only root filesystem for security.", [file.path])
}

# Check for capability drops
violation[{"msg": msg, "severity": "MEDIUM"}] if {
    file := input.files[_]
    is_k8s_manifest(file)
    contains(file.content, "securityContext:")
    not contains(file.content, "drop:")
    msg := sprintf("K8s manifest '%s' should drop unnecessary capabilities (add 'drop: [ALL]').", [file.path])
}

# Check for secrets in plain text
violation[{"msg": msg, "severity": "CRITICAL"}] if {
    file := input.files[_]
    is_k8s_manifest(file)
    contains(file.content, "kind: ConfigMap")
    regex.match("(?i)(password|api[_-]?key|secret|token):\\s*['\"]?[A-Za-z0-9+/=]{10,}", file.content)
    msg := sprintf("K8s manifest '%s' contains secrets in ConfigMap. Use Secret resource instead.", [file.path])
}

# Check for latest image tag
violation[{"msg": msg, "severity": "MEDIUM"}] if {
    file := input.files[_]
    is_k8s_manifest(file)
    regex.match("image:.*:latest", file.content)
    msg := sprintf("K8s manifest '%s' uses :latest tag. Pin to specific version.", [file.path])
}

# Check for liveness/readiness probes
violation[{"msg": msg, "severity": "MEDIUM"}] if {
    file := input.files[_]
    is_k8s_manifest(file)
    contains(file.content, "kind: Deployment")
    not contains(file.content, "livenessProbe:")
    msg := sprintf("K8s manifest '%s' missing livenessProbe. Add for better reliability.", [file.path])
}

violation[{"msg": msg, "severity": "MEDIUM"}] if {
    file := input.files[_]
    is_k8s_manifest(file)
    contains(file.content, "kind: Deployment")
    not contains(file.content, "readinessProbe:")
    msg := sprintf("K8s manifest '%s' missing readinessProbe. Add for better availability.", [file.path])
}

# Check for pod disruption budget
violation[{"msg": msg, "severity": "LOW"}] if {
    file := input.files[_]
    is_k8s_manifest(file)
    contains(file.content, "kind: Deployment")
    contains(file.content, "replicas:")
    not any([f | 
        f := input.files[_]
        contains(f.content, "kind: PodDisruptionBudget")
    ])
    msg := sprintf("K8s deployment '%s' missing PodDisruptionBudget. Consider adding for high availability.", [file.path])
}

allow if {
    count(violation) == 0
}

deny[msg] if {
    v := violation[_]
    msg := v.msg
}
