#!/usr/bin/env python3
"""
Bundler Parser - Ruby Dependency Management Analysis.

[20260304_FEATURE] Full implementation of Bundler/bundler-audit parser.
Parses Gemfile and Gemfile.lock to extract gem dependencies and checks
for known vulnerabilities via bundler-audit.

Output format: bundler-audit check --format json (or plain text Gemfile parsing)
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Gem:
    """Represents a Ruby gem dependency."""

    name: str
    version: str
    version_constraint: Optional[str] = None
    source: str = "rubygems.org"
    is_direct_dependency: bool = True
    is_vulnerable: bool = False
    vulnerability_info: Optional[str] = None
    cve: Optional[str] = None


@dataclass
class BundleConfig:
    """Bundler configuration."""

    gemfile_path: Path = field(default_factory=lambda: Path("Gemfile"))
    lockfile_path: Path = field(default_factory=lambda: Path("Gemfile.lock"))
    ruby_version: Optional[str] = None
    bundler_version: Optional[str] = None


class BundlerParser:
    """
    Parser for Bundler Ruby dependency analysis.

    [20260304_FEATURE] Implements Gemfile parsing + bundler-audit vulnerability scanning.

    Analyzes Ruby project dependencies via Bundler parsing Gemfile and
    Gemfile.lock to extract dependency information, versions, and vulnerabilities.

    Graceful degradation: returns [] if bundler-audit is not installed.
    """

    def __init__(self) -> None:
        """Initialize Bundler parser."""
        self.config = BundleConfig()

    def parse_gemfile(self, gemfile_path: Path) -> List[Gem]:
        """
        Parse Gemfile to extract direct gem dependencies.

        [20260304_FEATURE] Parses `gem 'name', 'version_constraint'` lines.
        """
        try:
            content = Path(gemfile_path).read_text(encoding="utf-8")
        except (OSError, IOError):
            return []
        return self.extract_gems(content)

    def parse_gemfile_lock(self, lockfile_path: Path) -> List[Gem]:
        """
        Parse Gemfile.lock to extract resolved gem versions.

        [20260304_FEATURE] Parses the GEM SPECS section.
        """
        try:
            content = Path(lockfile_path).read_text(encoding="utf-8")
        except (OSError, IOError):
            return []
        return self._parse_lockfile_content(content)

    def _parse_lockfile_content(self, content: str) -> List[Gem]:
        """Parse raw Gemfile.lock content."""
        gems: List[Gem] = []
        in_specs = False
        for line in content.splitlines():
            if line.strip() == "GEM":
                in_specs = True
                continue
            if in_specs:
                if line.startswith(" " * 4) and not line.startswith(" " * 6):
                    # "    gemname (version)" lines
                    m = re.match(r"\s{4}(\S+)\s+\(([^)]+)\)", line)
                    if m:
                        gems.append(Gem(name=m.group(1), version=m.group(2), is_direct_dependency=False))
                elif not line.startswith(" "):
                    in_specs = False
        return gems

    def extract_gems(self, gemfile_content: str) -> List[Gem]:
        """
        Extract gems from Gemfile source text.

        [20260304_FEATURE] Handles `gem 'name'`, `gem 'name', '~> version'` patterns.
        """
        gems: List[Gem] = []
        # Match: gem 'name' or gem "name", '~> 1.0'
        pattern = re.compile(r"""gem\s+['"]([^'"]+)['"]\s*(?:,\s*['"]([^'"]+)['"])?""")
        for m in pattern.finditer(gemfile_content):
            gems.append(
                Gem(
                    name=m.group(1),
                    version=m.group(2) or "",
                    version_constraint=m.group(2),
                    is_direct_dependency=True,
                )
            )
        return gems

    def extract_locked_versions(self, lockfile_content: str) -> Dict[str, str]:
        """
        Extract resolved versions from Gemfile.lock.

        [20260304_FEATURE] Returns {gem_name: resolved_version} mapping.
        """
        versions: Dict[str, str] = {}
        for gem in self._parse_lockfile_content(lockfile_content):
            versions[gem.name] = gem.version
        return versions

    def scan_for_vulnerabilities(self, gems: List[Gem]) -> List[Gem]:
        """
        Run bundler-audit on current directory and annotate gems with vulnerabilities.

        [20260304_FEATURE] Graceful degradation when bundler-audit not installed.
        """
        if shutil.which("bundler-audit") is None:
            return gems
        try:
            result = subprocess.run(
                ["bundler-audit", "check", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            data = json.loads(result.stdout or "{}")
        except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError):
            return gems
        vulnerable: Dict[str, str] = {}
        for advisory in data.get("results", []):
            gem_name = advisory.get("gem", {}).get("name", "")
            cve = advisory.get("advisory", {}).get("cve", "")
            vulnerable[gem_name] = cve
        for gem in gems:
            if gem.name in vulnerable:
                gem.is_vulnerable = True
                gem.cve = vulnerable[gem.name]
                gem.vulnerability_info = f"CVE: {vulnerable[gem.name]}"
        return gems

    def detect_outdated_gems(self, gems: List[Gem]) -> List[Gem]:
        """
        Return gems that have version constraints suggesting possible outdatedness.

        [20260304_FEATURE] Simple heuristic: gems with no constraint may be outdated.
        """
        return [g for g in gems if not g.version_constraint]

    def analyze_transitive_dependencies(self, gems: List[Gem]) -> Dict[str, Any]:
        """
        Provide simple transitive dependency summary.

        [20260304_FEATURE] Returns count of direct vs transitive gems.
        """
        direct = [g for g in gems if g.is_direct_dependency]
        transitive = [g for g in gems if not g.is_direct_dependency]
        return {
            "total": len(gems),
            "direct": len(direct),
            "transitive": len(transitive),
        }

    def generate_dependency_report(self, gems: List[Gem]) -> str:
        """
        Generate a structured JSON dependency report.

        [20260304_FEATURE] Returns JSON string.
        """
        analysis = self.analyze_transitive_dependencies(gems)
        vulnerable_gems = [g for g in gems if g.is_vulnerable]
        report: Dict[str, Any] = {
            "tool": "bundler",
            **analysis,
            "vulnerable_count": len(vulnerable_gems),
            "gems": [
                {
                    "name": g.name,
                    "version": g.version,
                    "constraint": g.version_constraint,
                    "vulnerable": g.is_vulnerable,
                    "cve": g.cve,
                }
                for g in gems
            ],
        }
        return json.dumps(report, indent=2)
