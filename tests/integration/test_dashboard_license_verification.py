"""Integration tests for dashboard license verification.

Tests the license status API endpoint with local and remote verification modes.
Covers JWT validation, remote verifier configuration, and offline grace period behavior.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from code_scalpel.dashboard_service import DashboardServer


class TestLicenseStatusEndpoint:
    """Test GET /api/license endpoint."""

    def test_license_status_returns_valid_response(self):
        """Test that license status endpoint returns valid response."""
        server = DashboardServer()
        port = server.start()

        try:
            response = requests.get(f"http://localhost:{port}/api/license", timeout=5)
            assert response.status_code == 200

            data = response.json()
            assert "current_tier" in data
            assert "is_valid" in data
            assert "error_message" in data
            # Should be dict with license info
            assert isinstance(data, dict)
        finally:
            try:
                requests.get(f"http://localhost:{port}/shutdown", timeout=2)
            except Exception:
                pass
            server.stop()

    def test_license_status_includes_license_file_path(self):
        """Test that license status includes file path when available."""
        server = DashboardServer()
        port = server.start()

        try:
            response = requests.get(f"http://localhost:{port}/api/license", timeout=5)
            assert response.status_code == 200

            data = response.json()
            assert "license_file" in data
            # license_file can be None if no license file found
            if data["license_file"] is not None:
                assert isinstance(data["license_file"], str)
        finally:
            try:
                requests.get(f"http://localhost:{port}/shutdown", timeout=2)
            except Exception:
                pass
            server.stop()

    def test_license_status_includes_tier_info(self):
        """Test that license status includes tier information."""
        server = DashboardServer()
        port = server.start()

        try:
            response = requests.get(f"http://localhost:{port}/api/license", timeout=5)
            assert response.status_code == 200

            data = response.json()
            assert "current_tier" in data
            # Tier should be one of the known tiers
            valid_tiers = ["community", "pro", "enterprise"]
            assert data["current_tier"] in valid_tiers
        finally:
            try:
                requests.get(f"http://localhost:{port}/shutdown", timeout=2)
            except Exception:
                pass
            server.stop()


class TestLicenseUploadEndpoint:
    """Test POST /api/license endpoint for license file upload."""

    def test_license_upload_endpoint_exists(self):
        """Test that license upload endpoint exists."""
        server = DashboardServer()
        port = server.start()

        try:
            # Try to upload (will fail without valid file, but endpoint should exist)
            response = requests.post(
                f"http://localhost:{port}/api/license/upload", timeout=5
            )
            # Should return 400, 422, or similar, not 404
            assert response.status_code != 404
        finally:
            try:
                requests.get(f"http://localhost:{port}/shutdown", timeout=2)
            except Exception:
                pass
            server.stop()

    def test_license_upload_with_file(self):
        """Test uploading a license file."""
        server = DashboardServer()
        port = server.start()

        try:
            # Create a dummy JWT file (won't be valid, but structure is correct)
            jwt_content = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".jwt", delete=False
            ) as f:
                f.write(jwt_content)
                f.flush()

                # Try to upload the file
                with open(f.name, "rb") as file_obj:
                    files = {"file": file_obj}
                    response = requests.post(
                        f"http://localhost:{port}/api/license/upload",
                        files=files,
                        timeout=5,
                    )
                    # Should return 200 or error response (depends on validation)
                    assert response.status_code in [200, 400, 422, 500]

        finally:
            try:
                requests.get(f"http://localhost:{port}/shutdown", timeout=2)
            except Exception:
                pass
            server.stop()


class TestLicenseStatusWithValidation:
    """Test license status with JWT validation."""

    def test_license_status_returns_expiration_info(self):
        """Test that license status includes expiration info."""
        server = DashboardServer()
        port = server.start()

        try:
            response = requests.get(f"http://localhost:{port}/api/license", timeout=5)
            assert response.status_code == 200

            data = response.json()
            # Should indicate if license is expired
            assert "is_expired" in data or "error_message" in data
        finally:
            try:
                requests.get(f"http://localhost:{port}/shutdown", timeout=2)
            except Exception:
                pass
            server.stop()

    def test_license_status_returns_error_for_invalid_license(self):
        """Test that status endpoint handles invalid licenses gracefully."""
        server = DashboardServer()
        port = server.start()

        try:
            response = requests.get(f"http://localhost:{port}/api/license", timeout=5)
            assert response.status_code == 200

            data = response.json()
            # If there's no valid license, should indicate this
            if not data.get("is_valid"):
                assert (
                    data.get("error_message") or data.get("current_tier") == "community"
                )
        finally:
            try:
                requests.get(f"http://localhost:{port}/shutdown", timeout=2)
            except Exception:
                pass
            server.stop()


class TestLicenseEndpointWithMockedValidator:
    """Test license endpoints with mocked validator."""

    def test_license_status_with_valid_license(self):
        """Test license status with mocked valid license."""
        with patch(
            "code_scalpel.licensing.jwt_validator.JWTLicenseValidator"
        ) as MockValidator:
            # Mock a valid license
            mock_validator = MagicMock()
            mock_data = MagicMock()
            mock_data.is_valid = True
            mock_data.is_expired = False
            mock_data.tier = "enterprise"
            mock_data.error_message = None

            mock_validator.validate.return_value = mock_data
            mock_validator.find_license_file.return_value = Path(
                "/home/user/.scalpel-license"
            )
            MockValidator.return_value = mock_validator

            server = DashboardServer()
            port = server.start()

            try:
                response = requests.get(
                    f"http://localhost:{port}/api/license", timeout=5
                )
                assert response.status_code == 200

                data = response.json()
                # With mocked valid license
                assert data["is_valid"] is True
                assert data["is_expired"] is False
                assert data["license_file"] is not None
            finally:
                try:
                    requests.get(f"http://localhost:{port}/shutdown", timeout=2)
                except Exception:
                    pass
                server.stop()

    def test_license_status_with_expired_license(self):
        """Test license status with mocked expired license."""
        with patch(
            "code_scalpel.licensing.jwt_validator.JWTLicenseValidator"
        ) as MockValidator:
            # Mock an expired license
            mock_validator = MagicMock()
            mock_data = MagicMock()
            mock_data.is_valid = False
            mock_data.is_expired = True
            mock_data.tier = "pro"
            mock_data.error_message = "License expired"

            mock_validator.validate.return_value = mock_data
            mock_validator.find_license_file.return_value = Path(
                "/home/user/.scalpel-license"
            )
            MockValidator.return_value = mock_validator

            server = DashboardServer()
            port = server.start()

            try:
                response = requests.get(
                    f"http://localhost:{port}/api/license", timeout=5
                )
                assert response.status_code == 200

                data = response.json()
                # With mocked expired license
                assert data["is_valid"] is False
                assert data["is_expired"] is True
                assert data["error_message"] is not None
            finally:
                try:
                    requests.get(f"http://localhost:{port}/shutdown", timeout=2)
                except Exception:
                    pass
                server.stop()


class TestLicenseAPIJsonResponse:
    """Test that license API responses are valid JSON."""

    def test_license_endpoint_returns_valid_json(self):
        """Test that /api/license returns valid JSON."""
        server = DashboardServer()
        port = server.start()

        try:
            response = requests.get(f"http://localhost:{port}/api/license", timeout=5)
            assert response.status_code == 200

            # Should be parseable as JSON
            data = response.json()
            assert isinstance(data, dict)
            assert len(data) > 0
        finally:
            try:
                requests.get(f"http://localhost:{port}/shutdown", timeout=2)
            except Exception:
                pass
            server.stop()

    def test_license_endpoint_returns_consistent_schema(self):
        """Test that license endpoint always returns consistent schema."""
        server = DashboardServer()
        port = server.start()

        try:
            # Get license status multiple times
            for _ in range(3):
                response = requests.get(
                    f"http://localhost:{port}/api/license", timeout=5
                )
                assert response.status_code == 200

                data = response.json()
                # Same fields should be present each time
                assert "current_tier" in data
                assert "is_valid" in data
        finally:
            try:
                requests.get(f"http://localhost:{port}/shutdown", timeout=2)
            except Exception:
                pass
            server.stop()


class TestLicenseEndpointErrorHandling:
    """Test error handling in license endpoints."""

    def test_license_endpoint_handles_validation_errors(self):
        """Test that license endpoint handles validation errors gracefully."""
        with patch(
            "code_scalpel.licensing.jwt_validator.JWTLicenseValidator"
        ) as MockValidator:
            # Mock validator that raises an exception
            mock_validator = MagicMock()
            mock_validator.validate.side_effect = Exception("Validation error")
            MockValidator.return_value = mock_validator

            server = DashboardServer()
            port = server.start()

            try:
                response = requests.get(
                    f"http://localhost:{port}/api/license", timeout=5
                )
                # Should still return 200 with error info, not 500
                assert response.status_code in [200, 400, 500]

                if response.status_code == 200:
                    data = response.json()
                    # Should indicate there was an error
                    assert data.get("error_message") or not data.get("is_valid")
            finally:
                try:
                    requests.get(f"http://localhost:{port}/shutdown", timeout=2)
                except Exception:
                    pass
                server.stop()

    def test_license_endpoint_handles_missing_license_file(self):
        """Test that license endpoint handles missing license file gracefully."""
        with patch(
            "code_scalpel.licensing.jwt_validator.JWTLicenseValidator"
        ) as MockValidator:
            # Mock validator that can't find license file
            mock_validator = MagicMock()
            mock_data = MagicMock()
            mock_data.is_valid = False
            mock_data.is_expired = False
            mock_data.error_message = "License file not found"

            mock_validator.validate.return_value = mock_data
            mock_validator.find_license_file.return_value = None
            MockValidator.return_value = mock_validator

            server = DashboardServer()
            port = server.start()

            try:
                response = requests.get(
                    f"http://localhost:{port}/api/license", timeout=5
                )
                assert response.status_code == 200

                data = response.json()
                assert data["license_file"] is None
                assert (
                    data.get("error_message") is not None
                    or data["current_tier"] == "community"
                )
            finally:
                try:
                    requests.get(f"http://localhost:{port}/shutdown", timeout=2)
                except Exception:
                    pass
                server.stop()


class TestRemoteLicenseVerification:
    """Test remote license verification features."""

    def test_license_endpoint_includes_remote_verification_fields(self):
        """Test that license endpoint includes remote verification fields when verifier is configured."""
        with patch(
            "code_scalpel.licensing.remote_verifier.remote_verifier_configured",
            return_value=False,
        ):
            server = DashboardServer()
            port = server.start()

            try:
                response = requests.get(
                    f"http://localhost:{port}/api/license", timeout=5
                )
                assert response.status_code == 200

                data = response.json()
                # Should indicate no remote verification
                assert "remote_verified" in data
                assert data["remote_verified"] is False
            finally:
                try:
                    requests.get(f"http://localhost:{port}/shutdown", timeout=2)
                except Exception:
                    pass
                server.stop()

    def test_license_endpoint_with_remote_verifier_success(self):
        """Test license endpoint when remote verifier is configured and succeeds."""
        with patch(
            "code_scalpel.licensing.remote_verifier.remote_verifier_configured",
            return_value=True,
        ):
            with patch(
                "code_scalpel.licensing.remote_verifier.authorize_token"
            ) as mock_authorize:
                # Mock successful remote verification
                mock_decision = MagicMock()
                mock_decision.allowed = True
                mock_decision.reason = "remote_verified"
                mock_decision.entitlements = MagicMock()
                mock_decision.entitlements.tier = "enterprise"
                mock_authorize.return_value = mock_decision

                with patch(
                    "code_scalpel.licensing.jwt_validator.JWTLicenseValidator"
                ) as MockValidator:
                    mock_validator = MagicMock()
                    mock_data = MagicMock()
                    mock_data.is_valid = True
                    mock_data.is_expired = False
                    mock_data.error_message = None

                    mock_validator.validate.return_value = mock_data
                    mock_validator.find_license_file.return_value = Path(
                        "/home/user/.code-scalpel/license/license.jwt"
                    )
                    mock_validator.load_license_token.return_value = "mock.jwt.token"
                    MockValidator.return_value = mock_validator

                    server = DashboardServer()
                    port = server.start()

                    try:
                        response = requests.get(
                            f"http://localhost:{port}/api/license", timeout=5
                        )
                        assert response.status_code == 200

                        data = response.json()
                        assert data["remote_verified"] is True
                        assert data["remote_allowed"] is True
                        assert data["remote_reason"] == "remote_verified"
                        assert data.get("remote_tier") == "enterprise"
                    finally:
                        try:
                            requests.get(f"http://localhost:{port}/shutdown", timeout=2)
                        except Exception:
                            pass
                        server.stop()

    def test_license_endpoint_with_offline_grace_period(self):
        """Test license endpoint showing offline grace period."""
        with patch(
            "code_scalpel.licensing.remote_verifier.remote_verifier_configured",
            return_value=True,
        ):
            with patch(
                "code_scalpel.licensing.remote_verifier.authorize_token"
            ) as mock_authorize:
                # Mock offline grace period
                mock_decision = MagicMock()
                mock_decision.allowed = True
                mock_decision.reason = "offline_grace"
                mock_decision.entitlements = MagicMock()
                mock_decision.entitlements.tier = "pro"
                mock_authorize.return_value = mock_decision

                with patch(
                    "code_scalpel.licensing.jwt_validator.JWTLicenseValidator"
                ) as MockValidator:
                    mock_validator = MagicMock()
                    mock_data = MagicMock()
                    mock_data.is_valid = True
                    mock_data.is_expired = False

                    mock_validator.validate.return_value = mock_data
                    mock_validator.find_license_file.return_value = Path(
                        "/home/user/.code-scalpel/license/license.jwt"
                    )
                    mock_validator.load_license_token.return_value = "mock.jwt.token"
                    MockValidator.return_value = mock_validator

                    server = DashboardServer()
                    port = server.start()

                    try:
                        response = requests.get(
                            f"http://localhost:{port}/api/license", timeout=5
                        )
                        assert response.status_code == 200

                        data = response.json()
                        assert data["remote_verified"] is True
                        assert data["remote_reason"] == "offline_grace"
                        # During grace period, may still have pro tier
                        assert data.get("remote_tier") in ["pro", "community"]
                    finally:
                        try:
                            requests.get(f"http://localhost:{port}/shutdown", timeout=2)
                        except Exception:
                            pass
                        server.stop()

    def test_license_endpoint_with_license_expired(self):
        """Test license endpoint when license is expired."""
        with patch(
            "code_scalpel.licensing.remote_verifier.remote_verifier_configured",
            return_value=True,
        ):
            with patch(
                "code_scalpel.licensing.remote_verifier.authorize_token"
            ) as mock_authorize:
                # Mock expired license
                mock_decision = MagicMock()
                mock_decision.allowed = False
                mock_decision.reason = "license_expired"
                mock_authorize.return_value = mock_decision

                with patch(
                    "code_scalpel.licensing.jwt_validator.JWTLicenseValidator"
                ) as MockValidator:
                    mock_validator = MagicMock()
                    mock_data = MagicMock()
                    mock_data.is_valid = False
                    mock_data.is_expired = True
                    mock_data.error_message = "License expired"

                    mock_validator.validate.return_value = mock_data
                    mock_validator.find_license_file.return_value = Path(
                        "/home/user/.code-scalpel/license/license.jwt"
                    )
                    mock_validator.load_license_token.return_value = "mock.jwt.token"
                    MockValidator.return_value = mock_validator

                    server = DashboardServer()
                    port = server.start()

                    try:
                        response = requests.get(
                            f"http://localhost:{port}/api/license", timeout=5
                        )
                        assert response.status_code == 200

                        data = response.json()
                        assert data["is_expired"] is True
                        assert data["remote_reason"] == "license_expired"
                        assert data["current_tier"] == "community"
                    finally:
                        try:
                            requests.get(f"http://localhost:{port}/shutdown", timeout=2)
                        except Exception:
                            pass
                        server.stop()
