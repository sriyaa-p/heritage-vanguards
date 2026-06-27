# Open Issues Fix Report

**Date**: June 26, 2026  
**Branch**: `sriya-fix-audit-findings` (from `main`)  
**Author**: Antigravity AI (on behalf of sriya-p)

---

## Summary

This report documents the implementation of 7 in-scope audit findings identified across 13 project reports. All fixes are surgical — no refactors, no new dependencies, no out-of-scope changes.

---

## Implemented Issues

| Issue ID | Title | Severity | Status |
|---|---|---|---|
| **DEBT-02** | Shared API Configuration | High | ✅ Fixed |
| **PERF-01 / DEBT-01** | Frontend N+1 Fetch Removal | Critical | ✅ Fixed |
| **UX-01** | Review Detail Page Polling | Medium | ✅ Fixed |
| **SEC-02** | File Upload Extension Validation | High | ✅ Fixed |
| **DB-01** | Redundant Index on `UnescoSite.id` | Low | ✅ Fixed |
| **DB-02** | Missing Index on `Submission.status` | Medium | ✅ Fixed |
| **DB-03** | Missing Index on `Submission.created_at` | Medium | ✅ Fixed |

---

## Files Modified

### New Files
| File | Purpose |
|---|---|
| `frontend/src/lib/api.ts` | Shared API base URL constant (DEBT-02) |

### Modified Files
| File | Issue(s) | Change Description |
|---|---|---|
| `frontend/src/app/review/[id]/page.tsx` | DEBT-02, UX-01 | Replaced inline API constant with shared import; added polling `useEffect` for non-terminal pipeline states |
| `frontend/src/app/review/page.tsx` | DEBT-02, PERF-01 | Replaced inline API constant; removed `Promise.all` N+1 enrichment loop, now reads `score` from list response |
| `frontend/src/app/dashboard/page.tsx` | DEBT-02, PERF-01 | Replaced inline API constant; removed `Promise.all` N+1 enrichment loop, now reads `score` from list response |
| `frontend/src/app/submit/page.tsx` | DEBT-02 | Replaced inline API constant with shared import; removed redundant re-declaration inside `handleSubmit` |
| `backend/app/api/routes/submissions.py` | PERF-01, SEC-02 | Added `score` field to `GET /submissions` list response; added image extension whitelist to upload endpoint |
| `backend/app/models/dossier.py` | DB-01 | Removed `index=True` from `UnescoSite.id` primary key column |
| `backend/app/models/submission.py` | DB-02, DB-03 | Added `index=True` to `status` and `created_at` columns |

### Files NOT Modified (Confirmed Unaffected)
- `backend/app/agents/*` — No agent logic changes
- `backend/app/agents/pipeline.py` — Pipeline flow unchanged
- `backend/app/agents/scoring_engine.py` — Scoring logic unchanged
- `backend/app/agents/verification_agent.py` — Verification logic unchanged
- `backend/app/agents/registry_agents.py` — Registry logic unchanged
- `scripts/seed_database.py` — Seed script unchanged
- `docker-compose.yml` — Docker config unchanged
- `frontend/src/app/page.tsx` — Landing page unchanged
- `frontend/src/app/layout.tsx` — Layout unchanged
- `frontend/src/app/globals.css` — Styles unchanged
- `data/scoring_criteria.json` — Scoring criteria unchanged

---

## Detailed Fix Descriptions

### DEBT-02 — Shared API Configuration
- **Created** `frontend/src/lib/api.ts` exporting `const API`.
- **Replaced** hardcoded `const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"` in all 4 page files with `import { API } from "@/lib/api"`.
- **Removed** redundant re-declaration at `submit/page.tsx` line 119 (inside `handleSubmit`).

### PERF-01 / DEBT-01 — N+1 Fetch Elimination
- **Backend**: Added `"score"` field to the `GET /submissions` list endpoint response, extracted from `dossier.scoring.total`.
- **Frontend (review/page.tsx)**: Removed `Promise.all` loop that fired a `GET /submissions/{id}` per row. Now maps `row.score` directly.
- **Frontend (dashboard/page.tsx)**: Same pattern — removed enrichment loop, reads `row.score` from list response.
- **Net effect**: Loading the review queue or dashboard now makes **1 HTTP request** instead of **N+1**.

### UX-01 — Review Detail Page Polling
- **Added** a second `useEffect` to `review/[id]/page.tsx` that activates when `status` is `pending`, `registry_check`, or `evaluation`.
- **Polls** `GET /submissions/{id}` every 2 seconds.
- **Stops** when status becomes `verification`, `approved`, or `rejected`, and updates the dossier state.
- **Pattern**: Mirrors the existing `PipelineTracker` polling in `submit/page.tsx` lines 22-41.

