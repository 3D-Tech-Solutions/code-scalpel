"""Java remaining parser tests — Stage 4c.

Validates MavenParser, GradleParser, DependencyCheckParser, JaCoCoParser,
PitestParser, SemgrepParser.

All tests operate on fixture strings/XML — no installed CLI tools required.

[20260303_TEST] Created for Stage 4c Java tool parsers (Work-Tracking.md).
"""

from __future__ import annotations

import json
import textwrap

# ---------------------------------------------------------------------------
# MavenParser
# ---------------------------------------------------------------------------


class TestMavenParser:
    """Tests for MavenParser."""

    _POM_XML = textwrap.dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <project xmlns="http://maven.apache.org/POM/4.0.0">
          <groupId>com.example</groupId>
          <artifactId>myapp</artifactId>
          <version>1.0.0</version>
          <dependencies>
            <dependency>
              <groupId>org.springframework</groupId>
              <artifactId>spring-core</artifactId>
              <version>5.3.20</version>
            </dependency>
            <dependency>
              <groupId>junit</groupId>
              <artifactId>junit</artifactId>
              <version>4.13.2</version>
              <scope>test</scope>
            </dependency>
          </dependencies>
          <build>
            <plugins>
              <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.11.0</version>
              </plugin>
            </plugins>
          </build>
        </project>
    """)

    _BUILD_OUTPUT = textwrap.dedent("""\
        [ERROR] /home/user/project/src/Main.java:[10,5] cannot find symbol
        [WARNING] some warning message
        [INFO] BUILD FAILURE
    """)

    def _get_parser(self, tmp_path):
        from code_scalpel.code_parsers.java_parsers.java_parsers_Maven import (
            MavenParser,
        )

        pom = tmp_path / "pom.xml"
        pom.write_text(self._POM_XML, encoding="utf-8")
        return MavenParser(pom_path=pom), pom

    def test_parse_pom_xml_dependencies(self, tmp_path):
        parser, pom = self._get_parser(tmp_path)
        data = parser.parse_pom_xml(pom)
        assert data["artifact_id"] == "myapp"
        assert data["group_id"] == "com.example"
        deps = data["dependencies"]
        assert len(deps) == 2
        assert deps[0].artifact_id == "spring-core"
        assert deps[1].scope == "test"

    def test_get_dependencies_after_parse(self, tmp_path):
        parser, pom = self._get_parser(tmp_path)
        parser.parse_pom_xml(pom)
        deps = parser.get_dependencies()
        assert len(deps) == 2
        artifact_ids = {d.artifact_id for d in deps}
        assert "spring-core" in artifact_ids
        assert "junit" in artifact_ids

    def test_get_plugins_after_parse(self, tmp_path):
        parser, pom = self._get_parser(tmp_path)
        parser.parse_pom_xml(pom)
        plugins = parser.get_plugins()
        assert len(plugins) == 1
        assert plugins[0].artifact_id == "maven-compiler-plugin"
        assert plugins[0].version == "3.11.0"

    def test_parse_build_output(self):
        from code_scalpel.code_parsers.java_parsers.java_parsers_Maven import (
            MavenParser,
        )

        parser = MavenParser()
        records = parser.parse_build_output(self._BUILD_OUTPUT)
        levels = [r["level"] for r in records]
        assert "ERROR" in levels
        assert "WARNING" in levels
        assert "INFO" in levels

    def test_extract_compile_errors(self):
        from code_scalpel.code_parsers.java_parsers.java_parsers_Maven import (
            MavenParser,
        )

        parser = MavenParser()
        errors = parser.extract_compile_errors(self._BUILD_OUTPUT)
        assert len(errors) == 1
        err = errors[0]
        assert err.line == 10
        assert err.column == 5
        assert "cannot find symbol" in err.message
        assert err.error_type == "ERROR"

    def test_extract_compile_errors_empty(self):
        from code_scalpel.code_parsers.java_parsers.java_parsers_Maven import (
            MavenParser,
        )

        parser = MavenParser()
        assert parser.extract_compile_errors("") == []
        assert parser.extract_compile_errors("[INFO] BUILD SUCCESS") == []

    def test_generate_report_json(self, tmp_path):
        parser, _ = self._get_parser(tmp_path)
        parser.parse_pom_xml()
        data = json.loads(parser.generate_report(format="json"))
        assert data["tool"] == "maven"
        assert data["dependencies"] == 2

    def test_get_dependencies_before_parse(self):
        from code_scalpel.code_parsers.java_parsers.java_parsers_Maven import (
            MavenParser,
        )

        parser = MavenParser()
        assert parser.get_dependencies() == []
        assert parser.get_plugins() == []

    def test_parse_bad_pom(self, tmp_path):
        from code_scalpel.code_parsers.java_parsers.java_parsers_Maven import (
            MavenParser,
        )

        bad = tmp_path / "pom.xml"
        bad.write_text("NOT XML", encoding="utf-8")
        parser = MavenParser()
        result = parser.parse_pom_xml(bad)
        assert result == {}


# ---------------------------------------------------------------------------
# GradleParser
# ---------------------------------------------------------------------------


class TestGradleParser:
    """Tests for GradleParser."""

    _BUILD_GRADLE = textwrap.dedent("""\
        plugins {
            id 'java'
        }

        dependencies {
            implementation 'org.springframework.boot:spring-boot-starter:3.1.0'
            testImplementation 'org.junit.jupiter:junit-jupiter:5.9.3'
            runtimeOnly 'com.h2database:h2:2.1.214'
        }
    """)

    _BUILD_OUTPUT = textwrap.dedent("""\
        > Task :compileJava FAILED
        src/main/java/Main.java:5:10: error: cannot find symbol
        BUILD FAILED
    """)

    def _get_parser(self, tmp_path):
        from code_scalpel.code_parsers.java_parsers.java_parsers_Gradle import (
            GradleParser,
        )

        gradle = tmp_path / "build.gradle"
        gradle.write_text(self._BUILD_GRADLE, encoding="utf-8")
        return GradleParser(build_path=gradle), gradle

    def test_parse_gradle_file_dependencies(self, tmp_path):
        parser, gradle = self._get_parser(tmp_path)
        data = parser.parse_gradle_file(gradle)
        assert "dependencies" in data
        assert len(data["dependencies"]) == 3

    def test_get_dependencies_from_content(self):
        from code_scalpel.code_parsers.java_parsers.java_parsers_Gradle import (
            GradleParser,
        )

        parser = GradleParser()
        deps = parser.get_dependencies(content=self._BUILD_GRADLE)
        assert len(deps) == 3
        configs = {d.configuration for d in deps}
        assert "implementation" in configs
        assert "testImplementation" in configs

    def test_get_dependencies_names(self):
        from code_scalpel.code_parsers.java_parsers.java_parsers_Gradle import (
            GradleParser,
        )

        parser = GradleParser()
        deps = parser.get_dependencies(content=self._BUILD_GRADLE)
        names = {d.name for d in deps}
        assert "spring-boot-starter" in names
        assert "h2" in names

    def test_parse_build_output_levels(self):
        from code_scalpel.code_parsers.java_parsers.java_parsers_Gradle import (
            GradleParser,
        )

        parser = GradleParser()
        records = parser.parse_build_output(self._BUILD_OUTPUT)
        # Should include at least ERROR and FAILED records
        levels = {r["level"] for r in records}
        assert "ERROR" in levels or "FAILED" in levels

    def test_extract_compile_errors(self):
        from code_scalpel.code_parsers.java_parsers.java_parsers_Gradle import (
            GradleParser,
        )

        parser = GradleParser()
        errors = parser.extract_compile_errors(self._BUILD_OUTPUT)
        assert len(errors) == 1
        e = errors[0]
        assert e.line == 5
        assert e.column == 10
        assert "cannot find symbol" in e.message

    def test_generate_report_json(self):
        from code_scalpel.code_parsers.java_parsers.java_parsers_Gradle import (
            GradleParser,
        )

        parser = GradleParser()
        deps = parser.get_dependencies(content=self._BUILD_GRADLE)
        data = json.loads(parser.generate_report(dependencies=deps, format="json"))
        assert data["tool"] == "gradle"
        assert data["dependencies"] == 3

    def test_get_dependencies_no_path(self):
        from code_scalpel.code_parsers.java_parsers.java_parsers_Gradle import (
            GradleParser,
        )

        parser = GradleParser()
        assert parser.get_dependencies() == []


# ---------------------------------------------------------------------------
# DependencyCheckParser
# ---------------------------------------------------------------------------


class TestDependencyCheckParser:
    """Tests for DependencyCheckParser."""

    _JSON_REPORT = json.dumps(
        {
            "dependencies": [
                {
                    "fileName": "log4j-1.2.17.jar",
                    "version": "1.2.17",
                    "vulnerabilities": [
                        {
                            "name": "CVE-2019-17571",
                            "severity": "CRITICAL",
                            "description": "Log4j insecure deserialization",
                            "cvssv3": {"baseScore": 9.8},
                        },
                        {
                            "name": "CVE-2020-9488",
                            "severity": "HIGH",
                            "description": "SMTP connection",
                            "cvssv2": {"score": 7.5},
                        },
                    ],
                },
                {
                    "fileName": "commons-lang-2.6.jar",
                    "version": "2.6",
                    "vulnerabilities": [],
                },
            ]
        }
    )

    _XML_REPORT = textwrap.dedent("""\
        <?xml version="1.0"?>
        <analysis>
          <dependencies>
            <dependency>
              <fileName>struts2-core-2.5.jar</fileName>
              <version>2.5</version>
              <vulnerabilities>
                <vulnerability>
                  <name>CVE-2017-5638</name>
                  <severity>CRITICAL</severity>
                  <cvssScore>10.0</cvssScore>
                  <description>Apache Struts RCE</description>
                </vulnerability>
              </vulnerabilities>
            </dependency>
          </dependencies>
        </analysis>
    """)

    def _get_parser(self):
        from code_scalpel.code_parsers.java_parsers.java_parsers_DependencyCheck import (
            DependencyCheckParser,
        )

        return DependencyCheckParser()

    def test_parse_json_output_basic(self):
        parser = self._get_parser()
        findings = parser.parse_json_output(self._JSON_REPORT)
        assert len(findings) == 2
        assert findings[0].cve_id == "CVE-2019-17571"
        assert findings[0].component == "log4j-1.2.17.jar"
        assert findings[0].cvss_score == 9.8

    def test_parse_json_output_empty(self):
        parser = self._get_parser()
        assert parser.parse_json_output("") == []
        assert parser.parse_json_output("{}") == []

    def test_map_to_cve(self):
        parser = self._get_parser()
        findings = parser.parse_json_output(self._JSON_REPORT)
        cve_map = parser.map_to_cve(findings)
        assert "CVE-2019-17571" in cve_map
        assert len(cve_map["CVE-2019-17571"]) == 1

    def test_map_to_cvss_severity(self):
        parser = self._get_parser()
        findings = parser.parse_json_output(self._JSON_REPORT)
        sev_map = parser.map_to_cvss(findings)
        assert "CRITICAL" in sev_map or "HIGH" in sev_map

    def test_get_vulnerable_dependencies(self):
        parser = self._get_parser()
        findings = parser.parse_json_output(self._JSON_REPORT)
        vulns = parser.get_vulnerable_dependencies(findings)
        assert "log4j-1.2.17.jar" in vulns
        # commons-lang has no vulnerabilities → not in findings
        assert "commons-lang-2.6.jar" not in vulns

    def test_parse_xml_report_from_string(self, tmp_path):
        from code_scalpel.code_parsers.java_parsers.java_parsers_DependencyCheck import (
            DependencyCheckParser,
        )

        xml_file = tmp_path / "report.xml"
        xml_file.write_text(self._XML_REPORT, encoding="utf-8")
        parser = DependencyCheckParser()
        findings = parser.parse_xml_report(xml_file)
        assert len(findings) == 1
        assert findings[0].cve_id == "CVE-2017-5638"
        assert findings[0].cvss_score == 10.0

    def test_generate_report_json(self):
        parser = self._get_parser()
        findings = parser.parse_json_output(self._JSON_REPORT)
        data = json.loads(parser.generate_report(findings, format="json"))
        assert data["tool"] == "dependency-check"
        assert data["total"] == 2


# ---------------------------------------------------------------------------
# JaCoCoParser
# ---------------------------------------------------------------------------


class TestJaCoCoParser:
    """Tests for JaCoCoParser."""

    _JACOCO_XML = textwrap.dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE report PUBLIC "-//JACOCO//DTD Report 1.1//EN" "report.dtd">
        <report name="MyApp">
          <package name="com/example">
            <class name="com/example/UserService" sourcefilename="UserService.java">
              <method name="createUser" desc="(Ljava/lang/String;)V" line="25">
                <counter type="LINE" missed="2" covered="8"/>
                <counter type="BRANCH" missed="1" covered="3"/>
              </method>
              <counter type="METHOD" missed="1" covered="4"/>
              <counter type="LINE" missed="5" covered="30"/>
              <counter type="BRANCH" missed="2" covered="8"/>
            </class>
            <class name="com/example/OrderService" sourcefilename="OrderService.java">
              <counter type="METHOD" missed="0" covered="3"/>
              <counter type="LINE" missed="0" covered="20"/>
              <counter type="BRANCH" missed="0" covered="4"/>
            </class>
          </package>
        </report>
    """)

    def _get_parser(self, tmp_path):
        from code_scalpel.code_parsers.java_parsers.java_parsers_JaCoCo import (
            JaCoCoParser,
        )

        xml_file = tmp_path / "jacoco.xml"
        xml_file.write_text(self._JACOCO_XML, encoding="utf-8")
        return JaCoCoParser(report_path=xml_file), xml_file

    def test_parse_xml_report_classes(self, tmp_path):
        parser, xml_file = self._get_parser(tmp_path)
        classes = parser.parse_xml_report(xml_file)
        assert len(classes) == 2
        class_names = {c.class_name for c in classes}
        assert "com.example.UserService" in class_names

    def test_get_class_coverage(self, tmp_path):
        parser, xml_file = self._get_parser(tmp_path)
        parser.parse_xml_report(xml_file)
        cov = parser.get_class_coverage()
        assert len(cov) == 2
        user_cov = next(c for c in cov if "UserService" in c["class"])
        assert user_cov["line_coverage"] > 0

    def test_get_method_coverage(self, tmp_path):
        parser, xml_file = self._get_parser(tmp_path)
        parser.parse_xml_report(xml_file)
        methods = parser.get_method_coverage()
        assert len(methods) >= 1
        assert "class" in methods[0]
        assert "name" in methods[0]

    def test_get_line_coverage_dict(self, tmp_path):
        parser, xml_file = self._get_parser(tmp_path)
        parser.parse_xml_report(xml_file)
        lc = parser.get_line_coverage()
        assert isinstance(lc, dict)
        assert len(lc) == 2

    def test_calculate_summary(self, tmp_path):
        parser, xml_file = self._get_parser(tmp_path)
        parser.parse_xml_report(xml_file)
        summary = parser.calculate_summary()
        assert summary["classes"] == 2
        assert 0.0 <= summary["line_coverage"] <= 100.0

    def test_calculate_summary_empty(self):
        from code_scalpel.code_parsers.java_parsers.java_parsers_JaCoCo import (
            JaCoCoParser,
        )

        parser = JaCoCoParser()
        summary = parser.calculate_summary()
        assert summary["classes"] == 0
        assert summary["line_coverage"] == 0.0

    def test_generate_report_json(self, tmp_path):
        parser, xml_file = self._get_parser(tmp_path)
        parser.parse_xml_report(xml_file)
        data = json.loads(parser.generate_report(format="json"))
        assert data["tool"] == "jacoco"
        assert "summary" in data
        assert data["summary"]["classes"] == 2

    def test_order_service_full_coverage(self, tmp_path):
        parser, xml_file = self._get_parser(tmp_path)
        parser.parse_xml_report(xml_file)
        lc = parser.get_line_coverage()
        order = next(v for k, v in lc.items() if "OrderService" in k)
        assert order == 100.0


