"""
Heritage Sentinel AI — Agent Pipeline
--------------------------------------
Full sequential workflow for a single submission:

  0. IntakeProcessor  — language detection + translation
  1. RegistryAgent    — BM25 + Gemini duplicate detection
  2. EvaluationAgent  — Gemini extraction + deterministic scoring
  3. VerificationAgent — Confidence Card routing + HITL gate

Runs as a FastAPI BackgroundTask. Each stage persists the dossier to
PostgreSQL so GET /submissions/{id} always reflects current progress.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.evaluation_agent import run_evaluation
from app.agents.intake_processor import run_intake
from app.agents.registry_agents import lookup_unesco_registry
from app.agents.verification_agent import run_verification
from app.db.session import AsyncSessionLocal
from app.models.dossier import CanonicalDossier, RegistryCheck, SubmissionStatus
from app.models.submission import Submission

log = logging.getLogger(__name__)


async def _load_submission(db: AsyncSession, submission_id: str) -> Submission | None:
    result = await db.execute(
        select(Submission).where(Submission.submission_id == submission_id)
    )
    return result.scalar_one_or_none()


async def _persist(
    db: AsyncSession,
    submission_id: str,
    dossier: CanonicalDossier,
    status: SubmissionStatus,
) -> None:
    dossier.metadata.status = status
    await db.execute(
        update(Submission)
        .where(Submission.submission_id == submission_id)
        .values(
            status=status,
            dossier=dossier.model_dump(mode="json"),
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()


async def run_pipeline(submission_id: str) -> None:
    """
    Full four-stage pipeline. Runs as a background task.
    Opens its own DB session independent of the request lifecycle.
    """
    log.info("Pipeline starting for %s", submission_id)

    async with AsyncSessionLocal() as db:
        submission = await _load_submission(db, submission_id)
        if not submission:
            log.error("Pipeline: submission %s not found", submission_id)
            return

        dossier = CanonicalDossier.model_validate(submission.dossier)

        # ── Stage 0: Intake — language detection + translation ────────────────
        log.info("Pipeline [0/3] IntakeProcessor — %s", submission_id)
        try:
            dossier = await run_intake(dossier)
        except Exception as exc:
            log.warning("Pipeline: IntakeProcessor failed for %s — %s", submission_id, exc)

        await _persist(db, submission_id, dossier, SubmissionStatus.registry_check)

        # ── Stage 1: RegistryAgent — BM25 + Gemini duplicate check ───────────
        log.info("Pipeline [1/3] RegistryAgent — %s", submission_id)
        try:
            description = (
                dossier.raw_evidence.translated_description
                or dossier.raw_evidence.description
            )
            registry_result = await lookup_unesco_registry(
                site_name=dossier.metadata.location_name,
                country=dossier.metadata.country,
                description=description,
            )
            dossier.registry_check = RegistryCheck(**registry_result)
        except Exception as exc:
            log.error("Pipeline: RegistryAgent failed for %s — %s", submission_id, exc)
            dossier.registry_check = RegistryCheck(is_duplicate=False)

        await _persist(db, submission_id, dossier, SubmissionStatus.registry_check)

        # Confirmed duplicate → skip evaluation, go straight to verification
        if dossier.registry_check and dossier.registry_check.is_duplicate:
            log.info("Pipeline: %s is a duplicate — skipping evaluation", submission_id)
            dossier, final_status = run_verification(dossier)
            await _persist(db, submission_id, dossier, final_status)
            log.info("Pipeline complete for %s — %s (duplicate)", submission_id, final_status)
            return

        # ── Stage 2: EvaluationAgent — Gemini extraction + deterministic score
        log.info("Pipeline [2/3] EvaluationAgent — %s", submission_id)
        await _persist(db, submission_id, dossier, SubmissionStatus.evaluation)

        # Re-fetch from DB so any photos uploaded after submission creation are included
        fresh = await _load_submission(db, submission_id)
        if fresh:
            fresh_dossier = CanonicalDossier.model_validate(fresh.dossier)
            dossier.raw_evidence.photo_urls = fresh_dossier.raw_evidence.photo_urls

        try:
            dossier = await run_evaluation(dossier)
        except Exception as exc:
            log.error("Pipeline: EvaluationAgent failed for %s — %s", submission_id, exc)

        await _persist(db, submission_id, dossier, SubmissionStatus.evaluation)

        # ── Stage 3: VerificationAgent — Confidence Card + HITL routing ──────
        log.info("Pipeline [3/3] VerificationAgent — %s", submission_id)
        dossier, final_status = run_verification(dossier)
        await _persist(db, submission_id, dossier, final_status)

        log.info(
            "Pipeline complete for %s — status: %s, score: %s/100",
            submission_id,
            final_status,
            dossier.scoring.total if dossier.scoring else "N/A",
        )
