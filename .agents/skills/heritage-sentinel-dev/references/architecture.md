# Architecture Deep Dive

## Pipeline Data Flow

The pipeline runs as a FastAPI `BackgroundTask` triggered by `POST /submissions`
or `POST /submissions/with-photos`. It opens its own `AsyncSession` independent
of the request lifecycle.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          run_pipeline(submission_id)                        │
│                          backend/app/agents/pipeline.py                     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  1. Load Submission from DB → deserialize dossier JSON → CanonicalDossier  │
│                                                                            │
│  2. Stage 0: IntakeProcessor                                               │
│     ├─ Input:  dossier.raw_evidence.description                            │
│     ├─ Action: lingua language detection → Gemini translation if non-EN    │
│     ├─ Output: sets language_detected + translated_description             │
│     └─ Persist: status → registry_check                                    │
│                                                                            │
│  3. Stage 1: RegistryAgent                                                 │
│     ├─ Input:  location_name, country, translated_description              │
│     ├─ Action: SQL ilike match → PostgreSQL FTS (ts_rank) → Gemini compare │
│     ├─ Output: RegistryCheck (is_duplicate, matched_site, top_candidates)  │
│     ├─ Persist: status → registry_check                                    │
│     └─ Short-circuit: if duplicate → run_verification → exit               │
│                                                                            │
│  4. Stage 2: EvaluationAgent                                               │
│     ├─ Input:  location_name, country, translated_description, photo count │
│     ├─ Guard:  skip if combined input < 20 chars (auto-zero)               │
│     ├─ Step 1: Gemini extracts 8 evidence text fields (no scores)          │
│     ├─ Step 2: ScoringEngine assigns deterministic scores from criteria    │
│     ├─ Output: ExtractedEvidence + ScoringResult                           │
│     └─ Persist: status → evaluation                                        │
│                                                                            │
│  5. Stage 3: VerificationAgent                                             │
│     ├─ Input:  full dossier (registry_check + scoring)                     │
│     ├─ Rules:                                                              │
│     │   ├─ duplicate → auto-reject                                         │
│     │   ├─ total < 25 → auto-reject (junk)                                │
│     │   ├─ no scoring → route to reviewer_review                           │
│     │   └─ total >= 25 → route to reviewer_review                          │
│     ├─ Output: ReviewDecision + final SubmissionStatus                     │
│     └─ Persist: final status                                               │
│                                                                            │
└──────────────────────────────────────────────────────────────────────────────┘
```

Each stage persists the dossier to PostgreSQL via `_persist()`, so
`GET /submissions/{id}` always reflects current pipeline progress.

---

## Agent-by-Agent Breakdown

### IntakeProcessor (`intake_processor.py`)

- **Purpose**: Multilingual support — detect language, translate to English
- **Language detection**: `lingua-language-detector` with
  `minimum_relative_distance(0.9)` to reduce false positives
- **Translation**: Gemini 2.5 Flash with `temperature=0.1`
- **Gemini client**: `genai.Client(api_key=settings.GEMINI_API_KEY)` — module-level singleton
- **Fallback**: if detection fails → `"unknown"`, if translation fails → original text
- **Key detail**: detector is rebuilt on every call (no caching) — this is by
  design for memory safety but could be optimized

### RegistryAgent (`registry_agents.py`)

- **Purpose**: Check if submission duplicates an existing UNESCO World Heritage Site
- **Three-step process**:
  1. **SQL ilike** (fast path): `UnescoSite.name.ilike(f"%{site_name}%")` AND
     country ilike. Only runs if site_name >= 4 chars. If match → return
     `is_duplicate=True` immediately.
  2. **PostgreSQL FTS**: `plainto_tsquery()` + `ts_rank()` on the computed
     `search_vector` column. Returns top 5 candidates. On SQLite (tests),
     falls back to Python word-overlap matching.
  3. **Gemini comparison**: If best FTS score >= 0.01, asks Gemini to compare
     submission against top candidates. Uses `temperature=0.0` and
     `thinking_budget=0` for determinism. Returns JSON with `is_duplicate`,
     `confidence`, `matched_site`, `reasoning`.
- **Fallback**: if Gemini fails → falls back to FTS-only result (`is_duplicate=False`)

### EvaluationAgent (`evaluation_agent.py`)

- **Purpose**: Extract structured evidence and score it
- **Input quality gate**: If `len(location_name + description) < 20` chars,
  skips Gemini entirely and returns zero scores. Prevents hallucination on
  junk inputs.
- **Step 1 — Gemini extraction**: Sends the submission text with a structured
  prompt requesting 8 JSON fields aligned to UNESCO nomination pillars.
  Uses `temperature=0.1`, `thinking_budget=0`.
- **Step 2 — Deterministic scoring**: Passes `ExtractedEvidence` to
  `score_evidence()` in `scoring_engine.py`. No Gemini involvement in scoring.
- **JSON parsing**: `_extract_json()` strips markdown fences, tries
  `json.loads()`, falls back to regex `{...}` extraction.
- **Error handling**: If Gemini fails, populates all fields with
  "Extraction unavailable" (scores to 0 via scoring engine keyword matching).

### ScoringEngine (`scoring_engine.py`)

- **Purpose**: Deterministic, reproducible scoring of extracted evidence
- **Criteria source**: `data/scoring_criteria.json` — loaded once via `@lru_cache`
- **Algorithm**: For each of 8 categories:
  1. Check for "unavailable" keyword → score 0
  2. Find highest tier where at least one signal keyword appears in text
  3. Scale score within that tier based on signal density (found/total)
  4. Clamp to category maximum
- **Category weights** (total = 100):
  - Historic Features: /25 (OUV i, iii, iv)
  - Cultural Significance: /20 (OUV ii, v, vi)
  - Integrity: /15
  - Authenticity: /15
  - Geographic Context: /10 (OUV vii–x)
  - Documentation: /10
  - Management & Protection: /5
  - Supporting Evidence: /15 (text + photo bonus up to +5)
- **Photo bonus**: `min(photo_count * 2, 5)` added to supporting evidence score
- **Confidence labels**: ≥80 High, ≥60 Moderate, <60 Low

### VerificationAgent (`verification_agent.py`)

- **Purpose**: Route submissions to the correct outcome
- **Synchronous** — `run_verification()` is a regular function (not async)
- **Decision tree**:
  - `registry_check.is_duplicate == True` → auto-reject with note naming the matched site
  - `scoring is None` → route to `reviewer_review` (evaluation failed)
  - `scoring.total < 25` → auto-reject as junk, list weak categories
  - `scoring.total >= 25` → route to `reviewer_review` with confidence label
- **Returns**: `(updated_dossier, SubmissionStatus)`

---

## CanonicalDossier Schema

The `CanonicalDossier` Pydantic model is the central data structure. It is
stored as JSONB in the `submissions.dossier` column.

```
CanonicalDossier
├── metadata: Metadata
│   ├── submission_id: str             # "SUB-YYYY-MM-XXXXXXXX"
│   ├── submitted_by: str
│   ├── submitted_at: datetime
│   ├── location_name: str
│   ├── country: str
│   ├── coordinates: Optional[tuple]   # (lat, lon)
│   └── status: SubmissionStatus       # enum: pending → registry_check → evaluation → ...
├── raw_evidence: RawEvidence
│   ├── description: str
│   ├── photo_urls: list[str]
│   ├── language_detected: Optional[str]
│   └── translated_description: Optional[str]
├── registry_check: Optional[RegistryCheck]
│   ├── is_duplicate: bool
│   ├── matched_site: Optional[str]
│   ├── similarity_score: Optional[float]
│   ├── top_candidates: list[BM25Candidate]
│   └── checked_at: Optional[datetime]
├── extracted_evidence: Optional[ExtractedEvidence]
│   ├── historic_features: str
│   ├── cultural_significance: str
│   ├── integrity: str
│   ├── authenticity: str
│   ├── geographic_context: str
│   ├── documentation_quality: str
│   ├── management_protection: str
│   └── supporting_evidence: str
├── scoring: Optional[ScoringResult]
│   ├── historic_features: int (0-25)
│   ├── cultural_significance: int (0-20)
│   ├── integrity: int (0-15)
│   ├── authenticity: int (0-15)
│   ├── geographic_context: int (0-10)
│   ├── documentation: int (0-10)
│   ├── management_protection: int (0-5)
│   ├── supporting_evidence: int (0-15)
│   ├── total: int (0-100)
│   └── rationale: str
├── review: Optional[ReviewDecision]
│   ├── decision: ReviewDecisionType   # approved | rejected | pending
│   ├── reviewer_id: Optional[str]
│   ├── reviewer_notes: Optional[str]
│   └── decided_at: Optional[datetime]
└── committee_review: Optional[CommitteeDecision]
    ├── decision: ReviewDecisionType
    ├── committee_id: Optional[str]
    ├── committee_comments: Optional[str]
    └── decided_at: Optional[datetime]
