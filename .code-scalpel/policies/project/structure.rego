# Code Scalpel Project Structure Policy
# Enforces consistent organization across the codebase

package project.structure

import future.keywords.if
import future.keywords.in

# Configuration loaded from .code-scalpel/project-structure.yaml
config := data.project_config

# =============================================================================
# FILE LOCATION RULES
# =============================================================================

# Rule: Files must be in their designated directories
violation[{"msg": msg, "severity": "HIGH", "file": file.path}] if {
    file := input.files[_]
    file_type := detect_file_type(file)
    file_type != "unknown"
    expected_dir := config.file_locations[file_type]
    expected_dir != null
    not path_matches(file.path, expected_dir)
    msg := sprintf("File type '%s' must be in '%s/', found in '%s'", 
                   [file_type, expected_dir, file.path])
}

# Rule: Core modules cannot be in integrations directory
violation[{"msg": msg, "severity": "CRITICAL", "file": file.path}] if {
    file := input.files[_]
    contains(file.path, "src/code_scalpel/integrations/")
    is_core_component(file)
    msg := sprintf("Core component '%s' must not be in integrations/", [file.path])
}

# Rule: Tests must be in tests/ directory
violation[{"msg": msg, "severity": "HIGH", "file": file.path}] if {
    file := input.files[_]
    is_test_file(file)
    not startswith(file.path, "tests/")
    msg := sprintf("Test file '%s' must be in tests/ directory", [file.path])
}

# =============================================================================
# README REQUIREMENTS
# =============================================================================

# Rule: Every directory must have README.md (with exclusions)
violation[{"msg": msg, "severity": "MEDIUM", "directory": dir}] if {
    dir := input.directories[_]
    not is_excluded_directory(dir)
    not has_readme(dir)
    not is_empty_directory(dir)
    msg := sprintf("Directory '%s' is missing README.md", [dir.path])
}

# Rule: READMEs must have required sections
violation[{"msg": msg, "severity": "LOW", "file": readme.path}] if {
    readme := input.files[_]
    endswith(readme.path, "README.md")
    dir_path := trim_suffix(readme.path, "/README.md")
    required := get_required_sections(dir_path)
    count(required) > 0
    missing := find_missing_sections(readme.content, required)
    count(missing) > 0
    msg := sprintf("%s missing sections: %s", 
                   [readme.path, concat(", ", missing)])
}

# Rule: Python packages must have __init__.py
violation[{"msg": msg, "severity": "HIGH", "directory": dir}] if {
    dir := input.directories[_]
    contains(dir.path, "src/code_scalpel/")
    not is_excluded_directory(dir)
    has_python_files(dir)
    not has_init_file(dir)
    msg := sprintf("Python package '%s' missing __init__.py", [dir.path])
}

# =============================================================================
# NAMING CONVENTIONS
# =============================================================================

# Rule: Python modules must follow snake_case
violation[{"msg": msg, "severity": "MEDIUM", "file": file.path}] if {
    file := input.files[_]
    endswith(file.path, ".py")
    not endswith(file.path, "__init__.py")
    filename := base_name(file.path)
    not matches_pattern(filename, config.naming_conventions["Python Module"])
    msg := sprintf("Python module '%s' must use snake_case naming", [filename])
}

# Rule: Rego policies must follow snake_case
violation[{"msg": msg, "severity": "MEDIUM", "file": file.path}] if {
    file := input.files[_]
    endswith(file.path, ".rego")
    filename := base_name(file.path)
    not matches_pattern(filename, config.naming_conventions["Rego Policy"])
    msg := sprintf("Rego policy '%s' must use snake_case naming", [filename])
}

# Rule: Test files must start with test_
violation[{"msg": msg, "severity": "HIGH", "file": file.path}] if {
    file := input.files[_]
    contains(file.path, "tests/")
    endswith(file.path, ".py")
    not endswith(file.path, "__init__.py")
    not endswith(file.path, "conftest.py")
    filename := base_name(file.path)
    not startswith(filename, "test_")
    msg := sprintf("Test file '%s' must start with 'test_'", [filename])
}

# Rule: Documentation files must use UPPERCASE
violation[{"msg": msg, "severity": "LOW", "file": file.path}] if {
    file := input.files[_]
    endswith(file.path, ".md")
    not endswith(file.path, "README.md")
    is_root_or_docs(file.path)
    filename := base_name(file.path)
    not is_uppercase_with_underscores(filename)
    msg := sprintf("Documentation '%s' should use UPPERCASE_WITH_UNDERSCORES", [filename])
}

# =============================================================================
# COHABITATION RULES
# =============================================================================

