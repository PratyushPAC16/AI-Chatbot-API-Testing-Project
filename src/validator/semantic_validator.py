"""
Semantic Validator
==================
Uses the sentence-transformers library with the all-MiniLM-L6-v2 model
to compute true semantic similarity between two text strings.

Advantages over TF-IDF cosine similarity:
  - Understands meaning, not just word overlap
  - "Paris is the capital" ≈ "France's capital city is Paris" → high score
  - Runs fully locally — no API key needed

Usage:
    from src.validator.semantic_validator import SemanticValidator

    sv = SemanticValidator()
    result = sv.compare("Paris is the capital of France", "France's capital is Paris")
    print(result)
    # {"score": 0.94, "verdict": "PASS"}

Install:
    pip install sentence-transformers
"""

from __future__ import annotations
from dataclasses import dataclass

# Lazy-import so the module can be imported without the package installed
# (tests will skip gracefully if package is absent)
_IMPORT_ERROR: Exception | None = None
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    _MODEL_AVAILABLE = True
except ImportError as e:
    _IMPORT_ERROR = e
    _MODEL_AVAILABLE = False

# ── Constants ─────────────────────────────────────────────────
MODEL_NAME  = "all-MiniLM-L6-v2"   # ~80 MB, cached after first download

# Verdict thresholds (cosine similarity 0.0 – 1.0)
PASS_THRESHOLD = 0.75   # ≥ 0.75 → PASS
WARN_THRESHOLD = 0.50   # 0.50–0.74 → WARN
                        # < 0.50 → FAIL


@dataclass
class SemanticResult:
    expected: str
    actual:   str
    score:    float   # cosine similarity 0.0 – 1.0
    verdict:  str     # PASS / WARN / FAIL
    details:  str


class SemanticValidator:
    """
    Computes semantic similarity using sentence-transformers.

    The model is loaded once at construction time and reused for all
    subsequent compare() calls (thread-safe, no re-download after first use).
    """

    def __init__(self, model_name: str = MODEL_NAME):
        if not _MODEL_AVAILABLE:
            raise ImportError(
                "sentence-transformers is not installed. "
                "Run: pip install sentence-transformers"
            ) from _IMPORT_ERROR

        # Loading prints progress — suppress for cleaner test output
        import logging
        logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

        self._model = SentenceTransformer(model_name)

    # ── Public API ─────────────────────────────────────────────

    def compare(self, expected: str, actual: str) -> SemanticResult:
        """
        Compute semantic similarity between expected and actual strings.

        Args:
            expected: The reference / ideal response.
            actual:   The chatbot response to evaluate.

        Returns:
            SemanticResult with score (0.0–1.0) and verdict (PASS/WARN/FAIL).
        """
        if not expected.strip() or not actual.strip():
            return SemanticResult(
                expected = expected,
                actual   = actual,
                score    = 0.0,
                verdict  = "FAIL",
                details  = "One or both inputs are empty.",
            )

        embeddings = self._model.encode(
            [expected, actual],
            convert_to_numpy       = True,
            normalize_embeddings   = True,   # unit vectors → dot product = cosine
            show_progress_bar      = False,
        )

        # Cosine similarity = dot product of unit vectors
        score = float(np.dot(embeddings[0], embeddings[1]))
        score = round(max(0.0, min(1.0, score)), 4)   # clamp to [0, 1]

        verdict, details = self._verdict(score)

        return SemanticResult(
            expected = expected,
            actual   = actual,
            score    = score,
            verdict  = verdict,
            details  = details,
        )

    def compare_batch(self, pairs: list[dict]) -> list[SemanticResult]:
        """
        Compare multiple (expected, actual) pairs efficiently in one forward pass.

        Args:
            pairs: [{"expected": "...", "actual": "..."}, ...]

        Returns:
            List of SemanticResult objects.
        """
        if not pairs:
            return []

        texts = []
        for pair in pairs:
            texts.append(pair["expected"])
            texts.append(pair["actual"])

        embeddings = self._model.encode(
            texts,
            convert_to_numpy     = True,
            normalize_embeddings = True,
            show_progress_bar    = False,
        )

        results = []
        for i, pair in enumerate(pairs):
            exp_emb = embeddings[i * 2]
            act_emb = embeddings[i * 2 + 1]
            score   = round(float(max(0.0, min(1.0, np.dot(exp_emb, act_emb)))), 4)
            verdict, details = self._verdict(score)
            results.append(SemanticResult(
                expected = pair["expected"],
                actual   = pair["actual"],
                score    = score,
                verdict  = verdict,
                details  = details,
            ))

        return results

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _verdict(score: float) -> tuple[str, str]:
        if score >= PASS_THRESHOLD:
            return "PASS", f"Semantic similarity is high ({score:.2%})."
        elif score >= WARN_THRESHOLD:
            return "WARN", f"Semantic similarity is moderate ({score:.2%}). Consider reviewing."
        else:
            return "FAIL", f"Semantic similarity is too low ({score:.2%}). Responses differ significantly."


# ── Quick smoke test ──────────────────────────────────────────

if __name__ == "__main__":
    sv = SemanticValidator()

    pairs = [
        # Near-identical
        ("Hello! How can I assist you today?",
         "Hi there! How may I help you?"),

        # Same meaning, different words
        ("What is the capital of France?",
         "Paris is the capital city of France."),

        # Clearly unrelated
        ("Tell me a joke.",
         "The database connection failed at 03:00 UTC."),
    ]

    print(f"Model: {MODEL_NAME}\n")
    for expected, actual in pairs:
        r = sv.compare(expected, actual)
        print(f"  Expected : {r.expected[:60]}")
        print(f"  Actual   : {r.actual[:60]}")
        print(f"  Score    : {r.score:.4f}  →  {r.verdict}")
        print(f"  Details  : {r.details}")
        print()
