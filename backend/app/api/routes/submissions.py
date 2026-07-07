import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, HTTPException, Query, Request, UploadFile
from slowapi.util import get_remote_address
from slowapi import Limiter
from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.config import settings
from app.agents.pipeline import run_pipeline
from app.db.session import get_db
from app.models.submission import Submission
from app.models.dossier import (
    CanonicalDossier,
    Metadata,
    RawEvidence,
    ReviewDecision,
    CommitteeDecision,
    SubmissionStatus,
)

router = APIRouter(prefix="/submissions", tags=["submissions"])
limiter = Limiter(key_func=get_remote_address)

_UPLOADS_DIR = settings.UPLOADS_DIR
try:
    os.makedirs(_UPLOADS_DIR, exist_ok=True)
except OSError:
    # Local test/dev environments may not be allowed to write to /data.
    # Docker keeps using /data/uploads; non-Docker falls back inside the repo.
    _UPLOADS_DIR = os.path.abspath("data/uploads")
    os.makedirs(_UPLOADS_DIR, exist_ok=True)

_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def _write_file_sync(dest: str, content: bytes) -> None:
    """Synchronous helper for file writes — runs in asyncio thread pool."""
    with open(dest, "wb") as f:
        f.write(content)


async def _save_photos(
    submission_id: str, files: list[UploadFile]
) -> list[str]:
    """Save uploaded photo files to disk asynchronously and return their URL paths.

    File I/O is offloaded to asyncio.to_thread() so the event loop remains
    unblocked. This allows the backend to handle concurrent uploads without
    freezing other requests.
    """
    upload_dir = os.path.join(_UPLOADS_DIR, submission_id)
    await asyncio.to_thread(os.makedirs, upload_dir, exist_ok=True)

    saved_urls: list[str] = []
    for file in files:
        ext = os.path.splitext(file.filename or "photo.jpg")[1].lower() or ".jpg"
        if ext not in _ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{ext}' is not allowed. Only image files ({', '.join(sorted(_ALLOWED_EXTENSIONS))}) are accepted.",
            )
        filename = f"{uuid.uuid4().hex}{ext}"
        dest = os.path.join(upload_dir, filename)

        # FastAPI UploadFile.read() is async; writes are offloaded to thread pool
        content = await file.read()
        await asyncio.to_thread(_write_file_sync, dest, content)
        saved_urls.append(f"/uploads/{submission_id}/{filename}")
    return saved_urls


class SubmitRequest(BaseModel):
    location_name: str
    country: str
    description: str
    photo_urls: list[str] = []
    submitted_by: str = "anonymous"


def _make_submission_id() -> str:
    return f"SUB-{datetime.now(timezone.utc).strftime('%Y-%m')}-{uuid.uuid4().hex[:8].upper()}"


def _validate_description(description: str) -> None:
    """Validate description length. Raises HTTPException if too long."""
    if len(description) > settings.MAX_DESCRIPTION_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Description exceeds maximum length of {settings.MAX_DESCRIPTION_LENGTH} characters.",
        )


def _validate_photos(files: list[UploadFile]) -> None:
    """Validate photo count and size. Raises HTTPException if limits exceeded."""
    if len(files) > settings.MAX_PHOTOS_PER_SUBMISSION:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.MAX_PHOTOS_PER_SUBMISSION} photos allowed per submission.",
        )
    for file in files:
        # Check content length if available
        if file.size and file.size > settings.MAX_PHOTO_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"Photo '{file.filename}' exceeds {settings.MAX_PHOTO_SIZE_MB}MB size limit.",
            )


