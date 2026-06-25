from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class SubmissionStatus(str, Enum):
    pending = "pending"
    registry_check = "registry_check"
    evaluation = "evaluation"
    verification = "verification"
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
    historic_features: str
    cultural_significance: str
    geographic_context: str
    documentation_quality: str
    supporting_evidence: str


class ScoringResult(BaseModel):
    historic_features: int = Field(ge=0, le=30)
    cultural_significance: int = Field(ge=0, le=25)
    geographic_context: int = Field(ge=0, le=15)
    documentation: int = Field(ge=0, le=15)
    supporting_evidence: int = Field(ge=0, le=15)
    total: int = Field(ge=0, le=100)
    rationale: str


class ReviewDecision(BaseModel):
    decision: ReviewDecisionType = ReviewDecisionType.pending
    reviewer_id: Optional[str] = None
    reviewer_notes: Optional[str] = None
    decided_at: Optional[datetime] = None


class CanonicalDossier(BaseModel):
    metadata: Metadata
    raw_evidence: RawEvidence
    registry_check: Optional[RegistryCheck] = None
    extracted_evidence: Optional[ExtractedEvidence] = None
    scoring: Optional[ScoringResult] = None
    review: Optional[ReviewDecision] = None
