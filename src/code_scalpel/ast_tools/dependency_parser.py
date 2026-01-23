from __future__ import annotations

import json
import os
import re

from defusedxml import ElementTree as ET

try:
    import tomllib  # type: ignore[import]
except ImportError:
    import tomli as tomllib  # type: ignore[import]


class DependencyParser:
    """Parses project dependencies from standard configuration files."""

    def __init__(self, root_path: str):
        self.root_path = root_path

    def get_dependencies(self) -> dict[str, list[dict[str, str]]]:
        """Returns dependencies grouped by ecosystem."""
        deps = {
            "python": self._parse_python_deps(),
            "javascript": self._parse_javascript_deps(),
            "maven": self._parse_maven_deps(),  # [20251215_FEATURE] v2.0.1 Maven/Gradle support
        }
        return {k: v for k, v in deps.items() if v}

    def _parse_python_deps(self) -> list[dict[str, str]]:
        deps = []

        # 1. pyproject.toml (PEP 621 & Poetry)
        pp_path = os.path.join(self.root_path, "pyproject.toml")
        if os.path.exists(pp_path):
            try:
                with open(pp_path, "rb") as f:
                    data = tomllib.load(f)

                # Standard PEP 621
                if "project" in data and "dependencies" in data["project"]:
                    for d in data["project"]["dependencies"]:
                        deps.append(self._parse_pep508(d))

                # Poetry
                if "tool" in data and "poetry" in data["tool"] and "dependencies" in data["tool"]["poetry"]:
                    for k, v in data["tool"]["poetry"]["dependencies"].items():
                        if k.lower() != "python":
                            deps.append({"name": k, "version": str(v)})
            except Exception:
                pass  # Fail silently, we are scanning

        # 2. requirements.txt
        req_path = os.path.join(self.root_path, "requirements.txt")
        if os.path.exists(req_path):
            try:
                with open(req_path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and not line.startswith("-"):
                            deps.append(self._parse_pep508(line))
            except Exception:
                pass

        return self._deduplicate(deps)

    def _parse_javascript_deps(self) -> list[dict[str, str]]:
        deps = []
        pj_path = os.path.join(self.root_path, "package.json")
        if os.path.exists(pj_path):
            try:
                with open(pj_path, encoding="utf-8") as f:
                    data = json.load(f)
                for k, v in data.get("dependencies", {}).items():
                    deps.append({"name": k, "version": v})
                for k, v in data.get("devDependencies", {}).items():
                    deps.append({"name": k, "version": v, "type": "dev"})
            except Exception:
                pass
        return deps

    def _parse_maven_deps(self) -> list[dict[str, str]]:
        deps: list[dict[str, str]] = []

        # Minimal pom.xml parsing for groupId/artifactId/version triples
        pom_path = os.path.join(self.root_path, "pom.xml")
        if os.path.exists(pom_path):
            try:
                tree = ET.parse(pom_path)
                root = tree.getroot()
                if root is None:
                    return deps

                ns = {"m": root.tag.split("}")[0].strip("{")}

                for dep in root.findall(".//m:dependencies/m:dependency", ns):
                    gid = dep.findtext("m:groupId", default="", namespaces=ns)
                    aid = dep.findtext("m:artifactId", default="", namespaces=ns)
                    ver = dep.findtext("m:version", default="*", namespaces=ns)
                    scope = dep.findtext("m:scope", default="", namespaces=ns)
                    if gid and aid:
                        name = f"{gid}:{aid}"
                        entry = {"name": name, "version": ver or "*"}
                        if scope in {"test", "provided"}:
                            entry["type"] = "dev"
                        deps.append(entry)
            except Exception:
                pass

        # Gradle build.gradle/build.gradle.kts minimal grep
        for gradle_file in ("build.gradle", "build.gradle.kts"):
            g_path = os.path.join(self.root_path, gradle_file)
            if os.path.exists(g_path):
                try:
                    with open(g_path, encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith("//"):
                                continue
                            match = re.search(r"['\"]([\w\-.]+:[\w\-.]+):([\w\-.]+)['\"]", line)
                            if match:
                                coords = match.group(1)
                                ver = match.group(2)
                                entry = {"name": coords, "version": ver}
                                if any(k in line for k in ("testImplementation", "testCompile")):
                                    entry["type"] = "dev"
                                deps.append(entry)
                except Exception:
                    pass

        return self._deduplicate(deps)

    def _parse_pep508(self, s: str) -> dict[str, str]:
        # Basic parsing: "requests>=2.0" -> name="requests", version=">=2.0"
        s = s.split(";")[0].split("#")[0].strip()
        match = re.match(r"^([a-zA-Z0-9_\-\.]+)(.*)$", s)
        if match:
            return {"name": match.group(1), "version": match.group(2).strip() or "*"}
        return {"name": s, "version": "*"}

    def _deduplicate(self, deps: list[dict[str, str]]) -> list[dict[str, str]]:
        seen = set()
        unique = []
        for d in deps:
            if d["name"] not in seen:
                seen.add(d["name"])
                unique.append(d)
        return unique