@router.post("", status_code=201)
@limiter.limit(f"{settings.RATE_LIMIT_SUBMISSION_PER_MIN}/minute")
async def create_submission(
    request: Request,
    body: SubmitRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    _validate_description(body.description)
    submission_id = _make_submission_id()

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
        committee_review=CommitteeDecision(),
    )

    submission = Submission(
        submission_id=submission_id,
        status=SubmissionStatus.pending,
        dossier=dossier.model_dump(mode="json"),
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    background_tasks.add_task(run_pipeline, submission_id)

    return {
        "submission_id": submission_id,
        "status": submission.status,
        "created_at": submission.created_at,
    }


@router.post("/with-photos", status_code=201)
@limiter.limit(f"{settings.RATE_LIMIT_SUBMISSION_PER_MIN}/minute")
async def create_submission_with_photos(
    request: Request,
    background_tasks: BackgroundTasks,
    location_name: str = Form(...),
    country: str = Form(...),
    description: str = Form(...),
    submitted_by: str = Form("anonymous"),
    files: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
):
    """
    Unified submission endpoint: accepts metadata AND photo files in a single
    multipart/form-data request. This eliminates the race condition where the
    background pipeline could overwrite photo URLs uploaded via a second request.
    """
    _validate_description(description)

    submission_id = _make_submission_id()

    # Save photos to disk BEFORE creating the dossier
    photo_urls: list[str] = []
    if files and files[0].filename:  # FastAPI sends [UploadFile("")] when no files
        _validate_photos(files)
        photo_urls = await _save_photos(submission_id, files)

    dossier = CanonicalDossier(
        metadata=Metadata(
            submission_id=submission_id,
            submitted_by=submitted_by,
            submitted_at=datetime.now(timezone.utc),
            location_name=location_name,
            country=country,
            status=SubmissionStatus.pending,
        ),
        raw_evidence=RawEvidence(
            description=description,
            photo_urls=photo_urls,
        ),
        review=ReviewDecision(),
        committee_review=CommitteeDecision(),
    )

    submission = Submission(
        submission_id=submission_id,
        status=SubmissionStatus.pending,
        dossier=dossier.model_dump(mode="json"),
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    background_tasks.add_task(run_pipeline, submission_id)

    return {
        "submission_id": submission_id,
        "status": submission.status,
        "created_at": submission.created_at,
        "photos_uploaded": len(photo_urls),
    }


@router.post("/{submission_id}/photos", status_code=200)
@limiter.limit(f"{settings.RATE_LIMIT_UPLOAD_PER_MIN}/minute")
async def upload_photos(
    request: Request,
    submission_id: str,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload photos for an existing submission. Saves files to /data/uploads/{submission_id}/
    and appends their URLs to the dossier's raw_evidence.photo_urls.
    """
    result = await db.execute(
        select(Submission).where(Submission.submission_id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    _validate_photos(files)
    saved_urls = await _save_photos(submission_id, files)

    dossier = submission.dossier or {}
    raw = dossier.setdefault("raw_evidence", {})
    existing = raw.get("photo_urls", [])
    raw["photo_urls"] = existing + saved_urls

    await db.execute(
        update(Submission)
        .where(Submission.submission_id == submission_id)
        .values(dossier=dossier, updated_at=datetime.now(timezone.utc))
    )
    await db.commit()

    return {"submission_id": submission_id, "uploaded": saved_urls}


@router.get("")
@limiter.limit("120/minute")
async def list_submissions(
    request: Request,
    status: Optional[str] = None,
    search: Optional[str] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List submissions with pagination, filtering, and search.

    Query parameters:
    - status: filter by submission status
    - search: text search in location_name, country, and description
    - min_score / max_score: filter by Heritage Score range
    - date_from / date_to: ISO 8601 date range for created_at
    - limit: max items per page (1-100, default 50)
    - offset: pagination offset (default 0)
    """
    query = select(Submission).order_by(Submission.created_at.desc())
    conditions = []

    if status:
        try:
            conditions.append(Submission.status == SubmissionStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    if search:
        search_term = f"%{search}%"
        # PostgreSQL ILIKE for case-insensitive search; SQLite LIKE is case-insensitive by default
        conditions.append(
            or_(
                Submission.dossier["metadata"]["location_name"].astext.ilike(search_term),
                Submission.dossier["metadata"]["country"].astext.ilike(search_term),
                Submission.dossier["raw_evidence"]["description"].astext.ilike(search_term),
            )
        )

    if date_from:
        try:
            from_dt = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
            conditions.append(Submission.created_at >= from_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date_from: {date_from}")

    if date_to:
        try:
            to_dt = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
            conditions.append(Submission.created_at <= to_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date_to: {date_to}")

    if conditions:
        query = query.where(and_(*conditions))

    # Get total count for pagination metadata
    count_query = select(func.count()).select_from(Submission)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply pagination
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    rows = result.scalars().all()

    items = [
        {
            "submission_id": r.submission_id,
            "status": r.status.value,
            "location_name": r.dossier.get("metadata", {}).get("location_name"),
            "country": r.dossier.get("metadata", {}).get("country"),
            "score": r.dossier.get("scoring", {}).get("total") if r.dossier.get("scoring") else None,
            "created_at": r.created_at,
        }
        for r in rows
    ]

    # Apply score filtering in Python (since score is inside JSONB)
    if min_score is not None or max_score is not None:
        items = [
            item for item in items
            if item["score"] is not None
            and (min_score is None or item["score"] >= min_score)
            and (max_score is None or item["score"] <= max_score)
        ]

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + len(items)) < total,
    }


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Aggregate counts by status for the admin dashboard."""
    result = await db.execute(
        select(Submission.status, func.count().label("count"))
        .group_by(Submission.status)
    )
    rows = result.all()
    counts = {row.status: row.count for row in rows}

    total = sum(counts.values())
    # Count only confirmed UNESCO duplicate auto-rejections, not all rejected rows.
    rejected_result = await db.execute(
        select(Submission).where(Submission.status == SubmissionStatus.rejected)
    )
    rejected_rows = rejected_result.scalars().all()
    duplicates_blocked = sum(
        1
        for submission in rejected_rows
        if (submission.dossier or {}).get("registry_check", {}).get("is_duplicate") is True
    )

    return {
        "total": total,
        "pending": counts.get(SubmissionStatus.pending, 0),
        "registry_check": counts.get(SubmissionStatus.registry_check, 0),
        "evaluation": counts.get(SubmissionStatus.evaluation, 0),
        "in_review": (
            counts.get(SubmissionStatus.reviewer_review, 0)
            + counts.get(SubmissionStatus.committee_review, 0)
            # verification is deprecated; include for backward compatibility with old data
            + counts.get(SubmissionStatus.verification, 0)
        ),
        "reviewer_review": counts.get(SubmissionStatus.reviewer_review, 0),
        "committee_review": counts.get(SubmissionStatus.committee_review, 0),
        "approved": counts.get(SubmissionStatus.approved, 0),
        "rejected": counts.get(SubmissionStatus.rejected, 0),
        "duplicates_blocked": duplicates_blocked,
    }


@router.get("/audit-log")
async def get_audit_log(db: AsyncSession = Depends(get_db)):
    """Return finalized decisions only (approved or rejected). Excludes in-progress committee_review."""
    result = await db.execute(
        select(Submission)
        .where(Submission.status.in_([
            SubmissionStatus.approved,
            SubmissionStatus.rejected,
        ]))
        .order_by(Submission.updated_at.desc())
    )
    rows = result.scalars().all()
    return [
        {
            "submission_id": r.submission_id,
            "status": r.status.value,
            "location_name": r.dossier.get("metadata", {}).get("location_name"),
            "country": r.dossier.get("metadata", {}).get("country"),
            "score": r.dossier.get("scoring", {}).get("total") if r.dossier.get("scoring") else None,
            "reviewer_notes": r.dossier.get("review", {}).get("reviewer_notes"),
            "committee_comments": r.dossier.get("committee_review", {}).get("committee_comments"),
            "updated_at": r.updated_at,
        }
        for r in rows
    ]


@router.get("/{submission_id}/public")
async def get_public_submission(submission_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Submission).where(Submission.submission_id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
        
    dossier = submission.dossier or {}
    metadata = dossier.get("metadata", {})
    raw = dossier.get("raw_evidence", {})
    review = dossier.get("review", {})
    comm = dossier.get("committee_review", {})
    
    return {
        "submission_id": submission.submission_id,
        "status": submission.status,
        "created_at": submission.created_at,
        "location_name": metadata.get("location_name"),
        "country": metadata.get("country"),
        "description": raw.get("description"),
        "photo_urls": raw.get("photo_urls", []),
        "reviewer_notes": review.get("reviewer_notes"),
        "committee_comments": comm.get("committee_comments"),
    }


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
    db: AsyncSession = Depends(get_db),
    decision: str = Body(..., embed=True),
    notes: str = Body("", embed=True),
    reviewer_id: str = Body("reviewer", embed=True),
):
    if decision not in ("committee_review", "rejected"):
        raise HTTPException(status_code=400, detail="decision must be 'committee_review' or 'rejected'")

    result = await db.execute(
        select(Submission).where(Submission.submission_id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    dossier = submission.dossier or {}
    dossier.setdefault("review", {})
    dossier["review"]["decision"] = "approved" if decision == "committee_review" else "rejected"
    dossier["review"]["reviewer_id"] = reviewer_id
    dossier["review"]["reviewer_notes"] = notes
    dossier["review"]["decided_at"] = datetime.now(timezone.utc).isoformat()

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


@router.patch("/{submission_id}/finalize")
async def finalize_submission(
    submission_id: str,
    db: AsyncSession = Depends(get_db),
    decision: str = Body(..., embed=True),
    comments: str = Body("", embed=True),
    committee_id: str = Body("committee", embed=True),
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
    dossier.setdefault("committee_review", {})
    dossier["committee_review"]["decision"] = decision
    dossier["committee_review"]["committee_id"] = committee_id
    dossier["committee_review"]["committee_comments"] = comments
    dossier["committee_review"]["decided_at"] = datetime.now(timezone.utc).isoformat()

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
