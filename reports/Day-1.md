# Heritage Sentinel AI

## Day 1 Progress Report

### Project Status Summary

During Day 1 of the Heritage Sentinel AI project, the foundational infrastructure and the workflow components for the first agent (RegistryAgent) were successfully set up. This includes Dockerizing the PostgreSQL, FastAPI backend, and Next.js frontend services, creating the database schema with Alembic migrations, implementing the UNESCO database seed script, defining the core Canonical Dossier models, and building and testing the RegistryAgent duplicate detection logic using BM25 search. 

---

## Work Completed

### Responsibility 1 — Project Skeleton

Documented project skeleton setup consisting of:
* **Docker Compose setup**: Defines services for `postgres`, `backend`, and `frontend` allowing the complete stack to run in unified, isolated environments.
* **Backend container**: Runs a FastAPI application with Python 3.11, configured with Uvicorn.
* **Frontend container**: Runs a Next.js application with React and Tailwind CSS.
* **PostgreSQL container**: Uses PostgreSQL 16-alpine with volume mounts for persistent data storage.
* **.env.example**: Template for setting up environment variables (Postgres credentials, database URLs, and API keys).
* **requirements.txt**: Unified list of Python dependencies (FastAPI, SQLAlchemy, Alembic, psycopg2-binary, sentence-transformers, etc.).
* **Repository structure**: Well-structured hierarchy separating `backend/`, `frontend/`, `data/`, `scripts/`, `tests/`, and documentation `docs/`.

Status: Completed

---

### Responsibility 2 — Database Schema

Implementation of the database models and persistence layers:
* **SQLAlchemy models**: Integrated SQLAlchemy ORM models (`Base` and `UnescoSite` in `dossier.py` and `Submission` in `submission.py`).
* **submissions table**: Schema defined with columns for `id` (UUID), `submission_id` (String), `status` (Enum), `dossier` (JSONB), and timestamps.
* **Alembic migrations**: Initial database migrations generated and executed successfully to apply the database schema.
* **JSONB Canonical Dossier storage**: Structured dossier data stored in a native PostgreSQL `JSONB` column to allow flexible metadata and extraction updates.

Status: Completed

---

### Responsibility 3 — UNESCO Dataset & Registry Foundation

Integration of the historical site registry dataset:
* **UNESCO dataset integration**: Processed raw UNESCO World Heritage Site data cleaned and stored as `data/processed/unesco_sites_clean.json`.
* **heritage_sites table**: Map of original sites.
* **Seed script**: `scripts/seed_database.py` implemented to parse and insert/upsert the UNESCO site list into the database, handling duplicates gracefully.
* **RegistryAgent dataset availability**: Seeding provides the underlying ground-truth registry required for deduplication.

*Verified Result*:
* Seed script executed successfully inside the Docker container.
* 41 UNESCO sites were successfully inserted/updated in the PostgreSQL database.

Status: Completed

---

### Responsibility 4 — Canonical Dossier Models

Defined the key Pydantic data schemas representing the progress of a nomination dossier through the agent workflow:
* **Metadata**: Submission identification, submitter information, timestamp, and status.
* **RawEvidence**: Text description and list of photo URLs.
* **RegistryCheck**: Duplicate status, matched site info, similarity scores, and candidate search lists.
* **ExtractedEvidence**: Structured analysis of historic features, cultural significance, geographic context, documentation, and supporting evidence.
* **ScoringResult**: Numeric scores for each heritage criteria alongside qualitative rationales (total score out of 100).
* **ReviewDecision**: Decision status (approved/rejected/pending), reviewer ID, timestamp, and notes.

Status: Completed

---

### RegistryAgent Progress

Implementation and testing of the first pipeline agent:
* **Duplicate detection logic**: Matches incoming nominations against the seeded UNESCO registry using both exact and fuzzy checks.
* **BM25 retrieval**: Uses BM25 algorithm to extract candidate historical sites based on text similarities.
* **RegistryCheck generation**: Populates the `RegistryCheck` model with duplicate status, matching similarity score, and top candidate sites.
* **RegistryAgent unit tests**: Defined unit tests in `tests/test_registry_agent.py`.

*Verified Result*:
* 7/7 RegistryAgent tests passing successfully under pytest execution.

Status: Completed

---

### Bug Fixes Completed

#### Seed Script Conflict Resolution

During conflict resolution, two separate implementations of the database seeding script were merged into `scripts/seed_database.py`. 
* **Fix**: Removed the entire legacy psycopg2 implementation block, keeping only the async SQLAlchemy version.
* **Portability**: Updated `sys.path` resolution to support both local host execution and container execution where the backend is mounted at `/app`.
* **Verification**: Syntax validation checks (`python3 -m py_compile`) and docker execution successfully verified that the script correctly seeds 41 sites in PostgreSQL without `ModuleNotFoundError` or syntax errors.

Status: Completed

---

## Integration Verification Results

### Passed

* ✅ API verification passed (POST /submissions, GET /submissions, GET /submissions/{id}, PATCH /submissions/{id}/review endpoints are fully operational and verified through an end-to-end integration workflow)
* ✅ UI verification passed (Frontend pages `/`, `/submit`, `/review`, and `/dashboard` load and render successfully without 404s or console/network errors)
* Docker containers running
* PostgreSQL healthy
* Backend running
* Frontend running
* Alembic migrations successful
* UNESCO dataset seeded
* RegistryAgent tests passing
* Canonical Dossier validation passing

### Failed

* None. All verification checks passed.

---

## Outstanding Work

### API Layer

* None. Completed and verified.

### Frontend Integration

* None. Completed and verified.

### Agent 2 — EvaluationAgent

Not started.

Planned scope:
* Gemini evidence extraction
* Deterministic scoring engine
* Confidence calculation
* Canonical Dossier updates

---

## Day 1 Outcome

Infrastructure, database layer, RegistryAgent foundation, dataset integration, and Canonical Dossier architecture are complete. End-to-end MVP infrastructure is now operational through the Verification layer, and Agent 2 (EvaluationAgent) is now ready to begin. Can start tomorrow.
