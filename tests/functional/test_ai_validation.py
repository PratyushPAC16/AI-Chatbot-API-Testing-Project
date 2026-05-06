"""
AI Response Validation Tests
=============================
Tests the ResponseValidator itself AND uses it to score actual chatbot responses.
Generates an accuracy report at the end.

Run: pytest tests/functional/test_ai_validation.py -v -s
"""

import json
import pytest
import requests
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.validator.response_validator import ResponseValidator

BASE_URL = "http://localhost:5001"
CHAT_URL = f"{BASE_URL}/api/v1/chat"

validator = ResponseValidator()

# ─── Validation unit tests ────────────────────────────────────────────────────

class TestResponseValidatorUnit:
    """Unit tests for the ResponseValidator component itself."""

    def test_identical_strings_score_1(self):
        """Identical expected and actual should score 1.0."""
        result = validator.validate("Hello world", "Hello world")
        assert result.semantic_score == 1.0
        assert result.keyword_score  == 1.0
        assert result.accuracy_score == 1.0

    def test_completely_different_strings_score_low(self):
        """Completely different texts should score near 0."""
        result = validator.validate("Hello greetings welcome", "Goodbye farewell exit")
        assert result.accuracy_score < 0.3

    def test_partial_match_gives_mid_score(self):
        """Partial keyword overlap gives intermediate score."""
        result = validator.validate(
            "Hello! How can I assist you today?",
            "Hello! What can I do?",
        )
        assert 0.2 < result.accuracy_score < 1.0

    def test_verdict_pass_when_high_accuracy(self):
        """PASS verdict for high-accuracy response."""
        result = validator.validate("Hello world today", "Hello world today")
        assert result.verdict == "PASS"

    def test_verdict_fail_when_low_accuracy(self):
        """FAIL verdict for very low accuracy."""
        result = validator.validate(
            "The quick brown fox jumps over the lazy dog",
            "Computer science is great",
        )
        assert result.verdict == "FAIL"

    def test_matched_keywords_populated(self):
        """matched_keywords contains words found in both texts."""
        result = validator.validate("hello world assist", "hello assist please")
        assert "hello" in result.matched_keywords
        assert "assist" in result.matched_keywords

    def test_missing_keywords_populated(self):
        """missing_keywords contains words from expected not in actual."""
        result = validator.validate("hello world assist", "goodbye")
        assert len(result.missing_keywords) > 0

    def test_result_to_dict(self):
        """Result serializes to a dict cleanly."""
        result = validator.validate("hello", "hi there")
        d = result.to_dict()
        assert "accuracy_score" in d
        assert "verdict" in d

    def test_batch_validate_length(self):
        """Batch validation returns same number of results as inputs."""
        pairs = [
            {"expected": "Hello", "actual": "Hi"},
            {"expected": "Bye",   "actual": "Goodbye"},
        ]
        results = validator.validate_batch(pairs)
        assert len(results) == len(pairs)

    def test_batch_summary_structure(self):
        """Batch summary contains all required keys."""
        pairs = [
            {"expected": "Hello world", "actual": "Hello world"},
            {"expected": "Goodbye",     "actual": "Completely unrelated text here"},
        ]
        results = validator.validate_batch(pairs)
        summary = validator.batch_summary(results)
        for key in ["total", "passed", "failed", "pass_rate", "average_accuracy"]:
            assert key in summary


# ─── Integration: validate actual API responses ───────────────────────────────

# Define test scenarios: (input_message, expected_response_text, min_accuracy)
VALIDATION_SCENARIOS = [
    ("Hello",           "Hello! How can I assist you today?",                   0.55),
    ("hi",              "Hi there! What can I help you with?",                  0.55),
    ("help",            "I can help you with questions, information",            0.40),
    ("joke",            "Why don't scientists trust atoms? Because they make up everything!", 0.50),
    ("bye",             "Goodbye! Have a great day!",                            0.60),
    ("weather",         "I don't have real-time data",                           0.30),
    ("what is the time","The current server time",                               0.25),
    ("random message",  "I understand your query",                               0.30),
]


class TestApiResponseAccuracy:
    """Integration tests: call the chatbot and score its actual responses."""

    accuracy_report = []   # Collected across all tests for final report

    @pytest.mark.parametrize("message, expected_response, min_accuracy", VALIDATION_SCENARIOS)
    def test_response_accuracy(self, message, expected_response, min_accuracy):
        """Validate chatbot accuracy for each scenario."""
        r = requests.post(CHAT_URL, json={"message": message})
        assert r.status_code == 200, f"API returned {r.status_code} for '{message}'"

        actual = r.json().get("response", "")
        result = validator.validate(expected_response, actual)

        # Store for report
        TestApiResponseAccuracy.accuracy_report.append({
            "input":          message,
            "expected":       expected_response[:60] + "...",
            "actual":         actual[:60] + "...",
            "accuracy":       result.accuracy_score,
            "verdict":        result.verdict,
        })

        print(f"\n  [{result.verdict}] '{message}' → accuracy={result.accuracy_score:.0%}")

        assert result.accuracy_score >= min_accuracy, (
            f"Response accuracy for '{message}' is {result.accuracy_score:.0%}, "
            f"minimum required: {min_accuracy:.0%}.\n"
            f"  Expected: {expected_response}\n"
            f"  Actual:   {actual}"
        )

    @classmethod
    def teardown_class(cls):
        """Print accuracy report after all tests in this class run."""
        report = cls.accuracy_report
        if not report:
            return

        avg = sum(r["accuracy"] for r in report) / len(report)
        passed = sum(1 for r in report if r["verdict"] == "PASS")

        print("\n\n" + "═" * 60)
        print("  AI RESPONSE ACCURACY REPORT")
        print("═" * 60)
        for row in report:
            bar = "█" * int(row["accuracy"] * 20) + "░" * (20 - int(row["accuracy"] * 20))
        print(f"  {'Input':<18} {'Accuracy':>8}  {'Verdict':<6}")
        print("  " + "-" * 40)
        for row in report:
            print(f"  {row['input']:<18} {row['accuracy']:>7.0%}  {row['verdict']:<6}")
        print("  " + "-" * 40)
        print(f"  Average accuracy : {avg:.0%}")
        print(f"  Pass rate        : {passed}/{len(report)}")
        print("═" * 60 + "\n")

        # Save report to file
        import os
        os.makedirs("reports", exist_ok=True)
        with open("reports/accuracy_report.json", "w") as f:
            json.dump({
                "average_accuracy": round(avg, 4),
                "pass_rate":        f"{passed}/{len(report)}",
                "scenarios":        report,
            }, f, indent=2)
        print("  📄 Report saved to reports/accuracy_report.json")
