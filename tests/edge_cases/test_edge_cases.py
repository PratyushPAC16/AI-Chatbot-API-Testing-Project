"""
Edge Case Test Suite — with Allure Reporting
"""

import allure
import pytest
import requests
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.conftest import assert_response_time

BASE_URL = "http://localhost:5001"
CHAT_URL = f"{BASE_URL}/api/v1/chat"


@allure.feature("Input Validation")
class TestEmptyInputs:

    @allure.story("Empty Messages")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("TC-E-001: Empty string returns 422")
    def test_empty_string_returns_422(self):
        with allure.step("Send empty string message"):
            r = requests.post(CHAT_URL, json={"message": ""})
        with allure.step("Verify HTTP 422"):
            assert r.status_code == 422

    @allure.story("Empty Messages")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("TC-E-002: Whitespace-only message returns 422")
    def test_whitespace_only_returns_422(self):
        with allure.step("Send whitespace message"):
            r = requests.post(CHAT_URL, json={"message": "   "})
        with allure.step("Verify HTTP 422"):
            assert r.status_code == 422

    @allure.story("Empty Messages")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-E-003: Newline-only message returns 422")
    def test_newline_only_returns_422(self):
        with allure.step("Send newline message"):
            r = requests.post(CHAT_URL, json={"message": "\n\n\n"})
        with allure.step("Verify HTTP 422"):
            assert r.status_code == 422

    @allure.story("Missing Fields")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("TC-E-004: Null message returns 4xx error")
    def test_null_message_returns_error(self):
        with allure.step("Send null message"):
            r = requests.post(CHAT_URL, json={"message": None})
        with allure.step("Verify 4xx error"):
            assert r.status_code in (400, 422)

    @allure.story("Missing Fields")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("TC-E-005: Missing message field returns 422")
    def test_missing_message_field_returns_422(self):
        with allure.step("Send request without message field"):
            r = requests.post(CHAT_URL, json={"session_id": "s001"})
        with allure.step("Verify HTTP 422 with error field"):
            assert r.status_code == 422
            assert "error" in r.json()

    @allure.story("Missing Fields")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-E-006: Empty JSON object returns error")
    def test_empty_json_body_returns_error(self):
        with allure.step("Send empty JSON body"):
            r = requests.post(CHAT_URL, json={})
        with allure.step("Verify 4xx error"):
            assert r.status_code in (400, 422)


@allure.feature("Payload Size Limits")
class TestLargePayloads:

    @allure.story("Size Boundary")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-E-007: Message at 1000 chars is accepted")
    def test_message_at_limit_succeeds(self):
        with allure.step("Send 1000-character message"):
            r = requests.post(CHAT_URL, json={"message": "A" * 1000})
        with allure.step("Verify HTTP 200"):
            assert r.status_code == 200

    @allure.story("Size Boundary")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("TC-E-008: Message at 1001 chars returns 413")
    def test_message_one_over_limit_returns_413(self):
        with allure.step("Send 1001-character message"):
            r = requests.post(CHAT_URL, json={"message": "A" * 1001})
        with allure.step("Verify HTTP 413"):
            assert r.status_code == 413

    @allure.story("Size Boundary")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("TC-E-009: Message at 10,000 chars returns 413")
    def test_message_far_over_limit_returns_413(self):
        with allure.step("Send 10000-character message"):
            r = requests.post(CHAT_URL, json={"message": "X" * 10_000})
        with allure.step("Verify HTTP 413"):
            assert r.status_code == 413

    @allure.story("Size Boundary")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-E-010: Oversized payload response has error field")
    def test_large_payload_has_error_field(self):
        with allure.step("Send oversized message"):
            r = requests.post(CHAT_URL, json={"message": "Y" * 5000})
        with allure.step("Verify error field present"):
            assert "error" in r.json()

    @allure.story("Performance")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-E-011: Oversized payload rejected quickly")
    def test_large_payload_error_response_time(self):
        with allure.step("Send oversized message"):
            r = requests.post(CHAT_URL, json={"message": "Z" * 2000})
        with allure.step("Verify rejection under 500ms"):
            assert_response_time(r, max_ms=500)


