# Heritage Sentinel AI

## Day 2 Progress Report

### Project Status Summary

Day 2 is **in progress**. Building on the Day 1 infrastructure and RegistryAgent foundation, Day 2 has focused on completing the full three-agent pipeline — including the IntakeProcessor (multilingual), EvaluationAgent (Gemini extraction + deterministic scoring), VerificationAgent (Confidence Card and HITL routing), and a live real-time frontend with pipeline tracking, review queue, and dashboard. End-to-end integration was verified and all 14 tests pass inside Docker.

---

## Work Completed

### Responsibility 5 — IntakeProcessor (Multilingual Stage 0)

Implemented the pre-pipeline intake stage that normalises all incoming submissions to English before the agents run:

* **Language Detection**: Uses `lingua-language-detector` (`LanguageDetectorBuilder.from_all_languages`) to detect the ISO 639-1 language code of the incoming description text.
* **Gemini Translation**: If the detected language is not English, calls Gemini 2.5 Flash to translate the description to English with `temperature=0.1` for consistency.
* **Dossier Update**: Stores `language_detected` and `translated_description` in `raw_evidence`. All downstream agents (`RegistryAgent`, `EvaluationAgent`) receive translated text.
* **Graceful Fallback**: Translation or detection failures are caught and logged. The pipeline continues with the original description rather than crashing.

**File**: `backend/app/agents/intake_processor.py`

*Verified Result*:
* Multilingual detection and translation confirmed working via Architecture-Compliance audit.
* Pipeline continues cleanly on both English and non-English inputs.

Status: Completed

---

### Responsibility 6 — EvaluationAgent (Stage 2)

Implemented the two-step evaluation architecture specified in `PROJECT.md`, now fully calibrated to align with official UNESCO Operational Guidelines (WHC.25/01) across 8 dimensions:

**Step 1 — Gemini Evidence Extraction**:
* Calls Gemini 2.5 Flash with a structured extraction prompt requesting a JSON object with eight evidence fields:
  * `historic_features` — Outstanding Universal Value in human history, architecture, and archaeology (OUV criteria i, iii, iv)
  * `cultural_significance` — Cultural exchange, living traditions, intangible heritage, and traditional land use (OUV criteria ii, v, vi)
  * `integrity` — Wholeness and intactness of the property (required for all nominations)
  * `authenticity` — Authenticity of cultural heritage in materials, form, design, use, and setting (required for cultural sites)
  * `geographic_context` — Natural values, landscape setting, and ecological significance (OUV criteria vii–x)
  * `documentation_quality` — Quality and depth of academic, governmental, and archival documentation
  * `management_protection` — Legal protection framework and management plan
  * `supporting_evidence` — Visual evidence (photos, videos, surveys) submitted
* Uses `temperature=0.1` and `max_output_tokens=1024` for near-deterministic extraction.
* JSON parsing is robust: strips markdown fences, then falls back to regex extraction if standard parsing fails.

**Step 2 — Deterministic ScoringEngine**:
* Gemini assigns **no scores**. All scoring is handed off to `ScoringEngine`.
* Reads `data/scoring_criteria.json` (cached via `@lru_cache`) defining keyword signal tiers and maximum scores per category.
* Calibrated Scoring breakdown (total out of 100):
  * Historic Features: `/25`
  * Cultural Significance: `/20`
  * Integrity: `/15`
  * Authenticity: `/15`
  * Geographic Context: `/10`
  * Documentation Quality: `/10`
  * Management & Protection: `/5`
  * Supporting Evidence: `/15` (includes +2 per photo, capped at +5)
* Identical inputs always produce identical scores — no model variance.
* **Dossier Model Validation Fix**: Modified `backend/app/models/dossier.py` to cap `ScoringResult.total` at `le=100` instead of `le=115` to correct the validation bounds since the sum of the 7 core pillars (25+20+15+15+10+10+5) is exactly 100.

**Error Handling**: If Gemini fails, fallback text `"Extraction unavailable — evaluation service error."` is used for all fields, resulting in a near-zero score which routes the submission for auto-rejection via VerificationAgent.

**Files**: `backend/app/agents/evaluation_agent.py`, `backend/app/agents/scoring_engine.py`

Status: Completed

