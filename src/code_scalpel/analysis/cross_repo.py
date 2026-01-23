"""
Cross-Repository Dependency Linking - Analyze dependencies across repositories.

[20251226_FEATURE] Enterprise tier feature for crawl_project.

Features:
- Track external package dependencies
- Detect internal package references
- Map import graphs across repositories
- Generate dependency visualization

Usage:
    from code_scalpel.analysis.cross_repo import CrossRepoLinker

    linker = CrossRepoLinker()
    linker.add_repo("/path/to/repo1", "repo1")
    linker.add_repo("/path/to/repo2", "repo2")

    links = linker.find_cross_repo_links()
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ExternalDependency:
    """An external package dependency."""

    name: str
    version: str | None
    source: str  # "npm", "pypi", "maven", "cargo", etc.
    repo_name: str
    declared_in: str  # File path where declared


@dataclass
class InternalLink:
    """A link between two internal packages/modules."""

    from_repo: str
    from_file: str
    from_symbol: str
    to_repo: str
    to_package: str
    link_type: str  # "import", "dependency", "reference"


@dataclass
class CrossRepoAnalysis:
    """Complete cross-repository analysis."""

    repos: list[str]
    external_deps: list[ExternalDependency]
    internal_links: list[InternalLink]
    shared_deps: dict[str, list[str]]  # dep_name -> [repos using it]
    conflict_versions: list[dict[str, Any]]  # Dependencies with version conflicts
    mermaid_diagram: str


class CrossRepoLinker:
    """Analyze and link dependencies across repositories."""

    def __init__(self):
        """Initialize the cross-repo linker."""
        self.repos: dict[str, Path] = {}  # name -> path
        self._external_deps: dict[str, list[ExternalDependency]] = {}
        self._internal_packages: dict[str, set[str]] = {}  # repo -> packages

    def add_repo(self, repo_path: str | Path, name: str | None = None) -> None:
        """
        Add a repository to analyze.

        Args:
            repo_path: Path to the repository
            name: Optional name (defaults to directory name)
        """
        path = Path(repo_path).resolve()
        repo_name = name or path.name
        self.repos[repo_name] = path

        # Scan for dependencies
        self._external_deps[repo_name] = self._scan_dependencies(path, repo_name)
        self._internal_packages[repo_name] = self._scan_internal_packages(path)

    def _scan_dependencies(
        self,
        repo_path: Path,
        repo_name: str,
    ) -> list[ExternalDependency]:
        """Scan repository for external dependencies."""
        deps: list[ExternalDependency] = []

        # Python dependencies
        deps.extend(self._scan_python_deps(repo_path, repo_name))

        # Node.js dependencies
        deps.extend(self._scan_npm_deps(repo_path, repo_name))

        # Java dependencies
        deps.extend(self._scan_maven_deps(repo_path, repo_name))

        return deps

    def _scan_python_deps(
        self,
        repo_path: Path,
        repo_name: str,
    ) -> list[ExternalDependency]:
        """Scan Python dependency files."""
        deps: list[ExternalDependency] = []

        # requirements.txt
        req_file = repo_path / "requirements.txt"
        if req_file.exists():
            try:
                for line in req_file.read_text().splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("-"):
                        # Parse package==version or package>=version etc.
                        match = re.match(r"([a-zA-Z0-9_-]+)([<>=!]+)?(.+)?", line)
                        if match:
                            deps.append(
                                ExternalDependency(
                                    name=match.group(1),
                                    version=match.group(3),
                                    source="pypi",
                                    repo_name=repo_name,
                                    declared_in=str(req_file.relative_to(repo_path)),
                                )
                            )
            except Exception:
                pass

        # pyproject.toml
        pyproject = repo_path / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text()
                # Simple TOML parsing for dependencies
                in_deps = False
                for line in content.splitlines():
                    if "[project.dependencies]" in line or "[tool.poetry.dependencies]" in line:
                        in_deps = True
                    elif line.startswith("[") and in_deps:
                        in_deps = False
                    elif in_deps and "=" in line:
                        parts = line.split("=")
                        pkg_name = parts[0].strip().strip('"')
                        if pkg_name and pkg_name != "python":
                            deps.append(
                                ExternalDependency(
                                    name=pkg_name,
                                    version=(parts[1].strip().strip('"') if len(parts) > 1 else None),
                                    source="pypi",
                                    repo_name=repo_name,
                                    declared_in=str(pyproject.relative_to(repo_path)),
                                )
                            )
            except Exception:
                pass

        return deps

    def _scan_npm_deps(
        self,
        repo_path: Path,
        repo_name: str,
    ) -> list[ExternalDependency]:
        """Scan npm package.json for dependencies."""
        deps: list[ExternalDependency] = []

        pkg_json = repo_path / "package.json"
        if pkg_json.exists():
            try:
                pkg = json.loads(pkg_json.read_text())
                for dep_type in ["dependencies", "devDependencies", "peerDependencies"]:
                    for name, version in pkg.get(dep_type, {}).items():
                        deps.append(
                            ExternalDependency(
                                name=name,
                                version=version,
                                source="npm",
                                repo_name=repo_name,
                                declared_in="package.json",
                            )
                        )
            except Exception:
                pass

        return deps

    def _scan_maven_deps(
        self,
        repo_path: Path,
        repo_name: str,
    ) -> list[ExternalDependency]:
        """Scan Maven pom.xml for dependencies."""
        deps: list[ExternalDependency] = []

        pom_xml = repo_path / "pom.xml"
        if pom_xml.exists():
            try:
                content = pom_xml.read_text()
                # Simple XML parsing for dependencies
                dep_pattern = re.compile(
                    r"<dependency>\s*<groupId>([^<]+)</groupId>\s*"
                    r"<artifactId>([^<]+)</artifactId>\s*"
                    r"(?:<version>([^<]+)</version>)?",
                    re.DOTALL,
                )
                for match in dep_pattern.finditer(content):
                    deps.append(
                        ExternalDependency(
                            name=f"{match.group(1)}:{match.group(2)}",
                            version=match.group(3),
                            source="maven",
                            repo_name=repo_name,
                            declared_in="pom.xml",
                        )
                    )
            except Exception:
                pass

        return deps

    def _scan_internal_packages(self, repo_path: Path) -> set[str]:
        """Scan for internally defined packages/modules."""
        packages: set[str] = set()

        # Python packages
        for init_file in repo_path.rglob("__init__.py"):
            pkg_path = init_file.parent
            if "site-packages" not in str(pkg_path) and ".venv" not in str(pkg_path):
                try:
                    rel_path = pkg_path.relative_to(repo_path)
                    packages.add(str(rel_path).replace("/", ".").replace("\\", "."))
                except ValueError:
                    pass

        # npm packages
        pkg_json = repo_path / "package.json"
        if pkg_json.exists():
            try:
                pkg = json.loads(pkg_json.read_text())
                if "name" in pkg:
                    packages.add(pkg["name"])
            except Exception:
                pass

        return packages

    def find_cross_repo_links(self) -> CrossRepoAnalysis:
        """
        Analyze all repositories and find cross-repo dependencies.

        Returns:
            CrossRepoAnalysis with complete dependency information
        """
        all_external_deps: list[ExternalDependency] = []
        internal_links: list[InternalLink] = []

        # Collect all external dependencies
        for repo_name, deps in self._external_deps.items():
            all_external_deps.extend(deps)

        # Find shared dependencies
        shared_deps: dict[str, list[str]] = {}
        for dep in all_external_deps:
            if dep.name not in shared_deps:
                shared_deps[dep.name] = []
            if dep.repo_name not in shared_deps[dep.name]:
                shared_deps[dep.name].append(dep.repo_name)

        # Filter to only truly shared deps
        shared_deps = {k: v for k, v in shared_deps.items() if len(v) > 1}

        # Find version conflicts
        conflicts = self._find_version_conflicts(all_external_deps)

        # Find internal links (repos depending on each other's packages)
        for repo_name, repo_path in self.repos.items():
            other_packages = {}
            for other_repo, packages in self._internal_packages.items():
                if other_repo != repo_name:
                    for pkg in packages:
                        other_packages[pkg] = other_repo

            # Scan Python imports
            links = self._find_internal_imports(
                repo_path,
                repo_name,
                other_packages,
            )
            internal_links.extend(links)

        # Generate Mermaid diagram
        diagram = self._generate_mermaid(
            list(self.repos.keys()),
            shared_deps,
            internal_links,
        )

        return CrossRepoAnalysis(
            repos=list(self.repos.keys()),
            external_deps=all_external_deps,
            internal_links=internal_links,
            shared_deps=shared_deps,
            conflict_versions=conflicts,
            mermaid_diagram=diagram,
        )

    def _find_version_conflicts(
        self,
        deps: list[ExternalDependency],
    ) -> list[dict[str, Any]]:
        """Find dependencies with conflicting versions across repos."""
        conflicts: list[dict[str, Any]] = []

        # Group by (name, source)
        dep_versions: dict[tuple[str, str], dict[str, str]] = {}
        for dep in deps:
            key = (dep.name, dep.source)
            if key not in dep_versions:
                dep_versions[key] = {}
            if dep.version:
                dep_versions[key][dep.repo_name] = dep.version

        # Find conflicts
        for (name, source), versions in dep_versions.items():
            unique_versions = set(versions.values())
            if len(unique_versions) > 1:
                conflicts.append(
                    {
                        "name": name,
                        "source": source,
                        "versions": dict(versions),
                    }
                )

        return conflicts

    def _find_internal_imports(
        self,
        repo_path: Path,
        repo_name: str,
        other_packages: dict[str, str],
    ) -> list[InternalLink]:
        """Find imports of other repo packages."""
        links: list[InternalLink] = []

        for py_file in repo_path.rglob("*.py"):
            if ".venv" in str(py_file) or "node_modules" in str(py_file):
                continue

            try:
                content = py_file.read_text()
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            pkg_root = alias.name.split(".")[0]
                            if pkg_root in other_packages:
                                links.append(
                                    InternalLink(
                                        from_repo=repo_name,
                                        from_file=str(py_file.relative_to(repo_path)),
                                        from_symbol=alias.name,
                                        to_repo=other_packages[pkg_root],
                                        to_package=pkg_root,
                                        link_type="import",
                                    )
                                )
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            pkg_root = node.module.split(".")[0]
                            if pkg_root in other_packages:
                                links.append(
                                    InternalLink(
                                        from_repo=repo_name,
                                        from_file=str(py_file.relative_to(repo_path)),
                                        from_symbol=node.module,
                                        to_repo=other_packages[pkg_root],
                                        to_package=pkg_root,
                                        link_type="import",
                                    )
                                )
            except Exception:
                pass

        return links

    def _generate_mermaid(
        self,
        repos: list[str],
        shared_deps: dict[str, list[str]],
        internal_links: list[InternalLink],
    ) -> str:
        """Generate Mermaid diagram of cross-repo dependencies."""
        lines = ["graph LR"]

        # Add repo nodes
        for repo in repos:
            lines.append(f'    {repo}["{repo}"]')

        # Add shared dependency edges
        for dep_name, using_repos in list(shared_deps.items())[:10]:  # Limit for readability
            safe_name = dep_name.replace("-", "_").replace("@", "").replace("/", "_")
            lines.append(f'    {safe_name}(("{dep_name}"))')
            for repo in using_repos:
                lines.append(f"    {repo} --> {safe_name}")

        # Add internal links
        for link in internal_links[:20]:  # Limit for readability
            lines.append(f"    {link.from_repo} -.-> |{link.to_package}| {link.to_repo}")

        return "\n".join(lines)


def analyze_cross_repo_deps(
    repo_paths: list[str | Path],
    repo_names: list[str] | None = None,
) -> CrossRepoAnalysis:
    """
    Convenience function to analyze cross-repository dependencies.

    Args:
        repo_paths: List of repository paths
        repo_names: Optional list of names for each repo

    Returns:
        CrossRepoAnalysis with complete dependency information
    """
    linker = CrossRepoLinker()

    names = repo_names or [None] * len(repo_paths)
    for path, name in zip(repo_paths, names, strict=False):
        linker.add_repo(path, name)

    return linker.find_cross_repo_links()
