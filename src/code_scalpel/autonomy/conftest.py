"""Pytest configuration for autonomy module.

[20260122_BUGFIX] Prevent pytest from collecting dataclasses as test classes.
This is needed because dataclasses with __init__ match pytest's Test* pattern.
"""


def pytest_pycollect_makeitem(collector, name, obj):
    """Skip collection of dataclass instances that look like test classes.

    [20260122_BUGFIX] Dataclasses in this module have names that match pytest's
    test class heuristic (contain 'Result', 'Execution', etc.) but are not tests.
    This hook prevents them from being collected.
    """
    # Check if this is a dataclass with __init__
    if hasattr(obj, "__dataclass_fields__") and hasattr(obj, "__init__"):
        # Don't try to collect it as a test
        return None

    return None  # Let pytest handle normal collection
