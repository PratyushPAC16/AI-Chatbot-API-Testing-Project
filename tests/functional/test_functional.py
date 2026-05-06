"""
Functional Test Suite
=====================
Tests core chatbot API functionality.
Covers: health checks, chat endpoint, session management, feedback, history.

Run: pytest tests/functional/test_functional.py -v
"""

import pytest
import requests
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.conftest import assert_response_time, assert_json_keys
from src.logger.test_logger import TestLogger, TestLogEntry, TestStatus, BugReport, Severity
from src.validator.response_validator import ResponseValidator

BASE_URL = "http://localhost:5001"


# ─── TC-F-001 to TC-F-005: Health Check ──────────────────────────────────────

class TestHealthEndpoint:

    def test_health_returns_200(self):
        """TC-F-001: Health endpoint returns HTTP 200."""
        r = requests.get(f"{BASE_URL}/health")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"

    def test_health_response_is_json(self):
        """TC-F-002: Health endpoint returns valid JSON."""
        r = requests.get(f"{BASE_URL}/health")
        assert r.headers["Content-Type"].startswith("application/json")
        data = r.json()
        assert isinstance(data, dict)

    def test_health_has_required_fields(self):
        """TC-F-003: Health response contains status, timestamp, version."""
        r = requests.get(f"{BASE_URL}/health")
        data = r.json()
        assert_json_keys(data, ["status", "timestamp", "version"])

    def test_health_status_is_healthy(self):
        """TC-F-004: Health status value is 'healthy'."""
        r = requests.get(f"{BASE_URL}/health")
        assert r.json()["status"] == "healthy"

    def test_health_response_time(self):
        """TC-F-005: Health endpoint responds within 500ms."""
        r = requests.get(f"{BASE_URL}/health")
        assert_response_time(r, max_ms=500)


# ─── TC-F-006 to TC-F-014: Chat Endpoint ─────────────────────────────────────

class TestChatEndpoint:

    def test_chat_valid_request_returns_200(self):
        """TC-F-006: Valid chat request returns HTTP 200."""
        r = requests.post(
            f"{BASE_URL}/api/v1/chat",
            json={"message": "Hello!", "session_id": "s001"},
        )
        assert r.status_code == 200

    def test_chat_response_has_required_fields(self):
        """TC-F-007: Chat response contains response, session_id, latency_ms."""
        r = requests.post(
            f"{BASE_URL}/api/v1/chat",
            json={"message": "Hello!", "session_id": "s002"},
        )
        data = r.json()
        assert_json_keys(data, ["response", "session_id", "latency_ms", "timestamp"])

    def test_chat_response_is_string(self):
        """TC-F-008: 'response' field must be a non-empty string."""
        r = requests.post(
            f"{BASE_URL}/api/v1/chat",
            json={"message": "Hello!"},
        )
        assert isinstance(r.json()["response"], str)
        assert len(r.json()["response"]) > 0

    def test_chat_session_id_preserved(self):
        """TC-F-009: Session ID sent in request is returned in response."""
        sid = "test-session-preserve"
        r = requests.post(
            f"{BASE_URL}/api/v1/chat",
            json={"message": "Hello!", "session_id": sid},
        )
        assert r.json()["session_id"] == sid

    def test_chat_auto_generates_session_id(self):
        """TC-F-010: If no session_id is provided, one is generated."""
        r = requests.post(
            f"{BASE_URL}/api/v1/chat",
            json={"message": "Hello!"},
        )
        assert "session_id" in r.json()
        assert len(r.json()["session_id"]) > 0

    def test_chat_latency_field_is_numeric(self):
        """TC-F-011: latency_ms field is a positive number."""
        r = requests.post(
            f"{BASE_URL}/api/v1/chat",
            json={"message": "Hello!"},
        )
        latency = r.json()["latency_ms"]
        assert isinstance(latency, (int, float))
        assert latency > 0

    def test_chat_response_time_under_2s(self):
        """TC-F-012: API responds within 2 seconds for valid input."""
        r = requests.post(
            f"{BASE_URL}/api/v1/chat",
            json={"message": "Tell me a joke"},
        )
        assert_response_time(r, max_ms=2000)

    def test_chat_hello_response_content(self):
        """TC-F-013: 'Hello' message returns a greeting response."""
        r = requests.post(
            f"{BASE_URL}/api/v1/chat",
            json={"message": "Hello"},
        )
        response_text = r.json()["response"].lower()
        greetings = ["hello", "hi", "hey", "assist", "help"]
        assert any(g in response_text for g in greetings), (
            f"Expected a greeting in response, got: {r.json()['response']}"
        )

    def test_chat_joke_response(self):
        """TC-F-014: 'joke' message returns a joke."""
        r = requests.post(
            f"{BASE_URL}/api/v1/chat",
            json={"message": "Tell me a joke"},
        )
        assert r.status_code == 200
        # AI Validation
        validator = ResponseValidator()
        result = validator.validate(
            expected="Why don't scientists trust atoms? Because they make up everything!",
            actual=r.json()["response"],
        )
        assert result.verdict in ["PASS", "WARN"], (
            f"Joke response accuracy too low: {result.accuracy_score}"
        )


# ─── TC-F-015 to TC-F-018: Sessions ──────────────────────────────────────────

class TestSessionEndpoints:

    def test_get_session_returns_200(self):
        """TC-F-015: GET session returns 200 for a valid session ID."""
        r = requests.get(f"{BASE_URL}/api/v1/sessions/test-session-abc")
        assert r.status_code == 200

    def test_get_session_has_required_fields(self):
        """TC-F-016: Session response contains session_id, active."""
        r = requests.get(f"{BASE_URL}/api/v1/sessions/abc123")
        assert_json_keys(r.json(), ["session_id", "active"])

    def test_delete_session_returns_200(self):
        """TC-F-017: DELETE session returns 200."""
        r = requests.delete(f"{BASE_URL}/api/v1/sessions/test-delete-session")
        assert r.status_code == 200

    def test_delete_session_confirmation_message(self):
        """TC-F-018: DELETE session response includes confirmation message."""
        r = requests.delete(f"{BASE_URL}/api/v1/sessions/session-to-delete")
        assert "message" in r.json()
        assert "deleted" in r.json()["message"].lower()


# ─── TC-F-019 to TC-F-022: Feedback & History ────────────────────────────────

class TestFeedbackAndHistory:

    def test_feedback_valid_returns_201(self):
        """TC-F-019: Valid feedback returns HTTP 201."""
        r = requests.post(
            f"{BASE_URL}/api/v1/feedback",
            json={"session_id": "s001", "rating": 5},
        )
        assert r.status_code == 201

    def test_feedback_returns_feedback_id(self):
        """TC-F-020: Feedback response includes a feedback_id."""
        r = requests.post(
            f"{BASE_URL}/api/v1/feedback",
            json={"session_id": "s001", "rating": 4, "comment": "Great!"},
        )
        assert "feedback_id" in r.json()

    def test_history_returns_200(self):
        """TC-F-021: Chat history endpoint returns HTTP 200."""
        r = requests.get(f"{BASE_URL}/api/v1/history/session-abc")
        assert r.status_code == 200

    def test_history_contains_messages(self):
        """TC-F-022: History response contains a messages list."""
        r = requests.get(f"{BASE_URL}/api/v1/history/session-abc")
        data = r.json()
        assert "messages" in data
        assert isinstance(data["messages"], list)
