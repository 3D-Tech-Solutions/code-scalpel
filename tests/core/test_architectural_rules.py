"""
Tests for Enterprise tier Architectural Rule Engine.

[20251230_TEST] Tests for:
- Architecture configuration loading
- Layer detection and mapping
- Dependency rule checking
- Custom rules evaluation
- Coupling limit validation
- Exemption handling

These tests verify the Enterprise tier features as defined
in the get_cross_file_dependencies roadmap.
"""

import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from code_scalpel.ast_tools.architectural_rules import (
    ArchitecturalRuleEngine,
    ViolationAction,
    ViolationSeverity,
)


@pytest.fixture
def temp_project() -> Generator[Path, None, None]:
    """Create a temporary project directory for testing."""
    temp_dir = tempfile.mkdtemp(prefix="code_scalpel_arch_test_")
    temp_path = Path(temp_dir)
    yield temp_path
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_config_toml() -> str:
    """Sample architecture.toml content."""
    return """
[layers]
order = ["presentation", "application", "domain", "infrastructure"]

[layers.mapping]
presentation = ["**/controllers/**", "**/api/**"]
application = ["**/services/**"]
domain = ["**/models/**", "**/domain/**"]
infrastructure = ["**/database/**", "**/repositories/**"]

[rules]
enable_layer_rules = true
enable_custom_rules = true
enable_coupling_rules = true
layer_direction = "downward_only"
allow_same_layer = true

[[rules.custom]]
name = "no_db_from_api"
description = "API controllers should not directly access database"
from_pattern = "**/api/**"
to_pattern = "**/database/**"
action = "deny"
severity = "critical"

[[rules.custom]]
name = "no_circular_services"
description = "Services should not have circular dependencies"
from_pattern = "**/services/**"
to_pattern = "**/services/**"
action = "warn"
severity = "minor"

[rules.coupling]
max_fan_in = 10
max_fan_out = 8
max_dependency_depth = 5

[exemptions]
patterns = ["**/tests/**", "**/test_*.py"]
modules = ["__init__", "utils", "constants"]
"""


class TestConfigurationLoading:
    """Tests for architecture configuration loading."""

    def test_load_defaults(self, temp_project: Path):
        """Test loading default configuration when no file exists."""
        engine = ArchitecturalRuleEngine(temp_project)
        engine.load_config()

        # Should load defaults (file not found returns True with defaults)
        assert engine._loaded is True
        assert len(engine.config.layers) == 4
        assert "presentation" in engine.config.layers

    def test_load_from_file(self, temp_project: Path, sample_config_toml: str):
        """Test loading configuration from TOML file."""
        # Create config directory and file
        config_dir = temp_project / ".code-scalpel"
        config_dir.mkdir()
        config_file = config_dir / "architecture.toml"
        config_file.write_text(sample_config_toml)

        engine = ArchitecturalRuleEngine(temp_project)
        result = engine.load_config()

        assert result is True
        assert engine.config.layers == [
            "presentation",
            "application",
            "domain",
            "infrastructure",
        ]
        assert len(engine.config.custom_rules) == 2
        assert engine.config.coupling_limits.max_fan_in == 10

    def test_load_from_explicit_path(self, temp_project: Path, sample_config_toml: str):
        """Test loading from explicitly specified path."""
        custom_path = temp_project / "my_arch.toml"
        custom_path.write_text(sample_config_toml)

        engine = ArchitecturalRuleEngine(temp_project)
        result = engine.load_config(str(custom_path))

        assert result is True
        assert len(engine.config.custom_rules) == 2


