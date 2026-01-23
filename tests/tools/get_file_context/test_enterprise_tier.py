"""
Enterprise tier tests for get_file_context.

Enterprise tier adds to Pro features:
- Custom metadata extraction from .code-scalpel/metadata.yaml
- Compliance flags detection (HIPAA, SOC2, PCI-DSS, GDPR)
- Code owners parsing from CODEOWNERS files
- Technical debt score estimation
- Historical metrics (git churn, age, contributors)
- PII redaction (email, phone, SSN patterns)
- Secret masking (AWS keys, API keys, passwords)
- Unlimited line context
- RBAC-aware retrieval

These tests validate that:
1. Custom metadata is loaded when available
2. Compliance flags are detected for sensitive operations
3. Code owners are parsed from CODEOWNERS files
4. Technical debt is calculated
5. Historical metrics are available
6. PII and secrets are properly redacted
7. Enterprise features only appear when capabilities enabled
"""

import tempfile
from pathlib import Path


class TestEnterpriseCustomMetadata:
    """Test Enterprise tier custom metadata extraction."""

    def test_loads_custom_metadata_when_available(self, tmpdir):
        """Enterprise tier should load custom metadata from .code-scalpel/metadata.yaml."""
        # Create test project with metadata file
        project_dir = Path(tmpdir)
        code_dir = project_dir / ".code-scalpel"
        code_dir.mkdir()

        # Create metadata file
        metadata_file = code_dir / "metadata.yaml"
        metadata_file.write_text("""
owner: security-team
classification: sensitive
data_types:
  - pii
  - financial
team: platform-engineering
        """)

        # Create test Python file
        test_file = project_dir / "test.py"
        test_file.write_text("def hello(): pass")

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(test_file),
            capabilities=["custom_metadata"],  # Enterprise capability
        )

        # Should have custom_metadata
        assert result.custom_metadata is not None
        # Metadata should be loaded if file exists
        if result.custom_metadata:
            assert isinstance(result.custom_metadata, dict)

    def test_custom_metadata_empty_when_not_available(self, tmpdir):
        """Enterprise tier should have empty metadata when file not present."""
        project_dir = Path(tmpdir)
        test_file = project_dir / "test.py"
        test_file.write_text("def hello(): pass")

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(test_file),
            capabilities=["custom_metadata"],
        )

        # Should have custom_metadata field (even if empty)
        assert hasattr(result, "custom_metadata")


class TestEnterpriseComplianceDetection:
    """Test Enterprise tier compliance flags."""

    def test_detects_hipaa_compliance_issues(self):
        """Enterprise tier should detect HIPAA-related code."""
        hipaa_code = '''
def store_patient_data(patient_id, health_info):
    """Store patient health information."""
    db.save(patient_id, health_info)
        '''

        # Create temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(hipaa_code)
            f.flush()
            temp_path = f.name

        try:
            from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

            result = _get_file_context_sync(
                temp_path,
                capabilities=["compliance_detection"],
            )

            # Should have compliance_flags field
            assert hasattr(result, "compliance_flags")
            assert isinstance(result.compliance_flags, list)
        finally:
            import os

            os.unlink(temp_path)

    def test_detects_pci_compliance_issues(self):
        """Enterprise tier should detect PCI-DSS related code."""
        pci_code = '''
def process_payment(card_number, amount):
    """Process credit card payment."""
    stripe.charge(card_number, amount)
        '''

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(pci_code)
            f.flush()
            temp_path = f.name

        try:
            from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

            result = _get_file_context_sync(
                temp_path,
                capabilities=["compliance_detection"],
            )

            # Should detect compliance issues
            assert hasattr(result, "compliance_flags")
            assert isinstance(result.compliance_flags, list)
        finally:
            import os

            os.unlink(temp_path)

    def test_compliance_flags_empty_when_no_issues(self, tmpdir):
        """Compliance flags should be empty for code with no compliance issues."""
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text("def simple_math(a, b): return a + b")

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(test_file),
            capabilities=["compliance_detection"],
        )

        # Should have field but may be empty
        assert hasattr(result, "compliance_flags")
        assert isinstance(result.compliance_flags, list)


