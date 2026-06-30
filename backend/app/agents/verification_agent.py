"""
VerificationAgent — Heritage Sentinel AI
-----------------------------------------
Final stage of the pipeline. Reads the scoring result and decides
whether the submission should go to human review or be auto-rejected.

Rules:
  duplicate          → auto-rejected (already in UNESCO registry)
  total < 25         → auto-rejected (clearly invalid/spam submission)
  total >= 25        → routed to human archaeologist review
  scoring unavailable → routed to human review

The AI assists reviewers — it does NOT make the final approval/rejection
decision for genuine submissions. Only obvious junk (score < 25) and
confirmed UNESCO duplicates are auto-rejected.
"""

from __future__ import annotations

import logging

from app.models.dossier import CanonicalDossier, ReviewDecision, ReviewDecisionType, SubmissionStatus

log = logging.getLogger(__name__)

_JUNK_THRESHOLD = 25


def _confidence_label(total: int) -> str:
    if total >= 80:
        return "High Confidence"
    if total >= 60:
        return "Moderate Confidence"
    if total >= 25:
        return "Low Confidence"
    return "Insufficient Evidence"


def run_verification(dossier: CanonicalDossier) -> tuple[CanonicalDossier, SubmissionStatus]:
    """
    Assess the dossier and determine final pipeline status.

    Returns:
        (updated_dossier, new_status)
    """
    meta = dossier.metadata
    registry = dossier.registry_check
    scoring = dossier.scoring

    # Confirmed UNESCO duplicate → auto-reject
    if registry and registry.is_duplicate:
        matched = registry.matched_site or "unknown site"
        log.info(
            "VerificationAgent: %s is a duplicate of '%s' — auto-rejecting",
            meta.submission_id,
            matched,
        )
        dossier.review = ReviewDecision(
            decision=ReviewDecisionType.rejected,
            reviewer_id="system",
            reviewer_notes=(
                f"This site is a duplicate. It already exists in the UNESCO World Heritage registry as '{matched}'. "
                f"Only sites not yet inscribed on the UNESCO list are eligible for nomination."
            ),
        )
        return dossier, SubmissionStatus.rejected

    # No scoring available (evaluation failed) → send to human review
    if scoring is None:
        log.warning(
            "VerificationAgent: %s has no scoring — routing to verification for manual review",
            meta.submission_id,
        )
        dossier.review = ReviewDecision(
            decision=ReviewDecisionType.pending,
            reviewer_notes="Evaluation could not be completed. Manual review required.",
        )
        return dossier, SubmissionStatus.reviewer_review

    label = _confidence_label(scoring.total)
    log.info(
        "VerificationAgent: %s total=%d — %s",
        meta.submission_id,
        scoring.total,
        label,
    )

    # Clearly invalid / spam submission → auto-reject
    if scoring.total < _JUNK_THRESHOLD:
        low_cats = _low_scoring_categories(scoring)
        dossier.review = ReviewDecision(
            decision=ReviewDecisionType.rejected,
            reviewer_id="system",
            reviewer_notes=(
                f"Submission scored {scoring.total}/100 — insufficient evidence to warrant review. "
                f"Areas needing improvement: {low_cats}. "
                f"You may resubmit with additional documentation, photos, and a more detailed description."
            ),
        )
        return dossier, SubmissionStatus.rejected

    # Route everything else to human archaeologist review
    dossier.review = ReviewDecision(
        decision=ReviewDecisionType.pending,
        reviewer_notes=(
            f"{label} ({scoring.total}/100). Awaiting archaeologist review. "
            f"{scoring.rationale}"
        ),
    )
    return dossier, SubmissionStatus.reviewer_review


def _low_scoring_categories(scoring) -> str:
    """Return a human-readable list of the weakest scoring categories."""
    categories = [
        ("Historic Features", scoring.historic_features, 25),
        ("Cultural Significance", scoring.cultural_significance, 20),
        ("Integrity", scoring.integrity, 15),
        ("Authenticity", scoring.authenticity, 15),
        ("Geographic Context", scoring.geographic_context, 10),
        ("Documentation", scoring.documentation, 10),
        ("Supporting Evidence", scoring.supporting_evidence, 15),
    ]
    weak = [name for name, score, max_score in categories if score < (max_score * 0.3)]
    return ", ".join(weak) if weak else "overall evidence quality"
