"""
Architectural Rule Engine for Enterprise Tier.

[20251230_FEATURE] v3.4.0 - Configurable dependency rules for Enterprise tier

This module provides configurable architectural boundary enforcement for
cross-file dependency analysis. It allows users to define:

- Layer definitions (presentation, application, domain, infrastructure)
- Custom dependency rules (allow/deny patterns)
- Coupling limits (fan-in, fan-out, depth)
- Exemptions for test files and utility modules

Configuration is loaded from .code-scalpel/architecture.toml

Example:
    >>> engine = ArchitecturalRuleEngine("/myproject")
    >>> engine.load_config()
    >>> violations = engine.check_dependency("controllers.api", "database.models")
    >>> for v in violations:
    ...     print(f"{v.severity}: {v.description}")
"""

import fnmatch
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

try:
    import tomllib  # type: ignore[import]  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[import,no-redef]  # Fallback for Python < 3.11
    except ImportError:
        tomllib = None  # type: ignore[assignment]  # Will use defaults

logger = logging.getLogger(__name__)


class ViolationSeverity(Enum):
    """Severity levels for architectural violations."""

    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class ViolationAction(Enum):
    """Actions to take when a violation is detected."""

    BLOCK = "block"
    WARN = "warn"
    INFO = "info"


@dataclass
class ArchitecturalViolation:
    """
    Represents a detected architectural violation.

    Attributes:
        rule_name: Name of the violated rule
        description: Human-readable description
        from_module: Source module path
        to_module: Target module path
        severity: Violation severity level
        action: Recommended action (block/warn/info)
        from_layer: Layer of source module (if applicable)
        to_layer: Layer of target module (if applicable)
    """

    rule_name: str
    description: str
    from_module: str
    to_module: str
    severity: ViolationSeverity
    action: ViolationAction
    from_layer: str | None = None
    to_layer: str | None = None


@dataclass
class CustomRule:
    """A custom dependency rule."""

    name: str
    description: str
    from_pattern: str
    to_pattern: str
    action: str  # "allow" or "deny"
    severity: str  # "critical", "major", "minor"


@dataclass
class CouplingLimits:
    """Coupling limit configuration."""

    max_fan_in: int = 20
    max_fan_out: int = 15
    max_dependency_depth: int = 10
    coupling_threshold: float = 0.7


@dataclass
class ArchitectureConfig:
    """
    Complete architecture configuration.

    Attributes:
        layers: Ordered list of layer names (highest to lowest)
        layer_mapping: Dict mapping layer name to module patterns
        layer_direction: "downward_only" or "any"
        allow_same_layer: Whether same-layer imports are allowed
        custom_rules: List of custom dependency rules
        coupling_limits: Coupling metric limits
        exemptions: Patterns exempt from rule checking
        exempt_modules: Module names exempt from rules
    """

    layers: list[str] = field(default_factory=list)
    layer_mapping: dict[str, list[str]] = field(default_factory=dict)
    layer_direction: str = "downward_only"
    allow_same_layer: bool = True
    enable_layer_rules: bool = True
    enable_custom_rules: bool = True
    enable_coupling_rules: bool = True
    custom_rules: list[CustomRule] = field(default_factory=list)
    coupling_limits: CouplingLimits = field(default_factory=CouplingLimits)
    exemptions: list[str] = field(default_factory=list)
    exempt_modules: list[str] = field(default_factory=list)