```

### SubmissionStatus Enum

```
pending → registry_check → evaluation → verification →
  ├── reviewer_review → committee_review → approved
  │                                     └→ rejected
  └── rejected (auto: duplicate or junk)
```

---

## Database Schema

### `submissions` table

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key (auto uuid4) |
| `submission_id` | String | Unique, indexed. Format: `SUB-YYYY-MM-XXXXXXXX` |
| `status` | Enum(SubmissionStatus) | Indexed |
| `dossier` | JSONB | Full CanonicalDossier serialized |
| `created_at` | DateTime(tz) | `server_default=now()`, indexed |
| `updated_at` | DateTime(tz) | `server_default=now()`, `onupdate` trigger |

### `unesco_sites` table

| Column | Type | Notes |
|---|---|---|
| `id` | Integer | Primary key |
| `name` | String(512) | Indexed |
| `country` | String(256) | Indexed |
| `region` | String(256) | Nullable |
| `inscription_year` | Integer | Nullable |
| `criteria` | String(64) | Comma-separated OUV codes: "i,ii,vi" |
| `description` | Text | Nullable |
| `search_vector` | TSVECTOR (computed) | GIN indexed, auto-computed from name+country+description |

Indexes: `ix_unesco_sites_name`, `ix_unesco_sites_country`,
`ix_unesco_sites_name_country` (composite), `ix_unesco_sites_search_vector` (GIN).

---

## Gemini Integration Pattern

All agents use the same client pattern:

```python
from google import genai
from google.genai import types as genai_types
from app.core.config import settings

