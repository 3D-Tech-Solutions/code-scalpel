# [20260103_TEST] Sample functions for update_symbol testing


# Basic function
def add_numbers(a, b):
    """Add two numbers together."""
    return a + b


# Function with type hints
def calculate_discount(price: float, rate: float = 0.1) -> float:
    """Calculate discounted price."""
    return price * (1 - rate)


# Async function
async def fetch_data(url: str):
    """Fetch data from URL asynchronously."""
    # Simulated async operation
    return {"status": "success", "url": url}


# Function with decorator
@staticmethod
def parse_json(data: str):
    """Parse JSON string."""
    import json

    return json.loads(data)


# Function with multiple decorators
@classmethod
@property
def get_config(cls):
    """Get configuration object."""
    return cls._config


# Nested function
def outer_function(x):
    """Outer function."""

    def inner_function(y):
        """Inner function."""
        return x + y

    return inner_function


# Lambda-style function (edge case) - converted to def per ruff E731
def simple_multiply(x, y):
    return x * y


# Function with complex docstring
def complex_operation(data):
    """
    Perform complex operation.

    Args:
        data: Input data dictionary

    Returns:
        Processed result

    Raises:
        ValueError: If data invalid
    """
    if not isinstance(data, dict):
        raise ValueError("Data must be dict")
    return {k: v for k, v in data.items() if v is not None}


# Function with inline comments
def commented_function(value):
    # Initialize result
    result = 0
    # Process value
    result += value  # Add to result
    return result  # Return result


# Generator function
def generate_numbers(n):
    """Generate numbers from 0 to n."""
    yield from range(n)


# Function with default arguments
def greet(name="World", greeting="Hello"):
    """Greet someone."""
    return f"{greeting}, {name}!"


# Function with *args and **kwargs
def flexible_function(*args, **kwargs):
    """Accept any arguments."""
    return {"positional": args, "keyword": kwargs}