class TestLayerDetection:
    """Tests for layer detection and mapping."""

    def test_get_layer_presentation(self, temp_project: Path, sample_config_toml: str):
        """Test detecting presentation layer modules."""
        config_dir = temp_project / ".code-scalpel"
        config_dir.mkdir()
        (config_dir / "architecture.toml").write_text(sample_config_toml)

        engine = ArchitecturalRuleEngine(temp_project)
        engine.load_config()

        # These should be in presentation layer
        assert engine.get_layer("app/controllers/user") == "presentation"
        assert engine.get_layer("src/api/routes") == "presentation"

    def test_get_layer_domain(self, temp_project: Path, sample_config_toml: str):
        """Test detecting domain layer modules."""
        config_dir = temp_project / ".code-scalpel"
        config_dir.mkdir()
        (config_dir / "architecture.toml").write_text(sample_config_toml)

        engine = ArchitecturalRuleEngine(temp_project)
        engine.load_config()

        assert engine.get_layer("src/models/user") == "domain"
        assert engine.get_layer("myapp/domain/entities") == "domain"

    def test_get_layer_unmapped(self, temp_project: Path, sample_config_toml: str):
        """Test modules not mapped to any layer."""
        config_dir = temp_project / ".code-scalpel"
        config_dir.mkdir()
        (config_dir / "architecture.toml").write_text(sample_config_toml)

        engine = ArchitecturalRuleEngine(temp_project)
        engine.load_config()

        # Module not matching any pattern
        assert engine.get_layer("random/module") is None
        assert engine.get_layer("utils/helpers") is None

    def test_layer_index(self, temp_project: Path, sample_config_toml: str):
        """Test layer index ordering."""
        config_dir = temp_project / ".code-scalpel"
        config_dir.mkdir()
        (config_dir / "architecture.toml").write_text(sample_config_toml)

        engine = ArchitecturalRuleEngine(temp_project)
        engine.load_config()

        # Presentation is highest (index 0)
        assert engine.get_layer_index("presentation") == 0
        # Infrastructure is lowest (index 3)
        assert engine.get_layer_index("infrastructure") == 3
        # Unknown layer
        assert engine.get_layer_index("unknown") == -1


class TestDependencyRuleChecking:
    """Tests for dependency rule checking."""

    def test_upward_dependency_violation(self, temp_project: Path, sample_config_toml: str):
        """Test detecting upward dependency violations."""
        config_dir = temp_project / ".code-scalpel"
        config_dir.mkdir()
        (config_dir / "architecture.toml").write_text(sample_config_toml)

        engine = ArchitecturalRuleEngine(temp_project)
        engine.load_config()

        # Infrastructure depending on presentation - violation!
        violations = engine.check_dependency(
            "src/database/queries",  # infrastructure
            "src/controllers/api",  # presentation
        )

        assert len(violations) >= 1
        upward = [v for v in violations if v.rule_name == "upward_dependency"]
        assert len(upward) == 1
        assert upward[0].severity == ViolationSeverity.MAJOR

    def test_downward_dependency_allowed(self, temp_project: Path, sample_config_toml: str):
        """Test that downward dependencies are allowed."""
        config_dir = temp_project / ".code-scalpel"
        config_dir.mkdir()
        (config_dir / "architecture.toml").write_text(sample_config_toml)

        engine = ArchitecturalRuleEngine(temp_project)
        engine.load_config()

        # Presentation depending on domain - allowed (downward)
        violations = engine.check_dependency("src/controllers/user", "src/models/user")  # presentation  # domain

        # No upward violations
        upward = [v for v in violations if v.rule_name == "upward_dependency"]
        assert len(upward) == 0

    def test_layer_skip_warning(self, temp_project: Path, sample_config_toml: str):
        """Test detecting layer skip (presentation -> infrastructure)."""
        config_dir = temp_project / ".code-scalpel"
        config_dir.mkdir()
        (config_dir / "architecture.toml").write_text(sample_config_toml)

        engine = ArchitecturalRuleEngine(temp_project)
        engine.load_config()

        # Presentation directly depending on infrastructure - layer skip
        violations = engine.check_dependency(
            "src/api/routes",  # presentation (0)
            "src/database/models",  # infrastructure (3)
        )

        skip = [v for v in violations if v.rule_name == "layer_skip"]
        assert len(skip) == 1
        assert skip[0].severity == ViolationSeverity.MINOR

    def test_same_layer_allowed(self, temp_project: Path, sample_config_toml: str):
        """Test same-layer dependencies when allowed."""
        config_dir = temp_project / ".code-scalpel"
        config_dir.mkdir()
        (config_dir / "architecture.toml").write_text(sample_config_toml)

        engine = ArchitecturalRuleEngine(temp_project)
        engine.load_config()

        # Domain -> Domain (same layer)
        violations = engine.check_dependency("src/models/user", "src/models/order")

        # Should be allowed (no same_layer violation)
        same_layer = [v for v in violations if v.rule_name == "same_layer_dependency"]
        assert len(same_layer) == 0


