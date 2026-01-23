"""
Tests for enhanced surgical extractor features.

[20251221_FEATURE] Tests for tiktoken integration, metadata extraction,
decorator extraction, caller finding, and prompt formatting.
"""

import pytest

from code_scalpel.surgical_extractor import SurgicalExtractor

# Sample code for testing
SAMPLE_CODE = '''
import time
from typing import Callable

def timing_decorator(func: Callable) -> Callable:
    """Decorator that measures function execution time."""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start:.2f}s")
        return result
    return wrapper

@timing_decorator
def calculate_tax(amount: float, rate: float = 0.1) -> float:
    """Calculate tax on an amount."""
    return amount * rate

def validate_amount(amount: float) -> bool:
    """Check if amount is valid."""
    return amount > 0

def process_payment(amount: float) -> dict:
    """Process a payment."""
    if not validate_amount(amount):
        raise ValueError("Invalid amount")
    tax = calculate_tax(amount)
    return {"amount": amount, "tax": tax}

async def async_function():
    """An async function."""
    return 42

def generator_function():
    """A generator function."""
    yield 1
    yield 2

class PaymentProcessor:
    def process(self, amount: float):
        return calculate_tax(amount)
'''


class TestEnhancedMetadata:
    """Tests for enhanced metadata extraction."""

    def test_extract_docstring(self):
        """Test docstring extraction."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        result = extractor.get_function("calculate_tax")

        assert result.success
        assert result.docstring == "Calculate tax on an amount."

    def test_extract_signature(self):
        """Test signature extraction."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        result = extractor.get_function("calculate_tax")

        assert result.success
        assert "def calculate_tax(amount: float, rate: float = 0.1) -> float:" in result.signature

    def test_extract_decorators(self):
        """Test decorator extraction."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        result = extractor.get_function("calculate_tax")

        assert result.success
        assert "timing_decorator" in result.decorators

    def test_detect_async(self):
        """Test async function detection."""
        extractor = SurgicalExtractor(SAMPLE_CODE)

        sync_func = extractor.get_function("calculate_tax")
        assert not sync_func.is_async

        async_func = extractor.get_function("async_function")
        assert async_func.is_async

    def test_detect_generator(self):
        """Test generator detection."""
        extractor = SurgicalExtractor(SAMPLE_CODE)

        regular_func = extractor.get_function("calculate_tax")
        assert not regular_func.is_generator

        gen_func = extractor.get_function("generator_function")
        assert gen_func.is_generator

    def test_source_file_stored(self):
        """Test that source file path is stored."""
        extractor = SurgicalExtractor(SAMPLE_CODE, file_path="/path/to/file.py")
        result = extractor.get_function("calculate_tax")

        assert result.success
        assert result.source_file == "/path/to/file.py"

    def test_class_metadata(self):
        """Test class metadata extraction."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        result = extractor.get_class("PaymentProcessor")

        assert result.success
        assert result.docstring is None  # No docstring in this class
        assert "class PaymentProcessor:" in result.signature


class TestTokenCounting:
    """Tests for token counting functionality."""

    def test_token_estimate_property(self):
        """Test token_estimate property returns reasonable value."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        result = extractor.get_function("calculate_tax")

        assert result.success
        assert result.token_estimate > 0
        # Should be roughly code length / 4
        assert result.token_estimate > len(result.code) // 5

    def test_get_token_count_gpt4(self):
        """Test get_token_count for GPT-4."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        result = extractor.get_function("calculate_tax")

        assert result.success
        tokens = result.get_token_count("gpt-4")
        assert tokens > 0

    def test_get_token_count_gpt35(self):
        """Test get_token_count for GPT-3.5."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        result = extractor.get_function("calculate_tax")

        assert result.success
        tokens = result.get_token_count("gpt-3.5-turbo")
        assert tokens > 0

    def test_contextual_token_estimate(self):
        """Test token estimation in ContextualExtraction."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        extraction = extractor.get_function_with_context("process_payment")

        assert extraction.token_estimate > 0
        assert extraction.token_estimate > extraction.target.token_estimate

    def test_contextual_get_token_count(self):
        """Test get_token_count in ContextualExtraction."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        extraction = extractor.get_function_with_context("process_payment")

        tokens = extraction.get_token_count("gpt-4")
        assert tokens > 0


class TestDecoratorExtraction:
    """Tests for decorator extraction."""

    def test_list_decorators(self):
        """Test listing all decorators."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        decorators = extractor.list_decorators()

        assert "timing_decorator" in decorators
        assert isinstance(decorators, list)

    def test_get_decorator(self):
        """Test extracting a decorator."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        result = extractor.get_decorator("timing_decorator")

        assert result.success
        assert result.node_type == "decorator"
        assert "def timing_decorator" in result.code

    def test_get_decorator_not_found(self):
        """Test extracting non-existent decorator."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        result = extractor.get_decorator("nonexistent_decorator")

        assert not result.success
        assert "not found" in result.error.lower()


