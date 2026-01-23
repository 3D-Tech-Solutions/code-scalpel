# [20260108_TEST] Enterprise multi-repository coordination tests
"""
Tests for Enterprise-tier multi-repository coordination.

Verifies cross-repo change management:
- Multi-repo session tracking
- Atomic commits across repositories
- Rollback on failure
- Dependency ordering
- Backup and restore
"""

import tempfile
from pathlib import Path

import pytest

from code_scalpel.surgery.multi_repo import (
    MultiRepoCoordinator,
    RepoChange,
    SessionStatus,
)


class TestMultiRepoBasics:
    """Test basic multi-repo functionality."""

    def test_repo_change_creation(self):
        """RepoChange can be created."""
        change = RepoChange(
            operation="rename_symbol",
            target_file="src/module.py",
            old_name="old_func",
            new_name="new_func",
        )

        assert change.operation == "rename_symbol"
        assert change.target_file == "src/module.py"
        assert change.old_name == "old_func"
        assert change.new_name == "new_func"

    def test_coordinator_init(self):
        """MultiRepoCoordinator can be initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            coordinator = MultiRepoCoordinator(backup_dir=Path(tmpdir))
            assert coordinator.backup_dir == Path(tmpdir)

    def test_begin_session(self):
        """Sessions can be started."""
        coordinator = MultiRepoCoordinator()
        session_id = coordinator.begin_session()

        assert session_id is not None
        assert coordinator.get_session_status(session_id) == SessionStatus.ACTIVE


class TestSessionManagement:
    """Test session lifecycle management."""

    def test_add_change_to_session(self):
        """Changes can be added to session."""
        coordinator = MultiRepoCoordinator()
        session_id = coordinator.begin_session()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "repo1"
            repo_path.mkdir()

            change = RepoChange(
                operation="rename_symbol",
                target_file="test.py",
                old_name="old",
                new_name="new",
            )

            success = coordinator.add_change(session_id, repo_path, change)
            assert success is True

    def test_add_multiple_changes_same_repo(self):
        """Multiple changes can be added to same repo."""
        coordinator = MultiRepoCoordinator()
        session_id = coordinator.begin_session()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "repo1"
            repo_path.mkdir()

            change1 = RepoChange(
                operation="rename_symbol",
                target_file="file1.py",
                old_name="old1",
                new_name="new1",
            )

            change2 = RepoChange(
                operation="rename_symbol",
                target_file="file2.py",
                old_name="old2",
                new_name="new2",
            )

            coordinator.add_change(session_id, repo_path, change1)
            coordinator.add_change(session_id, repo_path, change2)

            repos = coordinator.list_session_repos(session_id)
            assert len(repos) == 1

    def test_add_changes_multiple_repos(self):
        """Changes can be added to multiple repos."""
        coordinator = MultiRepoCoordinator()
        session_id = coordinator.begin_session()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo1 = Path(tmpdir) / "repo1"
            repo1.mkdir()

            repo2 = Path(tmpdir) / "repo2"
            repo2.mkdir()

            change1 = RepoChange(
                operation="rename_symbol",
                target_file="test.py",
                old_name="old",
                new_name="new",
            )

            change2 = RepoChange(
                operation="rename_symbol",
                target_file="test.py",
                old_name="old",
                new_name="new",
            )

            coordinator.add_change(session_id, repo1, change1)
            coordinator.add_change(session_id, repo2, change2)

            repos = coordinator.list_session_repos(session_id)
            assert len(repos) == 2

    def test_cannot_add_to_nonexistent_session(self):
        """Cannot add changes to nonexistent session."""
        coordinator = MultiRepoCoordinator()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "repo1"
            repo_path.mkdir()

            change = RepoChange(
                operation="rename_symbol",
                target_file="test.py",
                old_name="old",
                new_name="new",
            )

            success = coordinator.add_change("invalid-session", repo_path, change)
            assert success is False


class TestDependencyOrdering:
    """Test repository dependency ordering."""

    def test_set_dependencies(self):
        """Dependencies can be set for session."""
        coordinator = MultiRepoCoordinator()
        session_id = coordinator.begin_session()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo1 = str(Path(tmpdir) / "repo1")
            repo2 = str(Path(tmpdir) / "repo2")

            success = coordinator.set_dependencies(session_id, dependency_order=[repo1, repo2])
            assert success is True

    def test_set_dependencies_invalid_session(self):
        """Cannot set dependencies for invalid session."""
        coordinator = MultiRepoCoordinator()

        success = coordinator.set_dependencies("invalid-session", dependency_order=["repo1", "repo2"])
        assert success is False


class TestAtomicCommit:
    """Test atomic commit across repositories."""

    def test_commit_empty_session(self):
        """Can commit empty session."""
        coordinator = MultiRepoCoordinator()
        session_id = coordinator.begin_session()

        result = coordinator.commit_session(session_id)
        assert result.success is True
        assert result.repos_affected == 0

    def test_commit_single_repo(self):
        """Can commit single repository."""
        coordinator = MultiRepoCoordinator()
        session_id = coordinator.begin_session()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "repo1"
            repo_path.mkdir()

            # Create test file
            test_file = repo_path / "test.py"
            test_file.write_text("def old_func(): pass")

            change = RepoChange(
                operation="rename_symbol",
                target_file="test.py",
                old_name="old_func",
                new_name="new_func",
            )

            coordinator.add_change(session_id, repo_path, change)
            result = coordinator.commit_session(session_id)

            assert result.success is True
            assert result.repos_affected == 1
            assert result.changes_applied == 1

    def test_commit_multiple_repos(self):
        """Can commit multiple repositories."""
        coordinator = MultiRepoCoordinator()
        session_id = coordinator.begin_session()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two repos
            repo1 = Path(tmpdir) / "repo1"
            repo1.mkdir()
            (repo1 / "file1.py").write_text("def func1(): pass")

            repo2 = Path(tmpdir) / "repo2"
            repo2.mkdir()
            (repo2 / "file2.py").write_text("def func2(): pass")

            # Add changes
            change1 = RepoChange(
                operation="rename_symbol",
                target_file="file1.py",
                old_name="func1",
                new_name="new_func1",
            )

            change2 = RepoChange(
                operation="rename_symbol",
                target_file="file2.py",
                old_name="func2",
                new_name="new_func2",
            )

            coordinator.add_change(session_id, repo1, change1)
            coordinator.add_change(session_id, repo2, change2)

            result = coordinator.commit_session(session_id)

            assert result.success is True
            assert result.repos_affected == 2
            assert result.changes_applied == 2

    def test_dry_run_mode(self):
        """Dry run validates without applying."""
        coordinator = MultiRepoCoordinator()
        session_id = coordinator.begin_session()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "repo1"
            repo_path.mkdir()
            (repo_path / "test.py").write_text("def old(): pass")

            change = RepoChange(
                operation="rename_symbol",
                target_file="test.py",
                old_name="old",
                new_name="new",
            )

            coordinator.add_change(session_id, repo_path, change)
            result = coordinator.commit_session(session_id, dry_run=True)

            assert result.success is True
            assert "Dry-run" in result.error
            assert result.changes_applied == 0

    def test_cannot_commit_twice(self):
        """Cannot commit same session twice."""
        coordinator = MultiRepoCoordinator()
        session_id = coordinator.begin_session()

        # First commit
        result1 = coordinator.commit_session(session_id)
        assert result1.success is True

        # Second commit should fail
        result2 = coordinator.commit_session(session_id)
        assert result2.success is False


class TestRollback:
    """Test rollback functionality."""

    def test_manual_rollback(self):
        """Can manually rollback session."""
        coordinator = MultiRepoCoordinator()
        session_id = coordinator.begin_session()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "repo1"
            repo_path.mkdir()
            (repo_path / "test.py").write_text("def old(): pass")

            change = RepoChange(
                operation="rename_symbol",
                target_file="test.py",
                old_name="old",
                new_name="new",
            )

            coordinator.add_change(session_id, repo_path, change)

            # Commit
            commit_result = coordinator.commit_session(session_id)
            assert commit_result.success is True

            # Rollback
            rollback_result = coordinator.rollback_session(session_id)
            assert rollback_result.success is True

            # Check status
            status = coordinator.get_session_status(session_id)
            assert status == SessionStatus.ROLLED_BACK

    def test_rollback_nonexistent_session(self):
        """Rollback of nonexistent session fails gracefully."""
        coordinator = MultiRepoCoordinator()

        result = coordinator.rollback_session("invalid-session")
        assert result.success is False


class TestSessionQueries:
    """Test session query operations."""

    def test_get_session_status(self):
        """Can query session status."""
        coordinator = MultiRepoCoordinator()
        session_id = coordinator.begin_session()

        status = coordinator.get_session_status(session_id)
        assert status == SessionStatus.ACTIVE

    def test_list_session_repos(self):
        """Can list repos in session."""
        coordinator = MultiRepoCoordinator()
        session_id = coordinator.begin_session()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo1 = Path(tmpdir) / "repo1"
            repo1.mkdir()
            repo2 = Path(tmpdir) / "repo2"
            repo2.mkdir()

            change = RepoChange(
                operation="rename_symbol",
                target_file="test.py",
                old_name="old",
                new_name="new",
            )

            coordinator.add_change(session_id, repo1, change)
            coordinator.add_change(session_id, repo2, change)

            repos = coordinator.list_session_repos(session_id)
            assert len(repos) == 2

    def test_list_repos_empty_session(self):
        """Empty session returns empty repo list."""
        coordinator = MultiRepoCoordinator()
        session_id = coordinator.begin_session()

        repos = coordinator.list_session_repos(session_id)
        assert repos == []

    def test_list_repos_invalid_session(self):
        """Invalid session returns empty repo list."""
        coordinator = MultiRepoCoordinator()

        repos = coordinator.list_session_repos("invalid-session")
        assert repos == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
