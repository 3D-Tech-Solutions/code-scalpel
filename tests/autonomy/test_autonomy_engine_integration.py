"""
[20251218_FEATURE] Integration tests for AutonomyEngine with governance configuration.

Tests the complete integration of:
- GovernanceConfigLoader
- AutonomyEngine
- BlastRadiusCalculator
- ChangeBudget
- FixLoop
- Configuration profiles

Verifies config-driven behavior across different profiles and scenarios.
"""

import json
import tempfile
from pathlib import Path

import pytest

from code_scalpel.autonomy.engine import AutonomyEngine, BlastRadiusCalculator
from code_scalpel.governance import GovernanceConfigLoader


class TestAutonomyEngineIntegration:
    """Integration tests for AutonomyEngine with governance configuration."""

    @pytest.fixture
    def temp_project_root(self):
        """Create temporary project directory with .code-scalpel/ subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            scalpel_dir = project_root / ".code-scalpel"
            scalpel_dir.mkdir()
            yield project_root

    @pytest.fixture
    def default_config_file(self, temp_project_root):
        """Create default config file."""
        config = {
            "governance": {
                "change_budgeting": {
                    "enabled": True,
                    "max_lines_per_change": 500,
                    "max_files_per_change": 10,
                    "max_complexity_delta": 50,
                },
                "blast_radius": {
                    "enabled": True,
                    "max_affected_functions": 20,
                    "max_affected_classes": 5,
                    "max_call_graph_depth": 3,
                    "block_on_critical_paths": True,
                    "critical_paths": ["src/security/", "src/auth/"],
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
            }
        }

        config_path = temp_project_root / ".code-scalpel" / "config.json"
        with open(config_path, "w") as f:
            json.dump(config, f)

        return config_path

    @pytest.fixture
    def restrictive_config_file(self, temp_project_root):
        """Create restrictive config file for security-critical systems."""
        config = {
            "governance": {
                "change_budgeting": {
                    "enabled": True,
                    "max_lines_per_change": 100,
                    "max_files_per_change": 3,
                    "max_complexity_delta": 5,
                },
                "blast_radius": {
                    "enabled": True,
                    "critical_paths": [
                        "src/security/",
                        "src/auth/",
                        "src/payment/",
                        "src/api/",
                    ],
                    "critical_path_max_lines": 20,
                    "block_on_critical_paths": True,
                },
                "autonomy_constraints": {
                    "max_autonomous_iterations": 3,
                    "require_approval_for_security_changes": True,
                    "sandbox_execution_required": True,
                },
                "audit": {"log_all_changes": True, "retention_days": 365},
            }
        }

        config_path = temp_project_root / ".code-scalpel" / "config.restrictive.json"
        with open(config_path, "w") as f:
            json.dump(config, f)

        return config_path

    def test_engine_initialization_with_default_config(self, temp_project_root, default_config_file):
        """Test engine initializes correctly with default config."""
        engine = AutonomyEngine(project_root=temp_project_root, config_path=default_config_file)

        # Verify config loaded correctly
        assert engine.config.change_budgeting.max_lines_per_change == 500
        assert engine.config.change_budgeting.max_files_per_change == 10
        assert engine.config.autonomy_constraints.max_autonomous_iterations == 10
        assert len(engine.config.blast_radius.critical_paths) == 2

        # Verify components initialized with config values
        assert engine.change_budget.max_files == 10
        assert engine.fix_loop.max_attempts == 10

    def test_engine_initialization_with_restrictive_config(self, temp_project_root, restrictive_config_file):
        """Test engine respects restrictive config limits."""
        engine = AutonomyEngine(project_root=temp_project_root, config_path=restrictive_config_file)

        # Verify restrictive limits
        assert engine.config.change_budgeting.max_lines_per_change == 100
        assert engine.config.change_budgeting.max_files_per_change == 3
        assert engine.config.autonomy_constraints.max_autonomous_iterations == 3
        assert engine.config.blast_radius.critical_path_max_lines == 20

        # Verify components use restrictive limits
        assert engine.fix_loop.max_attempts == 3

    def test_change_allowed_within_standard_limits(self, temp_project_root, default_config_file):
        """Test that changes within standard limits are allowed."""
        engine = AutonomyEngine(project_root=temp_project_root, config_path=default_config_file)

        # Change to non-critical file within limits
        result = engine.check_change_allowed(files=["src/utils/helpers.py"], lines_changed={"src/utils/helpers.py": 50})

        assert result.allowed
        assert not result.critical_path_violation
        assert result.max_lines_allowed == 500  # Standard limit

    def test_change_blocked_exceeds_standard_limits(self, temp_project_root, default_config_file):
        """Test that changes exceeding standard limits are blocked."""
        engine = AutonomyEngine(project_root=temp_project_root, config_path=default_config_file)

        # Change exceeds max_lines_per_change
        result = engine.check_change_allowed(
            files=["src/utils/helpers.py"],
            lines_changed={"src/utils/helpers.py": 600},  # Exceeds 500
        )

        assert not result.allowed
        assert "exceed" in result.reason.lower()

    def test_critical_path_detection(self, temp_project_root, default_config_file):
        """Test that critical paths are detected correctly."""
        engine = AutonomyEngine(project_root=temp_project_root, config_path=default_config_file)

        # Change to critical path file within critical path limits
        result = engine.check_change_allowed(
            files=["src/security/auth.py"],
            lines_changed={"src/security/auth.py": 30},  # Within 50 line critical path limit
        )

        # Should be blocked due to require_approval_for_security_changes
        assert not result.allowed
        assert result.critical_path_violation
        assert "require human approval" in result.reason.lower()

    def test_critical_path_exceeds_limits(self, temp_project_root, default_config_file):
        """Test that critical path changes exceeding limits are blocked."""
        engine = AutonomyEngine(project_root=temp_project_root, config_path=default_config_file)

        # Change to critical path file exceeds critical path limits
        result = engine.check_change_allowed(
            files=["src/security/crypto.py"],
            lines_changed={"src/security/crypto.py": 60},  # Exceeds 50 line limit
        )

        assert not result.allowed
        assert result.critical_path_violation
        assert "60" in result.reason  # Mentions attempted lines
        assert "50" in result.reason  # Mentions max lines

    def test_multiple_files_within_limits(self, temp_project_root, default_config_file):
        """Test multiple file changes within limits."""
        engine = AutonomyEngine(project_root=temp_project_root, config_path=default_config_file)

        # 5 files, each with small changes
        result = engine.check_change_allowed(
            files=[
                "src/utils/helpers.py",
                "src/utils/validators.py",
                "src/models/user.py",
                "src/models/post.py",
                "src/api/routes.py",
            ],
            lines_changed={
                "src/utils/helpers.py": 50,
                "src/utils/validators.py": 30,
                "src/models/user.py": 40,
                "src/models/post.py": 25,
                "src/api/routes.py": 35,
            },
        )

        assert result.allowed
        assert result.max_files_allowed == 10

    def test_multiple_files_exceeds_file_limit(self, temp_project_root, restrictive_config_file):
        """Test that exceeding file limit blocks change."""
        engine = AutonomyEngine(project_root=temp_project_root, config_path=restrictive_config_file)

        # 5 files, but restrictive config allows only 3
        result = engine.check_change_allowed(
            files=[
                "src/utils/helpers.py",
                "src/utils/validators.py",
                "src/models/user.py",
                "src/models/post.py",
                "src/api/routes.py",
            ],
            lines_changed={
                f: 10
                for f in [
                    "src/utils/helpers.py",
                    "src/utils/validators.py",
                    "src/models/user.py",
                    "src/models/post.py",
                    "src/api/routes.py",
                ]
            },
        )

        assert not result.allowed
        assert "5" in result.reason  # Mentions actual file count
        assert "3" in result.reason or result.max_files_allowed == 3  # Max files

    def test_blast_radius_calculator_critical_path_matching(self, temp_project_root, default_config_file):
        """Test BlastRadiusCalculator critical path pattern matching."""
        engine = AutonomyEngine(project_root=temp_project_root, config_path=default_config_file)

        # Test exact prefix matching
        is_crit, reason, max_lines = engine.blast_radius.check_critical_path_impact(
            files=["src/security/auth.py"], lines_changed={"src/security/auth.py": 10}
        )

        assert is_crit
        assert max_lines == 50  # Critical path limit

        # Test non-critical file
        is_crit, reason, max_lines = engine.blast_radius.check_critical_path_impact(
            files=["src/utils/helpers.py"], lines_changed={"src/utils/helpers.py": 10}
        )

        assert not is_crit
        assert max_lines == 500  # Standard limit

    def test_config_summary_returns_all_settings(self, temp_project_root, default_config_file):
        """Test that config summary includes all key settings."""
        engine = AutonomyEngine(project_root=temp_project_root, config_path=default_config_file)

        summary = engine.get_config_summary()

        # Verify structure
        assert "change_budgeting" in summary
        assert "blast_radius" in summary
        assert "autonomy_constraints" in summary
        assert "audit" in summary

        # Verify values
        assert summary["change_budgeting"]["max_lines"] == 500
        assert summary["autonomy_constraints"]["max_iterations"] == 10
        assert summary["blast_radius"]["critical_paths"] == [
            "src/security/",
            "src/auth/",
        ]

    def test_engine_respects_environment_overrides(self, temp_project_root, default_config_file, monkeypatch):
        """Test that environment variables override config file."""
        # Override max lines via environment
        monkeypatch.setenv("SCALPEL_CHANGE_BUDGET_MAX_LINES", "1000")
        monkeypatch.setenv("SCALPEL_MAX_AUTONOMOUS_ITERATIONS", "20")

        engine = AutonomyEngine(project_root=temp_project_root, config_path=default_config_file)

        # Verify overrides applied
        assert engine.config.change_budgeting.max_lines_per_change == 1000
        assert engine.config.autonomy_constraints.max_autonomous_iterations == 20
        assert engine.fix_loop.max_attempts == 20

    def test_restrictive_profile_blocks_more_aggressively(
        self, temp_project_root, default_config_file, restrictive_config_file
    ):
        """Test that restrictive profile is stricter than default."""
        # Default engine
        default_engine = AutonomyEngine(project_root=temp_project_root, config_path=default_config_file)

        # Restrictive engine
        restrictive_engine = AutonomyEngine(project_root=temp_project_root, config_path=restrictive_config_file)

        # Change that default allows but restrictive blocks
        files = ["src/utils/helpers.py"]
        lines = {"src/utils/helpers.py": 150}

        default_result = default_engine.check_change_allowed(files, lines)
        restrictive_result = restrictive_engine.check_change_allowed(files, lines)

        # Default allows 150 lines (within 500 limit)
        assert default_result.allowed

        # Restrictive blocks 150 lines (exceeds 100 limit)
        assert not restrictive_result.allowed


class TestBlastRadiusCalculator:
    """Unit tests for BlastRadiusCalculator critical path detection."""

    @pytest.fixture
    def temp_config(self):
        """Create temporary config with critical paths."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "governance": {
                    "change_budgeting": {"max_lines_per_change": 500},
                    "blast_radius": {
                        "critical_paths": [
                            "src/security/",
                            "src/payment/",
                            "config/production.yaml",
                        ],
                        "critical_path_max_lines": 50,
                    },
                    "autonomy_constraints": {},
                    "audit": {},
                }
            }
            json.dump(config, f)
            path = Path(f.name)

        try:
            loader = GovernanceConfigLoader(path)
            config = loader.load()
            yield config
        finally:
            path.unlink()

    def test_critical_path_directory_prefix(self, temp_config):
        """Test critical path detection with directory prefix."""
        calculator = BlastRadiusCalculator(temp_config)

        is_crit, reason, max_lines = calculator.check_critical_path_impact(
            files=["src/security/auth.py"], lines_changed={"src/security/auth.py": 25}
        )

        assert is_crit
        assert max_lines == 50
        assert "within limits" in reason.lower()

    def test_critical_path_nested_files(self, temp_config):
        """Test critical path matches nested files."""
        calculator = BlastRadiusCalculator(temp_config)

        is_crit, reason, max_lines = calculator.check_critical_path_impact(
            files=["src/security/oauth/provider.py"],
            lines_changed={"src/security/oauth/provider.py": 30},
        )

        assert is_crit
        assert max_lines == 50

    def test_non_critical_path_uses_standard_limit(self, temp_config):
        """Test non-critical files use standard limit."""
        calculator = BlastRadiusCalculator(temp_config)

        is_crit, reason, max_lines = calculator.check_critical_path_impact(
            files=["src/utils/helpers.py"], lines_changed={"src/utils/helpers.py": 100}
        )

        assert not is_crit
        assert max_lines == 500  # Standard limit
        assert "no critical paths" in reason.lower()

    def test_critical_path_exceeds_limit_blocked(self, temp_config):
        """Test critical path changes exceeding limit are caught."""
        calculator = BlastRadiusCalculator(temp_config)

        is_crit, reason, max_lines = calculator.check_critical_path_impact(
            files=["src/security/crypto.py"],
            lines_changed={"src/security/crypto.py": 75},  # Exceeds 50
        )

        assert is_crit
        assert "exceed" in reason.lower()
        assert "75" in reason  # Mentions actual
        assert "50" in reason  # Mentions max

    def test_mixed_critical_and_non_critical_files(self, temp_config):
        """Test mix of critical and non-critical files."""
        calculator = BlastRadiusCalculator(temp_config)

        is_crit, reason, max_lines = calculator.check_critical_path_impact(
            files=[
                "src/security/auth.py",  # Critical
                "src/utils/helpers.py",  # Non-critical
            ],
            lines_changed={"src/security/auth.py": 25, "src/utils/helpers.py": 100},
        )

        # Should be marked critical since at least one file is critical
        assert is_crit
        # Should check critical files only (25 lines, within 50 limit)
        assert "within limits" in reason.lower()
