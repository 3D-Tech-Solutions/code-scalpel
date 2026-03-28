"""Tests for license upgrade functionality in dashboard."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from code_scalpel.dashboard_service import create_app


def test_license_endpoint_exists():
    """Test that license API endpoint is registered."""
    app, _ = create_app()

    # Check routes are registered
    routes = [route.path for route in app.routes]
    assert "/api/license" in routes, "License endpoint not found"
    assert "/api/license/upload" in routes, "License upload endpoint not found"
    print("✓ License endpoints registered")


def test_license_panel_html():
    """Test that license panel is present in HTML."""
    from code_scalpel.dashboard_service import get_dashboard_html

    html = get_dashboard_html()
    assert "license-panel" in html
    assert "Upgrade Your Tier" in html
    assert "license.jwt" in html
    assert "code-scalpel.dev" in html
    print("✓ License upgrade panel in dashboard HTML")


def test_license_html_elements():
    """Test that all license UI elements are present."""
    from code_scalpel.dashboard_service import get_dashboard_html

    html = get_dashboard_html()

    # Check for key UI elements
    assert "tier-badge" in html, "Tier badge not found"
    assert "license-status" in html, "License status div not found"
    assert "upgrade-prompt" in html, "Upgrade prompt not found"
    assert "file-upload-area" in html, "File upload area not found"
    assert "license-file" in html, "File input not found"

    # Check for instructions
    assert "Choose File" in html, "Upload button not found"
    assert "Don't have a license?" in html, "License instructions not found"

    print("✓ All license UI elements present")


def test_license_css_styles():
    """Test that license CSS classes are defined."""
    from code_scalpel.dashboard_service import get_dashboard_html

    html = get_dashboard_html()

    # Check for license-related CSS classes
    css_classes = [
        ".license-panel",
        ".tier-badge",
        ".tier-community",
        ".tier-pro",
        ".tier-enterprise",
        ".file-upload-area",
        ".upgrade-section",
    ]

    for css_class in css_classes:
        assert css_class in html, f"CSS class {css_class} not found"

    print("✓ All license CSS styles defined")


def test_license_javascript():
    """Test that license JavaScript functions are present."""
    from code_scalpel.dashboard_service import get_dashboard_html

    html = get_dashboard_html()

    # Check for JavaScript functions
    js_functions = [
        "loadLicenseStatus",
        "setupFileUpload",
        "uploadLicense",
    ]

    for func in js_functions:
        assert (
            f"function {func}" in html or f"{func}(" in html
        ), f"JavaScript function {func} not found"

    print("✓ License JavaScript functions present")


if __name__ == "__main__":
    test_license_endpoint_exists()
    test_license_panel_html()
    test_license_html_elements()
    test_license_css_styles()
    test_license_javascript()
    print("\n✅ All license upgrade tests passed!")
