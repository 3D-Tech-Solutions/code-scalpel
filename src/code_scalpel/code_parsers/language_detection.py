"""
Unified Language Detection - Central language detection for code-scalpel.

[20251221_FEATURE] Provides comprehensive language detection from:
- File extensions
- Shebang lines
- Content heuristics
- Explicit user specification

This module should be the single source of truth for language detection
across all code-scalpel modules.

"""

import re
from enum import Enum
from pathlib import Path


class Language(Enum):
    """Supported programming languages."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    C = "c"
    CSHARP = "csharp"
    GO = "go"
    RUST = "rust"
    RUBY = "ruby"
    PHP = "php"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    SCALA = "scala"
    HTML = "html"
    CSS = "css"
    SQL = "sql"
    SHELL = "shell"
    YAML = "yaml"
    JSON = "json"
    XML = "xml"
    MARKDOWN = "markdown"
    UNKNOWN = "unknown"


# Extension to language mapping (comprehensive)
EXTENSION_MAP: dict[str, Language] = {
    # Python
    ".py": Language.PYTHON,
    ".pyi": Language.PYTHON,
    ".pyx": Language.PYTHON,
    ".pxd": Language.PYTHON,
    # JavaScript
    ".js": Language.JAVASCRIPT,
    ".mjs": Language.JAVASCRIPT,
    ".cjs": Language.JAVASCRIPT,
    ".jsx": Language.JAVASCRIPT,
    # TypeScript
    ".ts": Language.TYPESCRIPT,
    ".tsx": Language.TYPESCRIPT,
    ".mts": Language.TYPESCRIPT,
    ".cts": Language.TYPESCRIPT,
    ".d.ts": Language.TYPESCRIPT,
    # Java
    ".java": Language.JAVA,
    # C/C++
    ".c": Language.C,
    ".h": Language.C,
    ".cpp": Language.CPP,
    ".cc": Language.CPP,
    ".cxx": Language.CPP,
    ".hpp": Language.CPP,
    ".hxx": Language.CPP,
    ".hh": Language.CPP,
    # C#
    ".cs": Language.CSHARP,
    # Go
    ".go": Language.GO,
    # Rust
    ".rs": Language.RUST,
    # Ruby
    ".rb": Language.RUBY,
    ".rake": Language.RUBY,
    ".gemspec": Language.RUBY,
    # PHP
    ".php": Language.PHP,
    ".phtml": Language.PHP,
    # Swift
    ".swift": Language.SWIFT,
    # Kotlin
    ".kt": Language.KOTLIN,
    ".kts": Language.KOTLIN,
    # Scala
    ".scala": Language.SCALA,
    ".sc": Language.SCALA,
    # Web
    ".html": Language.HTML,
    ".htm": Language.HTML,
    ".css": Language.CSS,
    ".scss": Language.CSS,
    ".sass": Language.CSS,
    ".less": Language.CSS,
    # Data formats
    ".sql": Language.SQL,
    ".yaml": Language.YAML,
    ".yml": Language.YAML,
    ".json": Language.JSON,
    ".jsonc": Language.JSON,
    ".xml": Language.XML,
    ".xsl": Language.XML,
    ".xslt": Language.XML,
    # Documentation
    ".md": Language.MARKDOWN,
    ".markdown": Language.MARKDOWN,
    ".rst": Language.MARKDOWN,
    # Shell
    ".sh": Language.SHELL,
    ".bash": Language.SHELL,
    ".zsh": Language.SHELL,
    ".fish": Language.SHELL,
}

# Shebang patterns
SHEBANG_PATTERNS: list[tuple[re.Pattern, Language]] = [
    (re.compile(r"^#!.*\bpython\d?"), Language.PYTHON),
    (re.compile(r"^#!.*\bnode\b"), Language.JAVASCRIPT),
    (re.compile(r"^#!.*\bdeno\b"), Language.TYPESCRIPT),
    (re.compile(r"^#!.*\bbash\b"), Language.SHELL),
    (re.compile(r"^#!.*\bzsh\b"), Language.SHELL),
    (re.compile(r"^#!.*\bsh\b"), Language.SHELL),
    (re.compile(r"^#!.*\bruby\b"), Language.RUBY),
    (re.compile(r"^#!.*\bperl\b"), Language.UNKNOWN),  # Perl not supported yet
    (re.compile(r"^#!.*\bphp\b"), Language.PHP),
]

# Content heuristics (patterns that suggest a language)
CONTENT_HEURISTICS: list[tuple[re.Pattern, Language, int]] = [
    # Python
    (re.compile(r"\bdef\s+\w+\s*\("), Language.PYTHON, 5),
    (re.compile(r"\bclass\s+\w+\s*[\(:]"), Language.PYTHON, 4),
    (re.compile(r"\bimport\s+\w+|from\s+\w+\s+import"), Language.PYTHON, 3),
    (re.compile(r"if\s+__name__\s*==\s*['\"]__main__['\"]"), Language.PYTHON, 10),
    (
        re.compile(r"^\s*\w+\s*=\s*[^=]", re.MULTILINE),
        Language.PYTHON,
        2,
    ),  # Simple assignment (x = 1)
    (re.compile(r"\bprint\s*\("), Language.PYTHON, 3),  # print() function
    (re.compile(r"\bTrue\b|\bFalse\b|\bNone\b"), Language.PYTHON, 2),  # Python keywords
    # JavaScript/TypeScript
    (re.compile(r"\bfunction\s+\w+\s*\("), Language.JAVASCRIPT, 4),
    (
        re.compile(r"\bconst\s+\w+\s*=|let\s+\w+\s*=|var\s+\w+\s*="),
        Language.JAVASCRIPT,
        3,
    ),
    (re.compile(r"=>\s*\{|=>\s*[^{]"), Language.JAVASCRIPT, 4),
    (re.compile(r"module\.exports|exports\.\w+"), Language.JAVASCRIPT, 5),
    (re.compile(r"require\s*\(['\"]"), Language.JAVASCRIPT, 4),
    (re.compile(r"import\s+\{.*\}\s+from\s+['\"]"), Language.JAVASCRIPT, 4),
    # TypeScript-specific
    (re.compile(r":\s*(string|number|boolean|void|any)\b"), Language.TYPESCRIPT, 6),
    (re.compile(r"interface\s+\w+\s*\{"), Language.TYPESCRIPT, 5),
    (re.compile(r"type\s+\w+\s*="), Language.TYPESCRIPT, 5),
    (re.compile(r"<\w+>"), Language.TYPESCRIPT, 2),  # Generic types (weak signal)
    # Java
    (re.compile(r"\bpublic\s+class\s+\w+"), Language.JAVA, 8),
    (re.compile(r"\bprivate\s+\w+\s+\w+\s*[\(;]"), Language.JAVA, 5),
    (re.compile(r"\bpackage\s+[\w\.]+;"), Language.JAVA, 10),
    (re.compile(r"\bimport\s+[\w\.]+\.\*?;"), Language.JAVA, 6),
    (re.compile(r"public\s+static\s+void\s+main"), Language.JAVA, 10),
    (re.compile(r"@Override|@Deprecated|@SuppressWarnings"), Language.JAVA, 5),
    # C/C++
    (re.compile(r"#include\s*[<\"]"), Language.CPP, 7),
    (re.compile(r"\bint\s+main\s*\(\s*(int|void)?\s*"), Language.CPP, 5),
    (re.compile(r"std::\w+"), Language.CPP, 6),
    (re.compile(r"nullptr|nullptr_t"), Language.CPP, 8),
    # Go
    (re.compile(r"package\s+\w+\s*$", re.MULTILINE), Language.GO, 6),
    (re.compile(r"func\s+\w+\s*\("), Language.GO, 6),
    (re.compile(r"import\s*\("), Language.GO, 4),
    # Rust
    (re.compile(r"fn\s+\w+\s*\("), Language.RUST, 5),
    (re.compile(r"let\s+mut\s+"), Language.RUST, 8),
    (re.compile(r"impl\s+\w+\s+for\s+\w+"), Language.RUST, 8),
    (re.compile(r"use\s+\w+::\w+"), Language.RUST, 5),
    # Ruby
    (re.compile(r"\bdef\s+\w+\s*$", re.MULTILINE), Language.RUBY, 4),
    (re.compile(r"\bclass\s+\w+\s*<\s*\w+"), Language.RUBY, 5),
    (re.compile(r"\battr_accessor\s+:\w+"), Language.RUBY, 8),
    (re.compile(r"\bdo\s*\|"), Language.RUBY, 5),
    # PHP
    (re.compile(r"<\?php"), Language.PHP, 10),
    (re.compile(r"\$\w+\s*="), Language.PHP, 4),
]


def detect_language(
    filepath: str | None = None,
    code: str | None = None,
    *,
    prefer_extension: bool = True,
) -> Language:
    """
    Detect the programming language from file path and/or content.

    This function uses multiple strategies:
    1. File extension (if prefer_extension=True and filepath provided)
    2. Shebang line (if code starts with #!)
    3. Content heuristics (pattern matching)
    4. File extension (if prefer_extension=False)

    Args:
        filepath: Path to the file (optional)
        code: Source code content (optional)
        prefer_extension: If True, check extension before content

    Returns:
        Detected Language enum value

    Example:
        >>> detect_language("hello.py")
        Language.PYTHON
        >>> detect_language(code="public class Hello {}")
        Language.JAVA
    """
    if filepath is None and code is None:
        return Language.UNKNOWN

    # Strategy 1: Extension (if preferred)
    if prefer_extension and filepath:
        ext_lang = _detect_from_extension(filepath)
        if ext_lang != Language.UNKNOWN:
            return ext_lang

    # Strategy 2 & 3: Content-based detection
    if code:
        content_lang = _detect_from_content(code)
        if content_lang != Language.UNKNOWN:
            return content_lang

    # Strategy 4: Extension (fallback)
    if not prefer_extension and filepath:
        return _detect_from_extension(filepath)

    return Language.UNKNOWN


def _detect_from_extension(filepath: str) -> Language:
    """Detect language from file extension."""
    path = Path(filepath)

    # Handle compound extensions like .d.ts
    suffixes = "".join(path.suffixes).lower()
    if suffixes in EXTENSION_MAP:
        return EXTENSION_MAP[suffixes]

    # Single extension
    ext = path.suffix.lower()
    return EXTENSION_MAP.get(ext, Language.UNKNOWN)


def _detect_from_shebang(code: str) -> Language:
    """Detect language from shebang line."""
    first_line = code.split("\n", 1)[0]

    if not first_line.startswith("#!"):
        return Language.UNKNOWN

    for pattern, lang in SHEBANG_PATTERNS:
        if pattern.match(first_line):
            return lang

    return Language.UNKNOWN


def _detect_from_content(code: str) -> Language:
    """Detect language from content patterns."""
    # First check shebang
    shebang_lang = _detect_from_shebang(code)
    if shebang_lang != Language.UNKNOWN:
        return shebang_lang

    # Score each language based on heuristics
    scores: dict[Language, int] = {}

    for pattern, lang, weight in CONTENT_HEURISTICS:
        matches = len(pattern.findall(code))
        if matches > 0:
            scores[lang] = scores.get(lang, 0) + (weight * min(matches, 3))

    if not scores:
        return Language.UNKNOWN

    # Return language with highest score (minimum threshold of 2)
    best_lang, best_score = max(scores.items(), key=lambda x: x[1])

    if best_score >= 2:
        return best_lang

    return Language.UNKNOWN


def get_language_name(lang: Language) -> str:
    """Get human-readable language name."""
    names = {
        Language.PYTHON: "Python",
        Language.JAVASCRIPT: "JavaScript",
        Language.TYPESCRIPT: "TypeScript",
        Language.JAVA: "Java",
        Language.CPP: "C++",
        Language.C: "C",
        Language.CSHARP: "C#",
        Language.GO: "Go",
        Language.RUST: "Rust",
        Language.RUBY: "Ruby",
        Language.PHP: "PHP",
        Language.SWIFT: "Swift",
        Language.KOTLIN: "Kotlin",
        Language.SCALA: "Scala",
        Language.HTML: "HTML",
        Language.CSS: "CSS",
        Language.SQL: "SQL",
        Language.SHELL: "Shell",
        Language.YAML: "YAML",
        Language.JSON: "JSON",
        Language.XML: "XML",
        Language.MARKDOWN: "Markdown",
        Language.UNKNOWN: "Unknown",
    }
    return names.get(lang, "Unknown")


def get_file_extensions(lang: Language) -> list[str]:
    """Get list of file extensions for a language."""
    # [20251222_BUGFIX] Avoid ambiguous variable name (E741).
    return [ext for ext, lang_value in EXTENSION_MAP.items() if lang_value == lang]


def is_parseable_language(lang: Language) -> bool:
    """Check if we have a parser available for this language."""
    # Languages with IParser adapters available
    parseable = {
        Language.PYTHON,
        Language.JAVASCRIPT,
        Language.TYPESCRIPT,
        Language.JAVA,
    }
    return lang in parseable


def detect_language_confidence(
    filepath: str | None = None,
    code: str | None = None,
) -> tuple[Language, float]:
    """
    Detect language with confidence score.

    [20251221_FEATURE] Returns both the detected language and a confidence
    score between 0.0 and 1.0.

    Args:
        filepath: Path to the file
        code: Source code content

    Returns:
        Tuple of (Language, confidence_score)
    """
    if filepath is None and code is None:
        return Language.UNKNOWN, 0.0

    confidence = 0.0
    detected = Language.UNKNOWN

    # Extension gives high confidence
    if filepath:
        ext_lang = _detect_from_extension(filepath)
        if ext_lang != Language.UNKNOWN:
            detected = ext_lang
            confidence = 0.9

    # Content heuristics can confirm or adjust
    if code:
        shebang_lang = _detect_from_shebang(code)
        if shebang_lang != Language.UNKNOWN:
            if detected == Language.UNKNOWN:
                detected = shebang_lang
                confidence = 0.95
            elif detected == shebang_lang:
                confidence = min(1.0, confidence + 0.05)

        # Check content patterns
        scores: dict[Language, int] = {}
        for pattern, lang, weight in CONTENT_HEURISTICS:
            matches = len(pattern.findall(code))
            if matches > 0:
                scores[lang] = scores.get(lang, 0) + (weight * min(matches, 3))

        if scores:
            best_lang, best_score = max(scores.items(), key=lambda x: x[1])
            content_confidence = min(0.8, best_score / 20.0)

            if detected == Language.UNKNOWN:
                detected = best_lang
                confidence = content_confidence
            elif detected == best_lang:
                confidence = min(1.0, confidence + content_confidence * 0.2)
            elif content_confidence > confidence:
                # Content suggests different language with higher confidence
                detected = best_lang
                confidence = content_confidence * 0.7  # Reduce for conflict

    return detected, confidence
