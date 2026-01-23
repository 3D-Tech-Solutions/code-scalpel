import tempfile
from pathlib import Path

from code_scalpel.ast_tools.dependency_parser import DependencyParser

POM_SAMPLE = """
<project xmlns=\"http://maven.apache.org/POM/4.0.0\"
         xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"
         xsi:schemaLocation=\"http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd\">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.acme</groupId>
  <artifactId>demo</artifactId>
  <version>1.0.0</version>
  <dependencies>
    <dependency>
      <groupId>org.springframework</groupId>
      <artifactId>spring-core</artifactId>
      <version>6.1.0</version>
    </dependency>
    <dependency>
      <groupId>org.springframework.security</groupId>
      <artifactId>spring-security-web</artifactId>
      <version>6.2.0</version>
      <scope>test</scope>
    </dependency>
  </dependencies>
</project>
"""

GRADLE_SAMPLE = """
dependencies {
    implementation "org.hibernate.orm:hibernate-core:6.4.0.Final"
    testImplementation "org.junit.jupiter:junit-jupiter:5.10.1"
}
"""


def test_dependency_parser_maven_and_gradle():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "pom.xml").write_text(POM_SAMPLE)
        (root / "build.gradle").write_text(GRADLE_SAMPLE)

        parser = DependencyParser(str(root))
        deps = parser.get_dependencies()

        maven = {d["name"]: d for d in deps.get("maven", [])}

        assert "org.springframework:spring-core" in maven
        assert maven["org.springframework:spring-core"]["version"] == "6.1.0"

        assert "org.springframework.security:spring-security-web" in maven
        assert maven["org.springframework.security:spring-security-web"].get("type") == "dev"

        gradle = {d["name"]: d for d in deps.get("maven", [])}
        assert "org.hibernate.orm:hibernate-core" in gradle
        assert gradle["org.hibernate.orm:hibernate-core"]["version"] == "6.4.0.Final"
        assert gradle["org.hibernate.orm:hibernate-core"].get("type") is None
        assert gradle["org.junit.jupiter:junit-jupiter"].get("type") == "dev"
