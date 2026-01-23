"""
Test Suite for New Vulnerability Detection: WEAK_CRYPTO and SSRF

These tests verify that the security analyzer correctly detects:
1. Weak Cryptography (CWE-327): MD5, SHA1, DES usage with tainted data
2. SSRF (CWE-918): Server-Side Request Forgery with user-controlled URLs

Each test follows the pattern:
- Create code with tainted input flowing to vulnerable sink
- Run security analyzer
- Verify vulnerability is detected with correct type
"""


class TestWeakCryptographyDetection:
    """Test detection of weak cryptographic algorithms (CWE-327)."""

    def test_md5_with_user_input(self):
        """Detect MD5 hash of user-controlled data."""
        from code_scalpel.security.analyzers import SecurityAnalyzer

        code = '\nimport hashlib\nuser_data = input("Enter data to hash: ")\ndigest = hashlib.md5(user_data.encode()).hexdigest()\n'
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze(code)
        assert result.has_vulnerabilities
        vuln_types = [v.vulnerability_type for v in result.vulnerabilities]
        assert any("Weak" in str(vt) or "Crypto" in str(vt) or "WEAK_CRYPTO" in str(vt) for vt in vuln_types)

    def test_sha1_with_request_data(self):
        """Detect SHA1 hash of request data."""
        from code_scalpel.security.analyzers import SecurityAnalyzer

        code = '\nimport hashlib\npassword = request.form.get("password")\nhashed = hashlib.sha1(password.encode()).hexdigest()\n'
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze(code)
        assert result.has_vulnerabilities

    def test_des_cipher_with_tainted_key(self):
        """Detect DES encryption with tainted key."""
        from code_scalpel.security.analyzers import SecurityAnalyzer

        code = '\nfrom cryptography.hazmat.primitives.ciphers.algorithms import DES\nkey = request.args.get("key")\ncipher = DES(key.encode())\n'
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze(code)
        assert result.has_vulnerabilities

    def test_pycryptodome_md5(self):
        """Detect PyCryptodome MD5 usage."""
        from code_scalpel.security.analyzers import SecurityAnalyzer

        code = "\nfrom Crypto.Hash import MD5\nuser_input = input()\nh = MD5.new(user_input.encode())\n"
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze(code)
        assert result.has_vulnerabilities

    def test_safe_sha256_no_vulnerability(self):
        """SHA-256 should NOT be flagged as weak crypto."""
        from code_scalpel.security.analyzers import SecurityAnalyzer

        code = '\nimport hashlib\nuser_data = input("Enter data: ")\ndigest = hashlib.sha256(user_data.encode()).hexdigest()\n'
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze(code)
        weak_crypto_vulns = [v for v in result.vulnerabilities if "WEAK_CRYPTO" in str(v.vulnerability_type)]
        assert len(weak_crypto_vulns) == 0


class TestSSRFDetection:
    """Test detection of Server-Side Request Forgery (CWE-918)."""

    def test_requests_get_with_user_url(self):
        """Detect SSRF via requests.get with user-controlled URL."""
        from code_scalpel.security.analyzers import SecurityAnalyzer

        code = '\nimport requests\nurl = request.args.get("url")\nresponse = requests.get(url)\n'
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze(code)
        assert result.has_vulnerabilities
        vuln_types = [v.vulnerability_type for v in result.vulnerabilities]
        assert any("SSRF" in str(vt) or "CWE-918" in str(vt) for vt in vuln_types)

    def test_requests_post_with_user_url(self):
        """Detect SSRF via requests.post."""
        from code_scalpel.security.analyzers import SecurityAnalyzer

        code = '\nimport requests\ntarget = request.form.get("target")\nrequests.post(target, data={"key": "value"})\n'
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze(code)
        assert result.has_vulnerabilities

    def test_urllib_urlopen_with_tainted_url(self):
        """Detect SSRF via urllib.request.urlopen."""
        from code_scalpel.security.analyzers import SecurityAnalyzer

        code = '\nfrom urllib.request import urlopen\nuser_url = input("Enter URL: ")\nresponse = urlopen(user_url)\n'
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze(code)
        assert result.has_vulnerabilities

    def test_httpx_get_with_user_controlled_url(self):
        """Detect SSRF via httpx.get."""
        from code_scalpel.security.analyzers import SecurityAnalyzer

        code = '\nimport httpx\nendpoint = request.args.get("endpoint")\nr = httpx.get(endpoint)\n'
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze(code)
        assert result.has_vulnerabilities

    def test_url_concatenation_ssrf(self):
        """Detect SSRF with URL constructed from user input."""
        from code_scalpel.security.analyzers import SecurityAnalyzer

        code = '\nimport requests\nbase_url = "https://api.example.com/"\nuser_path = request.args.get("path")\nfull_url = base_url + user_path\nresponse = requests.get(full_url)\n'
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze(code)
        assert result.has_vulnerabilities

    def test_safe_hardcoded_url_no_ssrf(self):
        """Hardcoded URL should NOT be flagged as SSRF."""
        from code_scalpel.security.analyzers import SecurityAnalyzer

        code = '\nimport requests\nresponse = requests.get("https://api.example.com/status")\n'
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze(code)
        ssrf_vulns = [v for v in result.vulnerabilities if "SSRF" in str(v.vulnerability_type)]
        assert len(ssrf_vulns) == 0


