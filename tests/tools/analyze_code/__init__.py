"""
Test suite for analyze_code tool.

Organized test structure:
- test_core_functionality.py: Core features, input validation, language support
- test_edge_cases.py: Decorators, async, nested, special methods, comprehensions
- test_tiers.py: Community, Pro, Enterprise tier features and field gating

Run all tests:
    pytest tests/tools/analyze_code/ -v

Run specific test file:
    pytest tests/tools/analyze_code/test_core_functionality.py -v

Run specific test class:
    pytest tests/tools/analyze_code/test_core_functionality.py::TestNominal -v

Run specific test:
    pytest tests/tools/analyze_code/test_core_functionality.py::TestNominal::test_analyze_python_single_function -v
"""