class ArchitecturalRuleEngine:
    """
    Engine for checking architectural boundary violations.

    This class loads configuration from architecture.toml and provides
    methods to check dependencies against defined rules.

    Example:
        >>> engine = ArchitecturalRuleEngine("/myproject")
        >>> engine.load_config()
        >>>
        >>> # Check a single dependency
        >>> violations = engine.check_dependency("api.routes", "db.models")
        >>>
        >>> # Check all dependencies for a module
        >>> all_violations = engine.check_module_dependencies(
        ...     "api.routes",
        ...     ["services.auth", "db.models", "utils.helpers"]
        ... )
    """

    DEFAULT_CONFIG_PATHS = [
        ".code-scalpel/architecture.toml",
        ".code-scalpel/architecture.local.toml",  # Local overrides
    ]

    def __init__(self, project_root: str | Path):
        """
        Initialize the rule engine.

        Args:
            project_root: Path to the project root directory
        """
        self.project_root = Path(project_root).resolve()
        self.config = ArchitectureConfig()
        self._loaded = False
        self._warnings: list[str] = []

    def load_config(self, config_path: str | None = None) -> bool:
        """
        Load architecture configuration from TOML file.

        Args:
            config_path: Optional explicit path to config file

        Returns:
            True if config was loaded successfully
        """
        if tomllib is None:
            logger.warning("tomllib not available, using default configuration")
            self._load_defaults()
            self._loaded = True
            return True

        # Find config file
        if config_path:
            paths_to_try = [Path(config_path)]
        else:
            # Check environment variable
            env_path = os.environ.get("CODE_SCALPEL_ARCHITECTURE_FILE")
            if env_path:
                paths_to_try = [Path(env_path)]
            else:
                paths_to_try = [self.project_root / p for p in self.DEFAULT_CONFIG_PATHS]

        config_data = None
        for path in paths_to_try:
            if path.exists():
                try:
                    with open(path, "rb") as f:
                        config_data = tomllib.load(f)
                    logger.info(f"Loaded architecture config from {path}")
                    break
                except Exception as e:
                    self._warnings.append(f"Failed to load {path}: {e}")

        if config_data:
            self._parse_config(config_data)
        else:
            self._load_defaults()

        self._loaded = True
        return config_data is not None

    def _load_defaults(self) -> None:
        """Load default configuration values."""
        self.config = ArchitectureConfig(
            layers=["presentation", "application", "domain", "infrastructure"],
            layer_mapping={
                "presentation": ["**/controllers/**", "**/views/**", "**/api/**"],
                "application": ["**/services/**", "**/use_cases/**"],
                "domain": ["**/models/**", "**/entities/**", "**/domain/**"],
                "infrastructure": ["**/repositories/**", "**/database/**"],
            },
            layer_direction="downward_only",
            allow_same_layer=True,
            coupling_limits=CouplingLimits(),
            exemptions=["**/tests/**", "**/test_*.py"],
            exempt_modules=["__init__", "utils", "helpers", "constants"],
        )

    @property
    def layers(self) -> list[str]:
        """Expose configured layers for compatibility with older helpers."""
        return self.config.layers

    def _parse_config(self, data: dict) -> None:
        """Parse TOML configuration data."""
        # Parse layers
        layers_section = data.get("layers", {})
        self.config.layers = layers_section.get("order", self.config.layers)
        self.config.layer_mapping = layers_section.get("mapping", {})

        # Parse rules
        rules_section = data.get("rules", {})
        self.config.enable_layer_rules = rules_section.get("enable_layer_rules", True)
        self.config.enable_custom_rules = rules_section.get("enable_custom_rules", True)
        self.config.enable_coupling_rules = rules_section.get("enable_coupling_rules", True)
        self.config.layer_direction = rules_section.get("layer_direction", "downward_only")
        self.config.allow_same_layer = rules_section.get("allow_same_layer", True)

        # Parse custom rules
        custom_rules = rules_section.get("custom", [])
        self.config.custom_rules = [
            CustomRule(
                name=r.get("name", "unnamed_rule"),
                description=r.get("description", ""),
                from_pattern=r.get("from_pattern", "**"),
                to_pattern=r.get("to_pattern", "**"),
                action=r.get("action", "deny"),
                severity=r.get("severity", "major"),
            )
            for r in custom_rules
        ]

        # Parse coupling limits
        coupling_section = rules_section.get("coupling", {})
        self.config.coupling_limits = CouplingLimits(
            max_fan_in=coupling_section.get("max_fan_in", 20),
            max_fan_out=coupling_section.get("max_fan_out", 15),
            max_dependency_depth=coupling_section.get("max_dependency_depth", 10),
            coupling_threshold=coupling_section.get("coupling_threshold", 0.7),
        )

        # Parse exemptions
        exemptions_section = data.get("exemptions", {})
        self.config.exemptions = exemptions_section.get("patterns", [])
        self.config.exempt_modules = exemptions_section.get("modules", [])

    def is_exempt(self, module_path: str) -> bool:
        """
        Check if a module is exempt from rule checking.

        Args:
            module_path: Module path (e.g., "tests.test_api" or "src/tests/test_api.py")

        Returns:
            True if module is exempt
        """
        # Check module name exemptions
        module_name = module_path.split(".")[-1].replace(".py", "")
        if module_name in self.config.exempt_modules:
            return True

        # Check pattern exemptions
        # Normalize to path-like for glob matching
        path_like = module_path.replace(".", "/")
        for pattern in self.config.exemptions:
            if fnmatch.fnmatch(path_like, pattern):
                return True
            if fnmatch.fnmatch(module_path, pattern):
                return True

        return False

    def get_layer(self, module_path: str) -> str | None:
        """
        Determine which architectural layer a module belongs to.

        Args:
            module_path: Module path (e.g., "myapp.controllers.api")

        Returns:
            Layer name or None if not mapped
        """
        # Normalize to path-like for glob matching
        path_like = module_path.replace(".", "/")

        for layer, patterns in self.config.layer_mapping.items():
            for pattern in patterns:
                if fnmatch.fnmatch(path_like, pattern):
                    return layer
                if fnmatch.fnmatch(module_path, pattern):
                    return layer

        return None

    def get_layer_index(self, layer_name: str) -> int:
        """
        Get the index of a layer (0 = highest).

        Args:
            layer_name: Name of the layer

        Returns:
            Layer index, or -1 if not found
        """
        try:
            return self.config.layers.index(layer_name)
        except ValueError:
            return -1

    def check_dependency(self, from_module: str, to_module: str) -> list[ArchitecturalViolation]:
        """
        Check a single dependency for architectural violations.

        Args:
            from_module: Source module path
            to_module: Target module path

        Returns:
            List of violations found (empty if dependency is allowed)
        """
        if not self._loaded:
            self.load_config()

        violations = []

        # Check exemptions
        if self.is_exempt(from_module) or self.is_exempt(to_module):
            return violations

        # Check layer rules
        if self.config.enable_layer_rules:
            layer_violations = self._check_layer_rules(from_module, to_module)
            violations.extend(layer_violations)

        # Check custom rules
        if self.config.enable_custom_rules:
            custom_violations = self._check_custom_rules(from_module, to_module)
            violations.extend(custom_violations)

        return violations

    def _check_layer_rules(self, from_module: str, to_module: str) -> list[ArchitecturalViolation]:
        """Check layer boundary rules."""
        violations = []

        from_layer = self.get_layer(from_module)
        to_layer = self.get_layer(to_module)

        # If either module is not in a defined layer, skip layer rules
        if from_layer is None or to_layer is None:
            return violations

        # Same layer check
        if from_layer == to_layer:
            if not self.config.allow_same_layer:
                violations.append(
                    ArchitecturalViolation(
                        rule_name="same_layer_dependency",
                        description=f"Same-layer dependencies not allowed: {from_layer}",
                        from_module=from_module,
                        to_module=to_module,
                        severity=ViolationSeverity.MINOR,
                        action=ViolationAction.WARN,
                        from_layer=from_layer,
                        to_layer=to_layer,
                    )
                )
            return violations

        # Direction check (downward only)
        if self.config.layer_direction == "downward_only":
            from_idx = self.get_layer_index(from_layer)
            to_idx = self.get_layer_index(to_layer)

            if from_idx > to_idx:
                # Lower layer importing from higher layer - violation!
                violations.append(
                    ArchitecturalViolation(
                        rule_name="upward_dependency",
                        description=(
                            f"Upward dependency detected: {from_layer} ({from_idx}) "
                            f"depends on {to_layer} ({to_idx}). "
                            f"Dependencies should flow downward only."
                        ),
                        from_module=from_module,
                        to_module=to_module,
                        severity=ViolationSeverity.MAJOR,
                        action=ViolationAction.WARN,
                        from_layer=from_layer,
                        to_layer=to_layer,
                    )
                )

            # Check for layer skipping (e.g., presentation -> infrastructure)
            if to_idx - from_idx > 1:
                violations.append(
                    ArchitecturalViolation(
                        rule_name="layer_skip",
                        description=(
                            f"Layer skip detected: {from_layer} directly depends on "
                            f"{to_layer}, skipping intermediate layers."
                        ),
                        from_module=from_module,
                        to_module=to_module,
                        severity=ViolationSeverity.MINOR,
                        action=ViolationAction.INFO,
                        from_layer=from_layer,
                        to_layer=to_layer,
                    )
                )

        return violations

    def _check_custom_rules(self, from_module: str, to_module: str) -> list[ArchitecturalViolation]:
        """Check custom dependency rules."""
        violations = []

        # Normalize to path-like for glob matching
        from_path = from_module.replace(".", "/")
        to_path = to_module.replace(".", "/")

        for rule in self.config.custom_rules:
            from_matches = fnmatch.fnmatch(from_path, rule.from_pattern) or fnmatch.fnmatch(
                from_module, rule.from_pattern
            )
            to_matches = fnmatch.fnmatch(to_path, rule.to_pattern) or fnmatch.fnmatch(to_module, rule.to_pattern)

            # Both "deny" and "warn" actions trigger violations
            if from_matches and to_matches and rule.action in ("deny", "warn"):
                severity = ViolationSeverity(rule.severity.lower())

                # Determine action based on rule action and severity
                if rule.action == "deny" and severity == ViolationSeverity.CRITICAL:
                    action = ViolationAction.BLOCK
                elif rule.action == "deny":
                    action = ViolationAction.WARN
                else:  # action == "warn"
                    action = ViolationAction.WARN

                violations.append(
                    ArchitecturalViolation(
                        rule_name=rule.name,
                        description=rule.description,
                        from_module=from_module,
                        to_module=to_module,
                        severity=severity,
                        action=action,
                    )
                )

        return violations

    def check_module_dependencies(self, module: str, dependencies: list[str]) -> list[ArchitecturalViolation]:
        """
        Check all dependencies of a module.

        Args:
            module: Source module path
            dependencies: List of modules that this module imports

        Returns:
            List of all violations found
        """
        all_violations = []
        for dep in dependencies:
            violations = self.check_dependency(module, dep)
            all_violations.extend(violations)
        return all_violations

    def check_coupling(
        self,
        module: str,
        fan_in: int,
        fan_out: int,
        max_depth: int = 0,
    ) -> list[ArchitecturalViolation]:
        """
        Check coupling metrics against limits.

        Args:
            module: Module to check
            fan_in: Number of modules that import this module
            fan_out: Number of modules this module imports
            max_depth: Maximum depth of dependency chain (if known)

        Returns:
            List of coupling violations
        """
        if not self.config.enable_coupling_rules:
            return []

        violations = []
        limits = self.config.coupling_limits

        if fan_in > limits.max_fan_in:
            violations.append(
                ArchitecturalViolation(
                    rule_name="high_fan_in",
                    description=(
                        f"Module {module} has high fan-in ({fan_in}), "
                        f"exceeding limit of {limits.max_fan_in}. "
                        f"Consider splitting this module."
                    ),
                    from_module=module,
                    to_module="*",
                    severity=ViolationSeverity.MAJOR,
                    action=ViolationAction.WARN,
                )
            )

        if fan_out > limits.max_fan_out:
            violations.append(
                ArchitecturalViolation(
                    rule_name="high_fan_out",
                    description=(
                        f"Module {module} has high fan-out ({fan_out}), "
                        f"exceeding limit of {limits.max_fan_out}. "
                        f"This module may be doing too much."
                    ),
                    from_module=module,
                    to_module="*",
                    severity=ViolationSeverity.MAJOR,
                    action=ViolationAction.WARN,
                )
            )

        if max_depth > limits.max_dependency_depth:
            violations.append(
                ArchitecturalViolation(
                    rule_name="deep_dependency_chain",
                    description=(
                        f"Module {module} has dependency chain depth {max_depth}, "
                        f"exceeding limit of {limits.max_dependency_depth}."
                    ),
                    from_module=module,
                    to_module="*",
                    severity=ViolationSeverity.MINOR,
                    action=ViolationAction.INFO,
                )
            )

        return violations

    def get_all_rules(self) -> dict[str, Any]:
        """
        Get all configured rules for reporting.

        Returns:
            Dict with 'layer_rules', 'custom_rules', 'coupling_limits'
        """
        return {
            "layer_rules": {
                "enabled": self.config.enable_layer_rules,
                "layers": self.config.layers,
                "direction": self.config.layer_direction,
                "allow_same_layer": self.config.allow_same_layer,
            },
            "custom_rules": [
                {
                    "name": r.name,
                    "description": r.description,
                    "from_pattern": r.from_pattern,
                    "to_pattern": r.to_pattern,
                    "action": r.action,
                    "severity": r.severity,
                }
                for r in self.config.custom_rules
            ],
            "coupling_limits": {
                "enabled": self.config.enable_coupling_rules,
                "max_fan_in": self.config.coupling_limits.max_fan_in,
                "max_fan_out": self.config.coupling_limits.max_fan_out,
                "max_dependency_depth": self.config.coupling_limits.max_dependency_depth,
            },
            "exemptions": {
                "patterns": self.config.exemptions,
                "modules": self.config.exempt_modules,
            },
        }

    @property
    def warnings(self) -> list[str]:
        """Get warnings generated during config loading."""
        return self._warnings.copy()


def load_architecture_config(project_root: str) -> ArchitectureConfig:
    """Convenience loader for backward compatibility.

    Some callers patch or import this helper directly; keep behavior simple:
    return a fully constructed ArchitectureConfig whether loaded from disk or
    the default fallback.
    """
    engine = ArchitecturalRuleEngine(project_root)
    engine.load_config()
    return engine.config
