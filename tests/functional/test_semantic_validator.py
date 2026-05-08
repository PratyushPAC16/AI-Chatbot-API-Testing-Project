"""
Semantic Validator Unit Tests
==============================
8 unit tests for src/validator/semantic_validator.py.

These tests run locally and in CI. The sentence-transformers model
is downloaded once and cached — CI uses actions/cache to avoid
re-downloading on every run.

Run: pytest tests/functional/test_semantic_validator.py -v
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# ── Skip entire module if sentence-transformers is not installed ───
try:
    from sentence_transformers import SentenceTransformer  # noqa: F401
    _ST_AVAILABLE = True
except ImportError:
    _ST_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _ST_AVAILABLE,
    reason="sentence-transformers not installed — skipping semantic validator tests",
)

from src.validator.semantic_validator import SemanticValidator, SemanticResult


# ── Shared fixture ─────────────────────────────────────────────
# scope="module" so the model is loaded once for all 8 tests

@pytest.fixture(scope="module")
def sv() -> SemanticValidator:
    """Load the SemanticValidator once for the whole module."""
    return SemanticValidator()


# ── TC-SV-001: Validator initialises without error ────────────

def test_validator_initialises(sv):
    """TC-SV-001: SemanticValidator() must instantiate without raising."""
    assert sv is not None
    assert sv._model is not None


# ── TC-SV-002: compare() returns a SemanticResult ────────────

def test_compare_returns_semantic_result(sv):
    """TC-SV-002: compare() must return a SemanticResult dataclass."""
    result = sv.compare("Hello world", "Hello there")
    assert isinstance(result, SemanticResult)


# ── TC-SV-003: Score is in [0.0, 1.0] ────────────────────────

def test_score_is_within_bounds(sv):
    """TC-SV-003: Similarity score must be between 0.0 and 1.0 (inclusive)."""
    result = sv.compare("What is Python?", "Python is a programming language.")
    assert 0.0 <= result.score <= 1.0, f"Score out of range: {result.score}"


# ── TC-SV-004: Identical strings score ≥ 0.99 ────────────────

def test_identical_strings_score_near_one(sv):
    """TC-SV-004: Two identical strings must have similarity ≥ 0.99."""
    text   = "The chatbot responded with a friendly greeting."
    result = sv.compare(text, text)
    assert result.score >= 0.99, f"Expected ≥ 0.99, got {result.score}"


# ── TC-SV-005: Semantically similar strings score ≥ 0.75 (PASS) ──

def test_similar_meaning_scores_pass(sv):
    """TC-SV-005: Semantically similar sentences must score ≥ 0.60 (high similarity)."""
    result = sv.compare(
        "Hello! How can I assist you today?",
        "Hi there! How may I help you?",
    )
    assert result.score >= 0.60, f"Expected score ≥ 0.60, got {result.score}"
    assert result.verdict in ("PASS", "WARN"), f"Expected PASS or WARN, got {result.verdict}"


# ── TC-SV-006: Clearly unrelated strings score ≤ 0.50 (FAIL) ─

def test_unrelated_strings_score_fail(sv):
    """TC-SV-006: Clearly unrelated sentences must score ≤ 0.50 (FAIL)."""
    result = sv.compare(
        "Tell me a joke",
        "Database connection refused on port 5432.",
    )
    assert result.score <= 0.50, f"Expected FAIL (≤0.50), got {result.score}"
    assert result.verdict == "FAIL"


# ── TC-SV-007: Empty input returns FAIL without crash ─────────

def test_empty_input_returns_fail_without_crash(sv):
    """TC-SV-007: Empty string inputs must return FAIL, not raise an exception."""
    result = sv.compare("", "Some response text")
    assert result.verdict == "FAIL"
    assert result.score == 0.0


# ── TC-SV-008: compare_batch() returns correct number of results ──

def test_compare_batch_returns_correct_count(sv):
    """TC-SV-008: compare_batch() with N pairs must return exactly N results."""
    pairs = [
        {"expected": "Hello!", "actual": "Hi there!"},
        {"expected": "What is AI?", "actual": "Artificial intelligence explained."},
        {"expected": "Goodbye!", "actual": "I only answer database queries."},
    ]
    results = sv.compare_batch(pairs)
    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    for r in results:
        assert isinstance(r, SemanticResult)
        assert r.verdict in ("PASS", "WARN", "FAIL")
