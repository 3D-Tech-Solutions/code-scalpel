"""
Comprehensive tests for all governance configuration profiles.

[20251218_FEATURE] Test all 6 configuration profiles with validation,
edge cases, and integration scenarios.
"""

import json
import tempfile
from pathlib import Path

import pytest

from code_scalpel.governance import GovernanceConfigLoader


class TestConfigurationProfiles:
    """Test all 6 configuration profiles load correctly."""

    @pytest.fixture
    def project_root(self):
        """Get actual project root with .code-scalpel/ directory."""
        return Path(__file__).parent.parent

    def test_default_profile_loads(self, project_root):
        """Test default config.json profile loads correctly."""
        config_path = project_root / ".code-scalpel" / "config.json"
        if not config_path.exists():
            pytest.skip("Default config not found - run from project root")

        loader = GovernanceConfigLoader(config_path)
        config = loader.load()

        # Verify expected values for default profile
        assert config.change_budgeting.max_lines_per_change == 500
        assert config.change_budgeting.max_files_per_change == 10
        assert config.autonomy_constraints.max_autonomous_iterations == 10
        assert len(config.blast_radius.critical_paths) > 0
        assert config.blast_radius.block_on_critical_paths

    def test_restrictive_profile_loads(self, project_root):
        """Test restrictive profile has tighter limits."""
        config_path = project_root / ".code-scalpel" / "config.restrictive.json"
        if not config_path.exists():
            pytest.skip("Restrictive config not found")

        loader = GovernanceConfigLoader(config_path)
        config = loader.load()

        # Restrictive should have lower limits
        assert config.change_budgeting.max_lines_per_change <= 100
        assert config.change_budgeting.max_files_per_change <= 3
        assert config.autonomy_constraints.max_autonomous_iterations <= 3
        # More critical paths
        assert len(config.blast_radius.critical_paths) >= 5
        assert config.audit.retention_days >= 365  # Long retention for security

    def test_permissive_profile_loads(self, project_root):
        """Test permissive profile has higher limits."""
        config_path = project_root / ".code-scalpel" / "config.permissive.json"
        if not config_path.exists():
            pytest.skip("Permissive config not found")

        loader = GovernanceConfigLoader(config_path)
        config = loader.load()

        # Permissive should have higher limits
        assert config.change_budgeting.max_lines_per_change >= 2000
        assert config.change_budgeting.max_files_per_change >= 50
        assert config.autonomy_constraints.max_autonomous_iterations >= 50
        # Fewer or no critical paths
        assert len(config.blast_radius.critical_paths) == 0

    def test_cicd_profile_loads(self, project_root):
        """Test CI/CD profile is optimized for automation."""
        config_path = project_root / ".code-scalpel" / "config.ci-cd.json"
        if not config_path.exists():
            pytest.skip("CI/CD config not found")

        loader = GovernanceConfigLoader(config_path)
        config = loader.load()

        # CI/CD should be moderate
        assert config.change_budgeting.max_lines_per_change == 1000
        assert config.change_budgeting.max_files_per_change == 20
        assert config.autonomy_constraints.max_autonomous_iterations == 20
        # Should still have sandbox
        assert config.autonomy_constraints.sandbox_execution_required

    def test_development_profile_loads(self, project_root):
        """Test development profile is developer-friendly."""
        config_path = project_root / ".code-scalpel" / "config.development.json"
        if not config_path.exists():
            pytest.skip("Development config not found")

        loader = GovernanceConfigLoader(config_path)
        config = loader.load()

        # Development should be balanced
        assert config.change_budgeting.max_lines_per_change == 750
        assert config.change_budgeting.max_files_per_change == 15
        assert config.autonomy_constraints.max_autonomous_iterations == 15

    def test_testing_profile_loads(self, project_root):
        """Test testing profile has minimal limits."""
        config_path = project_root / ".code-scalpel" / "config.testing.json"
        if not config_path.exists():
            pytest.skip("Testing config not found")

        loader = GovernanceConfigLoader(config_path)
        config = loader.load()

        # Testing should have very low limits
        assert config.change_budgeting.max_lines_per_change == 50
        assert config.change_budgeting.max_files_per_change == 2
        assert config.autonomy_constraints.max_autonomous_iterations == 2

    def test_all_profiles_are_valid_json(self, project_root):
        """Test all profile files are valid JSON."""
        config_dir = project_root / ".code-scalpel"
        if not config_dir.exists():
            pytest.skip(".code-scalpel directory not found")

        profiles = [
            "config.json",
            "config.restrictive.json",
            "config.permissive.json",
            "config.ci-cd.json",
            "config.development.json",
            "config.testing.json",
        ]

        for profile in profiles:
            path = config_dir / profile
            if not path.exists():
                continue

            # Should parse without error
            with open(path) as f:
                data = json.load(f)

            # Should have required structure
            assert "governance" in data
            assert "change_budgeting" in data["governance"]
            assert "blast_radius" in data["governance"]
            assert "autonomy_constraints" in data["governance"]
            assert "audit" in data["governance"]

    def test_profile_hierarchy(self, project_root):
        """Test that profiles follow expected limit hierarchy."""
        config_dir = project_root / ".code-scalpel"
        if not config_dir.exists():
            pytest.skip(".code-scalpel directory not found")

        # Load all profiles
        profiles = {}
        for name in ["restrictive", "default", "development", "ci-cd", "permissive"]:
            filename = f"config.{name}.json" if name != "default" else "config.json"
            path = config_dir / filename
            if path.exists():
                loader = GovernanceConfigLoader(path)
                profiles[name] = loader.load()

        if len(profiles) < 2:
            pytest.skip("Not enough profiles to compare")

        # Restrictive should have lowest limits
        if "restrictive" in profiles and "default" in profiles:
            assert (
                profiles["restrictive"].change_budgeting.max_lines_per_change
                < profiles["default"].change_budgeting.max_lines_per_change
            )

        # Permissive should have highest limits
        if "permissive" in profiles and "default" in profiles:
            assert (
                profiles["permissive"].change_budgeting.max_lines_per_change
                > profiles["default"].change_budgeting.max_lines_per_change
            )


