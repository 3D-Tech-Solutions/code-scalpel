import textwrap

import pytest

from code_scalpel.mcp.server import security_scan
from code_scalpel.security.analyzers.taint_tracker import SINK_PATTERNS, SecuritySink


@pytest.mark.parametrize(
    "key, sink",
    [
        ("entityManager.createNamedQuery", SecuritySink.SQL_QUERY),
        ("entityManager.createStoredProcedureQuery", SecuritySink.SQL_QUERY),
        ("Query.setParameter", SecuritySink.SQL_QUERY),
        ("TypedQuery.setParameter", SecuritySink.SQL_QUERY),
        ("JpaRepository.deleteBy", SecuritySink.SQL_QUERY),
        ("JdbcTemplate.batchUpdate", SecuritySink.SQL_QUERY),
        ("LdapTemplate.authenticate", SecuritySink.SQL_QUERY),
        ("BindAuthenticator.authenticate", SecuritySink.SQL_QUERY),
        ("JwtDecoder.decode", SecuritySink.SSTI),
        ("JwtEncoder.encode", SecuritySink.SSTI),
        (
            "Saml2AuthenticationRequestFactory.createAuthenticationRequest",
            SecuritySink.SSTI,
        ),
        ("Saml2AuthenticationRequestContext", SecuritySink.SSTI),
    ],
)
def test_spring_jpa_oauth_saml_sinks_present(key, sink):
    assert key in SINK_PATTERNS, f"Missing sink: {key}"
    assert SINK_PATTERNS[key] == sink


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sink_call, expected_line",
    [
        (
            'entityManager.createNamedQuery(f"SELECT * FROM users WHERE name = {user}")',
            6,
        ),
        ('JdbcTemplate.batchUpdate(f"DELETE FROM users WHERE name = {user}")', 6),
    ],
)
async def test_spring_jpa_taint_flow_detected(sink_call, expected_line):
    code = textwrap.dedent(
        f'\n        from flask import request\n\n        def handler():\n            user = request.args.get("name")\n            return {sink_call}\n        '
    )
    result = await security_scan(code=code)
    assert result.success
    assert result.has_vulnerabilities
    # Vulnerabilities are dicts with 'line' key
    assert any(
        (vuln["line"] == expected_line if isinstance(vuln, dict) else vuln.line == expected_line)
        for vuln in result.vulnerabilities
    )