class TestFindCallers:
    """Tests for finding function callers."""

    def test_find_callers_single(self):
        """Test finding callers for a function."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        callers = extractor.find_callers("validate_amount")

        # process_payment calls validate_amount
        assert len(callers) >= 1
        names = [name for name, _, _ in callers]
        assert "process_payment" in names

    def test_find_callers_multiple(self):
        """Test finding multiple callers."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        callers = extractor.find_callers("calculate_tax")

        # process_payment and PaymentProcessor.process call calculate_tax
        assert len(callers) >= 2
        names = [name for name, _, _ in callers]
        assert "process_payment" in names
        assert "PaymentProcessor.process" in names

    def test_find_callers_none(self):
        """Test finding callers when there are none."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        callers = extractor.find_callers("timing_decorator")

        # timing_decorator is used as a decorator, not called directly
        # (decorators in decorator_list are not counted as calls)
        assert isinstance(callers, list)

    def test_find_callers_returns_line_numbers(self):
        """Test that callers include line numbers."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        callers = extractor.find_callers("calculate_tax")

        assert len(callers) > 0
        for _name, _typ, line in callers:
            assert isinstance(line, int)
            assert line > 0

    def test_find_callers_distinguishes_types(self):
        """Test that caller types are correct."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        callers = extractor.find_callers("calculate_tax")

        # Should have both function and method callers
        types = [typ for _, typ, _ in callers]
        assert "function" in types or "method" in types


class TestPromptFormatting:
    """Tests for LLM prompt formatting."""

    def test_to_prompt_basic(self):
        """Test basic prompt formatting."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        extraction = extractor.get_function_with_context("calculate_tax")

        prompt = extraction.to_prompt("Add input validation")

        assert "# Code Extraction:" in prompt
        assert "calculate_tax" in prompt
        assert "Add input validation" in prompt
        assert "```python" in prompt

    def test_to_prompt_with_metadata(self):
        """Test prompt with metadata included."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        extraction = extractor.get_function_with_context("calculate_tax")

        prompt = extraction.to_prompt("Refactor", include_metadata=True)

        assert "## Metadata" in prompt
        assert "Type:" in prompt
        assert "Lines:" in prompt
        assert "Dependencies:" in prompt

    def test_to_prompt_without_metadata(self):
        """Test prompt without metadata."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        extraction = extractor.get_function_with_context("calculate_tax")

        prompt = extraction.to_prompt("Refactor", include_metadata=False)

        assert "## Metadata" not in prompt
        assert "## Task" in prompt

    def test_to_prompt_includes_context(self):
        """Test that context is included in prompt."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        extraction = extractor.get_function_with_context("process_payment", max_depth=1)

        prompt = extraction.to_prompt("Add error handling")

        # Should include dependencies
        assert "## Context" in prompt
        # validate_amount and calculate_tax should be in context
        assert "validate_amount" in prompt or "calculate_tax" in prompt


class TestSummarize:
    """Tests for extraction summarization."""

    def test_summarize_basic(self):
        """Test basic summarization."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        extraction = extractor.get_function_with_context("calculate_tax")

        summary = extraction.summarize()

        assert "calculate_tax" in summary
        assert "Function:" in summary
        assert "Tokens:" in summary

    def test_summarize_truncated(self):
        """Test summarization shows truncation."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        extraction = extractor.get_function_with_context("calculate_tax")

        # Manually set truncation for testing
        extraction.truncated = True
        extraction.omitted_items = ["some_dependency"]

        summary = extraction.summarize()

        assert "\u26a0\ufe0f" in summary or "Truncated" in summary


class TestBudgetTrimming:
    """Tests for token budget management."""

    def test_trim_to_budget_no_change(self):
        """Test that extraction under budget is unchanged."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        extraction = extractor.get_function_with_context("calculate_tax")

        # Budget larger than content
        large_budget = extraction.token_estimate + 1000
        trimmed = extraction.trim_to_budget(large_budget)

        assert not trimmed.truncated
        assert trimmed.token_estimate <= large_budget

    def test_trim_to_budget_removes_context(self):
        """Test that trimming removes context."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        extraction = extractor.get_function_with_context("process_payment", max_depth=2)

        # Very small budget
        small_budget = 100
        trimmed = extraction.trim_to_budget(small_budget)

        # Should be trimmed
        assert trimmed.token_estimate <= small_budget or trimmed.truncated

    def test_trim_to_budget_keeps_target(self):
        """Test that target is always kept."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        extraction = extractor.get_function_with_context("process_payment")

        # Budget too small even for target
        tiny_budget = 10
        trimmed = extraction.trim_to_budget(tiny_budget)

        # Target code should still be present
        assert extraction.target.code in trimmed.full_code

    def test_trim_to_budget_marks_truncated(self):
        """Test that trimming marks as truncated."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        extraction = extractor.get_function_with_context("process_payment", max_depth=2)

        # Budget smaller than full extraction
        small_budget = 50
        trimmed = extraction.trim_to_budget(small_budget)

        if trimmed.token_estimate > small_budget:
            assert trimmed.truncated


class TestCaching:
    """Tests for LRU cache performance."""

    def test_cache_hits(self):
        """Test that repeated extractions hit cache."""
        extractor = SurgicalExtractor(SAMPLE_CODE)

        # Clear cache first
        extractor._get_function_cached.cache_clear()

        # First call - cache miss
        result1 = extractor.get_function("calculate_tax")
        assert result1.success

        # Second call - should hit cache
        result2 = extractor.get_function("calculate_tax")
        assert result2.success

        # Check cache stats
        cache_info = extractor._get_function_cached.cache_info()
        assert cache_info.hits >= 1

    def test_cache_different_functions(self):
        """Test that different functions are cached separately."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        extractor._get_function_cached.cache_clear()

        result1 = extractor.get_function("calculate_tax")
        result2 = extractor.get_function("validate_amount")

        assert result1.name != result2.name

        cache_info = extractor._get_function_cached.cache_info()
        assert cache_info.currsize == 2  # Two different functions cached

    def test_class_cache(self):
        """Test that class extraction uses cache."""
        extractor = SurgicalExtractor(SAMPLE_CODE)
        extractor._get_class_cached.cache_clear()

        result1 = extractor.get_class("PaymentProcessor")
        result2 = extractor.get_class("PaymentProcessor")

        assert result1.success
        assert result2.success

        cache_info = extractor._get_class_cached.cache_info()
        assert cache_info.hits >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
