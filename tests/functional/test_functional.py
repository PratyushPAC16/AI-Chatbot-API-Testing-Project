"""
Functional Test Suite — with Allure Reporting
===============================================
Allure decorators added for beautiful interactive reports.

Run normally  : pytest tests/functional/test_functional.py -v
Run with Allure: pytest tests/functional/ --alluredir=reports/allure-results
View report   : allure serve reports/allure-results
"""

import allure
import pytest
import requests
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.conftest import assert_response_time, assert_json_keys
from src.validator.response_validator import ResponseValidator

BASE_URL  = "http://localhost:5001"
CHAT_URL  = f"{BASE_URL}/api/v1/chat"
validator = ResponseValidator()


# ── Health Check Tests ────────────────────────────────────────

@allure.feature("Health Check")
class TestHealthEndpoint:

    @allure.story("Basic Availability")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("TC-F-001: Health endpoint returns HTTP 200")
    def test_health_returns_200(self):
        with allure.step("Send GET request to /health"):
            r = requests.get(f"{BASE_URL}/health")
        with allure.step("Verify HTTP status is 200"):
            assert r.status_code == 200

    @allure.story("Basic Availability")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("TC-F-002: Health endpoint returns valid JSON")
    def test_health_response_is_json(self):
        with allure.step("Send GET request to /health"):
            r = requests.get(f"{BASE_URL}/health")
        with allure.step("Verify Content-Type is application/json"):
            assert r.headers["Content-Type"].startswith("application/json")
        with allure.step("Verify response body is a dict"):
            assert isinstance(r.json(), dict)

    @allure.story("Schema Validation")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("TC-F-003: Health response has required fields")
    def test_health_has_required_fields(self):
        with allure.step("Send GET request to /health"):
            r = requests.get(f"{BASE_URL}/health")
        with allure.step("Verify required fields exist"):
            data = r.json()
            allure.attach(
                str(data),
                name             = "Response Body",
                attachment_type  = allure.attachment_type.TEXT,
            )
            assert_json_keys(data, ["status", "timestamp", "version"])

    @allure.story("Schema Validation")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-F-004: Health status value is 'healthy'")
    def test_health_status_is_healthy(self):
        with allure.step("Send GET request to /health"):
            r = requests.get(f"{BASE_URL}/health")
        with allure.step("Verify status field equals 'healthy'"):
            assert r.json()["status"] == "healthy"

    @allure.story("Performance")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-F-005: Health endpoint responds within 500ms")
    def test_health_response_time(self):
        with allure.step("Send GET request to /health"):
            r = requests.get(f"{BASE_URL}/health")
        with allure.step("Verify response time is under 500ms"):
            assert_response_time(r, max_ms=500)


# ── Chat Endpoint Tests ───────────────────────────────────────

@allure.feature("Chat API")
class TestChatEndpoint:

    @allure.story("Valid Requests")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("TC-F-006: Valid chat request returns HTTP 200")
    def test_chat_valid_request_returns_200(self):
        with allure.step("Prepare valid chat payload"):
            payload = {"message": "Hello!", "session_id": "s001"}
        with allure.step("Send POST to /api/v1/chat"):
            r = requests.post(CHAT_URL, json=payload)
            allure.attach(
                str(r.json()),
                name            = "API Response",
                attachment_type = allure.attachment_type.TEXT,
            )
        with allure.step("Verify HTTP 200 status"):
            assert r.status_code == 200

    @allure.story("Schema Validation")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("TC-F-007: Chat response has required fields")
    def test_chat_response_has_required_fields(self):
        with allure.step("Send valid chat request"):
            r = requests.post(CHAT_URL, json={"message": "Hello!", "session_id": "s002"})
        with allure.step("Verify all required fields present"):
            data = r.json()
            allure.attach(str(data), name="Response Body", attachment_type=allure.attachment_type.TEXT)
            assert_json_keys(data, ["response", "session_id", "latency_ms", "timestamp"])

    @allure.story("Valid Requests")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("TC-F-008: Response field is a non-empty string")
    def test_chat_response_is_string(self):
        with allure.step("Send chat request"):
            r = requests.post(CHAT_URL, json={"message": "Hello!"})
        with allure.step("Verify response is non-empty string"):
            assert isinstance(r.json()["response"], str)
            assert len(r.json()["response"]) > 0

    @allure.story("Session Management")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-F-009: Session ID is preserved in response")
    def test_chat_session_id_preserved(self):
        sid = "test-session-preserve"
        with allure.step(f"Send request with session_id: {sid}"):
            r = requests.post(CHAT_URL, json={"message": "Hello!", "session_id": sid})
        with allure.step("Verify same session_id is returned"):
            assert r.json()["session_id"] == sid

    @allure.story("Session Management")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-F-010: Auto-generates session ID when not provided")
    def test_chat_auto_generates_session_id(self):
        with allure.step("Send request without session_id"):
            r = requests.post(CHAT_URL, json={"message": "Hello!"})
        with allure.step("Verify session_id was auto-generated"):
            assert "session_id" in r.json()
            assert len(r.json()["session_id"]) > 0

    @allure.story("Performance")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-F-011: latency_ms field is a positive number")
    def test_chat_latency_field_is_numeric(self):
        with allure.step("Send chat request"):
            r = requests.post(CHAT_URL, json={"message": "Hello!"})
        with allure.step("Verify latency_ms is a positive number"):
            latency = r.json()["latency_ms"]
            assert isinstance(latency, (int, float))
            assert latency > 0

    @allure.story("Performance")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("TC-F-012: Chat API responds within 2 seconds")
    def test_chat_response_time_under_2s(self):
        with allure.step("Send chat request"):
            r = requests.post(CHAT_URL, json={"message": "Tell me a joke"})
        with allure.step("Verify response under 2000ms"):
            assert_response_time(r, max_ms=2000)

    @allure.story("AI Response Quality")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-F-013: Hello message returns a greeting")
    def test_chat_hello_response_content(self):
        with allure.step("Send 'Hello' message"):
            r = requests.post(CHAT_URL, json={"message": "Hello"})
        with allure.step("Verify response contains greeting keywords"):
            response_text = r.json()["response"].lower()
            greetings = ["hello", "hi", "hey", "assist", "help"]
            assert any(g in response_text for g in greetings)

    @allure.story("AI Response Quality")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-F-014: Joke response passes AI accuracy check")
    def test_chat_joke_response_accuracy(self):
        with allure.step("Send joke request"):
            r = requests.post(CHAT_URL, json={"message": "Tell me a joke"})
        with allure.step("Validate AI response accuracy"):
            result = validator.validate(
                expected = "Why don't scientists trust atoms? Because they make up everything!",
                actual   = r.json()["response"],
            )
            allure.attach(
                f"Accuracy: {result.accuracy_score}\nVerdict: {result.verdict}",
                name            = "AI Validation Result",
                attachment_type = allure.attachment_type.TEXT,
            )
            assert result.verdict in ["PASS", "WARN"]