### SEC-02 — File Upload Extension Validation
- **Added** `_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}` whitelist.
- **Added** `.lower()` normalization on the extracted extension.
- **Rejects** non-whitelisted extensions with `HTTPException(400)` and a descriptive error message.
- **No new dependencies** — pure string comparison.

### DB-01 — Redundant Index Removal
- **Changed** `id = Column(Integer, primary_key=True, index=True)` → `id = Column(Integer, primary_key=True)` in `UnescoSite`.
- The `primary_key=True` constraint already creates a unique B-tree index in PostgreSQL.

### DB-02 + DB-03 — Missing Index Addition
- **Added** `index=True` to `Submission.status` column definition.
- **Added** `index=True` to `Submission.created_at` column definition.
- These indexes will take effect when a new Alembic migration is generated and applied.

---

## Verification Results

### Backend Test Suite
- **Command**: `docker compose exec -w /app backend python -m pytest /tests -v`
- **Result**: **14/14 tests PASSED** ✅

```
tests/test_evaluation_agent.py::test_verification_routes_high_score_to_review PASSED
tests/test_evaluation_agent.py::test_verification_auto_rejects_low_score PASSED
tests/test_evaluation_agent.py::test_verification_rejects_duplicate PASSED
tests/test_evaluation_agent.py::test_verification_routes_boundary_score_60 PASSED
tests/test_evaluation_agent.py::test_verification_auto_rejects_score_59 PASSED
tests/test_evaluation_agent.py::test_evaluation_agent_scores_correctly PASSED
tests/test_evaluation_agent.py::test_evaluation_agent_handles_gemini_failure PASSED
tests/test_registry_agent.py::test_exact_duplicate_detected PASSED
tests/test_registry_agent.py::test_partial_name_match_is_duplicate PASSED
tests/test_registry_agent.py::test_non_duplicate_returns_false PASSED
tests/test_registry_agent.py::test_top_candidates_populated PASSED
tests/test_registry_agent.py::test_checked_at_is_iso_timestamp PASSED
tests/test_registry_agent.py::test_result_validates_as_registry_check PASSED
tests/test_registry_agent.py::test_country_mismatch_not_duplicate PASSED
```

### Manual Verification Expectations

#### Review Detail Page (UX-01)
- Navigate to `/review/[id]` while pipeline is running → page should show spinner and auto-update every 2s
- Once pipeline finishes (status becomes `verification`/`approved`/`rejected`) → polling stops, Confidence Card renders

#### Dashboard (PERF-01)
- Browser DevTools Network tab → loading `/dashboard` should show **2 requests**: `GET /submissions/stats` + `GET /submissions`
- Previously would show **N+1 requests** (1 list + 1 per row)

#### Review Queue (PERF-01)
- Browser DevTools Network tab → loading `/review` should show **1 request**: `GET /submissions?status=verification`
- Previously would show **N+1 requests**

#### Upload Validation (SEC-02)
- Upload `.jpg` → ✅ 200 OK
- Upload `.png` → ✅ 200 OK
- Upload `.html` → ❌ 400 Bad Request with error message
- Upload `.txt` → ❌ 400 Bad Request with error message
- Upload `.pdf` → ❌ 400 Bad Request with error message

#### Database (DB-01, DB-02, DB-03)
- Application starts successfully after model changes ✅ (confirmed via Docker test run)
- No Alembic migrations generated automatically (as specified)

---

## Not Implemented (Confirmed Out of Scope)

The following issues were **explicitly excluded** per the implementation plan:

| Issue | Reason |
|---|---|
| SEC-01 (Authentication) | Requires JWT/OAuth2 — new dependency |
| SEC-03 (Upload size limits) | Requires python-magic — new dependency |
| SEC-04 (Rate limiting) | Requires slowapi/Redis — new dependency |
| PERF-02 (BM25 cache) | Architectural refactor |
| PERF-03 (Seed script N+1) | Acceptable at 41 sites |
| PERF-04 (Duplicate SQL) | Medium-priority refactor |
| PERF-05 (API pagination) | Architectural addition |
| DEBT-03 (Pipeline retry) | Requires task queue |
| DEBT-04 (Test coverage) | Enhancement |
| DEBT-05 (JSONB handling) | Refactor |
| DEBT-06 (Hardcoded threshold) | Low-priority config |
| DATASET (41 vs ~1100 sites) | Requires dataset procurement |

---

## Unexpected Observations

1. **Local pytest fails**: Running `pytest` locally on the host machine fails with `ModuleNotFoundError: No module named 'sqlalchemy'` because the host Python environment does not have project dependencies installed. This is a **pre-existing issue** documented in `Deployment-Readiness.md` ("Always run tests inside Docker"). Our changes did not cause this.

2. **Blank line artifact**: After removing the redundant `const API` re-declaration on `submit/page.tsx` line 119, a blank line remains at that position. This is cosmetically neutral and does not affect functionality.
