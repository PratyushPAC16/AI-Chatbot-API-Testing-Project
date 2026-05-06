"""
conftest.py
===========
Shared pytest fixtures for the entire test suite.
All test files import these automatically via pytest's fixture injection.
"""

import pytest
import requests
from src.logger.test_logger import TestLogger
from src.validator.response_validator import ResponseValidator

# ─── Base URL ─────────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:5001"


# ─── Session-scoped fixtures (created once per test session) ──────────────────

@pytest.fixture(scope="session")
def base_url():
    """Return the mock server base URL."""
    return BASE_URL


@pytest.fixture(scope="session")
def api_client():
    """
    A persistent requests.Session with shared headers.
    Reusing a session improves performance across 50+ tests.
    """
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Accept":       "application/json",
        "X-Test-Run":   "pytest-automation",
    })
    yield session
    session.close()


@pytest.fixture(scope="session")
def logger():
    """Shared TestLogger instance. Writes JSON + SQLite logs."""
    _logger = TestLogger()
    yield _logger
    _logger.print_summary()     # Print summary at end of session


@pytest.fixture(scope="session")
def validator():
    """Shared ResponseValidator instance."""
    return ResponseValidator()


# ─── Function-scoped fixtures ─────────────────────────────────────────────────

@pytest.fixture
def chat_endpoint(base_url):
    return f"{base_url}/api/v1/chat"


@pytest.fixture
def health_endpoint(base_url):
    return f"{base_url}/health"


@pytest.fixture
def valid_payload():
    """A standard valid chat payload."""
    return {"message": "Hello, how are you?", "session_id": "test-session-001"}


@pytest.fixture
def large_payload():
    """A payload near the max allowed length."""
    return {"message": "A" * 999, "session_id": "test-session-large"}


@pytest.fixture
def oversized_payload():
    """A payload exceeding the max allowed length."""
    return {"message": "X" * 1500, "session_id": "test-session-oversized"}


@pytest.fixture
def toxic_payload():
    """A payload containing a toxic keyword."""
    return {"message": "I want to harm someone", "session_id": "test-toxic"}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def assert_response_time(response, max_ms: float = 2000):
    """Assert that response time is below max_ms milliseconds."""
    elapsed_ms = response.elapsed.total_seconds() * 1000
    assert elapsed_ms < max_ms, (
        f"Response too slow: {elapsed_ms:.0f}ms (limit: {max_ms}ms)"
    )

def assert_json_keys(data: dict, required_keys: list):
    """Assert all required keys are present in the JSON response."""
    for key in required_keys:
        assert key in data, f"Missing required key in response: '{key}'"