# ── Session Endpoint Tests ────────────────────────────────────

@allure.feature("Session Management")
class TestSessionEndpoints:

    @allure.story("Get Session")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-F-015: GET session returns 200")
    def test_get_session_returns_200(self):
        with allure.step("Send GET request for a session"):
            r = requests.get(f"{BASE_URL}/api/v1/sessions/test-session-abc")
        with allure.step("Verify HTTP 200"):
            assert r.status_code == 200

    @allure.story("Get Session")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-F-016: Session response has required fields")
    def test_get_session_has_required_fields(self):
        with allure.step("Send GET request for session"):
            r = requests.get(f"{BASE_URL}/api/v1/sessions/abc123")
        with allure.step("Verify session_id and active fields exist"):
            assert_json_keys(r.json(), ["session_id", "active"])

    @allure.story("Delete Session")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-F-017: DELETE session returns 200")
    def test_delete_session_returns_200(self):
        with allure.step("Send DELETE request"):
            r = requests.delete(f"{BASE_URL}/api/v1/sessions/test-delete-session")
        with allure.step("Verify HTTP 200"):
            assert r.status_code == 200

    @allure.story("Delete Session")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-F-018: DELETE response includes confirmation message")
    def test_delete_session_confirmation_message(self):
        with allure.step("Send DELETE request"):
            r = requests.delete(f"{BASE_URL}/api/v1/sessions/session-to-delete")
        with allure.step("Verify confirmation message contains 'deleted'"):
            assert "message" in r.json()
            assert "deleted" in r.json()["message"].lower()


# ── Feedback & History Tests ──────────────────────────────────

@allure.feature("Feedback")
class TestFeedbackAndHistory:

    @allure.story("Submit Feedback")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-F-019: Valid feedback returns HTTP 201")
    def test_feedback_valid_returns_201(self):
        with allure.step("Submit feedback with rating 5"):
            r = requests.post(
                f"{BASE_URL}/api/v1/feedback",
                json={"session_id": "s001", "rating": 5},
            )
        with allure.step("Verify HTTP 201"):
            assert r.status_code == 201

    @allure.story("Submit Feedback")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-F-020: Feedback response includes feedback_id")
    def test_feedback_returns_feedback_id(self):
        with allure.step("Submit feedback"):
            r = requests.post(
                f"{BASE_URL}/api/v1/feedback",
                json={"session_id": "s001", "rating": 4, "comment": "Great!"},
            )
        with allure.step("Verify feedback_id in response"):
            assert "feedback_id" in r.json()

    @allure.feature("Chat History")
    @allure.story("Get History")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-F-021: History endpoint returns 200")
    def test_history_returns_200(self):
        with allure.step("Send GET request for history"):
            r = requests.get(f"{BASE_URL}/api/v1/history/session-abc")
        with allure.step("Verify HTTP 200"):
            assert r.status_code == 200

    @allure.feature("Chat History")
    @allure.story("Get History")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-F-022: History response contains messages list")
    def test_history_contains_messages(self):
        with allure.step("Send GET request for history"):
            r = requests.get(f"{BASE_URL}/api/v1/history/session-abc")
        with allure.step("Verify messages list exists"):
            data = r.json()
            assert "messages" in data
            assert isinstance(data["messages"], list)