_client = genai.Client(api_key=settings.GEMINI_API_KEY)
_MODEL = "gemini-2.5-flash"

response = _client.models.generate_content(
    model=_MODEL,
    contents="...",
    config=genai_types.GenerateContentConfig(
        temperature=0.1,       # near-deterministic
        max_output_tokens=1024,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
    ),
)
```

- **SDK**: `google-genai` (new SDK, not the legacy `google-generativeai`)
- **Model**: `gemini-2.5-flash` across all agents
- **JSON parsing**: Both `registry_agents.py` and `evaluation_agent.py` have
  their own `_extract_json()` / `_parse_gemini_json()` functions that strip
  markdown code fences and use regex fallback
- **Thinking budget**: Set to 0 in RegistryAgent and EvaluationAgent for
  faster, more deterministic responses

---

## REST API Endpoints

All routes are under `/submissions` (defined in `submissions.py`):

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/submissions` | Create submission (JSON body), triggers pipeline |
| `POST` | `/submissions/with-photos` | Create with photo upload (multipart) |
| `POST` | `/submissions/{id}/photos` | Upload photos to existing submission |
| `GET` | `/submissions` | List all (optional `?status=` filter) |
| `GET` | `/submissions/stats` | Aggregate counts by status |
| `GET` | `/submissions/audit-log` | Finalized decisions only |
| `GET` | `/submissions/{id}` | Full dossier detail |
| `GET` | `/submissions/{id}/public` | Public-safe subset |
| `PATCH` | `/submissions/{id}/review` | Reviewer decision (committee_review or rejected) |
| `PATCH` | `/submissions/{id}/finalize` | Committee final decision (approved or rejected) |
| `GET` | `/health` | Health check (defined in `main.py`) |

---

## Alembic Migration Chain

```
d1637cbc70cb  — create submissions table (initial)
    ↓
e4e3b1c6d6f2  — add unesco_sites table + FTS search_vector + GIN index
    ↓
c7a8b9c1d2e3  — add reviewer_review + committee_review to SubmissionStatus enum
```

The template for new migrations is `alembic/script.py.mako`.
