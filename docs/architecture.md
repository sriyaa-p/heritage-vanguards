# Heritage Sentinel AI — Architecture

## Purpose

Heritage Sentinel AI helps communities submit potential cultural heritage sites for expert review. The system does **not** designate UNESCO status automatically. It structures evidence, checks for duplicates, scores the submission transparently, and routes the result to a human reviewer.

## High-Level Flow

```text
Community Submission
        │
        ▼
IntakeProcessor
(language detection + translation)
        │
        ▼
RegistryAgent
(SQL match + PostgreSQL FTS + Gemini comparison)
        │
   Duplicate?
   ├── Yes → VerificationAgent → Auto-reject as existing UNESCO site
   └── No
        ▼
EvaluationAgent
(Gemini evidence extraction + deterministic scoring)
        │
        ▼
VerificationAgent
(score threshold + confidence-card routing)
        │
        ▼
Human Reviewer
(approve/reject final decision)
```

## Backend Components

### FastAPI App

Entry point: `backend/main.py`

Responsibilities:
- Initializes the FastAPI application
- Enables CORS for the frontend
- Mounts uploaded photos under `/uploads`
- Registers submission routes
- Provides `/health` for service checks

### Submission API

File: `backend/app/api/routes/submissions.py`

Endpoints:
- `POST /submissions` — create metadata-only submission
- `POST /submissions/with-photos` — create submission and upload photos together
- `POST /submissions/{submission_id}/photos` — add photos to an existing submission
- `GET /submissions` — list submissions, optionally filtered by status
- `GET /submissions/stats` — dashboard metrics
- `GET /submissions/{submission_id}` — retrieve full dossier
- `PATCH /submissions/{submission_id}/review` — human reviewer approve/reject action

Photo uploads default to `/data/uploads` in Docker. Local/test environments can override this with `UPLOADS_DIR` or fall back to `data/uploads` if `/data` is unavailable.

## Agent Pipeline

File: `backend/app/agents/pipeline.py`

The pipeline runs as a FastAPI background task and persists state after each stage. This makes submissions recoverable and lets the frontend poll live status.

Statuses:
- `pending`
- `registry_check`
- `evaluation`
- `verification`
- `approved`
- `rejected`

### Stage 0 — IntakeProcessor

File: `backend/app/agents/intake_processor.py`

Responsibilities:
- Detects the source language with `lingua-language-detector`
- Translates non-English submissions to English with Gemini 2.5 Flash
- Stores both the detected language and translated description in the dossier

Why it matters:
- Registry checks and evidence extraction operate on consistent English text
- The original description remains preserved in `raw_evidence.description`

### Stage 1 — RegistryAgent

File: `backend/app/agents/registry_agents.py`

Responsibilities:
1. Exact/fuzzy SQL match using site name + country
2. PostgreSQL Full-Text Search using `tsvector`, `plainto_tsquery`, and `ts_rank`
3. Gemini semantic comparison against top candidates when FTS finds plausible matches

Duplicate rule:
- A submission is a duplicate only if it clearly refers to the same physical UNESCO World Heritage Site.
- Nearby sites are **not** duplicates unless they are the same listed property.

### Stage 2 — EvaluationAgent

File: `backend/app/agents/evaluation_agent.py`

Responsibilities:
1. Gemini extracts structured evidence only
2. Pydantic validates the extraction schema
3. The deterministic scoring engine assigns points

Important guardrail:
- Gemini never assigns the heritage score.
- Identical extracted evidence should produce identical scores.

Minimum-quality gate:
- Very short submissions are treated as insufficient evidence and skip Gemini evaluation.

### Stage 3 — VerificationAgent

File: `backend/app/agents/verification_agent.py`

Responsibilities:
- Confirmed duplicate → auto-rejected
- Score below 25 → auto-rejected as insufficient evidence/junk
- Score 25 or above → routed to human review
- Missing score → routed to human review