---

### Responsibility 7 — VerificationAgent (Stage 3)

Implemented the final pipeline stage that packages the Confidence Card and routes the submission:

* **Duplicate Gate**: If `registry_check.is_duplicate = true`, auto-rejects with reviewer note `"Auto-rejected: duplicate of existing UNESCO site '{matched}'"`. Pipeline skips EvaluationAgent entirely for duplicate submissions.
* **Scoring Threshold Gate**:
  * Score `< 60` → `status = rejected`, auto-rejected with note showing exact score and rationale.
  * Score `>= 60` → `status = verification`, routes to human archaeologist review queue.
  * Score `>= 80` → labelled "High Confidence"
  * Score `60–79` → labelled "Medium Confidence"
* **No Scoring Available** (evaluation failure): Routes to `verification` for manual review rather than silently rejecting.

**Hardcoded Threshold**: `_AUTO_REJECT_THRESHOLD = 60` (flagged as DEBT-06 for future configuration externalisation).

**File**: `backend/app/agents/verification_agent.py`

*Verified Result*:
* 5/5 VerificationAgent unit tests pass (boundary score 60, score 59, high score 85, duplicate, no scoring cases).

Status: Completed

---

### Responsibility 8 — Agent Pipeline Orchestration

Implemented the sequential four-stage pipeline running as a FastAPI `BackgroundTask`:

* **Stage 0**: IntakeProcessor — language detection and translation
* **Stage 1**: RegistryAgent — BM25 + Gemini duplicate detection
* **Stage 2**: EvaluationAgent — Gemini extraction + deterministic scoring
* **Stage 3**: VerificationAgent — Confidence Card routing + HITL gate

Key architectural decisions:
* **Per-stage DB persistence**: After each stage, `_persist()` writes the updated dossier and status to PostgreSQL. This means `GET /submissions/{id}` always reflects live progress during background execution.
* **Independent DB session**: The pipeline opens its own `AsyncSessionLocal` session, decoupled from the HTTP request lifecycle.
* **Duplicate short-circuit**: If RegistryAgent detects a duplicate, pipeline skips EvaluationAgent and goes directly to VerificationAgent.
* **Per-stage exception handling**: Each stage is wrapped in `try/except`. A failure in one stage logs an error but does not crash the entire pipeline.

**File**: `backend/app/agents/pipeline.py`

Status: Completed

---

### Responsibility 9 — Real-Time Frontend (Live Pipeline Tracking)

Rebuilt and extended the Next.js frontend to support live pipeline status, a live review queue, and a live dashboard:

* **Submit Page** (`/submit`): Form for submitting location name, country, description, and submitter name. On success, redirects to `/review/{submission_id}`. Includes polling (`setInterval`) to detect when the pipeline completes.
* **Review Detail Page** (`/review/[id]`): Renders the full Confidence Card once the pipeline reaches `verification`, `approved`, or `rejected` state. Displays score breakdown (historic, cultural, geographic, documentation, supporting evidence), registry check status, extracted evidence text, and approve/reject action buttons.

  > ⚠️ **Known UX Bug**: If the user navigates directly to this page while the pipeline is still running, the "Pipeline in progress" loading screen has no polling loop and will remain stuck until manual reload. Tracked in Frontend-Audit.md and Integration-Test-Report.md as an open issue.

* **Review Queue** (`/review`): Tabbed interface showing submissions filtered by `verification` (Awaiting Review), `approved`, and `rejected`. Renders score, location, country, and status badge per card.
* **Dashboard** (`/dashboard`): Displays aggregate stats (total, in review, approved, rejected, duplicates blocked) and a recent submissions table.

  > ⚠️ **Known Performance Issue**: Both the dashboard and review queue fetch the full list and then fire a per-row `GET /submissions/{id}` to obtain the heritage score (N+1 pattern). Tracked as PERF-01 and DEBT-01 for resolution.

Status: Completed (with two known open issues noted above)

---

### Responsibility 10 — Day 2 Test Suite

Extended the test suite to cover the new agents added on Day 2 and resolved all local testing import issues:

