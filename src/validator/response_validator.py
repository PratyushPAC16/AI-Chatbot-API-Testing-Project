"""
AI Response Validator
=====================
Validates chatbot responses using:
  1. Keyword matching      – fast, rule-based
  2. Cosine similarity     – semantic similarity via TF-IDF vectors
  3. Combined accuracy score

Usage:
    validator = ResponseValidator()
    result = validator.validate("Hello there!", "Hello! How can I assist you today?")
    print(result)
"""

import re
import math
import json
from collections import Counter
from dataclasses import dataclass, asdict
from typing import Optional


# ─── Data class for validation results ──────────────────────────────────────

@dataclass
class ValidationResult:
    expected:           str
    actual:             str
    keyword_score:      float   # 0.0 – 1.0
    semantic_score:     float   # 0.0 – 1.0
    accuracy_score:     float   # weighted combined score
    matched_keywords:   list
    missing_keywords:   list
    verdict:            str     # PASS / WARN / FAIL
    details:            str

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ─── Validator ───────────────────────────────────────────────────────────────

class ResponseValidator:
    """
    Validates chatbot responses against expected outputs.
    Combines keyword matching and cosine similarity for an accuracy score.
    """

    # Thresholds
    PASS_THRESHOLD = 0.70   # ≥ 70 % → PASS
    WARN_THRESHOLD = 0.40   # 40–69 % → WARN
                            # < 40 %  → FAIL

    # Weight for combining scores
    KEYWORD_WEIGHT  = 0.40
    SEMANTIC_WEIGHT = 0.60

    # ── Text helpers ─────────────────────────────────────────────────────────

    def _tokenize(self, text: str) -> list[str]:
        """Lowercase, strip punctuation, split into tokens."""
        text = text.lower()
        text = re.sub(r"[^\w\s]", "", text)
        return text.split()

    def _remove_stopwords(self, tokens: list[str]) -> list[str]:
        stopwords = {
            "the","a","an","is","it","in","on","at","to","for","of","and",
            "or","but","with","this","that","i","you","we","he","she","they",
            "can","will","be","have","has","do","does","was","were","are","am"
        }
        return [t for t in tokens if t not in stopwords]

    # ── Keyword matching ──────────────────────────────────────────────────────

    def keyword_match(self, expected: str, actual: str) -> tuple[float, list, list]:
        """
        Extracts keywords from 'expected' and checks how many appear in 'actual'.

        Returns:
            score           – fraction of expected keywords found in actual
            matched         – keywords found
            missing         – keywords not found
        """
        exp_tokens    = set(self._remove_stopwords(self._tokenize(expected)))
        actual_tokens = set(self._tokenize(actual))

        if not exp_tokens:
            return 1.0, [], []

        matched = sorted(exp_tokens & actual_tokens)
        missing = sorted(exp_tokens - actual_tokens)
        score   = len(matched) / len(exp_tokens)

        return round(score, 4), matched, missing

    # ── TF-IDF cosine similarity ──────────────────────────────────────────────

    def _tf(self, tokens: list[str]) -> dict[str, float]:
        """Term frequency for a list of tokens."""
        count = Counter(tokens)
        total = len(tokens) or 1
        return {word: freq / total for word, freq in count.items()}

    def _cosine_similarity(self, text_a: str, text_b: str) -> float:
        """
        Computes cosine similarity between two texts using TF vectors.
        (IDF skipped for simplicity; suitable for short chatbot responses.)
        """
        tokens_a = self._remove_stopwords(self._tokenize(text_a))
        tokens_b = self._remove_stopwords(self._tokenize(text_b))

        if not tokens_a or not tokens_b:
            return 0.0

        tf_a = self._tf(tokens_a)
        tf_b = self._tf(tokens_b)

        vocab     = set(tf_a) | set(tf_b)
        vec_a     = [tf_a.get(w, 0.0) for w in vocab]
        vec_b     = [tf_b.get(w, 0.0) for w in vocab]

        dot       = sum(a * b for a, b in zip(vec_a, vec_b))
        mag_a     = math.sqrt(sum(a ** 2 for a in vec_a))
        mag_b     = math.sqrt(sum(b ** 2 for b in vec_b))

        if mag_a == 0 or mag_b == 0:
            return 0.0

        return round(dot / (mag_a * mag_b), 4)

    # ── Combined validation ───────────────────────────────────────────────────

    def validate(
        self,
        expected: str,
        actual:   str,
        keyword_weight:  Optional[float] = None,
        semantic_weight: Optional[float] = None,
    ) -> ValidationResult:
        """
        Validates actual response against expected.

        Args:
            expected:        The ideal/expected chatbot response.
            actual:          The real chatbot response to evaluate.
            keyword_weight:  Override default keyword weight.
            semantic_weight: Override default semantic weight.

        Returns:
            ValidationResult dataclass with full breakdown.
        """
        kw  = keyword_weight  or self.KEYWORD_WEIGHT
        sw  = semantic_weight or self.SEMANTIC_WEIGHT

        # Run both checks
        keyword_score, matched, missing = self.keyword_match(expected, actual)
        semantic_score = self._cosine_similarity(expected, actual)

        # Weighted combined score
        accuracy = round(kw * keyword_score + sw * semantic_score, 4)

        # Verdict
        if accuracy >= self.PASS_THRESHOLD:
            verdict = "PASS"
            details = f"Response meets quality threshold ({accuracy:.0%} accuracy)."
        elif accuracy >= self.WARN_THRESHOLD:
            verdict = "WARN"
            details = (
                f"Response is partially acceptable ({accuracy:.0%}). "
                f"Missing keywords: {missing or 'none'}."
            )
        else:
            verdict = "FAIL"
            details = (
                f"Response quality is too low ({accuracy:.0%}). "
                f"Missing keywords: {missing}. "
                "Semantic similarity is insufficient."
            )

        return ValidationResult(
            expected        = expected,
            actual          = actual,
            keyword_score   = keyword_score,
            semantic_score  = semantic_score,
            accuracy_score  = accuracy,
            matched_keywords= matched,
            missing_keywords= missing,
            verdict         = verdict,
            details         = details,
        )

    # ── Batch validation ──────────────────────────────────────────────────────

    def validate_batch(self, pairs: list[dict]) -> list[ValidationResult]:
        """
        Validate multiple (expected, actual) pairs at once.

        Args:
            pairs: List of {"expected": ..., "actual": ...} dicts.

        Returns:
            List of ValidationResult objects.
        """
        results = []
        for pair in pairs:
            result = self.validate(pair["expected"], pair["actual"])
            results.append(result)
        return results

    def batch_summary(self, results: list[ValidationResult]) -> dict:
        """Summarise a batch run."""
        total  = len(results)
        passed = sum(1 for r in results if r.verdict == "PASS")
        warned = sum(1 for r in results if r.verdict == "WARN")
        failed = sum(1 for r in results if r.verdict == "FAIL")
        avg    = round(sum(r.accuracy_score for r in results) / total, 4) if total else 0

        return {
            "total":          total,
            "passed":         passed,
            "warned":         warned,
            "failed":         failed,
            "pass_rate":      f"{passed/total:.0%}" if total else "0%",
            "average_accuracy": avg,
        }


# ─── CLI demo ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    validator = ResponseValidator()

    test_pairs = [
        {
            "expected": "Hello! How can I assist you today?",
            "actual":   "Hello! How can I help you today?",
        },
        {
            "expected": "Goodbye! Have a great day!",
            "actual":   "See you later! Bye!",
        },
        {
            "expected": "I can answer questions about weather, news, and more.",
            "actual":   "I only tell jokes.",
        },
    ]

    results = validator.validate_batch(test_pairs)
    for i, result in enumerate(results, 1):
        print(f"\n── Test {i} ──────────────────────────────")
        print(f"  Expected : {result.expected}")
        print(f"  Actual   : {result.actual}")
        print(f"  Keyword  : {result.keyword_score:.0%}")
        print(f"  Semantic : {result.semantic_score:.0%}")
        print(f"  Accuracy : {result.accuracy_score:.0%}")
        print(f"  Verdict  : {result.verdict}")
        print(f"  Details  : {result.details}")

    print("\n── Batch Summary ──────────────────────────")
    print(json.dumps(validator.batch_summary(results), indent=2))