This preserves the human-in-the-loop rule for genuine submissions.

## Canonical Dossier

File: `backend/app/models/dossier.py`

The Canonical Dossier is the system’s single source of truth. It is stored as JSONB in PostgreSQL and passed between agents.

Sections:
- `metadata` — submission ID, submitter, site name, country, status
- `raw_evidence` — original description, photo URLs, language metadata, translation
- `registry_check` — duplicate flag, matched site, top candidates
- `extracted_evidence` — structured UNESCO evidence categories
- `scoring` — category scores, total, rationale
- `review` — reviewer decision, notes, timestamp

## Scoring Architecture

File: `backend/app/agents/scoring_engine.py`
Data: `data/scoring_criteria.json`

The scoring engine is deterministic and UNESCO-aligned.

| Category | Max Points |
|---|---:|
| Historic Features | 25 |
| Cultural Significance | 20 |
| Integrity | 15 |
| Authenticity | 15 |
| Geographic Context | 10 |
| Documentation Quality | 10 |
| Management & Protection | 5 |
| Supporting Evidence | 15 |

Notes:
- Supporting evidence includes a photo-count bonus, capped at +5.
- Final total is capped by the Pydantic model at 100.
- Confidence labels: High (80+), Moderate (60–79), Low (<60).

## Database

### Tables

`submissions`
- Stores submission status and full dossier JSONB
- Indexed by `submission_id`, `status`, and timestamps

`unesco_sites`
- Stores UNESCO site registry data
- Includes a computed `search_vector` for PostgreSQL FTS
- Seeded from `data/processed/unesco_sites_clean.json`

### Migrations

Alembic migrations live in `backend/alembic/versions/`.

Important migrations:
- `d1637cbc70cb_create_submissions_table.py`
- `e4e3b1c6d6f2_add_unesco_sites_and_fts.py`

## Data Seeding

Script: `scripts/seed_database.py`

Behavior:
- Reads `data/processed/unesco_sites_clean.json`
- Upserts records by `(name, country)`
- Can reset the table with `--reset`

Docker entrypoint:
1. Sync/create database tables
2. Fetch latest UNESCO dataset
3. Seed database
4. Start Uvicorn

## Frontend

Path: `frontend/src/app/`

Pages:
- `/` — landing page
- `/submit` — community submission form with photo upload and live pipeline tracker
- `/dashboard` — admin metrics and recent submissions
- `/review` — review queue with filters
- `/review/[id]` — confidence card and reviewer decision UI

Frontend talks to the backend through `NEXT_PUBLIC_API_URL`, defaulting to `http://localhost:8000`.

## Quality and Testing

Current test coverage includes:
- EvaluationAgent + VerificationAgent scoring/routing behavior
- RegistryAgent duplicate lookup behavior with SQLite test fallback
- IntakeProcessor translation/no-translation behavior
- Pipeline orchestration and duplicate skip behavior
- API stats logic and health route behavior
- Settings validation behavior

Recommended test command:

```bash
pytest tests/ -q
```

Local pyenv command used during development:

```bash
~/.pyenv/versions/myenv311/bin/pytest tests/ -q
```

## Operational Notes

Environment variables:
- `GEMINI_API_KEY` — required for real Gemini calls; required in production/staging
- `DATABASE_URL` — optional if Postgres parts are provided
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` — used to build Docker database URL
- `ENV` — defaults to `development`
- `UPLOADS_DIR` — defaults to `/data/uploads`

Health check:

```bash
GET /health
```

Expected response:

```json
{"status": "ok", "service": "heritage-sentinel-ai"}
```

## Design Principles

1. Human reviewer makes final decisions for genuine submissions.
2. Gemini extracts evidence; deterministic code assigns scores.
3. PostgreSQL stores the persistent dossier state.
4. Duplicate detection is conservative: uncertain means not duplicate.
5. Tests should run without real Gemini credentials.
6. Docker remains production-like, while local/test environments remain runnable.
