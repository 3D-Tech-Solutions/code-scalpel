"""
Example demonstrating enhanced surgical extractor features.

[20251221_FEATURE] Showcases new token estimation, metadata extraction,
decorator extraction, caller finding, and prompt formatting.
"""

from code_scalpel.surgical_extractor import SurgicalExtractor

# Sample code to analyze
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

def log_decorator(func: Callable) -> Callable:
    """Decorator that logs function calls."""
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        result = func(*args, **kwargs)
        print(f"Finished {func.__name__}")
        return result
    return wrapper

@timing_decorator
@log_decorator
def calculate_tax(amount: float, rate: float = 0.1) -> float:
    """
    Calculate tax on an amount.
    
    Args:
        amount: Base amount
        rate: Tax rate (default 0.1)
    
    Returns:
        Tax amount
    """
    return amount * rate

def validate_amount(amount: float) -> bool:
    """Check if amount is valid."""
    return amount > 0

@timing_decorator
def process_payment(amount: float) -> dict:
    """
    Process a payment with validation and tax calculation.
    
    Args:
        amount: Payment amount
    
    Returns:
        Payment details dictionary
    """
    if not validate_amount(amount):
        raise ValueError("Invalid amount")
    
    tax = calculate_tax(amount)
    total = amount + tax
    
    return {
        "amount": amount,
        "tax": tax,
        "total": total
    }

async def async_process_payment(amount: float) -> dict:
    """Async version of process_payment."""
    # Simulate async operation
    import asyncio
    await asyncio.sleep(0.1)
    return process_payment(amount)

def batch_process_payments(amounts: list[float]):
    """Process multiple payments and yield results."""
    for amount in amounts:
        yield process_payment(amount)

class PaymentProcessor:
    """Payment processing class."""
    
    def __init__(self, tax_rate: float = 0.1):
        self.tax_rate = tax_rate
    
    def process(self, amount: float) -> dict:
        """Process a payment using class tax rate."""
        tax = calculate_tax(amount, self.tax_rate)
        return {"amount": amount, "tax": tax, "total": amount + tax}
