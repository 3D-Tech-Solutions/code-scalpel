"""
Tests for governance configuration system.

[20251218_FEATURE] Test config loading, validation, env overrides, and integrity checks.
"""

import hashlib
import hmac
import tempfile
from pathlib import Path

import pytest
import yaml

from code_scalpel.governance import BlastRadiusConfig, GovernanceConfigLoader


class TestBlastRadiusConfig:
    """Test blast radius configuration."""

    def test_is_critical_path_exact_match(self):
        """Test exact path matching."""
        config = BlastRadiusConfig(critical_paths=["src/security/auth.py"])
        assert config.is_critical_path("src/security/auth.py")
        assert not config.is_critical_path("src/security/auth_test.py")

    def test_is_critical_path_directory_prefix(self):
        """Test directory prefix matching."""
        config = BlastRadiusConfig(critical_paths=["src/security/"])
        assert config.is_critical_path("src/security/auth.py")
        assert config.is_critical_path("src/security/crypto.py")
        assert not config.is_critical_path("src/api/auth.py")

    def test_is_critical_path_glob_pattern(self):
        """Test glob pattern matching."""
        config = BlastRadiusConfig(critical_paths=["src/*/security/*.py"])
        assert config.is_critical_path("src/core/security/auth.py")
        assert config.is_critical_path("src/api/security/crypto.py")
        assert not config.is_critical_path("src/security/auth.py")  # Wrong depth

    def test_is_critical_path_multiple_patterns(self):
        """Test multiple patterns."""
        config = BlastRadiusConfig(critical_paths=["src/security/", "src/core/", "config/production.yaml"])
        assert config.is_critical_path("src/security/auth.py")
        assert config.is_critical_path("src/core/engine.py")
        assert config.is_critical_path("config/production.yaml")
        assert not config.is_critical_path("src/utils/helpers.py")


class TestGovernanceConfigLoader:
    """Test governance configuration loader."""

    @pytest.fixture
    def temp_config_file(self):
        """Create temporary config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config = {
                "version": "3.0.0",
                "autonomy": {
                    "governance": {
                        "change_budgeting": {
                            "enabled": True,
                            "max_lines_per_change": 750,
                            "max_files_per_change": 15,
                        },
                        "blast_radius": {
                            "enabled": True,
                            "critical_paths": ["src/security/", "src/core/"],
                        },
                        "autonomy_constraints": {"max_autonomous_iterations": 20},
                        "audit": {"retention_days": 180},
                    },
                },
            }
            yaml.dump(config, f)
            path = Path(f.name)

        yield path

        # Cleanup
        if path.exists():
            path.unlink()

    def test_load_from_file(self, temp_config_file):
        """Test loading configuration from file."""
        loader = GovernanceConfigLoader(temp_config_file)
        config = loader.load()

        assert config.change_budgeting.max_lines_per_change == 750
        assert config.change_budgeting.max_files_per_change == 15
        assert config.blast_radius.critical_paths == ["src/security/", "src/core/"]
        assert config.autonomy_constraints.max_autonomous_iterations == 20
        assert config.audit.retention_days == 180

    def test_load_defaults_when_no_file(self):
        """Test loading defaults when config file doesn't exist."""
        loader = GovernanceConfigLoader(Path("/nonexistent/path/governance.yaml"))
        config = loader.load()

        # Should use defaults
        assert config.change_budgeting.max_lines_per_change == 500
        assert config.change_budgeting.max_files_per_change == 10
        assert config.autonomy_constraints.max_autonomous_iterations == 10

    def test_env_override_max_lines(self, temp_config_file, monkeypatch):
        """Test environment variable override for max_lines_per_change."""
        monkeypatch.setenv("SCALPEL_CHANGE_BUDGET_MAX_LINES", "1000")

        loader = GovernanceConfigLoader(temp_config_file)
        config = loader.load()

        # Should override file value of 750
        assert config.change_budgeting.max_lines_per_change == 1000

    def test_env_override_critical_paths(self, temp_config_file, monkeypatch):
        """Test environment variable override for critical_paths."""
        monkeypatch.setenv("SCALPEL_CRITICAL_PATHS", "src/api/, src/database/, config/")

        loader = GovernanceConfigLoader(temp_config_file)
        config = loader.load()

        # Should override file value
        assert config.blast_radius.critical_paths == [
            "src/api/",
            "src/database/",
            "config/",
        ]

    def test_hash_validation_success(self, temp_config_file, monkeypatch):
        """Test successful hash validation."""
        # Calculate correct hash
        with open(temp_config_file, "rb") as f:
            content = f.read()
            expected_hash = f"sha256:{hashlib.sha256(content).hexdigest()}"

        monkeypatch.setenv("SCALPEL_CONFIG_HASH", expected_hash)

        loader = GovernanceConfigLoader(temp_config_file)
        config = loader.load()

        # Should load successfully
        assert config is not None

    def test_hash_validation_failure(self, temp_config_file, monkeypatch):
        """Test hash validation failure."""
        monkeypatch.setenv("SCALPEL_CONFIG_HASH", "sha256:wrong_hash_value")

        loader = GovernanceConfigLoader(temp_config_file)

        with pytest.raises(ValueError, match="Configuration hash mismatch"):
            loader.load()

    def test_hmac_signature_validation_success(self, temp_config_file, monkeypatch):
        """Test successful HMAC signature validation."""
        secret = "test_secret_key"

        # Calculate correct signature
        with open(temp_config_file, "rb") as f:
            content = f.read()
            expected_sig = hmac.new(secret.encode(), content, hashlib.sha256).hexdigest()

        monkeypatch.setenv("SCALPEL_CONFIG_SECRET", secret)
        monkeypatch.setenv("SCALPEL_CONFIG_SIGNATURE", expected_sig)

        loader = GovernanceConfigLoader(temp_config_file)
        config = loader.load()

        # Should load successfully
        assert config is not None

    def test_hmac_signature_validation_failure(self, temp_config_file, monkeypatch):
        """Test HMAC signature validation failure."""
        monkeypatch.setenv("SCALPEL_CONFIG_SECRET", "test_secret")
        monkeypatch.setenv("SCALPEL_CONFIG_SIGNATURE", "wrong_signature")

        loader = GovernanceConfigLoader(temp_config_file)

        with pytest.raises(ValueError, match="Configuration signature invalid"):
            loader.load()

    def test_config_path_env_override(self, temp_config_file, monkeypatch):
        """Test SCALPEL_CONFIG environment variable."""
        monkeypatch.setenv("SCALPEL_CONFIG", str(temp_config_file))

        # Use wrong path initially, should be overridden by env var
        loader = GovernanceConfigLoader(Path("/wrong/path/governance.yaml"))
        config = loader.load()

        # Should load from env var path
        assert config.change_budgeting.max_lines_per_change == 750

    def test_multiple_env_overrides(self, temp_config_file, monkeypatch):
        """Test multiple environment variable overrides."""
        monkeypatch.setenv("SCALPEL_CHANGE_BUDGET_MAX_LINES", "2000")
        monkeypatch.setenv("SCALPEL_CHANGE_BUDGET_MAX_FILES", "50")
        monkeypatch.setenv("SCALPEL_MAX_AUTONOMOUS_ITERATIONS", "30")
        monkeypatch.setenv("SCALPEL_AUDIT_RETENTION_DAYS", "365")

        loader = GovernanceConfigLoader(temp_config_file)
        config = loader.load()

        assert config.change_budgeting.max_lines_per_change == 2000
        assert config.change_budgeting.max_files_per_change == 50
        assert config.autonomy_constraints.max_autonomous_iterations == 30
        assert config.audit.retention_days == 365


