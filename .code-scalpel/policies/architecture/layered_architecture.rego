package code_scalpel.architecture

# Layered Architecture Policy
# Enforces clean separation between presentation, business, and data layers
#
# Architecture Layers:
# - Presentation (UI, Controllers, Views)
# - Application (Services, Use Cases)
# - Domain (Business Logic, Entities)
# - Infrastructure (Database, External APIs)
#
# Rules:
# 1. Presentation can call Application, but NOT Domain or Infrastructure
# 2. Application can call Domain, but NOT Presentation or Infrastructure
# 3. Domain cannot call any other layer (pure business logic)
# 4. Infrastructure can call Domain, but NOT Presentation or Application

import future.keywords.if
import future.keywords.in

# Define layer patterns
presentation_patterns := {
    "*/ui/*", "*/views/*", "*/controllers/*", "*/pages/*",
    "*/components/*", "*/routes/*", "*/middleware/*"
}

application_patterns := {
    "*/services/*", "*/usecases/*", "*/application/*",
    "*/handlers/*", "*/commands/*", "*/queries/*"
}

domain_patterns := {
    "*/domain/*", "*/entities/*", "*/models/*",
    "*/business/*", "*/core/*"
}

infrastructure_patterns := {
    "*/infrastructure/*", "*/persistence/*", "*/repositories/*",
    "*/database/*", "*/api/*", "*/adapters/*", "*/external/*"
}

# Check if a file belongs to a specific layer
is_in_layer(file_path, patterns) if {
    some pattern in patterns
    glob.match(pattern, [], file_path)
}

# Determine file's layer
file_layer(file_path) := "presentation" if {
    is_in_layer(file_path, presentation_patterns)
}

file_layer(file_path) := "application" if {
    is_in_layer(file_path, application_patterns)
}

file_layer(file_path) := "domain" if {
    is_in_layer(file_path, domain_patterns)
}

file_layer(file_path) := "infrastructure" if {
    is_in_layer(file_path, infrastructure_patterns)
}

file_layer(file_path) := "unknown" if {
    not is_in_layer(file_path, presentation_patterns)
    not is_in_layer(file_path, application_patterns)
    not is_in_layer(file_path, domain_patterns)
    not is_in_layer(file_path, infrastructure_patterns)
}

# Violations: Presentation layer
violation[{"msg": msg, "file": file}] if {
    file := input.files[_]
    file_layer(file.path) == "presentation"
    
    # Check imports
    import_path := file.imports[_]
    import_layer := file_layer(import_path)
    
    # Presentation can only call Application
    import_layer == "domain"
    msg := sprintf("Presentation layer '%s' cannot directly access Domain layer '%s'. Use Application services.", [file.path, import_path])
}

violation[{"msg": msg, "file": file}] if {
    file := input.files[_]
    file_layer(file.path) == "presentation"
    
    import_path := file.imports[_]
    import_layer := file_layer(import_path)
    
    # Presentation cannot call Infrastructure
    import_layer == "infrastructure"
    msg := sprintf("Presentation layer '%s' cannot directly access Infrastructure layer '%s'. Use Application services.", [file.path, import_path])
}

# Violations: Application layer
violation[{"msg": msg, "file": file}] if {
    file := input.files[_]
    file_layer(file.path) == "application"
    
    import_path := file.imports[_]
    import_layer := file_layer(import_path)
    
    # Application cannot call Presentation
    import_layer == "presentation"
    msg := sprintf("Application layer '%s' cannot depend on Presentation layer '%s'. Invert the dependency.", [file.path, import_path])
}

violation[{"msg": msg, "file": file}] if {
    file := input.files[_]
    file_layer(file.path) == "application"
    
    import_path := file.imports[_]
    import_layer := file_layer(import_path)
    
    # Application cannot call Infrastructure directly
    import_layer == "infrastructure"
    msg := sprintf("Application layer '%s' should not directly access Infrastructure layer '%s'. Use dependency injection and interfaces.", [file.path, import_path])
}

# Violations: Domain layer
violation[{"msg": msg, "file": file}] if {
    file := input.files[_]
    file_layer(file.path) == "domain"
    
    import_path := file.imports[_]
    import_layer := file_layer(import_path)
    
    # Domain cannot depend on ANY other layer
    import_layer != "domain"
    import_layer != "unknown"
    msg := sprintf("Domain layer '%s' must be pure business logic. Remove dependency on '%s' (%s layer).", [file.path, import_path, import_layer])
}

# Violations: Infrastructure layer
violation[{"msg": msg, "file": file}] if {
    file := input.files[_]
    file_layer(file.path) == "infrastructure"
    
    import_path := file.imports[_]
    import_layer := file_layer(import_path)
    
    # Infrastructure cannot call Presentation
    import_layer == "presentation"
    msg := sprintf("Infrastructure layer '%s' cannot depend on Presentation layer '%s'.", [file.path, import_path])
}

violation[{"msg": msg, "file": file}] if {
    file := input.files[_]
    file_layer(file.path) == "infrastructure"
    
    import_path := file.imports[_]
    import_layer := file_layer(import_path)
    
    # Infrastructure cannot call Application
    import_layer == "application"
    msg := sprintf("Infrastructure layer '%s' cannot depend on Application layer '%s'. Use dependency inversion.", [file.path, import_path])
}

# Main decision
allow if {
    count(violation) == 0
}

deny[msg] if {
    v := violation[_]
    msg := v.msg
}