# ---------------------------------------------------------------------------
# PitestParser
# ---------------------------------------------------------------------------


class TestPitestParser:
    """Tests for PitestParser."""

    _MUTATIONS_XML = textwrap.dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <mutations>
          <mutation detected="true" status="KILLED" numberOfTestsRun="3">
            <sourceFile>UserService.java</sourceFile>
            <mutatedClass>com.example.UserService</mutatedClass>
            <mutatedMethod>createUser</mutatedMethod>
            <lineNumber>42</lineNumber>
            <mutator>org.pitest.mutationtest.engine.gregor.mutators.ReturnValsMutator</mutator>
          </mutation>
          <mutation detected="false" status="SURVIVED" numberOfTestsRun="2">
            <sourceFile>UserService.java</sourceFile>
            <mutatedClass>com.example.UserService</mutatedClass>
            <mutatedMethod>validateInput</mutatedMethod>
            <lineNumber>58</lineNumber>
            <mutator>org.pitest.mutationtest.engine.gregor.mutators.NegateConditionalsMutator</mutator>
          </mutation>
          <mutation detected="false" status="NO_COVERAGE" numberOfTestsRun="0">
            <sourceFile>OrderService.java</sourceFile>
            <mutatedClass>com.example.OrderService</mutatedClass>
            <mutatedMethod>processOrder</mutatedMethod>
            <lineNumber>20</lineNumber>
            <mutator>org.pitest.mutationtest.engine.gregor.mutators.VoidMethodCallMutator</mutator>
          </mutation>
        </mutations>
    """)

    def _get_parser(self, tmp_path):
        from code_scalpel.code_parsers.java_parsers.java_parsers_Pitest import (
            PitestParser,
        )

        xml_file = tmp_path / "mutations.xml"
        xml_file.write_text(self._MUTATIONS_XML, encoding="utf-8")
        return PitestParser(report_path=xml_file), xml_file

    def test_parse_xml_report_basic(self, tmp_path):
        parser, xml_file = self._get_parser(tmp_path)
        results = parser.parse_xml_report(xml_file)
        assert len(results) == 3
        assert results[0].status == "KILLED"
        assert results[0].detected is True
        assert results[0].source_file == "UserService.java"

    def test_parse_xml_string(self):
        from code_scalpel.code_parsers.java_parsers.java_parsers_Pitest import (
            PitestParser,
        )

        parser = PitestParser()
        results = parser.parse_xml_string(self._MUTATIONS_XML)
        assert len(results) == 3

    def test_short_mutator_name(self, tmp_path):
        parser, xml_file = self._get_parser(tmp_path)
        results = parser.parse_xml_report(xml_file)
        # Short name = last part of the fully-qualified class name
        assert results[0].operator == "ReturnValsMutator"

    def test_get_mutation_score(self, tmp_path):
        parser, xml_file = self._get_parser(tmp_path)
        results = parser.parse_xml_report(xml_file)
        # Eligible: KILLED + SURVIVED (exclude NO_COVERAGE) → killed=1 / total=2 → 50%
        score = parser.get_mutation_score(results)
        assert score == 50.0

    def test_get_survived_mutations(self, tmp_path):
        parser, xml_file = self._get_parser(tmp_path)
        results = parser.parse_xml_report(xml_file)
        survived = parser.get_survived_mutations(results)
        assert len(survived) == 1
        assert survived[0].mutated_method == "validateInput"

    def test_categorize_by_mutator(self, tmp_path):
        parser, xml_file = self._get_parser(tmp_path)
        results = parser.parse_xml_report(xml_file)
        cats = parser.categorize_by_mutator(results)
        assert "ReturnValsMutator" in cats
        assert "NegateConditionalsMutator" in cats

    def test_generate_report_json(self, tmp_path):
        parser, xml_file = self._get_parser(tmp_path)
        results = parser.parse_xml_report(xml_file)
        data = json.loads(parser.generate_report(results, format="json"))
        assert data["tool"] == "pitest"
        assert data["total"] == 3
        assert data["mutation_score"] == 50.0
        assert data["survived"] == 1

    def test_parse_xml_string_empty(self):
        from code_scalpel.code_parsers.java_parsers.java_parsers_Pitest import (
            PitestParser,
        )

        parser = PitestParser()
        assert parser.parse_xml_string("") == []


# ---------------------------------------------------------------------------
# SemgrepParser
# ---------------------------------------------------------------------------


class TestSemgrepParser:
    """Tests for SemgrepParser."""

    _SEMGREP_JSON = json.dumps(
        {
            "results": [
                {
                    "check_id": "java.lang.security.insecure-object-deserialization",
                    "path": "src/UserController.java",
                    "start": {"line": 42, "col": 5},
                    "end": {"line": 42, "col": 60},
                    "extra": {
                        "message": "Insecure deserialization detected",
                        "severity": "ERROR",
                        "metadata": {
                            "cwe": ["CWE-502"],
                            "confidence": "HIGH",
                        },
                    },
                },
                {
                    "check_id": "java.spring.security.spring-csrf-disabled",
                    "path": "src/SecurityConfig.java",
                    "start": {"line": 20, "col": 1},
                    "end": {"line": 20, "col": 30},
                    "extra": {
                        "message": "CSRF protection disabled",
                        "severity": "WARNING",
                        "metadata": {
                            "cwe": ["CWE-352"],
                        },
                    },
                },
                {
                    "check_id": "java.lang.security.sql-injection",
                    "path": "src/DAO.java",
                    "start": {"line": 10, "col": 3},
                    "end": {"line": 10, "col": 50},
                    "extra": {
                        "message": "SQL injection vulnerability",
                        "severity": "ERROR",
                        "metadata": {
                            "cwe": ["CWE-89"],
                        },
                    },
                },
            ],
            "errors": [],
        }
    )

    def _get_parser(self):
        from code_scalpel.code_parsers.java_parsers.java_parsers_Semgrep import (
            SemgrepParser,
        )

        return SemgrepParser()

    def test_parse_json_output_basic(self):
        parser = self._get_parser()
        findings = parser.parse_json_output(self._SEMGREP_JSON)
        assert len(findings) == 3
        assert (
            findings[0].rule_id == "java.lang.security.insecure-object-deserialization"
        )
        assert findings[0].file == "src/UserController.java"
        assert findings[0].line == 42
        assert findings[0].severity == "ERROR"

    def test_parse_json_output_cwe_extraction(self):
        parser = self._get_parser()
        findings = parser.parse_json_output(self._SEMGREP_JSON)
        assert "CWE-502" in findings[0].cwe_ids
        assert "CWE-89" in findings[2].cwe_ids

    def test_parse_json_output_empty(self):
        parser = self._get_parser()
        assert parser.parse_json_output("") == []
        assert parser.parse_json_output('{"results":[]}') == []

    def test_map_to_cwe(self):
        parser = self._get_parser()
        findings = parser.parse_json_output(self._SEMGREP_JSON)
        cwe_map = parser.map_to_cwe(findings)
        assert "CWE-502" in cwe_map
        assert "CWE-89" in cwe_map
        assert len(cwe_map["CWE-502"]) == 1

    def test_categorize_by_severity(self):
        parser = self._get_parser()
        findings = parser.parse_json_output(self._SEMGREP_JSON)
        cats = parser.categorize_by_severity(findings)
        assert "ERROR" in cats
        assert "WARNING" in cats
        assert len(cats["ERROR"]) == 2
        assert len(cats["WARNING"]) == 1

    def test_execute_semgrep_no_binary(self, monkeypatch):
        import shutil

        monkeypatch.setattr(shutil, "which", lambda _: None)
        parser = self._get_parser()
        assert parser.execute_semgrep("./src") == []

    def test_generate_report_json(self):
        parser = self._get_parser()
        findings = parser.parse_json_output(self._SEMGREP_JSON)
        data = json.loads(parser.generate_report(findings, format="json"))
        assert data["tool"] == "semgrep"
        assert data["total"] == 3
        assert data["by_severity"]["ERROR"] == 2

    def test_generate_report_text(self):
        parser = self._get_parser()
        findings = parser.parse_json_output(self._SEMGREP_JSON)
        text = parser.generate_report(findings, format="text")
        assert "src/UserController.java" in text
        assert "CWE-502" not in text  # text format is simpler
