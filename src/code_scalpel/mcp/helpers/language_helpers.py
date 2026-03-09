"""Shared language resolution helpers for MCP tools.

[20260306_REFACTOR] Centralize canonical language detection and alias handling so
analysis tools route code through the correct parser stack consistently.
"""

from __future__ import annotations

from code_scalpel.code_parsers.language_detection import (
    Language as DetectedLanguage,
    detect_language as detect_canonical_language,
)


SUPPORTED_POLYGLOT_LANGUAGES: tuple[str, ...] = (
    "python",
    "javascript",
    "typescript",
    "java",
    "c",
    "cpp",
    "csharp",
    "go",
    "kotlin",
    "php",
    "ruby",
    "swift",
    "rust",
)


LANGUAGE_ALIASES: dict[str, str] = {
    "py": "python",
    "js": "javascript",
    "jsx": "javascript",
    "ts": "typescript",
    "tsx": "typescript",
    "cs": "csharp",
    "c++": "cpp",
    "cc": "cpp",
    "kt": "kotlin",
    "rb": "ruby",
}


DETECTED_LANGUAGE_MAP: dict[DetectedLanguage, str] = {
    DetectedLanguage.PYTHON: "python",
    DetectedLanguage.JAVASCRIPT: "javascript",
    DetectedLanguage.TYPESCRIPT: "typescript",
    DetectedLanguage.JAVA: "java",
    DetectedLanguage.C: "c",
    DetectedLanguage.CPP: "cpp",
    DetectedLanguage.CSHARP: "csharp",
    DetectedLanguage.GO: "go",
    DetectedLanguage.KOTLIN: "kotlin",
    DetectedLanguage.PHP: "php",
    DetectedLanguage.RUBY: "ruby",
    DetectedLanguage.SWIFT: "swift",
    DetectedLanguage.RUST: "rust",
}


def normalize_language_name(language: str | None) -> str | None:
    """Return a canonical lower-case language name or None for auto-detect."""
    if language is None:
        return None

    normalized = language.strip().lower()
    if not normalized or normalized == "auto":
        return None

    return LANGUAGE_ALIASES.get(normalized, normalized)


def detect_tool_language(
    *,
    file_path: str | None = None,
    code: str | None = None,
    language: str | None = None,
    default: str = "python",
) -> str:
    """Resolve the canonical language for a tool invocation.

    Explicit user language wins. Otherwise use the central language detector,
    which is the intended single source of truth for the code parser stack.
    """
    explicit = normalize_language_name(language)
    if explicit is not None:
        return explicit

    detected = detect_canonical_language(
        filepath=file_path,
        code=code,
        prefer_extension=bool(file_path),
    )
    return DETECTED_LANGUAGE_MAP.get(detected, default)


def is_supported_language(language: str, supported_languages: tuple[str, ...]) -> bool:
    """Return True when *language* is in the supported language set."""
    return normalize_language_name(language) in supported_languages