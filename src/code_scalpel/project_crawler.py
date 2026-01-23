"""
ProjectCrawler - DEPRECATED: Moved to code_scalpel.analysis.project_crawler.

# [20251224_DEPRECATE] This module has been moved to analysis/project_crawler.py
# as part of Issue #3 in PROJECT_REORG_REFACTOR.md Phase 1.
# This file provides backward-compatibility aliases.
# Import from code_scalpel.analysis.project_crawler instead.

Migration:
    # Old (deprecated):
    from code_scalpel.project_crawler import ProjectCrawler

    # New (recommended):
    from code_scalpel.analysis import ProjectCrawler
"""

import warnings

warnings.warn(
    "code_scalpel.project_crawler is deprecated. " "Import from code_scalpel.analysis instead.",
    DeprecationWarning,
    stacklevel=2,
)

# [20260102_REFACTOR] Backward-compat shim keeps imports below for legacy users.
# ruff: noqa: E402
# Re-export everything from new location for backward compatibility
from code_scalpel.analysis.project_crawler import (
    ClassInfo,
    CodeAnalyzerVisitor,
    CrawlResult,
    FileAnalysisResult,
    FunctionInfo,
    ProjectCrawler,
    crawl_project,
)

__all__ = [
    "ProjectCrawler",
    "CrawlResult",
    "FileAnalysisResult",
    "FunctionInfo",
    "ClassInfo",
    "CodeAnalyzerVisitor",
    "crawl_project",
]