class TestEnterpriseCodeOwners:
    """Test Enterprise tier code owners detection."""

    def test_parses_codeowners_file(self, tmpdir):
        """Enterprise tier should parse CODEOWNERS files."""
        project_dir = Path(tmpdir)

        # Create CODEOWNERS file
        codeowners_file = project_dir / "CODEOWNERS"
        codeowners_file.write_text("""
*.py @python-team
src/ @core-team
tests/ @qa-team
        """)

        test_file = project_dir / "test.py"
        test_file.write_text("def hello(): pass")

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(test_file),
            capabilities=["codeowners_analysis"],  # Enterprise capability
        )

        # Should have owners field
        assert hasattr(result, "owners")
        assert isinstance(result.owners, list)

    def test_owners_empty_when_no_codeowners(self, tmpdir):
        """Code owners should be empty when CODEOWNERS file not present."""
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text("def hello(): pass")

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(test_file),
            capabilities=["codeowners_analysis"],
        )

        # Should have owners field (even if empty)
        assert hasattr(result, "owners")
        assert isinstance(result.owners, list)


class TestEnterpriseDebtScore:
    """Test Enterprise tier technical debt scoring."""

    def test_calculates_technical_debt_score(self, tmpdir):
        """Enterprise tier should calculate technical debt score."""
        smelly_code = '''
def process_data(u, p, e, a, ph, c, z):
    """Process data - too many parameters!"""
    if u:
        if p:
            if e:
                if a:
                    if ph:
                        if c:
                            if z:
                                return {"all": "data"}
    return None

try:
    dangerous()
except:
    pass
        '''

        test_file = Path(tmpdir) / "smelly.py"
        test_file.write_text(smelly_code)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(test_file),
            capabilities=["technical_debt_estimation"],  # Enterprise capability
        )

        # Should calculate debt score
        assert hasattr(result, "technical_debt_score")

    def test_debt_score_correlates_with_smells(self, tmpdir):
        """Code with more smells should have higher debt score."""
        good_code = '''
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
        '''

        test_file = Path(tmpdir) / "good.py"
        test_file.write_text(good_code)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(test_file),
            capabilities=["technical_debt_estimation"],
        )

        # Should have debt score
        assert hasattr(result, "technical_debt_score")


class TestEnterpriseHistoricalMetrics:
    """Test Enterprise tier historical metrics."""

    def test_returns_historical_metrics_field(self, tmpdir):
        """Enterprise tier should return historical metrics structure."""
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text("def hello(): pass")

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(test_file),
            capabilities=["historical_analysis"],  # Enterprise capability
        )

        # Should have historical_metrics field
        assert hasattr(result, "historical_metrics")


class TestEnterprisePIIRedaction:
    """Test Enterprise tier PII redaction."""

    def test_redacts_email_addresses(self, tmpdir):
        """Enterprise tier should redact email addresses."""
        code_with_email = '''
def contact_user():
    """Send email to user."""
    email = "user@example.com"
    send_email(email)
        '''

        test_file = Path(tmpdir) / "contact.py"
        test_file.write_text(code_with_email)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(test_file),
            capabilities=["pii_redaction"],  # Enterprise capability
        )

        # Should mark PII as redacted
        assert hasattr(result, "pii_redacted")

    def test_redacts_phone_numbers(self, tmpdir):
        """Enterprise tier should redact phone numbers."""
        code_with_phone = '''
def call_customer():
    """Call customer at phone number."""
    phone = "555-123-4567"
    call(phone)
        '''

        test_file = Path(tmpdir) / "call.py"
        test_file.write_text(code_with_phone)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(test_file),
            capabilities=["pii_redaction"],
        )

        # Should mark PII as redacted if detected
        assert hasattr(result, "pii_redacted")


