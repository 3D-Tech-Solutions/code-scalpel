package code_scalpel.devsecops

# SBOM (Software Bill of Materials) Validation Policy
# Enforces dependency security and supply chain integrity
#
# Rules:
# 1. All dependencies must be inventoried
# 2. Known vulnerabilities (CVEs) must be addressed
# 3. License compatibility checked
# 4. Deprecated packages flagged
# 5. Unmaintained packages identified

import future.keywords.if
import future.keywords.in

# Known vulnerable packages (example list - integrate with actual CVE databases)
vulnerable_packages := {
    "lodash": {"versions": ["<4.17.21"], "cve": "CVE-2021-23337", "severity": "HIGH"},
    "axios": {"versions": ["<0.21.1"], "cve": "CVE-2020-28168", "severity": "MEDIUM"},
    "express": {"versions": ["<4.17.3"], "cve": "CVE-2022-24999", "severity": "HIGH"},
    "django": {"versions": ["<3.2.13"], "cve": "CVE-2022-28346", "severity": "HIGH"},
    "flask": {"versions": ["<2.2.5"], "cve": "CVE-2023-30861", "severity": "HIGH"},
    "requests": {"versions": ["<2.31.0"], "cve": "CVE-2023-32681", "severity": "MEDIUM"}
}

# Deprecated packages
deprecated_packages := {
    "request": "Package deprecated. Use axios or node-fetch instead.",
    "moment": "Package in maintenance mode. Use date-fns or dayjs instead.",
    "babel-core": "Deprecated. Use @babel/core instead.",
    "node-uuid": "Deprecated. Use uuid instead."
}

# License incompatibilities (example - customize for your needs)
incompatible_licenses := {
    "GPL": ["MIT", "Apache-2.0", "BSD"],  # GPL is viral
    "AGPL": ["MIT", "Apache-2.0", "BSD"]  # AGPL even more restrictive
}

# Check if package is vulnerable
is_vulnerable(pkg_name, pkg_version) if {
    vuln := vulnerable_packages[pkg_name]
    some version_constraint in vuln.versions
    # Simplified version check - real impl would use semver
    version_constraint == concat("", ["<", pkg_version])
}

# Check package.json dependencies
violation[{"msg": msg, "severity": "HIGH", "cve": cve}] if {
    file := input.files[_]
    file.path == "package.json"
    
    # Parse dependencies
    dep := input.dependencies[_]
    vuln := vulnerable_packages[dep.name]
    is_vulnerable(dep.name, dep.version)
    
    msg := sprintf(
        "Vulnerable package '%s@%s' in package.json. %s (Severity: %s). Update to safe version.",
        [dep.name, dep.version, vuln.cve, vuln.severity]
    )
    cve := vuln.cve
}

# Check requirements.txt dependencies
violation[{"msg": msg, "severity": "HIGH", "cve": cve}] if {
    file := input.files[_]
    file.path == "requirements.txt"
    
    dep := input.dependencies[_]
    vuln := vulnerable_packages[dep.name]
    is_vulnerable(dep.name, dep.version)
    
    msg := sprintf(
        "Vulnerable package '%s==%s' in requirements.txt. %s (Severity: %s). Update to safe version.",
        [dep.name, dep.version, vuln.cve, vuln.severity]
    )
    cve := vuln.cve
}

# Check for deprecated packages
violation[{"msg": msg, "severity": "MEDIUM"}] if {
    dep := input.dependencies[_]
    reason := deprecated_packages[dep.name]
    
    msg := sprintf(
        "Deprecated package '%s' detected. %s",
        [dep.name, reason]
    )
}

# Check for missing SBOM
violation[{"msg": msg, "severity": "MEDIUM"}] if {
    # Has dependencies but no SBOM
    count(input.dependencies) > 0
    not any([file | 
        file := input.files[_]
        endswith(file.path, "sbom.json")
    ])
    not any([file | 
        file := input.files[_]
        endswith(file.path, "bom.json")
    ])
    
    msg := "Missing Software Bill of Materials (SBOM). Generate using CycloneDX or SPDX format."
}

# Check for dependency lock files
violation[{"msg": msg, "severity": "HIGH"}] if {
    some file in input.files
    file.path == "package.json"
    
    not any([f | 
        f := input.files[_]
        f.path == "package-lock.json"
    ])
    not any([f | 
        f := input.files[_]
        f.path == "yarn.lock"
    ])
    
    msg := "Missing dependency lock file (package-lock.json or yarn.lock). Lock files ensure reproducible builds."
}

violation[{"msg": msg, "severity": "HIGH"}] if {
    some file in input.files
    file.path == "requirements.txt"
    
    # Check if versions are pinned
    not contains(file.content, "==")
    
    msg := "requirements.txt should pin exact versions (use '==' not '>=') for reproducibility."
}

# Check for unmaintained packages (no updates in 2+ years)
violation[{"msg": msg, "severity": "LOW"}] if {
    dep := input.dependencies[_]
    dep.last_update_days > 730  # 2 years
    
    msg := sprintf(
        "Package '%s' hasn't been updated in %d days. Consider finding actively maintained alternative.",
        [dep.name, dep.last_update_days]
    )
}

# Check for too many dependencies
violation[{"msg": msg, "severity": "LOW"}] if {
    dep_count := count(input.dependencies)
    dep_count > 100
    
    msg := sprintf(
        "Project has %d dependencies. Consider reducing attack surface by removing unused dependencies.",
        [dep_count]
    )
}

# License compatibility checks
violation[{"msg": msg, "severity": "MEDIUM"}] if {
    dep := input.dependencies[_]
    project_license := input.project.license
    dep_license := dep.license
    
    # Check if licenses are incompatible
    incompatible := incompatible_licenses[dep_license]
    project_license in incompatible
    
    msg := sprintf(
        "License conflict: Project uses '%s' but dependency '%s' uses '%s' which may be incompatible.",
        [project_license, dep.name, dep_license]
    )
}

# Remediation suggestions
remediation[suggestion] if {
    count(violation) > 0
    suggestion := "Run 'npm audit fix' or 'pip-audit --fix' to auto-update vulnerable packages"
}

remediation[suggestion] if {
    count(violation) > 0
    suggestion := "Use Dependabot or Renovate Bot for automated dependency updates"
}

remediation[suggestion] if {
    count(violation) > 0
    suggestion := "Generate SBOM with: 'cyclonedx-bom' or 'syft'"
}

remediation[suggestion] if {
    count(violation) > 0
    suggestion := "Scan for vulnerabilities with: 'grype', 'trivy', or 'snyk'"
}

allow if {
    count(violation) == 0
}

deny[msg] if {
    v := violation[_]
    msg := v.msg
}