class TestGovernanceConfigIntegration:
    """Integration tests for governance configuration."""

    def test_full_config_lifecycle(self):
        """Test complete configuration lifecycle."""
        # Create config
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config = {
                "version": "3.0.0",
                "autonomy": {
                    "governance": {
                        "change_budgeting": {
                            "enabled": True,
                            "max_lines_per_change": 500,
                            "max_files_per_change": 10,
                            "max_complexity_delta": 50,
                            "require_justification": True,
                            "budget_refresh_interval_hours": 24,
                        },
                        "blast_radius": {
                            "enabled": True,
                            "max_affected_functions": 20,
                            "max_affected_classes": 5,
                            "max_call_graph_depth": 3,
                            "warn_on_public_api_changes": True,
                            "block_on_critical_paths": True,
                            "critical_paths": [
                                "src/core/",
                                "src/security/",
                                "src/mcp/server.py",
                            ],
                            "critical_path_max_lines": 50,
                            "critical_path_max_complexity_delta": 10,
                        },
                        "autonomy_constraints": {
                            "max_autonomous_iterations": 10,
                            "require_approval_for_breaking_changes": True,
                            "require_approval_for_security_changes": True,
                            "sandbox_execution_required": True,
                        },
                        "audit": {
                            "log_all_changes": True,
                            "log_rejected_changes": True,
                            "retention_days": 90,
                        },
                    },
                },
            }
            yaml.dump(config, f)
            path = Path(f.name)

        try:
            # Load config
            loader = GovernanceConfigLoader(path)
            gov_config = loader.load()

            # Verify all settings
            assert gov_config.change_budgeting.enabled
            assert gov_config.change_budgeting.max_lines_per_change == 500
            assert gov_config.blast_radius.max_affected_functions == 20
            assert len(gov_config.blast_radius.critical_paths) == 3
            assert gov_config.autonomy_constraints.max_autonomous_iterations == 10
            assert gov_config.audit.retention_days == 90

            # Test critical path detection
            assert gov_config.blast_radius.is_critical_path("src/core/engine.py")
            assert gov_config.blast_radius.is_critical_path("src/security/auth.py")
            assert gov_config.blast_radius.is_critical_path("src/mcp/server.py")
            assert not gov_config.blast_radius.is_critical_path("src/utils/helpers.py")

        finally:
            if path.exists():
                path.unlink()

    def test_defaults_are_sensible(self):
        """Test that default configuration is sensible."""
        loader = GovernanceConfigLoader(Path("/nonexistent/governance.yaml"))
        config = loader.load()

        # Change budgeting defaults
        assert config.change_budgeting.enabled
        assert config.change_budgeting.max_lines_per_change > 0
        assert config.change_budgeting.max_files_per_change > 0

        # Blast radius defaults
        assert config.blast_radius.enabled
        assert config.blast_radius.max_affected_functions > 0
        assert config.blast_radius.max_call_graph_depth > 0

        # Autonomy constraints defaults
        assert config.autonomy_constraints.max_autonomous_iterations > 0
        assert config.autonomy_constraints.require_approval_for_security_changes

        # Audit defaults
        assert config.audit.log_all_changes
        assert config.audit.retention_days > 0
