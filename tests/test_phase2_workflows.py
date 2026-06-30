import pytest
from datetime import datetime, timezone
from fastapi import HTTPException
from types import SimpleNamespace

from app.models.dossier import (
    CanonicalDossier,
    Metadata,
    RawEvidence,
    ReviewDecision,
    CommitteeDecision,
    SubmissionStatus,
)


class _FakeResult:
    def __init__(self, scalar=None, scalars_list=None):
        self._scalar = scalar
        self._scalars_list = scalars_list or []

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        return SimpleNamespace(all=lambda: self._scalars_list)


class _FakeDB:
    def __init__(self, submission=None, submissions_list=None):
        self.submission = submission
        self.submissions_list = submissions_list or []
        self.updated_values = None

    async def execute(self, _query):
        return _FakeResult(scalar=self.submission, scalars_list=self.submissions_list)

    async def commit(self):
        pass


def _make_test_submission():
    dossier = CanonicalDossier(
        metadata=Metadata(
            submission_id="SUB-TEST-00000001",
            submitted_by="tester",
            submitted_at=datetime.now(timezone.utc),
            location_name="Test Site",
            country="Test Country",
            status=SubmissionStatus.pending,
        ),
        raw_evidence=RawEvidence(
            description="A beautiful test site.",
            photo_urls=["/uploads/photo1.jpg"],
        ),
        review=ReviewDecision(reviewer_notes="Initial reviewer notes"),
        committee_review=CommitteeDecision(committee_comments="Initial committee comments"),
    )
    # Mock database model
    submission = SimpleNamespace(
        submission_id="SUB-TEST-00000001",
        status=SubmissionStatus.pending,
        dossier=dossier.model_dump(mode="json"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    return submission


@pytest.mark.asyncio
async def test_get_public_submission_filters_sensitive_data():
    from app.api.routes.submissions import get_public_submission

    sub = _make_test_submission()
    db = _FakeDB(submission=sub)

    result = await get_public_submission("SUB-TEST-00000001", db=db)

    assert result["submission_id"] == "SUB-TEST-00000001"
    assert result["location_name"] == "Test Site"
    assert result["country"] == "Test Country"
    assert result["description"] == "A beautiful test site."
    assert result["photo_urls"] == ["/uploads/photo1.jpg"]
    assert result["reviewer_notes"] == "Initial reviewer notes"
    assert result["committee_comments"] == "Initial committee comments"
    # Ensure sensitive fields like scoring are completely omitted
    assert "score" not in result
    assert "scoring" not in result


@pytest.mark.asyncio
async def test_review_submission_recommendation():
    from app.api.routes.submissions import review_submission

    sub = _make_test_submission()
    db = _FakeDB(submission=sub)

    result = await review_submission(
        submission_id="SUB-TEST-00000001",
        decision="committee_review",
        notes="Highly recommended for designation.",
        reviewer_id="archaeologist_1",
        db=db,
    )

    assert result["status"] == "committee_review"
    assert sub.dossier["review"]["decision"] == "approved"
    assert sub.dossier["review"]["reviewer_notes"] == "Highly recommended for designation."
    assert sub.dossier["review"]["reviewer_id"] == "archaeologist_1"


@pytest.mark.asyncio
async def test_review_submission_invalid_decision():
    from app.api.routes.submissions import review_submission

    sub = _make_test_submission()
    db = _FakeDB(submission=sub)

    # Reviewer cannot directly 'approve' (must recommend/forward or reject)
    with pytest.raises(HTTPException) as exc_info:
        await review_submission(
            submission_id="SUB-TEST-00000001",
            decision="approved",
            notes="Direct approval",
            db=db,
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_finalize_submission_approval():
    from app.api.routes.submissions import finalize_submission

    sub = _make_test_submission()
    db = _FakeDB(submission=sub)

    result = await finalize_submission(
        submission_id="SUB-TEST-00000001",
        decision="approved",
        comments="Officially designated by UNESCO.",
        committee_id="committee_member_1",
        db=db,
    )

    assert result["status"] == "approved"
    assert sub.dossier["committee_review"]["decision"] == "approved"
    assert sub.dossier["committee_review"]["committee_comments"] == "Officially designated by UNESCO."
    assert sub.dossier["committee_review"]["committee_id"] == "committee_member_1"


@pytest.mark.asyncio
async def test_finalize_submission_invalid_decision():
    from app.api.routes.submissions import finalize_submission

    sub = _make_test_submission()
    db = _FakeDB(submission=sub)

    with pytest.raises(HTTPException) as exc_info:
        await finalize_submission(
            submission_id="SUB-TEST-00000001",
            decision="committee_review",
            comments="Invalid decision for committee",
            db=db,
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_get_audit_log():
    from app.api.routes.submissions import get_audit_log

    sub = _make_test_submission()
    db = _FakeDB(submissions_list=[sub])

    result = await get_audit_log(db=db)

    assert len(result) == 1
    assert result[0]["submission_id"] == "SUB-TEST-00000001"
    assert result[0]["reviewer_notes"] == "Initial reviewer notes"
    assert result[0]["committee_comments"] == "Initial committee comments"
