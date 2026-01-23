package code_scalpel.architecture

# Module Boundaries Policy
# Prevents cross-module dependencies that violate encapsulation
#
# Rules:
# 1. Modules can only access each other's public APIs
# 2. Internal implementation details are off-limits
# 3. Circular dependencies are prohibited
# 4. Shared code must go through a common/shared module

import future.keywords.if
import future.keywords.in

# Define module structure
# Each module has a root path and public API paths
modules := {
    "auth": {
        "root": "src/auth",
        "public": {"src/auth/api", "src/auth/models"},
        "internal": {"src/auth/internal", "src/auth/private"}
    },
    "user": {
        "root": "src/user",
        "public": {"src/user/api", "src/user/models"},
        "internal": {"src/user/internal", "src/user/services"}
    },
    "payment": {
        "root": "src/payment",
        "public": {"src/payment/api", "src/payment/models"},
        "internal": {"src/payment/internal", "src/payment/processors"}
    },
    "shared": {
        "root": "src/shared",
        "public": {"src/shared"},
        "internal": {}
    }
}

# Determine which module a file belongs to
file_module(file_path) := module_name if {
    some module_name, module_config in modules
    startswith(file_path, module_config.root)
}

# Check if import is accessing public API
is_public_import(import_path, target_module) if {
    module_config := modules[target_module]
    some public_path in module_config.public
    startswith(import_path, public_path)
}

# Check if import is accessing internal implementation
is_internal_import(import_path, target_module) if {
    module_config := modules[target_module]
    some internal_path in module_config.internal
    startswith(import_path, internal_path)
}

# Violation: Accessing another module's internal implementation
violation[{"msg": msg, "file": file.path, "severity": "CRITICAL"}] if {
    file := input.files[_]
    source_module := file_module(file.path)
    
    import_path := file.imports[_]
    target_module := file_module(import_path)
    
    # Different modules
    source_module != target_module
    
    # Accessing internal implementation
    is_internal_import(import_path, target_module)
    
    msg := sprintf(
        "Module boundary violation: '%s' (module: %s) is accessing internal implementation of module '%s' at '%s'. Use public API instead.",
        [file.path, source_module, target_module, import_path]
    )
}

# Violation: Circular dependencies between modules
circular_dependency[{"modules": [module1, module2]}] if {
    # Module1 depends on Module2
    file1 := input.files[_]
    module1 := file_module(file1.path)
    import1 := file1.imports[_]
    module2 := file_module(import1)
    module1 != module2
    
    # Module2 depends on Module1
    file2 := input.files[_]
    module2 == file_module(file2.path)
    import2 := file2.imports[_]
    module1 == file_module(import2)
}

violation[{"msg": msg, "severity": "HIGH"}] if {
    circ := circular_dependency[_]
    msg := sprintf(
        "Circular dependency detected between modules '%s' and '%s'. Extract shared code to 'shared' module.",
        circ.modules
    )
}

# Violation: Direct database access outside data layer
violation[{"msg": msg, "file": file.path, "severity": "HIGH"}] if {
    file := input.files[_]
    source_module := file_module(file.path)
    
    # Check for database imports
    import_path := file.imports[_]
    regex.match("(sqlalchemy|django\\.db|psycopg|pymongo|mysql)", import_path)
    
    # Only repository/infrastructure modules should access DB
    not endswith(file.path, "/repositories/")
    not endswith(file.path, "/infrastructure/")
    not endswith(file.path, "/persistence/")
    
    msg := sprintf(
        "Direct database access in '%s' (module: %s). Database access should only happen in repository layer.",
        [file.path, source_module]
    )
}

# Main decision
allow if {
    count(violation) == 0
}

deny[msg] if {
    v := violation[_]
    msg := v.msg
}
