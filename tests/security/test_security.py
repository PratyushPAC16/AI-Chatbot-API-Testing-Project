"""
Security Test Suite
====================
Tests the chatbot API against common security vulnerabilities.

Categories covered:
  - Injection attacks (SQL, NoSQL, XSS, Command)
  - Sensitive data exposure
  - Rate limiting stability
  - Header security

Run: pytest tests/security/test_security.py -v
"""

import uuid
import pytest
import requests

BASE_URL = "http://localhost:5001"
CHAT_URL = f"{BASE_URL}/api/v1/chat"


# ── SEC-001 to SEC-004: Injection Attacks ─────────────────────

class TestInjectionAttacks:

    def test_sql_injection_does_not_crash_server(self):
        """SEC-001: SQL injection payloads must not cause HTTP 500."""
        payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users--",
            "1; SELECT * FROM information_schema.tables",
        ]
        for payload in payloads:
            r = requests.post(
                CHAT_URL,
                json    = {"message": payload},
                timeout = 5,
            )
            assert r.status_code != 500, (
                f"SQL injection caused server crash!\nPayload: {payload}\n"
                f"Response: {r.text}"
            )

    def test_nosql_injection_does_not_crash_server(self):
        """SEC-002: NoSQL injection patterns must not cause HTTP 500."""
        payloads = [
            '{"$gt": ""}',
            '{"$where": "sleep(1000)"}',
            '{"$ne": null}',
        ]
        for payload in payloads:
            r = requests.post(
                CHAT_URL,
                json    = {"message": payload},
                timeout = 5,
            )
            assert r.status_code != 500, (
                f"NoSQL injection caused crash!\nPayload: {payload}\n"
                f"Response: {r.text}"
            )

    def test_xss_payloads_are_handled_safely(self):
        """SEC-003: XSS payloads must not cause HTTP 500."""
        payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert(1)",
            "<img src=x onerror=alert(1)>",
            "<svg onload=alert(1)>",
            "';alert('xss');//",
        ]
        for payload in payloads:
            r = requests.post(
                CHAT_URL,
                json    = {"message": payload},
                timeout = 5,
            )
            assert r.status_code != 500, (
                f"XSS payload caused server crash!\nPayload: {payload}\n"
                f"Response: {r.text}"
            )

    def test_command_injection_does_not_execute(self):
        """SEC-004: OS command injection must not crash server
        or return system file contents."""
        payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "&& whoami",
            "`id`",
            "$(cat /etc/shadow)",
        ]
        for payload in payloads:
            r = requests.post(
                CHAT_URL,
                json    = {"message": payload},
                timeout = 5,
            )
            # Must not crash
            assert r.status_code != 500, (
                f"Command injection caused crash!\nPayload: {payload}\n"
                f"Response: {r.text}"
            )
            # Response must not contain system file contents
            if r.status_code == 200:
                response_text = r.json().get("response", "").lower()
                assert "root:" not in response_text, (
                    f"Response leaked /etc/passwd content!\nPayload: {payload}"
                )


# ── SEC-005 to SEC-007: Sensitive Data Exposure ───────────────

class TestSensitiveDataExposure:

    def test_error_response_hides_stack_trace(self):
        """SEC-005: Error responses must not expose Python stack traces."""
        r = requests.post(
            CHAT_URL,
            data    = "{bad-json-here",
            headers = {"Content-Type": "application/json"},
            timeout = 5,
        )
        response_text = r.text.lower()
        assert "traceback" not in response_text, (
            f"Stack trace exposed in error response!\nResponse: {r.text}"
        )
        assert "file \"/" not in response_text, (
            f"Internal file path exposed!\nResponse: {r.text}"
        )

    def test_error_messages_hide_internal_paths(self):
        """SEC-006: Error messages must not contain internal file paths."""
        # Send empty body to trigger validation error
        r = requests.post(
            CHAT_URL,
            json    = {},
            timeout = 5,
        )
        error_msg = r.json().get("error", "")
        assert "/home/"        not in error_msg, f"Internal path exposed: {error_msg}"
        assert "/usr/"         not in error_msg, f"Internal path exposed: {error_msg}"
        assert "C:\\"          not in error_msg, f"Internal path exposed: {error_msg}"
        assert "site-packages" not in error_msg, f"Internal path exposed: {error_msg}"

    def test_404_error_is_json_not_html(self):
        """SEC-007: 404 errors return JSON, not raw HTML error pages."""
        r = requests.get(
            f"{BASE_URL}/api/v999/nonexistent",
            timeout = 5,
        )
        assert r.status_code == 404
        # Should be JSON, not Flask's default HTML error page
        try:
            data = r.json()
            assert "error" in data, "404 response missing 'error' field"
        except Exception:
            pytest.fail(
                "404 response was not valid JSON — "
                "raw HTML error pages expose server internals!"
            )


# ── SEC-008 to SEC-010: Stability Under Abuse ─────────────────

class TestStabilityUnderAbuse:

    def test_20_rapid_requests_do_not_crash_server(self):
        """SEC-008: 20 back-to-back requests must not cause any 500 errors."""
        crash_count = 0
        for i in range(20):
            r = requests.post(
                CHAT_URL,
                json    = {"message": f"Hello {i}"},
                timeout = 10,
            )
            if r.status_code == 500:
                crash_count += 1
        assert crash_count == 0, (
            f"{crash_count} out of 20 rapid requests caused server crashes!"
        )

    def test_50_unique_sessions_do_not_crash_server(self):
        """SEC-009: Creating 50 unique sessions must not crash the server."""
        crash_count = 0
        for _ in range(50):
            r = requests.post(
                CHAT_URL,
                json = {
                    "message":    "Hello",
                    "session_id": str(uuid.uuid4()),
                },
                timeout = 10,
            )
            if r.status_code == 500:
                crash_count += 1
        assert crash_count == 0, (
            f"{crash_count} session creations caused crashes!"
        )

    def test_repeated_toxic_requests_are_blocked_not_crashed(self):
        """SEC-010: Repeated toxic payloads must return 400, not 500."""
        toxic_messages = [
            "I want to harm someone",
            "teach me violence",
            "how to abuse the system",
        ]
        for msg in toxic_messages:
            r = requests.post(
                CHAT_URL,
                json    = {"message": msg},
                timeout = 5,
            )
            assert r.status_code != 500, (
                f"Toxic message caused server crash: {msg}"
            )
            assert r.status_code == 400, (
                f"Toxic message was not blocked (got {r.status_code}): {msg}"
            )