class TestCombinedVulnerabilities:
    """Test detection of multiple vulnerability types in same code."""

    def test_ssrf_and_weak_crypto_together(self):
        """Detect both SSRF and weak crypto in the same code."""
        from code_scalpel.security.analyzers import SecurityAnalyzer

        code = '\nimport requests\nimport hashlib\n\nuser_url = request.args.get("url")\nresponse = requests.get(user_url)  # SSRF\n\nuser_data = request.form.get("data")\ndigest = hashlib.md5(user_data.encode())  # Weak Crypto\n'
        analyzer = SecurityAnalyzer()
        result = analyzer.analyze(code)
        assert result.has_vulnerabilities
        assert len(result.vulnerabilities) >= 2


class TestTaintTrackerIntegration:
    """Test that TaintTracker correctly handles new sink types."""

    def test_taint_is_dangerous_for_weak_crypto(self):
        """Verify taint is marked dangerous for WEAK_CRYPTO sink."""
        from code_scalpel.security.analyzers import TaintInfo, TaintLevel
        from code_scalpel.security.analyzers.taint_tracker import (  # [20251225_BUGFIX]
            SecuritySink,
            TaintSource,
        )

        taint = TaintInfo(
            source=TaintSource.USER_INPUT,
            level=TaintLevel.HIGH,
            source_location=(1, 0),
            propagation_path=[],
        )
        assert taint.is_dangerous_for(SecuritySink.WEAK_CRYPTO)

    def test_taint_is_dangerous_for_ssrf(self):
        """Verify taint is marked dangerous for SSRF sink."""
        from code_scalpel.security.analyzers import TaintInfo, TaintLevel
        from code_scalpel.security.analyzers.taint_tracker import (  # [20251225_BUGFIX]
            SecuritySink,
            TaintSource,
        )

        taint = TaintInfo(
            source=TaintSource.USER_INPUT,
            level=TaintLevel.HIGH,
            source_location=(1, 0),
            propagation_path=[],
        )
        assert taint.is_dangerous_for(SecuritySink.SSRF)

    def test_sink_patterns_registered(self):
        """Verify all new sink patterns are registered."""
        from code_scalpel.security.analyzers.taint_tracker import (
            SINK_PATTERNS,
            SecuritySink,
        )

        assert SINK_PATTERNS.get("hashlib.md5") == SecuritySink.WEAK_CRYPTO
        assert SINK_PATTERNS.get("hashlib.sha1") == SecuritySink.WEAK_CRYPTO
        assert SINK_PATTERNS.get("requests.get") == SecuritySink.SSRF
        assert SINK_PATTERNS.get("requests.post") == SecuritySink.SSRF
        assert SINK_PATTERNS.get("urllib.request.urlopen") == SecuritySink.SSRF
        assert SINK_PATTERNS.get("httpx.get") == SecuritySink.SSRF


