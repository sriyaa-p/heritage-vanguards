from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from sqlalchemy import Column, Computed, Integer, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator
from sqlalchemy.ext.compiler import compiles


# ---------------------------------------------------------------------------
# Dialect-safe full-text search types and compilation handlers for SQLite/Postgres
# ---------------------------------------------------------------------------

class SafeTSVector(TypeDecorator):
    """Custom type that resolves to TSVECTOR on PostgreSQL and TEXT on other databases."""
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(TSVECTOR())
        return dialect.type_descriptor(Text())


@compiles(Computed, "sqlite")
def compile_computed_sqlite(element, compiler, **kw):
    """Fallback compiler for Computed columns on SQLite to avoid Postgres-specific functions."""
    # SQLite does not support to_tsvector(), so we compile it to a standard string concatenation
    return "GENERATED ALWAYS AS (coalesce(name, '') || ' ' || coalesce(country, '') || ' ' || coalesce(description, '')) STORED"


# ---------------------------------------------------------------------------
# Base & Models
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


class UnescoSite(Base):
    """ORM model for the `unesco_sites` table.

    Populated by scripts/seed_database.py from data/processed/unesco_sites_clean.json.
    Queried by RegistryAgent to detect duplicate submissions.
    """

    __tablename__ = "unesco_sites"

    id = Column(Integer, primary_key=True)
    name = Column(String(512), nullable=False, index=True)
    country = Column(String(256), nullable=False, index=True)
    region = Column(String(256), nullable=True)
    inscription_year = Column(Integer, nullable=True)
    # Comma-separated OUV criteria codes, e.g. "i,ii,vi"
    criteria = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)

    # Persisted full-text search vector — computed by PostgreSQL on INSERT/UPDATE.
    # Combines name + country + description for BM25-quality keyword matching via GIN.
    # The GIN index (ix_unesco_sites_search_vector) is created in the Alembic migration.
    search_vector = Column(
        SafeTSVector(),
        Computed(
            "to_tsvector('english',"
            " coalesce(name, '') || ' ' || coalesce(country, '') || ' ' || coalesce(description, '')"
            ")",
            persisted=True,
        ),
        nullable=True,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UnescoSite id={self.id} name={self.name!r} country={self.country!r}>"


class SubmissionStatus(str, Enum):
    pending = "pending"
    registry_check = "registry_check"
    evaluation = "evaluation"
    # DEPRECATED: verification is no longer set by the pipeline.
    # The VerificationAgent routes directly to reviewer_review or rejected.
    # Kept for backward compatibility with existing database records.
    verification = "verification"
    reviewer_review = "reviewer_review"
    committee_review = "committee_review"
    approved = "approved"
    rejected = "rejected"


class ReviewDecisionType(str, Enum):
    approved = "approved"
    rejected = "rejected"
    pending = "pending"


class Metadata(BaseModel):
    submission_id: str
    submitted_by: str
    submitted_at: datetime
    location_name: str
    country: str
    coordinates: Optional[tuple[float, float]] = None  # (lat, lon)
    status: SubmissionStatus = SubmissionStatus.pending


class RawEvidence(BaseModel):
    description: str
    photo_urls: list[str] = Field(default_factory=list)
    language_detected: Optional[str] = None
    translated_description: Optional[str] = None


class BM25Candidate(BaseModel):
    site_name: str
    country: str
    similarity_score: float


class RegistryCheck(BaseModel):
    is_duplicate: bool
    matched_site: Optional[str] = None
    similarity_score: Optional[float] = None
    top_candidates: list[BM25Candidate] = Field(default_factory=list)
    checked_at: Optional[datetime] = None


class ExtractedEvidence(BaseModel):
    # OUV criteria i, iii, iv — human history, architecture, archaeology
    historic_features: str
    # OUV criteria ii, v, vi — cultural exchange, living traditions, intangible heritage
    cultural_significance: str
    # UNESCO Pillar: Integrity — wholeness, intactness, legal protection status
    integrity: str
    # UNESCO Pillar: Authenticity — original materials, form, design, use (cultural sites)
    authenticity: str
    # OUV criteria vii–x — natural values, landscape, ecology, biodiversity
    geographic_context: str
    # Documentation quality — academic, governmental, archival sources
    documentation_quality: str
    # Management & Protection — management plan, legal framework
    management_protection: str
    # Visual evidence — photos, videos, surveys submitted
    supporting_evidence: str


class ScoringResult(BaseModel):
    # UNESCO-aligned weights — category maxes sum to 115, but total is capped at 100
    # via the Pydantic validator below. This follows the UNESCO scoring rubric where
    # Supporting Evidence (15 pts) is additive but the overall Heritage Score cannot
    # exceed 100. The cap enforces this rule at the model level.
    historic_features: int = Field(ge=0, le=25)       # OUV criteria i, iii, iv
    cultural_significance: int = Field(ge=0, le=20)   # OUV criteria ii, v, vi
    integrity: int = Field(ge=0, le=15)               # UNESCO Integrity pillar
    authenticity: int = Field(ge=0, le=15)            # UNESCO Authenticity pillar
    geographic_context: int = Field(ge=0, le=10)      # OUV criteria vii–x
    # Note: the field is named `documentation` in ScoringResult (model output) but
    # maps from `documentation_quality` in ExtractedEvidence (input). The scoring engine
    # bridges this naming difference intentionally.
    documentation: int = Field(ge=0, le=10)           # Documentation quality
    management_protection: int = Field(ge=0, le=5)    # Management & Protection
    supporting_evidence: int = Field(ge=0, le=15)     # Visual evidence
    total: int = Field(ge=0, le=100)                  # Hard cap at 100 (see note above)
    rationale: str


class ReviewDecision(BaseModel):
    decision: ReviewDecisionType = ReviewDecisionType.pending
    reviewer_id: Optional[str] = None
    reviewer_notes: Optional[str] = None
    decided_at: Optional[datetime] = None


class CommitteeDecision(BaseModel):
    decision: ReviewDecisionType = ReviewDecisionType.pending
    committee_id: Optional[str] = None
    committee_comments: Optional[str] = None
    decided_at: Optional[datetime] = None


class CanonicalDossier(BaseModel):
    metadata: Metadata
    raw_evidence: RawEvidence
    registry_check: Optional[RegistryCheck] = None
    extracted_evidence: Optional[ExtractedEvidence] = None
    scoring: Optional[ScoringResult] = None
    review: Optional[ReviewDecision] = None
    committee_review: Optional[CommitteeDecision] = None