'''


def demo_basic_extraction():
    """Demonstrate basic extraction with metadata."""
    print("=" * 80)
    print("DEMO 1: Basic Extraction with Enhanced Metadata")
    print("=" * 80)

    extractor = SurgicalExtractor(SAMPLE_CODE)

    # Extract a function
    result = extractor.get_function("calculate_tax")

    print(f"\n✓ Extracted: {result.name}")
    print(f"  - Type: {result.node_type}")
    print(f"  - Lines: {result.line_start}-{result.line_end}")
    print(f"  - Signature: {result.signature}")
    print(f"  - Decorators: {result.decorators}")
    print(f"  - Docstring: {result.docstring[:50]}..." if result.docstring else "  - Docstring: None")
    print(f"  - Is Async: {result.is_async}")
    print(f"  - Is Generator: {result.is_generator}")
    print(f"  - Dependencies: {result.dependencies}")
    print(f"  - Token estimate: {result.token_estimate}")

    print("\n" + "=" * 80 + "\n")


def demo_token_counting():
    """Demonstrate accurate token counting."""
    print("=" * 80)
    print("DEMO 2: Accurate Token Counting (with tiktoken if available)")
    print("=" * 80)

    extractor = SurgicalExtractor(SAMPLE_CODE)

    # Compare different extractions
    functions = ["calculate_tax", "validate_amount", "process_payment"]

    for func_name in functions:
        result = extractor.get_function(func_name)
        print(f"\n{func_name}:")
        print(f"  - Characters: {len(result.code)}")
        print(f"  - Estimated tokens: {result.token_estimate}")
        print(f"  - GPT-4 tokens: {result.get_token_count('gpt-4')}")
        print(f"  - GPT-3.5 tokens: {result.get_token_count('gpt-3.5-turbo')}")

    print("\n" + "=" * 80 + "\n")


def demo_decorator_extraction():
    """Demonstrate decorator extraction."""
    print("=" * 80)
    print("DEMO 3: Decorator Extraction")
    print("=" * 80)

    extractor = SurgicalExtractor(SAMPLE_CODE)

    # List all decorators
    decorators = extractor.list_decorators()
    print(f"\nFound {len(decorators)} decorators: {decorators}")

    # Extract a decorator
    for decorator_name in ["timing_decorator", "log_decorator"]:
        result = extractor.get_decorator(decorator_name)
        if result.success:
            print(f"\n✓ Extracted decorator: {result.name}")
            print(f"  - Type: {result.node_type}")
            print(f"  - Lines: {result.line_start}-{result.line_end}")
            print(f"  - Token estimate: {result.token_estimate}")

    print("\n" + "=" * 80 + "\n")


def demo_find_callers():
    """Demonstrate finding function callers."""
    print("=" * 80)
    print("DEMO 4: Finding Callers (Impact Analysis)")
    print("=" * 80)

    extractor = SurgicalExtractor(SAMPLE_CODE)

    # Find who calls calculate_tax
    target = "calculate_tax"
    callers = extractor.find_callers(target)

    print(f"\nFunctions/methods that call '{target}':")
    if callers:
        for caller_name, caller_type, line_num in callers:
            print(f"  - {caller_type.capitalize()}: {caller_name} (line {line_num})")
    else:
        print("  (none)")

    # Find who calls process_payment
    target = "process_payment"
    callers = extractor.find_callers(target)

    print(f"\nFunctions/methods that call '{target}':")
    if callers:
        for caller_name, caller_type, line_num in callers:
            print(f"  - {caller_type.capitalize()}: {caller_name} (line {line_num})")
    else:
        print("  (none)")

    print("\n" + "=" * 80 + "\n")


def demo_async_and_generator_detection():
    """Demonstrate async and generator detection."""
    print("=" * 80)
    print("DEMO 5: Async and Generator Detection")
    print("=" * 80)

    extractor = SurgicalExtractor(SAMPLE_CODE)

    # Check various function types
    functions = ["calculate_tax", "async_process_payment", "batch_process_payments"]

    for func_name in functions:
        result = extractor.get_function(func_name)
        if result.success:
            print(f"\n{result.name}:")
            print(f"  - Is Async: {'✓' if result.is_async else '✗'}")
            print(f"  - Is Generator: {'✓' if result.is_generator else '✗'}")
            print(f"  - Signature: {result.signature}")

    print("\n" + "=" * 80 + "\n")


def demo_prompt_formatting():
    """Demonstrate LLM prompt formatting."""
    print("=" * 80)
    print("DEMO 6: LLM-Ready Prompt Formatting")
    print("=" * 80)

    extractor = SurgicalExtractor(SAMPLE_CODE)

    # Extract with context and format as prompt
    extraction = extractor.get_function_with_context("process_payment", max_depth=2)

    instruction = """
    Add comprehensive error handling to this function:
    - Validate that amount is not negative or zero
    - Handle potential errors from calculate_tax
    - Add logging for successful and failed operations
    - Return a Result type instead of raising exceptions
    """

    prompt = extraction.to_prompt(instruction, include_metadata=True)

    print("\nGenerated LLM Prompt:")
    print("-" * 80)
    print(prompt)
    print("-" * 80)

    print("\n" + "=" * 80 + "\n")


def demo_budget_trimming():
    """Demonstrate token budget trimming."""
    print("=" * 80)
    print("DEMO 7: Token Budget Management")
    print("=" * 80)

    extractor = SurgicalExtractor(SAMPLE_CODE)

    # Extract with full context
    extraction = extractor.get_function_with_context("process_payment", max_depth=3)

    print("\nFull extraction:")
    print(f"  - Token estimate: {extraction.token_estimate}")
    print(f"  - Context items: {len(extraction.context_items)}")
    print(f"  - Total lines: {extraction.total_lines}")
    print(f"  - Summary: {extraction.summarize()}")

    # Trim to budget
    max_tokens = 500
    trimmed = extraction.trim_to_budget(max_tokens)

    print(f"\nTrimmed to {max_tokens} tokens:")
    print(f"  - Token estimate: {trimmed.token_estimate}")
    print(f"  - Context items: {len(trimmed.context_items)}")
    print(f"  - Total lines: {trimmed.total_lines}")
    print(f"  - Truncated: {trimmed.truncated}")
    print(f"  - Omitted: {trimmed.omitted_items}")
    print(f"  - Summary: {trimmed.summarize()}")

    print("\n" + "=" * 80 + "\n")


def demo_caching_performance():
    """Demonstrate extraction caching performance."""
    print("=" * 80)
    print("DEMO 8: LRU Cache Performance")
    print("=" * 80)

    import time

    extractor = SurgicalExtractor(SAMPLE_CODE)

    # First extraction (cache miss)
    start = time.time()
    for _ in range(100):
        extractor.get_function("calculate_tax")
    first_time = time.time() - start

    # Clear cache and repeat
    extractor._get_function_cached.cache_clear()

    start = time.time()
    for _ in range(100):
        extractor.get_function("calculate_tax")
    second_time = time.time() - start

    # Check cache info
    cache_info = extractor._get_function_cached.cache_info()

    print("\n100 extractions of 'calculate_tax':")
    print(f"  - Without cache: {first_time:.4f}s")
    print(f"  - With cache: {second_time:.4f}s")
    print(f"  - Speedup: {first_time / second_time:.1f}x")
    print("\nCache statistics:")
    print(f"  - Hits: {cache_info.hits}")
    print(f"  - Misses: {cache_info.misses}")
    print(f"  - Size: {cache_info.currsize}")
    print(f"  - Max size: {cache_info.maxsize}")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    print("\n")
    print("#" * 80)
    print("# Surgical Extractor Enhanced Features Demo")
    print("#" * 80)
    print("\n")

    demo_basic_extraction()
    demo_token_counting()
    demo_decorator_extraction()
    demo_find_callers()
    demo_async_and_generator_detection()
    demo_prompt_formatting()
    demo_budget_trimming()
    demo_caching_performance()

    print("\n")
    print("#" * 80)
    print("# All demos completed successfully!")
    print("#" * 80)
    print("\n")