# Rule: Files must coexist with allowed types only
violation[{"msg": msg, "severity": "HIGH", "file": file.path}] if {
    file := input.files[_]
    dir_path := dir_name(file.path)
    cohabitation := config.cohabitation[dir_path]
    cohabitation != null
    file_type := detect_file_type(file)
    count(cohabitation.forbidden) > 0
    file_type in cohabitation.forbidden
    msg := sprintf("File type '%s' forbidden in '%s' - %s", 
                   [file_type, dir_path, cohabitation.rationale])
}

# Rule: Integration code cannot mix with core analysis
violation[{"msg": msg, "severity": "CRITICAL", "file": file.path}] if {
    file := input.files[_]
    contains(file.path, "src/code_scalpel/pdg_tools/")
    has_integration_import(file)
    msg := sprintf("PDG tool '%s' cannot import integrations - violates architecture", [file.path])
}

# Rule: MCP server cannot import integrations
violation[{"msg": msg, "severity": "HIGH", "file": file.path}] if {
    file := input.files[_]
    contains(file.path, "src/code_scalpel/mcp/")
    has_integration_import(file)
    msg := sprintf("MCP server '%s' cannot import integrations - keep protocol boundary clean", [file.path])
}

# =============================================================================
# MODULE DEPENDENCY RULES
# =============================================================================

# Rule: Core cannot depend on integrations
violation[{"msg": msg, "severity": "CRITICAL", "file": file.path}] if {
    file := input.files[_]
    is_core_module(file)
    imports := extract_imports(file.content)
    some imp in imports
    contains(imp, "code_scalpel.integrations")
    msg := sprintf("Core module '%s' cannot import integrations - violates clean architecture", [file.path])
}

# Rule: Graph engine has minimal dependencies
violation[{"msg": msg, "severity": "HIGH", "file": file.path}] if {
    file := input.files[_]
    contains(file.path, "src/code_scalpel/graph_engine/")
    imports := extract_imports(file.content)
    some imp in imports
    is_forbidden_graph_import(imp)
    msg := sprintf("Graph engine '%s' has forbidden import '%s' - must stay isolated", [file.path, imp])
}

# Rule: Policy engine security isolation
violation[{"msg": msg, "severity": "CRITICAL", "file": file.path}] if {
    file := input.files[_]
    contains(file.path, "src/code_scalpel/policy_engine/")
    imports := extract_imports(file.content)
    some imp in imports
    is_forbidden_policy_import(imp)
    msg := sprintf("Policy engine '%s' has forbidden import '%s' - security boundary violation", [file.path, imp])
}

# =============================================================================
# FILE SIZE LIMITS
# =============================================================================

# Rule: Python files should not be too large
violation[{"msg": msg, "severity": "WARN", "file": file.path}] if {
    file := input.files[_]
    endswith(file.path, ".py")
    line_count := count_lines(file.content)
    line_count > config.file_limits.max_lines_python
    msg := sprintf("File '%s' has %d lines (max %d) - consider refactoring", 
                   [file.path, line_count, config.file_limits.max_lines_python])
}

