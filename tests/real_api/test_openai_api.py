"""
Real OpenAI API Test Suite
===========================
10 test cases that hit the live OpenAI API.

These tests are AUTOMATICALLY SKIPPED in CI because no OPENAI_API_KEY
secret is set there. They only run locally when you have a real key.

Run locally:
    # 1. Add your key to .env:
    #    OPENAI_API_KEY=sk-xxxxxxxxxxxx
    # 2. Run:
    pytest tests/real_api/test_openai_api.py -v

Skip behaviour:
    If OPENAI_API_KEY is missing → entire module is skipped with a clear message.
"""

import os
import sys
import time
import pytest

# ── Make project root importable ─────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from dotenv import load_dotenv
load_dotenv()

from src.real_api.openai_client import OpenAIChatClient, OpenAIClientError

# ── Skip entire module when OPENAI_API_KEY is absent ─────────
# This is what makes CI safe — the key is never stored in GitHub secrets
# for this project, so CI skips gracefully.
_API_KEY_PRESENT = bool(os.getenv("OPENAI_API_KEY"))

pytestmark = pytest.mark.skipif(
    not _API_KEY_PRESENT,
    reason="OPENAI_API_KEY not set — skipping real API tests (safe for CI)",
)


# ── Shared client fixture ─────────────────────────────────────

@pytest.fixture(scope="module")
def client() -> OpenAIChatClient:
    """Single client instance shared across all tests in this module."""
    return OpenAIChatClient()


# ── TC-OAI-001: Client initialises without error ─────────────

def test_client_initialises_without_error():
    """TC-OAI-001: OpenAIChatClient() must not raise when key is present."""
    c = OpenAIChatClient()
    assert c is not None
    assert c.api_key is not None


# ── TC-OAI-002: Basic greeting returns non-empty string ──────

def test_basic_greeting_returns_non_empty_string(client):
    """TC-OAI-002: A simple 'Hello' message returns a non-empty reply."""
    result = client.chat("Hello!")
    assert isinstance(result["response"], str)
    assert len(result["response"].strip()) > 0


# ── TC-OAI-003: Response dict contains all required keys ─────

def test_response_dict_has_all_required_keys(client):
    """TC-OAI-003: chat() return dict must contain all 7 expected keys."""
    result = client.chat("Say one word.")
    required_keys = [
        "response", "latency_ms", "tokens_used",
        "prompt_tokens", "reply_tokens", "model", "finish_reason",
    ]
    for key in required_keys:
        assert key in result, f"Missing key in response: {key}"


# ── TC-OAI-004: Latency is a positive number ─────────────────

def test_latency_is_positive_number(client):
    """TC-OAI-004: latency_ms must be a float/int greater than 0."""
    result = client.chat("Say one word.")
    assert isinstance(result["latency_ms"], (int, float))
    assert result["latency_ms"] > 0


# ── TC-OAI-005: Token counts are positive integers ───────────

def test_token_counts_are_positive(client):
    """TC-OAI-005: tokens_used, prompt_tokens, reply_tokens must all be > 0."""
    result = client.chat("Say one word.")
    assert result["tokens_used"]   > 0, "tokens_used should be > 0"
    assert result["prompt_tokens"] > 0, "prompt_tokens should be > 0"
    assert result["reply_tokens"]  > 0, "reply_tokens should be > 0"


# ── TC-OAI-006: model field is a non-empty string ────────────

def test_model_field_is_non_empty_string(client):
    """TC-OAI-006: model field must be a non-empty string (e.g. 'gpt-3.5-turbo')."""
    result = client.chat("Say one word.")
    assert isinstance(result["model"], str)
    assert len(result["model"]) > 0


# ── TC-OAI-007: finish_reason is 'stop' for normal reply ─────

def test_finish_reason_is_stop_for_short_reply(client):
    """TC-OAI-007: A short message should finish with reason 'stop'."""
    result = client.chat("Say the word 'yes'.", max_tokens=10)
    assert result["finish_reason"] == "stop", (
        f"Expected 'stop', got {result['finish_reason']!r}"
    )


# ── TC-OAI-008: Factual question about a capital city ────────

def test_capital_city_question(client):
    """TC-OAI-008: 'Capital of France?' must mention 'Paris' in the reply."""
    result = client.chat("What is the capital of France? Answer in one word.")
    assert "paris" in result["response"].lower(), (
        f"Expected 'paris' in response, got: {result['response']!r}"
    )


# ── TC-OAI-009: Custom system prompt is respected ────────────

def test_custom_system_prompt_is_respected(client):
    """TC-OAI-009: Custom system prompt 'Always reply with HELLO.' is obeyed."""
    result = client.chat(
        message       = "What is 2+2?",
        system_prompt = "No matter what the user asks, always reply with exactly: HELLO.",
        max_tokens    = 20,
    )
    assert "hello" in result["response"].lower(), (
        f"System prompt ignored. Got: {result['response']!r}"
    )


# ── TC-OAI-010: Invalid API key raises OpenAIClientError ─────

def test_invalid_api_key_raises_client_error():
    """TC-OAI-010: A bad API key must raise OpenAIClientError with status 401."""
    bad_client = OpenAIChatClient(api_key="sk-invalid-key-for-testing-only")
    with pytest.raises(OpenAIClientError) as exc_info:
        bad_client.chat("Hello")
    assert exc_info.value.status_code == 401, (
        f"Expected HTTP 401, got {exc_info.value.status_code}"
    )
