"""
Monorepo Support - Detect and handle multi-project repositories.

[20251226_FEATURE] Enterprise tier feature for crawl_project.

Detects monorepo workspace configurations:
- Lerna (lerna.json)
- Nx (nx.json, workspace.json)
- Turborepo (turbo.json)
- Yarn Workspaces (package.json workspaces field)
- pnpm Workspaces (pnpm-workspace.yaml)
- Bazel (WORKSPACE, BUILD files)
- Poetry (pyproject.toml with packages)

Usage:
    from code_scalpel.analysis.monorepo import MonorepoDetector

    detector = MonorepoDetector("/path/to/repo")
    result = detector.detect()

    for project in result.projects:
        print(f"{project.name}: {project.path}")
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MonorepoProject:
    """A project/package within a monorepo."""

    name: str
    path: str  # Relative path from repo root
    project_type: str  # "nodejs", "python", "go", etc.
    dependencies: list[str]  # Internal dependencies (other projects in monorepo)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MonorepoDetectionResult:
    """Result of monorepo detection."""

    is_monorepo: bool
    workspace_type: str | None  # "lerna", "nx", "turborepo", "bazel", etc.
    projects: list[MonorepoProject]
    root_config: dict[str, Any]
    cross_project_deps: dict[str, list[str]]  # project -> [dependencies]
    metadata: dict[str, Any] = field(default_factory=dict)


class MonorepoDetector:
    """Detects and analyzes monorepo structures."""

    def __init__(self, project_root: str | Path):
        """Initialize detector with repository root."""
        self.root = Path(project_root)

    def detect(self) -> MonorepoDetectionResult:
        """Detect monorepo configuration and enumerate projects."""
        # Try each detector in order of specificity
        detectors = [
            self._detect_nx,
            self._detect_turborepo,
            self._detect_lerna,
            self._detect_yarn_workspaces,
            self._detect_pnpm_workspaces,
            self._detect_bazel,
            self._detect_python_monorepo,
        ]

        for detector in detectors:
            result = detector()
            if result and result.is_monorepo:
                return result

        # Not a monorepo (single project)
        return MonorepoDetectionResult(
            is_monorepo=False,
            workspace_type=None,
            projects=[],
            root_config={},
            cross_project_deps={},
        )

    def _detect_nx(self) -> MonorepoDetectionResult | None:
        """Detect Nx monorepo."""
        nx_json = self.root / "nx.json"
        workspace_json = self.root / "workspace.json"

        if not (nx_json.exists() or workspace_json.exists()):
            return None

        projects: list[MonorepoProject] = []
        root_config: dict[str, Any] = {}

        # Read nx.json if exists
        if nx_json.exists():
            try:
                root_config = json.loads(nx_json.read_text())
            except Exception:
                pass

        # Scan for project.json files (Nx standard)
        for project_json in self.root.rglob("project.json"):
            try:
                config = json.loads(project_json.read_text())
                project_path = str(project_json.parent.relative_to(self.root))
                projects.append(
                    MonorepoProject(
                        name=config.get("name", project_path),
                        path=project_path,
                        project_type=self._detect_project_type(project_json.parent),
                        dependencies=[],
                        metadata={"nx_config": config},
                    )
                )
            except Exception:
                pass

        # Also check apps/ and libs/ directories (Nx convention)
        for subdir in ["apps", "libs", "packages"]:
            apps_dir = self.root / subdir
            if apps_dir.exists():
                for app in apps_dir.iterdir():
                    if app.is_dir() and (app / "package.json").exists():
                        pkg = self._read_package_json(app / "package.json")
                        if not any(p.path == str(app.relative_to(self.root)) for p in projects):
                            projects.append(
                                MonorepoProject(
                                    name=pkg.get("name", app.name),
                                    path=str(app.relative_to(self.root)),
                                    project_type="nodejs",
                                    dependencies=list(pkg.get("dependencies", {}).keys()),
                                )
                            )

        if not projects:
            return None

        # Build cross-project dependency graph
        cross_deps = self._build_cross_deps(projects)

        return MonorepoDetectionResult(
            is_monorepo=True,
            workspace_type="nx",
            projects=projects,
            root_config=root_config,
            cross_project_deps=cross_deps,
        )

    def _detect_turborepo(self) -> MonorepoDetectionResult | None:
        """Detect Turborepo monorepo."""
        turbo_json = self.root / "turbo.json"

        if not turbo_json.exists():
            return None

        try:
            root_config = json.loads(turbo_json.read_text())
        except Exception:
            root_config = {}

        # Turborepo uses package.json workspaces
        projects = self._scan_npm_workspaces()

        if not projects:
            return None

        cross_deps = self._build_cross_deps(projects)

        return MonorepoDetectionResult(
            is_monorepo=True,
            workspace_type="turborepo",
            projects=projects,
            root_config=root_config,
            cross_project_deps=cross_deps,
        )

    def _detect_lerna(self) -> MonorepoDetectionResult | None:
        """Detect Lerna monorepo."""
        lerna_json = self.root / "lerna.json"

        if not lerna_json.exists():
            return None

        try:
            root_config = json.loads(lerna_json.read_text())
        except Exception:
            root_config = {}

        # Get package locations from lerna.json
        package_patterns = root_config.get("packages", ["packages/*"])
        projects = self._scan_package_patterns(package_patterns)

        if not projects:
            return None

        cross_deps = self._build_cross_deps(projects)

        return MonorepoDetectionResult(
            is_monorepo=True,
            workspace_type="lerna",
            projects=projects,
            root_config=root_config,
            cross_project_deps=cross_deps,
        )

    def _detect_yarn_workspaces(self) -> MonorepoDetectionResult | None:
        """Detect Yarn Workspaces."""
        pkg_json = self.root / "package.json"

        if not pkg_json.exists():
            return None

        try:
            pkg = json.loads(pkg_json.read_text())
            workspaces = pkg.get("workspaces")
            if not workspaces:
                return None

            # Handle both array and object format
            if isinstance(workspaces, dict):
                patterns = workspaces.get("packages", [])
            else:
                patterns = workspaces

        except Exception:
            return None

        projects = self._scan_package_patterns(patterns)

        if not projects:
            return None

        cross_deps = self._build_cross_deps(projects)

        return MonorepoDetectionResult(
            is_monorepo=True,
            workspace_type="yarn_workspaces",
            projects=projects,
            root_config={"workspaces": workspaces},
            cross_project_deps=cross_deps,
        )

    def _detect_pnpm_workspaces(self) -> MonorepoDetectionResult | None:
        """Detect pnpm Workspaces."""
        pnpm_workspace = self.root / "pnpm-workspace.yaml"

        if not pnpm_workspace.exists():
            return None

        try:
            # Simple YAML parsing for packages field
            content = pnpm_workspace.read_text()
            patterns = []
            in_packages = False
            for line in content.splitlines():
                if line.strip() == "packages:":
                    in_packages = True
                elif in_packages and line.strip().startswith("- "):
                    pattern = line.strip()[2:].strip("'\"")
                    patterns.append(pattern)
                elif in_packages and not line.startswith(" "):
                    break
        except Exception:
            return None

        projects = self._scan_package_patterns(patterns)

        if not projects:
            return None

        cross_deps = self._build_cross_deps(projects)

        return MonorepoDetectionResult(
            is_monorepo=True,
            workspace_type="pnpm_workspaces",
            projects=projects,
            root_config={"packages": patterns},
            cross_project_deps=cross_deps,
        )

    def _detect_bazel(self) -> MonorepoDetectionResult | None:
        """Detect Bazel monorepo."""
        workspace_file = self.root / "WORKSPACE"
        workspace_bazel = self.root / "WORKSPACE.bazel"

        if not (workspace_file.exists() or workspace_bazel.exists()):
            return None

        projects: list[MonorepoProject] = []

        # Scan for BUILD files
        for build_file in self.root.rglob("BUILD*"):
            if build_file.name in ("BUILD", "BUILD.bazel"):
                project_path = str(build_file.parent.relative_to(self.root))
                if project_path == ".":
                    continue
                projects.append(
                    MonorepoProject(
                        name=project_path.replace("/", "_"),
                        path=project_path,
                        project_type=self._detect_project_type(build_file.parent),
                        dependencies=[],
                    )
                )

        if not projects:
            return None

        return MonorepoDetectionResult(
            is_monorepo=True,
            workspace_type="bazel",
            projects=projects,
            root_config={},
            cross_project_deps={},
        )

    def _detect_python_monorepo(self) -> MonorepoDetectionResult | None:
        """Detect Python monorepo (Poetry workspaces or packages/ structure)."""
        packages_dir = self.root / "packages"

        # Check for packages/ directory with multiple Python packages
        if packages_dir.exists():
            projects: list[MonorepoProject] = []
            for pkg_dir in packages_dir.iterdir():
                if pkg_dir.is_dir() and ((pkg_dir / "setup.py").exists() or (pkg_dir / "pyproject.toml").exists()):
                    projects.append(
                        MonorepoProject(
                            name=pkg_dir.name,
                            path=str(pkg_dir.relative_to(self.root)),
                            project_type="python",
                            dependencies=[],
                        )
                    )

            if len(projects) >= 2:
                return MonorepoDetectionResult(
                    is_monorepo=True,
                    workspace_type="python_packages",
                    projects=projects,
                    root_config={},
                    cross_project_deps={},
                )

        return None

    def _scan_npm_workspaces(self) -> list[MonorepoProject]:
        """Scan for npm workspace packages."""
        pkg_json = self.root / "package.json"
        if not pkg_json.exists():
            return []

        try:
            pkg = json.loads(pkg_json.read_text())
            workspaces = pkg.get("workspaces", [])
            if isinstance(workspaces, dict):
                workspaces = workspaces.get("packages", [])
            return self._scan_package_patterns(workspaces)
        except Exception:
            return []

    def _scan_package_patterns(self, patterns: list[str]) -> list[MonorepoProject]:
        """Scan glob patterns for packages."""
        projects: list[MonorepoProject] = []

        for pattern in patterns:
            # Convert npm glob to Python glob
            pattern = pattern.replace("/*", "")

            search_dir = self.root / pattern
            if search_dir.exists() and search_dir.is_dir():
                for pkg_dir in search_dir.iterdir():
                    if pkg_dir.is_dir():
                        pkg_json = pkg_dir / "package.json"
                        if pkg_json.exists():
                            pkg = self._read_package_json(pkg_json)
                            projects.append(
                                MonorepoProject(
                                    name=pkg.get("name", pkg_dir.name),
                                    path=str(pkg_dir.relative_to(self.root)),
                                    project_type="nodejs",
                                    dependencies=list(pkg.get("dependencies", {}).keys()),
                                )
                            )

        return projects

    def _read_package_json(self, path: Path) -> dict[str, Any]:
        """Read and parse a package.json file."""
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}

    def _detect_project_type(self, project_path: Path) -> str:
        """Detect the type of a project directory."""
        if (project_path / "package.json").exists():
            return "nodejs"
        if (project_path / "pyproject.toml").exists() or (project_path / "setup.py").exists():
            return "python"
        if (project_path / "go.mod").exists():
            return "go"
        if (project_path / "Cargo.toml").exists():
            return "rust"
        if (project_path / "pom.xml").exists() or (project_path / "build.gradle").exists():
            return "java"
        return "unknown"

    def _build_cross_deps(self, projects: list[MonorepoProject]) -> dict[str, list[str]]:
        """Build cross-project dependency graph."""
        project_names = {p.name for p in projects}
        cross_deps: dict[str, list[str]] = {}

        for project in projects:
            internal_deps = [d for d in project.dependencies if d in project_names]
            if internal_deps:
                cross_deps[project.name] = internal_deps

        return cross_deps


def detect_monorepo(project_root: str | Path) -> MonorepoDetectionResult:
    """Convenience function to detect monorepo configuration."""
    detector = MonorepoDetector(project_root)
    return detector.detect()