**EvaluationAgent Tests** (Gemini mocked):
* `test_evaluation_agent_scores_correctly` — verifies extracted evidence and deterministic scoring are non-zero for a well-described site.
* `test_evaluation_agent_handles_gemini_failure` — verifies pipeline gracefully falls back and produces near-zero score when Gemini raises an exception.

**VerificationAgent Tests** (pure Python, no mocks needed):
* `test_verification_routes_high_score_to_review` — score 93 → `verification`
* `test_verification_auto_rejects_low_score` — score 19 → `rejected`
* `test_verification_rejects_duplicate` — duplicate flag → `rejected`
* `test_verification_routes_boundary_score_60` — score 60 → `verification` (inclusive boundary)
* `test_verification_auto_rejects_score_59` — score 59 → `rejected`

**File**: `tests/test_evaluation_agent.py`

**Import & Test Configuration Fixes**:
* Added root and backend `conftest.py` and `pytest.ini` files to dynamically append correct paths to `sys.path`. This resolves `ModuleNotFoundError: No module named 'app'` when running pytest locally on the host.
* Configured `docker-compose.yml` to mount the test config files (`pytest.ini` and `conftest.py`) into the container to align local and containerized testing.
* Added test dependencies (`pytest-mock` and `anyio[asyncio]`) to `requirements.txt`.
* Updated `tests/test_evaluation_agent.py` to mock and validate the calibrated scoring dimensions and score assertions.

*Verified Result*:
* All 14 total unit tests pass successfully both locally on the host and inside Docker.

Status: Completed

---

## Integration Verification Results

### Passed
* ✅ Full 4-stage pipeline verified end-to-end (duplicate path and non-duplicate path)
* ✅ Duplicate detection auto-rejects correctly (Ajanta Caves → `rejected`, `similarity_score: 1.0`)
* ✅ High-confidence submission routes to review queue (`93/100` → `verification`)
* ✅ Human-in-the-loop approve/reject flow updates status and dashboard stats
* ✅ All 14 tests passing both locally on the host and in Docker
* ✅ API endpoints fully operational (all 13 endpoint/method combinations verified in API-Audit.md)
* ✅ Frontend pages `/`, `/submit`, `/review`, `/review/[id]`, `/dashboard` load without errors

### Known Open Issues (Day 2)

| ID | Issue | Severity | Tracker |
|---|---|---|---|
| UX-01 | Review detail page has no polling when pipeline is running — user must manually reload | Medium | Frontend-Audit.md, Integration-Test-Report.md |
| PERF-01 | N+1 HTTP fetch loop in dashboard and review queue to retrieve scores | High | Performance-Audit.md, Technical-Debt.md |
| SEC-01 | No authentication on review endpoints — any user can approve/reject | Critical | Security-Audit.md |
| SEC-02 | File uploads accept any extension including `.html` (stored XSS risk) | High | Security-Audit.md |
| DATASET | UNESCO dataset is 41 sites, not the expected ~1100 sites | High | Dataset-Audit-Report.md |
| DEBT-02 | `const API = ...` hardcoded on every frontend page | Medium | Technical-Debt.md |

### Resolved Issues (Day 2)

* **HOST-TEST**: Fixed `pytest` on host failing due to import issues. Adding `conftest.py` and `pytest.ini` files resolved the `ModuleNotFoundError` completely, and all 14 tests now pass successfully both locally and in Docker.

---

## Outstanding Work (Day 2 — In Progress)

### Still In Progress / Planned for Remainder of Day 2

* **SEC-01**: Authentication layer (JWT / OAuth2) on review endpoints
* **UX-01**: Add polling loop to `/review/[id]` page when pipeline status is non-terminal
* **PERF-01 / DEBT-01**: Enrich `GET /submissions` list response with score from dossier to eliminate N+1 loop
* **DATASET**: Commit the full ~1100-site UNESCO dataset and reseed
* **DEBT-02**: Extract shared `const API` into `frontend/src/lib/api.ts` utility module

---

## Day 2 Outcome (So Far)

The full three-agent pipeline is operational end-to-end. Multilingual intake, duplicate detection, evidence extraction, deterministic scoring, Confidence Card routing, and the HITL review workflow are all implemented and verified. Frontend is live with real-time pipeline tracking. 14 tests passing. Remaining work focuses on security hardening, UX polish, performance optimisations, and dataset expansion.
