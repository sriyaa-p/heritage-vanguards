import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.session import get_db
from app.models.submission import Submission
from app.models.dossier import (
    CanonicalDossier,
    Metadata,
    RawEvidence,
    ReviewDecision,
    SubmissionStatus,
)

router = APIRouter(prefix="/submissions", tags=["submissions"])


class SubmitRequest(BaseModel):
    location_name: str
    country: str
    description: str
    photo_urls: list[str] = []
    submitted_by: str = "anonymous"


@router.post("", status_code=201)
async def create_submission(
    body: SubmitRequest, db: AsyncSession = Depends(get_db)
):
    submission_id = f"SUB-{datetime.now(timezone.utc).strftime('%Y-%m')}-{uuid.uuid4().hex[:8].upper()}"

    dossier = CanonicalDossier(
        metadata=Metadata(
            submission_id=submission_id,
            submitted_by=body.submitted_by,
            submitted_at=datetime.now(timezone.utc),
            location_name=body.location_name,
            country=body.country,
            status=SubmissionStatus.pending,
        ),
        raw_evidence=RawEvidence(
            description=body.description,
            photo_urls=body.photo_urls,
        ),
        review=ReviewDecision(),
    )

    submission = Submission(
        submission_id=submission_id,
        status=SubmissionStatus.pending,
        dossier=dossier.model_dump(mode="json"),
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    return {
        "submission_id": submission_id,
        "status": submission.status,
        "created_at": submission.created_at,
    }


@router.get("")
async def list_submissions(
    status: str | None = None, db: AsyncSession = Depends(get_db)
):
    query = select(Submission).order_by(Submission.created_at.desc())
    if status:
        try:
            query = query.where(Submission.status == SubmissionStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    result = await db.execute(query)
    rows = result.scalars().all()

    return [
        {
            "submission_id": r.submission_id,
            "status": r.status,
            "location_name": r.dossier.get("metadata", {}).get("location_name"),
            "country": r.dossier.get("metadata", {}).get("country"),
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.get("/{submission_id}")
async def get_submission(submission_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Submission).where(Submission.submission_id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    return {
        "submission_id": submission.submission_id,
        "status": submission.status,
        "dossier": submission.dossier,
        "created_at": submission.created_at,
        "updated_at": submission.updated_at,
    }


@router.patch("/{submission_id}/review")
async def review_submission(
    submission_id: str,
    decision: str,
    notes: str = "",
    reviewer_id: str = "reviewer",
    db: AsyncSession = Depends(get_db),
):
    if decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="decision must be 'approved' or 'rejected'")

    result = await db.execute(
        select(Submission).where(Submission.submission_id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    dossier = submission.dossier or {}
    dossier.setdefault("review", {})
    dossier["review"]["decision"] = decision
    dossier["review"]["reviewer_id"] = reviewer_id
    dossier["review"]["reviewer_notes"] = notes
    dossier["review"]["decided_at"] = datetime.now(timezone.utc).isoformat()

    from sqlalchemy import update
    await db.execute(
        update(Submission)
        .where(Submission.submission_id == submission_id)
        .values(
            status=SubmissionStatus(decision),
            dossier=dossier,
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()

    return {"submission_id": submission_id, "status": decision}
