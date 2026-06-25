import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Enum as SAEnum, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.session import Base
from app.models.dossier import SubmissionStatus


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(String, unique=True, nullable=False, index=True)
    status = Column(
        SAEnum(SubmissionStatus, name="submissionstatus"),
        nullable=False,
        default=SubmissionStatus.pending,
    )
    dossier = Column(JSONB, nullable=False, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=lambda: datetime.now(timezone.utc),
    )
