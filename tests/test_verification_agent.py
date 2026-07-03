"""
Tests for VerificationAgent — Heritage Sentinel AI

Covers:
  - Confidence label generation (High, Moderate, Low, Insufficient)
  - Threshold routing (junk <25, boundary 24/25, normal range, high scores)
  - Duplicate detection auto-rejection
  - Missing scoring fallback
  - Low-scoring category extraction
  - Review notes content verification

All tests run without a real Gemini key — the VerificationAgent is
pure Python logic with no external API calls.
"""

from datetime import datetime, timezone

import pytest

from app.agents.verification_agent import (
    run_verification,
    _confidence_label,
    _low_scoring_categories,
)
from app.models.dossier import (
    CanonicalDossier,
    Metadata,
    RawEvidence,
    RegistryCheck,
    ReviewDecisionType,
    ScoringResult,
    SubmissionStatus,
)


def _make_dossier(location="Hampi", country="India", description="Ancient ruins."):
    return CanonicalDossier(
        metadata=Metadata(
            submission_id="SUB-TEST-00000001",
            submitted_by="test_user",
            submitted_at=datetime.now(timezone.utc),
            location_name=location,
            country=country,
            status=SubmissionStatus.pending,
        ),
        raw_evidence=RawEvidence(description=description),
    )


# ── Confidence label unit tests ─────────────────────────────────────────────

class TestConfidenceLabel:
    """Unit tests for _confidence_label(total_score)."""

    def test_high_confidence(self):
        assert _confidence_label(85) == "High Confidence"
        assert _confidence_label(100) == "High Confidence"
        # Boundary: exactly 80
        assert _confidence_label(80) == "High Confidence"

    def test_moderate_confidence(self):
        assert _confidence_label(60) == "Moderate Confidence"
        assert _confidence_label(79) == "Moderate Confidence"

    def test_low_confidence(self):
        assert _confidence_label(25) == "Low Confidence"
        assert _confidence_label(59) == "Low Confidence"

    def test_insufficient_evidence(self):
        assert _confidence_label(24) == "Insufficient Evidence"
        assert _confidence_label(0) == "Insufficient Evidence"


# ── Routing tests ───────────────────────────────────────────────────────────

class TestVerificationRouting:
    """End-to-end tests for run_verification() routing decisions."""

    def test_no_scoring_routes_to_reviewer_review(self):
        """Evaluation failure (scoring is None) → manual review."""
        dossier = _make_dossier()
        dossier.scoring = None

        updated, status = run_verification(dossier)

        assert status == SubmissionStatus.reviewer_review
        assert updated.review.decision == ReviewDecisionType.pending
        assert "Manual review required" in updated.review.reviewer_notes

    def test_high_score_routes_to_reviewer_review(self):
        """Score 93/100 → High Confidence, routed to human review."""
        dossier = _make_dossier()
        dossier.scoring = ScoringResult(
            historic_features=22,
            cultural_significance=18,
            integrity=12,
            authenticity=12,
            geographic_context=8,
            documentation=8,
            management_protection=3,
            supporting_evidence=10,
            total=93,
            rationale="Strong site.",
        )

        updated, status = run_verification(dossier)

        assert status == SubmissionStatus.reviewer_review
        assert updated.review.decision == ReviewDecisionType.pending
        assert "High Confidence" in updated.review.reviewer_notes
        assert "93/100" in updated.review.reviewer_notes

    def test_duplicate_auto_rejected(self):
        """Confirmed UNESCO duplicate → auto-rejected, notes contain matched site."""
        dossier = _make_dossier()
        dossier.registry_check = RegistryCheck(
            is_duplicate=True,
            matched_site="Hampi, India",
            similarity_score=1.0,
        )

        updated, status = run_verification(dossier)

        assert status == SubmissionStatus.rejected
        assert updated.review.decision == ReviewDecisionType.rejected
        assert "Hampi, India" in updated.review.reviewer_notes
        assert "duplicate" in updated.review.reviewer_notes.lower()

    def test_junk_below_threshold_auto_rejected(self):
        """Score 11/100 → auto-rejected as junk."""
        dossier = _make_dossier()
        dossier.scoring = ScoringResult(
            historic_features=3,
            cultural_significance=2,
            integrity=1,
            authenticity=1,
            geographic_context=1,
            documentation=1,
            management_protection=0,
            supporting_evidence=2,
            total=11,
            rationale="Insufficient evidence.",
        )

        updated, status = run_verification(dossier)

        assert status == SubmissionStatus.rejected
        assert updated.review.decision == ReviewDecisionType.rejected
        assert "11/100" in updated.review.reviewer_notes
        assert "Areas needing improvement" in updated.review.reviewer_notes

    def test_boundary_score_25_routes_to_review(self):
        """Score exactly 25 → NOT junk, routed to human review."""
        dossier = _make_dossier()
        dossier.scoring = ScoringResult(
            historic_features=8,
            cultural_significance=6,
            integrity=3,
            authenticity=3,
            geographic_context=2,
            documentation=2,
            management_protection=1,
            supporting_evidence=0,
            total=25,
            rationale="Borderline.",
        )

        _, status = run_verification(dossier)

        assert status == SubmissionStatus.reviewer_review

    def test_boundary_score_24_auto_rejected(self):
        """Score exactly 24 → junk threshold, auto-rejected."""
        dossier = _make_dossier()
        dossier.scoring = ScoringResult(
            historic_features=8,
            cultural_significance=5,
            integrity=3,
            authenticity=3,
            geographic_context=2,
            documentation=2,
            management_protection=1,
            supporting_evidence=0,
            total=24,
            rationale="Just below threshold.",
        )

        _, status = run_verification(dossier)

        assert status == SubmissionStatus.rejected

    def test_low_score_routes_to_human_review(self):
        """Score 31/100 → Low Confidence, but still routed to human review."""
        dossier = _make_dossier()
        dossier.scoring = ScoringResult(
            historic_features=8,
            cultural_significance=6,
            integrity=4,
            authenticity=4,
            geographic_context=3,
            documentation=3,
            management_protection=1,
            supporting_evidence=2,
            total=31,
            rationale="Low confidence.",
        )

        updated, status = run_verification(dossier)

        assert status == SubmissionStatus.reviewer_review
        assert "Low Confidence" in updated.review.reviewer_notes


# ── Low-scoring category extraction ─────────────────────────────────────────

class TestLowScoringCategories:
    """Unit tests for _low_scoring_categories(scoring)."""

    def test_no_weak_categories(self):
        """All scores strong → returns generic message."""
        scoring = ScoringResult(
            historic_features=25,
            cultural_significance=20,
            integrity=15,
            authenticity=15,
            geographic_context=10,
            documentation=10,
            management_protection=5,
            supporting_evidence=15,
            total=100,  # capped at 100 per Pydantic validator
            rationale="Perfect.",
        )
        result = _low_scoring_categories(scoring)
        assert result == "overall evidence quality"

    def test_some_weak_categories(self):
        """Mixed scores → lists weak categories."""
        scoring = ScoringResult(
            historic_features=5,   # < 25 * 0.3 = 7.5 → weak
            cultural_significance=20,
            integrity=2,             # < 15 * 0.3 = 4.5 → weak
            authenticity=15,
            geographic_context=10,
            documentation=10,
            management_protection=5,
            supporting_evidence=15,
            total=82,
            rationale="Mixed.",
        )
        result = _low_scoring_categories(scoring)
        assert "Historic Features" in result
        assert "Integrity" in result
        assert "Cultural Significance" not in result