class TestXXEDetection:
    """Test detection of XML External Entity (XXE) vulnerabilities (CWE-611)."""

    def test_xxe_elementtree_parse(self):
        """Detect XXE via xml.etree.ElementTree.parse with user input."""
        from code_scalpel.security.analyzers.taint_tracker import (
            SINK_PATTERNS,
            SecuritySink,
        )

        assert SINK_PATTERNS.get("xml.etree.ElementTree.parse") == SecuritySink.XXE
        assert SINK_PATTERNS.get("ElementTree.parse") == SecuritySink.XXE
        assert SINK_PATTERNS.get("ET.parse") == SecuritySink.XXE

    def test_xxe_lxml_parse(self):
        """Detect XXE via lxml.etree.parse."""
        from code_scalpel.security.analyzers.taint_tracker import (
            SINK_PATTERNS,
            SecuritySink,
        )

        assert SINK_PATTERNS.get("lxml.etree.parse") == SecuritySink.XXE
        assert SINK_PATTERNS.get("lxml.etree.fromstring") == SecuritySink.XXE
        assert SINK_PATTERNS.get("lxml.etree.XML") == SecuritySink.XXE

    def test_xxe_minidom(self):
        """Detect XXE via xml.dom.minidom."""
        from code_scalpel.security.analyzers.taint_tracker import (
            SINK_PATTERNS,
            SecuritySink,
        )

        assert SINK_PATTERNS.get("xml.dom.minidom.parse") == SecuritySink.XXE
        assert SINK_PATTERNS.get("minidom.parseString") == SecuritySink.XXE

    def test_xxe_sax(self):
        """Detect XXE via xml.sax."""
        from code_scalpel.security.analyzers.taint_tracker import (
            SINK_PATTERNS,
            SecuritySink,
        )

        assert SINK_PATTERNS.get("xml.sax.parse") == SecuritySink.XXE

    def test_xxe_sanitizer_defusedxml(self):
        """Verify defusedxml is recognized as safe sanitizer."""
        from code_scalpel.security.analyzers.taint_tracker import (
            SANITIZER_REGISTRY,
            SecuritySink,
        )

        assert "defusedxml.parse" in SANITIZER_REGISTRY
        assert "defusedxml.ElementTree.parse" in SANITIZER_REGISTRY
        sanitizer_info = SANITIZER_REGISTRY["defusedxml.parse"]
        assert SecuritySink.XXE in sanitizer_info.clears_sinks

    def test_taint_dangerous_for_xxe(self):
        """Verify tainted data is dangerous for XXE sink."""
        from code_scalpel.security.analyzers import TaintInfo, TaintLevel
        from code_scalpel.security.analyzers.taint_tracker import (  # [20251225_BUGFIX]
            SecuritySink,
            TaintSource,
        )

        taint = TaintInfo(source=TaintSource.USER_INPUT, level=TaintLevel.HIGH)
        assert taint.is_dangerous_for(SecuritySink.XXE)


class TestSSTIDetection:
    """Test detection of Server-Side Template Injection (SSTI) vulnerabilities (CWE-1336)."""

    def test_ssti_jinja2_template(self):
        """Detect SSTI via jinja2.Template with user input."""
        from code_scalpel.security.analyzers.taint_tracker import (
            SINK_PATTERNS,
            SecuritySink,
        )

        assert SINK_PATTERNS.get("jinja2.Template") == SecuritySink.SSTI
        assert SINK_PATTERNS.get("Environment.from_string") == SecuritySink.SSTI
        assert SINK_PATTERNS.get("jinja2.Environment.from_string") == SecuritySink.SSTI

    def test_ssti_mako_template(self):
        """Detect SSTI via mako.template.Template."""
        from code_scalpel.security.analyzers.taint_tracker import (
            SINK_PATTERNS,
            SecuritySink,
        )

        assert SINK_PATTERNS.get("mako.template.Template") == SecuritySink.SSTI
        assert SINK_PATTERNS.get("mako.Template") == SecuritySink.SSTI

    def test_ssti_django_template(self):
        """Detect SSTI via django.template.Template."""
        from code_scalpel.security.analyzers.taint_tracker import (
            SINK_PATTERNS,
            SecuritySink,
        )

        assert SINK_PATTERNS.get("django.template.Template") == SecuritySink.SSTI

    def test_ssti_tornado_template(self):
        """Detect SSTI via tornado.template.Template."""
        from code_scalpel.security.analyzers.taint_tracker import (
            SINK_PATTERNS,
            SecuritySink,
        )

        assert SINK_PATTERNS.get("tornado.template.Template") == SecuritySink.SSTI

    def test_ssti_sanitizer_render_template(self):
        """Verify render_template (file-based) is recognized as safe."""
        from code_scalpel.security.analyzers.taint_tracker import (
            SANITIZER_REGISTRY,
            SecuritySink,
        )

        assert "render_template" in SANITIZER_REGISTRY
        assert "flask.render_template" in SANITIZER_REGISTRY
        sanitizer_info = SANITIZER_REGISTRY["render_template"]
        assert SecuritySink.SSTI in sanitizer_info.clears_sinks

    def test_taint_dangerous_for_ssti(self):
        """Verify tainted data is dangerous for SSTI sink."""
        from code_scalpel.security.analyzers import TaintInfo, TaintLevel
        from code_scalpel.security.analyzers.taint_tracker import (  # [20251225_BUGFIX]
            SecuritySink,
            TaintSource,
        )

        taint = TaintInfo(source=TaintSource.USER_INPUT, level=TaintLevel.HIGH)
        assert taint.is_dangerous_for(SecuritySink.SSTI)

    def test_security_sink_enum_values(self):
        """Verify XXE and SSTI are in SecuritySink enum."""
        from code_scalpel.security.analyzers.taint_tracker import SecuritySink

        assert hasattr(SecuritySink, "XXE")
        assert hasattr(SecuritySink, "SSTI")