class TestConfigurationValidation:
    """Test configuration validation and error handling."""

    def test_invalid_json_raises_error(self):
        """Test that invalid JSON raises appropriate error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            path = Path(f.name)

        try:
            loader = GovernanceConfigLoader(path)
            with pytest.raises(json.JSONDecodeError):
                loader.load()
        finally:
            path.unlink()

    def test_negative_values_are_accepted(self):
        """Test that negative values don't crash (even if illogical)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "governance": {
                    "change_budgeting": {"max_lines_per_change": -100},  # Illogical but shouldn't crash
                    "blast_radius": {},
                    "autonomy_constraints": {},
                    "audit": {},
                }
            }
            json.dump(config, f)
            path = Path(f.name)

        try:
            loader = GovernanceConfigLoader(path)
            config = loader.load()
            # Should load, validation happens at usage time
            assert config.change_budgeting.max_lines_per_change == -100
        finally:
            path.unlink()

    def test_zero_values_allowed(self):
        """Test that zero values are allowed."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "governance": {
                    "change_budgeting": {
                        "max_lines_per_change": 0,
                        "max_files_per_change": 0,
                    },
                    "blast_radius": {},
                    "autonomy_constraints": {"max_autonomous_iterations": 0},
                    "audit": {},
                }
            }
            json.dump(config, f)
            path = Path(f.name)

        try:
            loader = GovernanceConfigLoader(path)
            config = loader.load()
            assert config.change_budgeting.max_lines_per_change == 0
            assert config.autonomy_constraints.max_autonomous_iterations == 0
        finally:
            path.unlink()

    def test_missing_optional_fields_use_defaults(self):
        """Test that missing optional fields get default values."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "governance": {
                    "change_budgeting": {
                        "max_lines_per_change": 1000
                        # Missing other fields
                    },
                    "blast_radius": {},
                    "autonomy_constraints": {},
                    "audit": {},
                }
            }
            json.dump(config, f)
            path = Path(f.name)

        try:
            loader = GovernanceConfigLoader(path)
            config = loader.load()
            # Should have defaults for missing fields
            assert config.change_budgeting.max_lines_per_change == 1000
            assert config.change_budgeting.max_files_per_change == 10  # default
            assert config.change_budgeting.enabled is True  # default
        finally:
            path.unlink()

    def test_extra_fields_at_top_level_ignored(self):
        """Test that extra unknown fields at governance level are ignored."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "governance": {
                    "change_budgeting": {"max_lines_per_change": 500},
                    "blast_radius": {},
                    "autonomy_constraints": {},
                    "audit": {},
                    "future_feature": {"foo": "bar"},  # Top-level extra field
                }
            }
            json.dump(config, f)
            path = Path(f.name)

        try:
            loader = GovernanceConfigLoader(path)
            config = loader.load()
            # Should load successfully, ignoring extra top-level fields
            assert config.change_budgeting.max_lines_per_change == 500
        finally:
            path.unlink()


class TestCriticalPathScenarios:
    """Test critical path detection in various scenarios."""

    def test_critical_path_with_nested_directories(self):
        """Test critical path detection with deeply nested files."""
        from code_scalpel.governance import BlastRadiusConfig

        config = BlastRadiusConfig(critical_paths=["src/core/"])

        # Should match all nested files
        assert config.is_critical_path("src/core/engine.py")
        assert config.is_critical_path("src/core/auth/login.py")
        assert config.is_critical_path("src/core/auth/oauth/provider.py")

        # Should not match siblings
        assert not config.is_critical_path("src/api/routes.py")

    def test_critical_path_with_specific_files(self):
        """Test critical path with specific file patterns."""
        from code_scalpel.governance import BlastRadiusConfig

        config = BlastRadiusConfig(critical_paths=["config/production.yaml", "src/*/security/*.py"])

        # Exact file match
        assert config.is_critical_path("config/production.yaml")
        assert not config.is_critical_path("config/development.yaml")

        # Glob pattern match
        assert config.is_critical_path("src/api/security/auth.py")
        assert config.is_critical_path("src/core/security/crypto.py")
        assert not config.is_critical_path("src/api/utils.py")

    def test_critical_path_windows_paths(self):
        """Test critical path works with Windows-style paths."""
        from pathlib import Path

        from code_scalpel.governance import BlastRadiusConfig

        config = BlastRadiusConfig(critical_paths=["src/security/"])

        # Should normalize and match
        assert config.is_critical_path("src/security/auth.py")
        # Windows paths get normalized to POSIX by Path.as_posix()
        # so we need to test with actual Path objects
        windows_path = Path("src") / "security" / "auth.py"
        assert config.is_critical_path(str(windows_path))

    def test_critical_path_empty_list(self):
        """Test behavior with no critical paths."""
        from code_scalpel.governance import BlastRadiusConfig

        config = BlastRadiusConfig(critical_paths=[])

        # Nothing should be critical
        assert not config.is_critical_path("src/security/auth.py")
        assert not config.is_critical_path("config/production.yaml")

    def test_critical_path_overlapping_patterns(self):
        """Test overlapping critical path patterns."""
        from code_scalpel.governance import BlastRadiusConfig

        config = BlastRadiusConfig(
            critical_paths=[
                "src/",  # Everything
                "src/security/",  # Redundant but shouldn't break
                "src/security/auth.py",  # Even more specific
            ]
        )

        # All should match
        assert config.is_critical_path("src/utils.py")
        assert config.is_critical_path("src/security/auth.py")
        assert config.is_critical_path("src/api/routes.py")


class TestEnvironmentVariablePrecedence:
    """Test environment variable override scenarios."""

    def test_env_overrides_take_precedence(self, monkeypatch):
        """Test env vars override file config."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "governance": {
                    "change_budgeting": {"max_lines_per_change": 500},
                    "blast_radius": {},
                    "autonomy_constraints": {},
                    "audit": {},
                }
            }
            json.dump(config, f)
            path = Path(f.name)

        try:
            # Set env var to different value
            monkeypatch.setenv("SCALPEL_CHANGE_BUDGET_MAX_LINES", "2000")

            loader = GovernanceConfigLoader(path)
            config = loader.load()

            # Env var should win
            assert config.change_budgeting.max_lines_per_change == 2000
        finally:
            path.unlink()

    def test_env_overrides_without_file(self, monkeypatch):
        """Test env vars work even without config file."""
        monkeypatch.setenv("SCALPEL_CHANGE_BUDGET_MAX_LINES", "3000")
        monkeypatch.setenv("SCALPEL_CRITICAL_PATHS", "src/api/, src/db/")

        loader = GovernanceConfigLoader(Path("/nonexistent/config.json"))
        config = loader.load()

        # Should use defaults + env overrides
        assert config.change_budgeting.max_lines_per_change == 3000
        assert config.blast_radius.critical_paths == ["src/api/", "src/db/"]

    def test_partial_env_overrides(self, monkeypatch):
        """Test partial env var overrides."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "governance": {
                    "change_budgeting": {
                        "max_lines_per_change": 500,
                        "max_files_per_change": 10,
                    },
                    "blast_radius": {},
                    "autonomy_constraints": {},
                    "audit": {},
                }
            }
            json.dump(config, f)
            path = Path(f.name)

        try:
            # Override only one field
            monkeypatch.setenv("SCALPEL_CHANGE_BUDGET_MAX_LINES", "1000")

            loader = GovernanceConfigLoader(path)
            config = loader.load()

            # One field overridden, other from file
            assert config.change_budgeting.max_lines_per_change == 1000
            assert config.change_budgeting.max_files_per_change == 10
        finally:
            path.unlink()

    def test_env_var_type_conversion(self, monkeypatch):
        """Test that env var strings are converted to correct types."""
        monkeypatch.setenv("SCALPEL_CHANGE_BUDGET_MAX_LINES", "999")
        monkeypatch.setenv("SCALPEL_MAX_AUTONOMOUS_ITERATIONS", "25")
        monkeypatch.setenv("SCALPEL_AUDIT_RETENTION_DAYS", "365")

        loader = GovernanceConfigLoader(Path("/nonexistent/config.json"))
        config = loader.load()

        # All should be integers, not strings
        assert isinstance(config.change_budgeting.max_lines_per_change, int)
        assert config.change_budgeting.max_lines_per_change == 999
        assert isinstance(config.autonomy_constraints.max_autonomous_iterations, int)
        assert config.autonomy_constraints.max_autonomous_iterations == 25


class TestSecurityScenarios:
    """Test security-focused configuration scenarios."""

    @pytest.fixture
    def project_root(self):
        """Get actual project root with .code-scalpel/ directory."""
        return Path(__file__).parent.parent

    def test_restrictive_config_blocks_large_changes(self, project_root):
        """Test restrictive config provides appropriate limits."""
        config_path = project_root / ".code-scalpel" / "config.restrictive.json"
        if not config_path.exists():
            pytest.skip("Restrictive config not found")

        loader = GovernanceConfigLoader(config_path)
        config = loader.load()

        # Should have security-focused settings
        assert config.change_budgeting.max_lines_per_change <= 100
        assert config.change_budgeting.require_justification
        assert config.blast_radius.block_on_critical_paths
        assert config.autonomy_constraints.require_approval_for_security_changes
        assert config.autonomy_constraints.sandbox_execution_required
        assert config.audit.log_all_changes
        assert config.audit.log_rejected_changes

    def test_production_suitable_defaults(self):
        """Test that defaults are production-suitable."""
        loader = GovernanceConfigLoader(Path("/nonexistent/config.json"))
        config = loader.load()

        # Defaults should be conservative
        assert config.change_budgeting.max_lines_per_change <= 500
        assert config.blast_radius.block_on_critical_paths
        assert config.autonomy_constraints.require_approval_for_breaking_changes
        assert config.autonomy_constraints.sandbox_execution_required
        assert config.audit.log_all_changes


class TestUseCaseScenarios:
    """Test configuration for specific use cases."""

    def test_financial_app_config(self):
        """Test configuration suitable for financial applications."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "governance": {
                    "change_budgeting": {
                        "enabled": True,
                        "max_lines_per_change": 100,
                        "max_files_per_change": 3,
                        "max_complexity_delta": 5,
                        "require_justification": True,
                    },
                    "blast_radius": {
                        "enabled": True,
                        "critical_paths": [
                            "src/payment/",
                            "src/transaction/",
                            "src/authentication/",
                            "src/audit/",
                        ],
                        "block_on_critical_paths": True,
                        "critical_path_max_lines": 20,
                    },
                    "autonomy_constraints": {
                        "max_autonomous_iterations": 3,
                        "require_approval_for_breaking_changes": True,
                        "require_approval_for_security_changes": True,
                        "sandbox_execution_required": True,
                    },
                    "audit": {
                        "log_all_changes": True,
                        "log_rejected_changes": True,
                        "retention_days": 2555,  # 7 years for SOX compliance
                    },
                }
            }
            json.dump(config, f)
            path = Path(f.name)

        try:
            loader = GovernanceConfigLoader(path)
            loaded = loader.load()

            # Verify financial-grade settings
            assert loaded.change_budgeting.max_lines_per_change <= 100
            assert loaded.blast_radius.is_critical_path("src/payment/processor.py")
            assert loaded.autonomy_constraints.max_autonomous_iterations <= 5
            assert loaded.audit.retention_days >= 2555
        finally:
            path.unlink()

    def test_experimental_prototype_config(self):
        """Test configuration for experimental/prototype projects."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "governance": {
                    "change_budgeting": {
                        "enabled": True,
                        "max_lines_per_change": 5000,
                        "max_files_per_change": 100,
                        "require_justification": False,
                    },
                    "blast_radius": {
                        "enabled": False,
                        "critical_paths": [],
                        "block_on_critical_paths": False,
                    },
                    "autonomy_constraints": {
                        "max_autonomous_iterations": 100,
                        "require_approval_for_breaking_changes": False,
                        "sandbox_execution_required": False,
                    },
                    "audit": {"log_all_changes": True, "retention_days": 7},
                }
            }
            json.dump(config, f)
            path = Path(f.name)

        try:
            loader = GovernanceConfigLoader(path)
            loaded = loader.load()

            # Verify experimental settings (very permissive)
            assert loaded.change_budgeting.max_lines_per_change >= 5000
            assert not loaded.blast_radius.enabled
            assert loaded.autonomy_constraints.max_autonomous_iterations >= 100
            assert not loaded.autonomy_constraints.require_approval_for_breaking_changes
        finally:
            path.unlink()
