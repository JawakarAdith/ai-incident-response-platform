import pytest
from app.agents.validation import compute_evidence_score


class TestEvidenceScore:
    """
    Tests for deterministic evidence-based scoring.
    These never call the LLM — fast and reliable.
    """

    def test_high_score_with_all_signals(
        self, clear_logs, strong_root_cause,
        strong_recommendation, rag_context
    ):
        """All signals present → score should be high."""
        score, breakdown = compute_evidence_score(
            logs=clear_logs,
            root_cause=strong_root_cause,
            recommendation=strong_recommendation,
            rag_context=rag_context
        )
        assert score >= 0.75, (
            f"Expected high score with all signals, got {score}. "
            f"Breakdown: {breakdown}"
        )

    def test_low_score_with_vague_logs(
        self, vague_logs, weak_root_cause,
        weak_recommendation
    ):
        """Vague logs, no RAG, weak recommendation → low score."""
        score, breakdown = compute_evidence_score(
            logs=vague_logs,
            root_cause=weak_root_cause,
            recommendation=weak_recommendation,
            rag_context=""
        )
        assert score < 0.75, (
            f"Expected low score with vague inputs, got {score}. "
            f"Breakdown: {breakdown}"
        )

    def test_rag_context_increases_score(
        self, clear_logs, strong_root_cause,
        strong_recommendation
    ):
        """RAG context should increase score by exactly 0.25."""
        score_without_rag, _ = compute_evidence_score(
            logs=clear_logs,
            root_cause=strong_root_cause,
            recommendation=strong_recommendation,
            rag_context=""
        )
        score_with_rag, _ = compute_evidence_score(
            logs=clear_logs,
            root_cause=strong_root_cause,
            recommendation=strong_recommendation,
            rag_context="PAST SIMILAR INCIDENT: DB pool exhausted. Fix: increase connections."
        )
        assert score_with_rag > score_without_rag, (
            "RAG context should increase confidence score"
        )
        assert abs((score_with_rag - score_without_rag) - 0.25) < 0.01, (
            f"RAG should add exactly 0.25. "
            f"Difference was {score_with_rag - score_without_rag:.2f}"
        )

    def test_score_is_deterministic(
        self, clear_logs, strong_root_cause,
        strong_recommendation, rag_context
    ):
        """Same input must always give same score — not random."""
        scores = [
            compute_evidence_score(
                clear_logs, strong_root_cause,
                strong_recommendation, rag_context
            )[0]
            for _ in range(5)
        ]
        assert len(set(scores)) == 1, (
            f"Score should be deterministic. Got different scores: {scores}"
        )

    def test_score_clamped_between_0_and_1(
        self, clear_logs, strong_root_cause,
        strong_recommendation, rag_context
    ):
        """Score must never go below 0 or above 1."""
        score, _ = compute_evidence_score(
            logs=clear_logs,
            root_cause=strong_root_cause,
            recommendation=strong_recommendation,
            rag_context=rag_context
        )
        assert 0.0 <= score <= 1.0, f"Score out of range: {score}"

    def test_vague_phrase_penalty_applied(self):
        """Vague phrases in logs should reduce score."""
        score_normal, _ = compute_evidence_score(
            logs="ERROR connection pool exhausted payment service crashed",
            root_cause="connection pool exhausted",
            recommendation="restart service",
            rag_context=""
        )
        score_vague, _ = compute_evidence_score(
            logs="ERROR something failed unknown error occurred",
            root_cause="something went wrong",
            recommendation="check service",
            rag_context=""
        )
        assert score_vague < score_normal, (
            "Vague logs should score lower than specific logs"
        )

    def test_no_rag_context_scores_lower(
        self, clear_logs, strong_root_cause, strong_recommendation
    ):
        """Missing RAG context should produce lower score."""
        score, breakdown = compute_evidence_score(
            logs=clear_logs,
            root_cause=strong_root_cause,
            recommendation=strong_recommendation,
            rag_context=""
        )
        assert breakdown["rag_context_found"] == 0.0