# Rule: Rego policies should not be too large
violation[{"msg": msg, "severity": "WARN", "file": file.path}] if {
    file := input.files[_]
    endswith(file.path, ".rego")
    line_count := count_lines(file.content)
    line_count > config.file_limits.max_lines_rego
    msg := sprintf("Policy '%s' has %d lines (max %d) - consider splitting", 
                   [file.path, line_count, config.file_limits.max_lines_rego])
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

# File type detection
detect_file_type(file) := "pdg_tool" if {
    contains(file.path, "src/code_scalpel/pdg_tools/")
    endswith(file.path, ".py")
}

detect_file_type(file) := "graph_engine" if {
    contains(file.path, "src/code_scalpel/graph_engine/")
    endswith(file.path, ".py")
}

detect_file_type(file) := "policy_engine" if {
    contains(file.path, "src/code_scalpel/policy_engine/")
    endswith(file.path, ".py")
}

detect_file_type(file) := "ai_integration" if {
    contains(file.path, "src/code_scalpel/integrations/")
    endswith(file.path, ".py")
}

detect_file_type(file) := "mcp_server" if {
    contains(file.path, "src/code_scalpel/mcp/")
    endswith(file.path, ".py")
}

detect_file_type(file) := "unit_test" if {
    contains(file.path, "tests/unit/")
    endswith(file.path, ".py")
}

detect_file_type(file) := "integration_test" if {
    contains(file.path, "tests/integration/")
    endswith(file.path, ".py")
}

detect_file_type(file) := "rego_policy" if {
    contains(file.path, ".code-scalpel/policies/")
    endswith(file.path, ".rego")
}

detect_file_type(file) := "unknown" if {
    not contains(file.path, "src/code_scalpel/")
    not contains(file.path, "tests/")
    not contains(file.path, ".code-scalpel/policies/")
}

# Path matching
path_matches(actual, expected) if {
    startswith(actual, expected)
}

# README checking
has_readme(dir) if {
    some file in input.files
    file.path == sprintf("%s/README.md", [dir.path])
}

is_excluded_directory(dir) if {
    excluded := config.readme_requirements.excluded_directories
    some pattern in excluded
    glob.match(pattern, ["/"], dir.path)
}

is_empty_directory(dir) if {
    count([f | f := input.files[_]; startswith(f.path, dir.path)]) == 0
}

# Section checking
get_required_sections(dir_path) := sections if {
    specific := config.readme_requirements.specific_requirements[dir_path]
    specific != null
    sections := specific.sections
}

get_required_sections(dir_path) := config.readme_requirements.sections if {
    specific := config.readme_requirements.specific_requirements[dir_path]
    specific == null
}

find_missing_sections(content, required) := missing if {
    present := [s | 
        s := required[_]
        section_exists(content, s)
    ]
    missing := [s | 
        s := required[_]
        not s in present
    ]
}

section_exists(content, section) if {
    contains(lower(content), lower(sprintf("# %s", [section])))
}

section_exists(content, section) if {
    contains(lower(content), lower(sprintf("## %s", [section])))
}

# Python package checking
has_python_files(dir) if {
    some file in input.files
    startswith(file.path, dir.path)
    endswith(file.path, ".py")
}

has_init_file(dir) if {
    some file in input.files
    file.path == sprintf("%s/__init__.py", [dir.path])
}

# Test file detection
is_test_file(file) if {
    endswith(file.path, ".py")
    filename := base_name(file.path)
    startswith(filename, "test_")
}

is_test_file(file) if {
    endswith(file.path, ".py")
    contains(file.path, "tests/")
}

# Core component detection
is_core_component(file) if {
    contains(file.path, "src/code_scalpel/pdg_tools/")
}

is_core_component(file) if {
    contains(file.path, "src/code_scalpel/graph_engine/")
}

is_core_component(file) if {
    contains(file.path, "src/code_scalpel/policy_engine/")
}

is_core_module(file) if {
    contains(file.path, "src/code_scalpel/")
    not contains(file.path, "src/code_scalpel/integrations/")
    not contains(file.path, "src/code_scalpel/mcp/")
}

# Import detection
has_integration_import(file) if {
    contains(file.content, "from code_scalpel.integrations")
}

has_integration_import(file) if {
    contains(file.content, "import code_scalpel.integrations")
}

extract_imports(content) := imports if {
    lines := split(content, "\n")
    imports := [imp | 
        line := lines[_]
        startswith(trim_space(line), "from ")
        or startswith(trim_space(line), "import ")
        imp := trim_space(line)
    ]
}

is_forbidden_graph_import(imp) if {
    contains(imp, "code_scalpel.pdg_tools")
}

is_forbidden_graph_import(imp) if {
    contains(imp, "code_scalpel.integrations")
}

is_forbidden_graph_import(imp) if {
    contains(imp, "code_scalpel.mcp")
}

is_forbidden_policy_import(imp) if {
    contains(imp, "code_scalpel.integrations")
}

is_forbidden_policy_import(imp) if {
    contains(imp, "code_scalpel.mcp")
}

# Naming pattern matching
matches_pattern(name, pattern) if {
    regex.match(pattern, name)
}

is_uppercase_with_underscores(filename) if {
    name := trim_suffix(filename, ".md")
    regex.match("^[A-Z][A-Z0-9_]*$", name)
}

is_root_or_docs(path) if {
    startswith(path, "./")
    not startswith(path, "./docs/")
    not startswith(path, "./src/")
    not startswith(path, "./tests/")
}

is_root_or_docs(path) if {
    startswith(path, "docs/")
}

# Utility functions
base_name(path) := name if {
    parts := split(path, "/")
    name := parts[count(parts) - 1]
}

dir_name(path) := dir if {
    parts := split(path, "/")
    dir_parts := array.slice(parts, 0, count(parts) - 1)
    dir := concat("/", dir_parts)
}

trim_suffix(str, suffix) := result if {
    endswith(str, suffix)
    result := substring(str, 0, count(str) - count(suffix))
}

trim_suffix(str, suffix) := str if {
    not endswith(str, suffix)
}

count_lines(content) := count(split(content, "\n"))

# Allow/Deny decisions
allow if {
    count(violation) == 0
}

deny[msg] if {
    v := violation[_]
    msg := v.msg
}
