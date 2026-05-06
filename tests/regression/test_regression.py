"""
Regression Test Suite
=====================
Ensures previously fixed bugs do not reappear.
These tests reference specific bug IDs for traceability.

Run: pytest tests/regression/test_regression.py -v
"""

import pytest
import requests
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.validator.response_validator import ResponseValidator

BASE_URL = "http://localhost:5001"
CHAT_URL = f"{BASE_URL}/api/v1/chat"

validator = ResponseValidator()


class TestRegressionSuite:

    # ── BUG-001: Empty message returned 200 (fixed → now 422) ────────────────

    def test_reg_empty_message_fixed(self):
        """REG-001 (BUG-001): Empty message must return 422, not 200."""
        r = requests.post(CHAT_URL, json={"message": ""})
        assert r.status_code == 422, (
            "REGRESSION: Empty message returned 200 again. BUG-001 has resurfaced."
        )

    # ── BUG-002: Missing session_id caused a 500 ──────────────────────────────

    def test_reg_missing_session_id_no_crash(self):
        """REG-002 (BUG-002): Missing session_id must not cause 500."""
        r = requests.post(CHAT_URL, json={"message": "Hello"})
        assert r.status_code != 500, (
            "REGRESSION: Missing session_id caused a 500. BUG-002 has resurfaced."
        )
        assert r.status_code == 200

    # ── BUG-003: Invalid Content-Type caused unhandled exception ─────────────

    def test_reg_wrong_content_type_no_crash(self):
        """REG-003 (BUG-003): Wrong Content-Type must return 415, not 500."""
        r = requests.post(
            CHAT_URL,
            data   = "hello",
            headers= {"Content-Type": "text/plain"},
        )
        assert r.status_code == 415, (
            "REGRESSION: Wrong Content-Type caused a crash. BUG-003 resurfaced."
        )

    # ── BUG-004: Oversized payload caused memory spike, no 413 ───────────────

    def test_reg_oversized_payload_returns_413(self):
        """REG-004 (BUG-004): Payload over 1000 chars must return 413."""
        r = requests.post(CHAT_URL, json={"message": "A" * 2000})
        assert r.status_code == 413, (
            "REGRESSION: Oversized payload did not return 413. BUG-004 resurfaced."
        )

    # ── BUG-005: Toxic content returned 200 with response ────────────────────

    def test_reg_toxic_content_blocked(self):
        """REG-005 (BUG-005): Toxic messages must return 400, not 200."""
        r = requests.post(CHAT_URL, json={"message": "I want to harm someone"})
        assert r.status_code == 400, (
            "REGRESSION: Toxic content was not blocked. BUG-005 resurfaced."
        )

    # ── Accuracy regression: AI response quality ─────────────────────────────

    def test_reg_hello_response_quality(self):
        """REG-006: 'Hello' response must maintain ≥ 60% accuracy score."""
        r = requests.post(CHAT_URL, json={"message": "Hello"})
        result = validator.validate(
            expected = "Hello! How can I assist you today?",
            actual   = r.json()["response"],
        )
        assert result.accuracy_score >= 0.60, (
            f"REGRESSION: Response quality degraded to {result.accuracy_score:.0%}. "
            "Minimum was 60%."
        )

    def test_reg_joke_response_quality(self):
        """REG-007: Joke response must maintain ≥ 40% accuracy score."""
        r = requests.post(CHAT_URL, json={"message": "joke"})
        result = validator.validate(
            expected = "Why don't scientists trust atoms? Because they make up everything!",
            actual   = r.json()["response"],
        )
        assert result.accuracy_score >= 0.40, (
            f"REGRESSION: Joke response quality dropped to {result.accuracy_score:.0%}."
        )

    # ── API contract regression ───────────────────────────────────────────────

    def test_reg_response_schema_unchanged(self):
        """REG-008: Chat response schema must still contain all original fields."""
        r = requests.post(CHAT_URL, json={"message": "Hello"})
        data = r.json()
        required_fields = ["response", "session_id", "latency_ms", "timestamp"]
        for field in required_fields:
            assert field in data, (
                f"REGRESSION: Field '{field}' was removed from the response schema."
            )

    def test_reg_health_endpoint_still_works(self):
        """REG-009: /health endpoint must remain available and return 200."""
        r = requests.get(f"{BASE_URL}/health")
        assert r.status_code == 200, (
            "REGRESSION: /health endpoint is broken."
        )

    def test_reg_feedback_endpoint_still_requires_rating(self):
        """REG-010: Feedback without rating must still return 422."""
        r = requests.post(
            f"{BASE_URL}/api/v1/feedback",
            json={"session_id": "s001"},   # Missing rating
        )
        assert r.status_code == 422, (
            "REGRESSION: Feedback accepted without 'rating'. Validation was removed."
        )
