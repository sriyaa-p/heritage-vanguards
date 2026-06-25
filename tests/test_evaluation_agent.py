"""
Tests for EvaluationAgent and VerificationAgent.
EvaluationAgent tests mock the Gemini API so they run without a real key.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.verification_agent import run_verification
from app.models.dossier import (
    CanonicalDossier,
    Metadata,
    RawEvidence,
    RegistryCheck,
    ReviewDecisionType,
    ScoringResult,
    SubmissionStatus,
)


def _make_dossier(location="Hampi Ruins", country="India", description="Ancient ruins."):
    return CanonicalDossier(
        metadata=Metadata(
            submission_id="SUB-TEST-00000001",
            submitted_by="test_user",
            submitted_at=datetime.now(timezone.utc),
            location_name=location,
            country=country,
            status=SubmissionStatus.pending,
        ),
        raw_evidence=RawEvidence(description=description, photo_urls=["photo1.jpg"]),
    )


# ── VerificationAgent tests ───────────────────────────────────────────────────

def test_verification_routes_high_score_to_review():
    dossier = _make_dossier()
    dossier.scoring = ScoringResult(
        historic_features=28, cultural_significance=22,
        geographic_context=12, documentation=13,
        supporting_evidence=10, total=85, rationale="Strong site."
    )
    updated, status = run_verification(dossier)
    assert status == SubmissionStatus.verification
    assert updated.review.decision == ReviewDecisionType.pending


def test_verification_auto_rejects_low_score():
    dossier = _make_dossier()
    dossier.scoring = ScoringResult(
        historic_features=5, cultural_significance=5,
        geographic_context=3, documentation=3,
        supporting_evidence=2, total=18, rationale="Insufficient evidence."
    )
    updated, status = run_verification(dossier)
    assert status == SubmissionStatus.rejected
    assert updated.review.decision == ReviewDecisionType.rejected
    assert "18/100" in updated.review.reviewer_notes


def test_verification_rejects_duplicate():
    dossier = _make_dossier()
    dossier.registry_check = RegistryCheck(
        is_duplicate=True,
        matched_site="Hampi",
        similarity_score=1.0,
    )
    updated, status = run_verification(dossier)
    assert status == SubmissionStatus.rejected
    assert "duplicate" in updated.review.reviewer_notes.lower()


def test_verification_routes_boundary_score_60():
    dossier = _make_dossier()
    dossier.scoring = ScoringResult(
        historic_features=20, cultural_significance=15,
        geographic_context=10, documentation=10,
        supporting_evidence=5, total=60, rationale="Borderline."
    )
    _, status = run_verification(dossier)
    assert status == SubmissionStatus.verification


def test_verification_auto_rejects_score_59():
    dossier = _make_dossier()
    dossier.scoring = ScoringResult(
        historic_features=20, cultural_significance=15,
        geographic_context=9, documentation=10,
        supporting_evidence=5, total=59, rationale="Just below threshold."
    )
    _, status = run_verification(dossier)
    assert status == SubmissionStatus.rejected


# ── EvaluationAgent tests (Gemini mocked) ────────────────────────────────────

MOCK_GEMINI_RESPONSE = """{
  "historic_features": "Ancient ruins dating to the 14th century Vijayanagara Empire.",
  "cultural_significance": "Capital of one of the greatest Hindu empires in South India.",
  "geographic_context": "Located in the Tungabhadra basin, Karnataka, India.",
  "documentation_quality": "Extensively documented by ASI and UNESCO.",
  "supporting_evidence": "One photo provided showing temple complex.",
  "score_historic_features": 27,
  "score_cultural_significance": 22,
  "score_geographic_context": 12,
  "score_documentation": 13,
  "score_supporting_evidence": 8,
  "rationale": "Hampi is a site of outstanding universal value with strong historic and cultural credentials. Photo evidence is limited."
}"""


@pytest.mark.asyncio
async def test_evaluation_agent_scores_correctly():
    dossier = _make_dossier(
        location="Hampi",
        description="Ancient ruins of the Vijayanagara Empire in Karnataka.",
    )

    mock_response = MagicMock()
    mock_response.text = MOCK_GEMINI_RESPONSE

    with patch("app.agents.evaluation_agent._client") as mock_client:
        mock_client.models.generate_content = MagicMock(return_value=mock_response)
        from app.agents.evaluation_agent import run_evaluation
        result = await run_evaluation(dossier)

    assert result.scoring is not None
    assert result.scoring.historic_features == 27
    assert result.scoring.cultural_significance == 22
    assert result.scoring.total == 82
    assert result.extracted_evidence is not None
    assert "Vijayanagara" in result.extracted_evidence.historic_features


@pytest.mark.asyncio
async def test_evaluation_agent_handles_gemini_failure():
    dossier = _make_dossier()

    with patch("app.agents.evaluation_agent._client") as mock_client:
        mock_client.models.generate_content = MagicMock(side_effect=Exception("API timeout"))
        from app.agents.evaluation_agent import run_evaluation
        result = await run_evaluation(dossier)

    # Should not raise — returns zero scores and continues
    assert result.scoring is not None
    assert result.scoring.total == 0
    assert "unavailable" in result.extracted_evidence.historic_features