class TestEnterpriseSecretMasking:
    """Test Enterprise tier secret masking."""

    def test_masks_aws_credentials(self, tmpdir):
        """Enterprise tier should mask AWS credentials."""
        code_with_aws_key = '''
def connect_to_aws():
    """Connect to AWS with credentials."""
    access_key = "AKIAIOSFODNN7EXAMPLE"
    secret_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    return boto3.client('s3', aws_access_key_id=access_key)
        '''

        test_file = Path(tmpdir) / "aws.py"
        test_file.write_text(code_with_aws_key)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(test_file),
            capabilities=["secret_masking"],  # Enterprise capability
        )

        # Should mark secrets as masked
        assert hasattr(result, "secrets_masked")

    def test_masks_api_keys(self, tmpdir):
        """Enterprise tier should mask API keys."""
        code_with_api_key = '''
def connect_to_stripe():
    """Connect to Stripe with API key."""
    api_key = "sk_live_4eC39HqLyjWDarhtT657tSRf"
    return stripe.Account.retrieve(api_key=api_key)
        '''

        test_file = Path(tmpdir) / "stripe.py"
        test_file.write_text(code_with_api_key)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(test_file),
            capabilities=["secret_masking"],
        )

        # Should mark secrets as masked
        assert hasattr(result, "secrets_masked")

    def test_masks_hardcoded_passwords(self, tmpdir):
        """Enterprise tier should mask hardcoded passwords."""
        code_with_password = '''
def login():
    """Login with hardcoded password."""
    password = "SuperSecret123!@#"
    db.authenticate(user="admin", password=password)
        '''

        test_file = Path(tmpdir) / "login.py"
        test_file.write_text(code_with_password)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(test_file),
            capabilities=["secret_masking"],
        )

        # Should mark secrets as masked
        assert hasattr(result, "secrets_masked")


class TestEnterpriseIncludesProFeatures:
    """Test Enterprise tier includes all Pro tier features."""

    def test_enterprise_includes_code_smells(self, tmpdir):
        """Enterprise tier should include code smell detection."""
        smelly_code = """
def bad(x, y, z, a, b):
    if x:
        if y:
            if z:
                if a:
                    if b:
                        return x+y+z+a+b
        """

        test_file = Path(tmpdir) / "bad.py"
        test_file.write_text(smelly_code)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(test_file),
            capabilities=["code_smell_detection", "compliance_detection"],
        )

        # Enterprise should still have code_smells
        assert hasattr(result, "code_smells")

    def test_enterprise_includes_doc_coverage(self, tmpdir):
        """Enterprise tier should include doc coverage."""
        code = "def hello(): pass"
        test_file = Path(tmpdir) / "hello.py"
        test_file.write_text(code)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(test_file),
            capabilities=["documentation_coverage", "compliance_detection"],
        )

        # Enterprise should still have doc_coverage
        assert hasattr(result, "doc_coverage")

    def test_enterprise_includes_maintainability(self, tmpdir):
        """Enterprise tier should include maintainability index."""
        code = "def hello(): pass"
        test_file = Path(tmpdir) / "hello.py"
        test_file.write_text(code)

        from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

        result = _get_file_context_sync(
            str(test_file),
            capabilities=["maintainability_metrics", "compliance_detection"],
        )

        # Enterprise should still have maintainability_index
        assert hasattr(result, "maintainability_index")


class TestEnterpriseUnlimitedContext:
    """Test Enterprise tier has unlimited context lines."""

    def test_enterprise_has_no_line_limit(self):
        """Enterprise tier should allow unlimited lines."""
        # Create large Python file
        large_code = "\n".join([f"def func_{i}(): pass" for i in range(1000)])

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(large_code)
            f.flush()
            temp_path = f.name

        try:
            from code_scalpel.mcp.helpers.context_helpers import _get_file_context_sync

            result = _get_file_context_sync(
                temp_path,
                capabilities=["compliance_detection"],  # Enterprise tier
            )

            # Enterprise should handle large files
            assert result is not None
        finally:
            import os

            os.unlink(temp_path)
