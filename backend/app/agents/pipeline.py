"""
Heritage Sentinel AI — Agent Pipeline
--------------------------------------
Orchestrates the three-agent workflow for a single submission:

  1. RegistryAgent  — BM25 duplicate detection against UNESCO registry
  2. EvaluationAgent — Gemini 2.5 Flash evidence extraction + scoring
  3. VerificationAgent — Confidence Card decision + HITL routing

Each stage updates the canonical dossier and persists it to the DB.
The pipeline runs as a FastAPI BackgroundTask so POST /submissions
returns immediately while processing happens asynchronously.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.evaluation_agent import run_evaluation
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
    Full three-agent pipeline. Intended to run as a background task.
    Opens its own DB session so it's independent of the request lifecycle.
    """
    log.info("Pipeline starting for %s", submission_id)

    async with AsyncSessionLocal() as db:
        submission = await _load_submission(db, submission_id)
        if not submission:
            log.error("Pipeline: submission %s not found", submission_id)
            return

        dossier = CanonicalDossier.model_validate(submission.dossier)

        # ── Stage 1: RegistryAgent ────────────────────────────────────────────
        log.info("Pipeline [1/3] RegistryAgent — %s", submission_id)
        await _persist(db, submission_id, dossier, SubmissionStatus.registry_check)

        try:
            registry_result = await lookup_unesco_registry(
                site_name=dossier.metadata.location_name,
                country=dossier.metadata.country,
            )
            dossier.registry_check = RegistryCheck(**registry_result)
        except Exception as exc:
            log.error("Pipeline: RegistryAgent failed for %s — %s", submission_id, exc)
            dossier.registry_check = RegistryCheck(
                is_duplicate=False,
                reviewer_notes=f"Registry check failed: {exc}",
            )

        await _persist(db, submission_id, dossier, SubmissionStatus.registry_check)

        # If it's a confirmed duplicate skip evaluation and go straight to verification
        if dossier.registry_check and dossier.registry_check.is_duplicate:
            log.info("Pipeline: %s is a duplicate — skipping evaluation", submission_id)
            dossier, final_status = run_verification(dossier)
            await _persist(db, submission_id, dossier, final_status)
            log.info("Pipeline complete for %s — status: %s", submission_id, final_status)
            return

        # ── Stage 2: EvaluationAgent ──────────────────────────────────────────
        log.info("Pipeline [2/3] EvaluationAgent — %s", submission_id)
        await _persist(db, submission_id, dossier, SubmissionStatus.evaluation)

        try:
            dossier = await run_evaluation(dossier)
        except Exception as exc:
            log.error("Pipeline: EvaluationAgent failed for %s — %s", submission_id, exc)

        await _persist(db, submission_id, dossier, SubmissionStatus.evaluation)

        # ── Stage 3: VerificationAgent ────────────────────────────────────────
        log.info("Pipeline [3/3] VerificationAgent — %s", submission_id)
        dossier, final_status = run_verification(dossier)
        await _persist(db, submission_id, dossier, final_status)

        log.info(
            "Pipeline complete for %s — status: %s, score: %s/100",
            submission_id,
            final_status,
            dossier.scoring.total if dossier.scoring else "N/A",
        )