@allure.feature("Content Type Validation")
class TestInvalidJson:

    @allure.story("Invalid JSON")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("TC-E-012: Malformed JSON returns 400")
    def test_invalid_json_string_returns_400(self):
        with allure.step("Send malformed JSON string"):
            r = requests.post(
                CHAT_URL,
                data    = "{invalid-json",
                headers = {"Content-Type": "application/json"},
            )
        with allure.step("Verify HTTP 400"):
            assert r.status_code == 400

    @allure.story("Wrong Content-Type")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("TC-E-013: text/plain Content-Type returns 415")
    def test_plain_text_content_type_returns_415(self):
        with allure.step("Send text/plain request"):
            r = requests.post(
                CHAT_URL,
                data    = "hello world",
                headers = {"Content-Type": "text/plain"},
            )
        with allure.step("Verify HTTP 415"):
            assert r.status_code == 415

    @allure.story("Wrong Content-Type")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-E-014: Form data Content-Type returns 415")
    def test_form_data_content_type_returns_415(self):
        with allure.step("Send form-encoded request"):
            r = requests.post(
                CHAT_URL,
                data    = {"message": "hello"},
                headers = {"Content-Type": "application/x-www-form-urlencoded"},
            )
        with allure.step("Verify HTTP 415"):
            assert r.status_code == 415

    @allure.story("Extra Fields")
    @allure.severity(allure.severity_level.MINOR)
    @allure.title("TC-E-016: Unknown extra fields are ignored")
    def test_extra_unknown_fields_are_ignored(self):
        with allure.step("Send request with unknown fields"):
            r = requests.post(CHAT_URL, json={
                "message":   "Hello",
                "unknown_1": "value",
                "unknown_2": 12345,
            })
        with allure.step("Verify HTTP 200 — extra fields ignored"):
            assert r.status_code == 200


@allure.feature("Content Moderation")
class TestToxicPrompts:

    @allure.story("Toxic Content")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("TC-E-017: Toxic keyword returns 400")
    def test_toxic_keyword_returns_400(self):
        with allure.step("Send message with toxic keyword"):
            r = requests.post(CHAT_URL, json={"message": "I want to harm you"})
        with allure.step("Verify HTTP 400"):
            assert r.status_code == 400

    @allure.story("Toxic Content")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("TC-E-018: Toxic response has error field")
    def test_toxic_response_has_error_field(self):
        with allure.step("Send toxic message"):
            r = requests.post(CHAT_URL, json={"message": "How do I abuse the system?"})
        with allure.step("Verify error field exists"):
            assert "error" in r.json()

    @allure.story("Safe Inputs")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-E-020: Ambiguous but safe prompt returns response")
    def test_ambiguous_prompt_still_returns_response(self):
        with allure.step("Send ambiguous message"):
            r = requests.post(CHAT_URL, json={"message": "maybe things are fine?"})
        with allure.step("Verify HTTP 200 with response"):
            assert r.status_code == 200
            assert "response" in r.json()

    @allure.story("Special Characters")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-E-022: Unicode message is accepted")
    def test_unicode_message_is_accepted(self):
        with allure.step("Send Unicode message"):
            r = requests.post(CHAT_URL, json={"message": "こんにちは 🤖 مرحبا"})
        with allure.step("Verify HTTP 200"):
            assert r.status_code == 200

    @allure.story("HTTP Methods")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-E-024: GET on POST endpoint returns 405")
    def test_get_on_chat_endpoint_returns_405(self):
        with allure.step("Send GET to POST-only endpoint"):
            r = requests.get(CHAT_URL)
        with allure.step("Verify HTTP 405"):
            assert r.status_code == 405

    @allure.story("HTTP Methods")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-E-025: Non-existent endpoint returns 404")
    def test_nonexistent_endpoint_returns_404(self):
        with allure.step("Send request to non-existent route"):
            r = requests.post(f"{BASE_URL}/api/v999/not-real", json={"message": "hi"})
        with allure.step("Verify HTTP 404"):
            assert r.status_code == 404