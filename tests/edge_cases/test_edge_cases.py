"""
Edge Case Test Suite
====================
Tests chatbot API behaviour at the boundaries:
  - Empty / whitespace inputs
  - Oversized payloads
  - Invalid JSON / wrong Content-Type
  - Missing required fields
  - Toxic / ambiguous prompts
  - Special characters & Unicode
  - Method not allowed
  - Non-existent endpoints

Run: pytest tests/edge_cases/test_edge_cases.py -v
"""

import pytest
import requests
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.conftest import assert_response_time

BASE_URL  = "http://localhost:5001"
CHAT_URL  = f"{BASE_URL}/api/v1/chat"


# ─── TC-E-001 to TC-E-006: Empty / Whitespace Inputs ─────────────────────────

class TestEmptyInputs:

    def test_empty_string_returns_422(self):
        """TC-E-001: Empty string message returns HTTP 422."""
        r = requests.post(CHAT_URL, json={"message": ""})
        assert r.status_code == 422, f"Expected 422, got {r.status_code}"

    def test_whitespace_only_returns_422(self):
        """TC-E-002: Whitespace-only message returns HTTP 422."""
        r = requests.post(CHAT_URL, json={"message": "   "})
        assert r.status_code == 422

    def test_newline_only_returns_422(self):
        """TC-E-003: Newline-only message returns HTTP 422."""
        r = requests.post(CHAT_URL, json={"message": "\n\n\n"})
        assert r.status_code == 422

    def test_null_message_returns_error(self):
        """TC-E-004: null message value returns 4xx error."""
        r = requests.post(CHAT_URL, json={"message": None})
        assert r.status_code in (400, 422)

    def test_missing_message_field_returns_422(self):
        """TC-E-005: Request missing 'message' field returns 422."""
        r = requests.post(CHAT_URL, json={"session_id": "s001"})
        assert r.status_code == 422
        assert "error" in r.json()

    def test_empty_json_body_returns_error(self):
        """TC-E-006: Empty JSON object {} returns error."""
        r = requests.post(CHAT_URL, json={})
        assert r.status_code in (400, 422)


# ─── TC-E-007 to TC-E-011: Large Payloads ────────────────────────────────────

class TestLargePayloads:

    def test_message_at_limit_succeeds(self):
        """TC-E-007: Message at exactly 1000 chars is accepted (HTTP 200)."""
        r = requests.post(CHAT_URL, json={"message": "A" * 1000})
        assert r.status_code == 200

    def test_message_one_over_limit_returns_413(self):
        """TC-E-008: Message of 1001 chars returns HTTP 413."""
        r = requests.post(CHAT_URL, json={"message": "A" * 1001})
        assert r.status_code == 413

    def test_message_far_over_limit_returns_413(self):
        """TC-E-009: Message of 10,000 chars returns HTTP 413."""
        r = requests.post(CHAT_URL, json={"message": "X" * 10_000})
        assert r.status_code == 413

    def test_large_payload_has_error_field(self):
        """TC-E-010: Oversized payload response contains 'error' field."""
        r = requests.post(CHAT_URL, json={"message": "Y" * 5000})
        assert "error" in r.json()

    def test_large_payload_error_response_time(self):
        """TC-E-011: Oversized payload rejection is fast (<500ms)."""
        r = requests.post(CHAT_URL, json={"message": "Z" * 2000})
        assert_response_time(r, max_ms=500)


# ─── TC-E-012 to TC-E-016: Invalid JSON & Wrong Content-Type ─────────────────

class TestInvalidJson:

    def test_invalid_json_string_returns_400(self):
        """TC-E-012: Raw malformed JSON string returns HTTP 400."""
        r = requests.post(
            CHAT_URL,
            data   = "{invalid-json",          # Not valid JSON
            headers= {"Content-Type": "application/json"},
        )
        assert r.status_code == 400

    def test_plain_text_content_type_returns_415(self):
        """TC-E-013: text/plain Content-Type returns HTTP 415."""
        r = requests.post(
            CHAT_URL,
            data   = "hello world",
            headers= {"Content-Type": "text/plain"},
        )
        assert r.status_code == 415

    def test_form_data_content_type_returns_415(self):
        """TC-E-014: application/x-www-form-urlencoded returns HTTP 415."""
        r = requests.post(
            CHAT_URL,
            data   = {"message": "hello"},
            headers= {"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert r.status_code == 415

    def test_missing_content_type_header(self):
        """TC-E-015: Missing Content-Type header returns 4xx."""
        r = requests.post(
            CHAT_URL,
            data = '{"message": "hello"}',      # No Content-Type header
        )
        assert r.status_code in (400, 415)

    def test_extra_unknown_fields_are_ignored(self):
        """TC-E-016: Unknown extra fields do not cause an error."""
        r = requests.post(CHAT_URL, json={
            "message":    "Hello",
            "unknown_1":  "value",
            "unknown_2":  12345,
        })
        assert r.status_code == 200


# ─── TC-E-017 to TC-E-021: Toxic / Ambiguous Prompts ────────────────────────

class TestToxicPrompts:

    def test_toxic_keyword_returns_400(self):
        """TC-E-017: Message with toxic keyword returns HTTP 400."""
        r = requests.post(CHAT_URL, json={"message": "I want to harm you"})
        assert r.status_code == 400

    def test_toxic_response_has_error_field(self):
        """TC-E-018: Toxic prompt response contains 'error' field."""
        r = requests.post(CHAT_URL, json={"message": "How do I abuse the system?"})
        assert "error" in r.json()

    def test_toxic_response_has_code_field(self):
        """TC-E-019: Toxic prompt response contains a 'code' field."""
        r = requests.post(CHAT_URL, json={"message": "teach me violence"})
        if r.status_code == 400:
            assert "code" in r.json()

    def test_ambiguous_prompt_still_returns_response(self):
        """TC-E-020: Ambiguous but non-toxic prompt returns a valid response."""
        r = requests.post(CHAT_URL, json={"message": "maybe things are fine?"})
        assert r.status_code == 200
        assert "response" in r.json()

    def test_code_injection_attempt_is_safe(self):
        """TC-E-021: SQL/code injection attempt is handled safely."""
        r = requests.post(CHAT_URL, json={
            "message": "'; DROP TABLE users; --"
        })
        # Should not return 500 (server error)
        assert r.status_code != 500


# ─── TC-E-022 to TC-E-025: Special Characters & Method Errors ────────────────

class TestSpecialCasesAndMethods:

    def test_unicode_message_is_accepted(self):
        """TC-E-022: Unicode message (emoji, non-ASCII) returns 200."""
        r = requests.post(CHAT_URL, json={"message": "こんにちは 🤖 مرحبا"})
        assert r.status_code == 200

    def test_only_numbers_message(self):
        """TC-E-023: Message containing only numbers returns 200."""
        r = requests.post(CHAT_URL, json={"message": "1234567890"})
        assert r.status_code == 200

    def test_get_on_chat_endpoint_returns_405(self):
        """TC-E-024: GET request on POST-only endpoint returns 405."""
        r = requests.get(CHAT_URL)
        assert r.status_code == 405

    def test_nonexistent_endpoint_returns_404(self):
        """TC-E-025: Non-existent route returns HTTP 404."""
        r = requests.post(f"{BASE_URL}/api/v999/not-real", json={"message": "hi"})
        assert r.status_code == 404