class TestCustomRules:
    """Tests for custom dependency rules."""

    def test_custom_deny_rule_triggers(self, temp_project: Path, sample_config_toml: str):
        """Test custom deny rule triggering violation."""
        config_dir = temp_project / ".code-scalpel"
        config_dir.mkdir()
        (config_dir / "architecture.toml").write_text(sample_config_toml)

        engine = ArchitecturalRuleEngine(temp_project)
        engine.load_config()

        # API directly accessing database - matches custom rule
        violations = engine.check_dependency("src/api/endpoints", "src/database/connection")

        custom = [v for v in violations if v.rule_name == "no_db_from_api"]
        assert len(custom) == 1
        assert custom[0].severity == ViolationSeverity.CRITICAL
        assert custom[0].action == ViolationAction.BLOCK

    def test_custom_warn_rule_triggers(self, temp_project: Path, sample_config_toml: str):
        """Test custom warn rule triggering."""
        config_dir = temp_project / ".code-scalpel"
        config_dir.mkdir()
        (config_dir / "architecture.toml").write_text(sample_config_toml)

        engine = ArchitecturalRuleEngine(temp_project)
        engine.load_config()

        # Service -> Service - matches circular warning rule
        # Pattern is "**/services/**" so we need a path with services in it
        violations = engine.check_dependency("myapp/services/auth", "myapp/services/user")

        custom = [v for v in violations if v.rule_name == "no_circular_services"]
        assert len(custom) == 1
        assert custom[0].severity == ViolationSeverity.MINOR


class TestCouplingLimits:
    """Tests for coupling limit validation."""

    def test_high_fan_in_violation(self, temp_project: Path, sample_config_toml: str):
        """Test detecting high fan-in violation."""
        config_dir = temp_project / ".code-scalpel"
        config_dir.mkdir()
        (config_dir / "architecture.toml").write_text(sample_config_toml)

        engine = ArchitecturalRuleEngine(temp_project)
        engine.load_config()

        # max_fan_in is 10 in config
        violations = engine.check_coupling("utils.helpers", fan_in=15, fan_out=5)

        assert len(violations) == 1
        assert violations[0].rule_name == "high_fan_in"
        assert violations[0].severity == ViolationSeverity.MAJOR

    def test_high_fan_out_violation(self, temp_project: Path, sample_config_toml: str):
        """Test detecting high fan-out violation."""
        config_dir = temp_project / ".code-scalpel"
        config_dir.mkdir()
        (config_dir / "architecture.toml").write_text(sample_config_toml)

        engine = ArchitecturalRuleEngine(temp_project)
        engine.load_config()

        # max_fan_out is 8 in config
        violations = engine.check_coupling("services.mega_service", fan_in=5, fan_out=12)

        fan_out = [v for v in violations if v.rule_name == "high_fan_out"]
        assert len(fan_out) == 1

    def test_deep_dependency_chain(self, temp_project: Path, sample_config_toml: str):
        """Test detecting deep dependency chain."""
        config_dir = temp_project / ".code-scalpel"
        config_dir.mkdir()
        (config_dir / "architecture.toml").write_text(sample_config_toml)

        engine = ArchitecturalRuleEngine(temp_project)
        engine.load_config()

        # max_dependency_depth is 5 in config
        violations = engine.check_coupling("deeply.nested.module", fan_in=3, fan_out=3, max_depth=8)

        deep = [v for v in violations if v.rule_name == "deep_dependency_chain"]
        assert len(deep) == 1

    def test_coupling_within_limits(self, temp_project: Path, sample_config_toml: str):
        """Test that coupling within limits produces no violations."""
        config_dir = temp_project / ".code-scalpel"
        config_dir.mkdir()
        (config_dir / "architecture.toml").write_text(sample_config_toml)

        engine = ArchitecturalRuleEngine(temp_project)
        engine.load_config()

        violations = engine.check_coupling("balanced.module", fan_in=5, fan_out=4, max_depth=3)

        assert len(violations) == 0


