"""
VerificationAgent — Heritage Sentinel AI
-----------------------------------------
Final stage of the pipeline. Reads the scoring result and decides
whether the submission should go to human review or be auto-rejected.

Rules:
  total >= 60  → status = "verification"  (Confidence Card shown to archaeologist)
  total < 60   → status = "rejected"      (auto-rejected, low evidence)
  duplicate    → status = "rejected"      (already in UNESCO registry)
"""

from __future__ import annotations

import logging

from app.models.dossier import CanonicalDossier, ReviewDecision, ReviewDecisionType, SubmissionStatus

log = logging.getLogger(__name__)

_AUTO_REJECT_THRESHOLD = 60


def _confidence_label(total: int) -> str:
    if total >= 80:
        return "High Confidence"
    if total >= 60:
        return "Medium Confidence"
    return "Low Confidence — Auto Rejected"


def run_verification(dossier: CanonicalDossier) -> tuple[CanonicalDossier, SubmissionStatus]:
    """
    Assess the dossier and determine final pipeline status.

    Returns:
        (updated_dossier, new_status)
    """
    meta = dossier.metadata
    registry = dossier.registry_check
    scoring = dossier.scoring

    # Duplicate detected by RegistryAgent → auto-reject
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
            reviewer_notes=f"Auto-rejected: duplicate of existing UNESCO site '{matched}'.",
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
        return dossier, SubmissionStatus.verification

    label = _confidence_label(scoring.total)
    log.info(
        "VerificationAgent: %s total=%d — %s",
        meta.submission_id,
        scoring.total,
        label,
    )

    # Below threshold → auto-reject
    if scoring.total < _AUTO_REJECT_THRESHOLD:
        dossier.review = ReviewDecision(
            decision=ReviewDecisionType.rejected,
            reviewer_id="system",
            reviewer_notes=(
                f"Auto-rejected: heritage score {scoring.total}/100 is below the "
                f"minimum threshold of {_AUTO_REJECT_THRESHOLD}. {scoring.rationale}"
            ),
        )
        return dossier, SubmissionStatus.rejected

    # Sufficient score → route to human archaeologist review
    dossier.review = ReviewDecision(
        decision=ReviewDecisionType.pending,
        reviewer_notes=f"{label} ({scoring.total}/100). Awaiting archaeologist review.",
    )
    return dossier, SubmissionStatus.verification