class TestExemptions:
    """Tests for exemption handling."""

    def test_test_file_exempt(self, temp_project: Path, sample_config_toml: str):
        """Test that test files are exempt from rules."""
        config_dir = temp_project / ".code-scalpel"
        config_dir.mkdir()
        (config_dir / "architecture.toml").write_text(sample_config_toml)

        engine = ArchitecturalRuleEngine(temp_project)
        engine.load_config()

        # Test file pattern "**/tests/**" needs path with tests/ in middle
        assert engine.is_exempt("myapp/tests/integration") is True
        assert engine.is_exempt("src/tests/test_db") is True
        # Test file pattern "**/test_*.py" needs full filename pattern
        assert engine.is_exempt("src/test_something.py") is True

    def test_utility_module_exempt(self, temp_project: Path, sample_config_toml: str):
        """Test that utility modules are exempt."""
        config_dir = temp_project / ".code-scalpel"
        config_dir.mkdir()
        (config_dir / "architecture.toml").write_text(sample_config_toml)

        engine = ArchitecturalRuleEngine(temp_project)
        engine.load_config()

        assert engine.is_exempt("src.utils") is True
        assert engine.is_exempt("mypackage.__init__") is True
        assert engine.is_exempt("config.constants") is True

    def test_exempt_module_skips_checks(self, temp_project: Path, sample_config_toml: str):
        """Test that exempt modules skip violation checking."""
        config_dir = temp_project / ".code-scalpel"
        config_dir.mkdir()
        (config_dir / "architecture.toml").write_text(sample_config_toml)

        engine = ArchitecturalRuleEngine(temp_project)
        engine.load_config()

        # Even if this would violate rules, tests are exempt
        violations = engine.check_dependency(
            "tests/test_api",  # exempt
            "src/database/connection",  # would be violation if not exempt
        )

        assert len(violations) == 0


class TestModuleDependencyChecking:
    """Tests for checking all dependencies of a module."""

    def test_check_module_dependencies(self, temp_project: Path, sample_config_toml: str):
        """Test checking multiple dependencies at once."""
        config_dir = temp_project / ".code-scalpel"
        config_dir.mkdir()
        (config_dir / "architecture.toml").write_text(sample_config_toml)

        engine = ArchitecturalRuleEngine(temp_project)
        engine.load_config()

        # Check all deps of an API module
        deps = ["src/services/auth", "src/database/users", "src/models/user"]
        violations = engine.check_module_dependencies("src/api/routes", deps)

        # Should have violations for api -> database (custom rule + layer skip)
        db_violations = [v for v in violations if "database" in v.to_module]
        assert len(db_violations) >= 1


class TestGetAllRules:
    """Tests for rule reporting."""

    def test_get_all_rules(self, temp_project: Path, sample_config_toml: str):
        """Test getting all configured rules."""
        config_dir = temp_project / ".code-scalpel"
        config_dir.mkdir()
        (config_dir / "architecture.toml").write_text(sample_config_toml)

        engine = ArchitecturalRuleEngine(temp_project)
        engine.load_config()

        rules = engine.get_all_rules()

        assert "layer_rules" in rules
        assert rules["layer_rules"]["enabled"] is True
        assert rules["layer_rules"]["direction"] == "downward_only"

        assert "custom_rules" in rules
        assert len(rules["custom_rules"]) == 2

        assert "coupling_limits" in rules
        assert rules["coupling_limits"]["max_fan_in"] == 10

        assert "exemptions" in rules
        assert "**/tests/**" in rules["exemptions"]["patterns"]
