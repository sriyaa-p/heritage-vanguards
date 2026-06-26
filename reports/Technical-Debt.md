# Technical Debt & Maintainability Report

This report identifies code-quality issues, missing abstractions, test coverage gaps, and architectural improvements to ensure long-term maintainability of the project.

---

## Ranked Debt Findings

| Debt ID | Title | Component | Priority | Description |
| :--- | :--- | :--- | :---: | :--- |
| **DEBT-01** | Frontend API Enrichment Loop | Frontend / API | **Critical** | The list view fetches basic items and then queries `/submissions/{id}` for each row to fetch scores. Needs to be refactored into a single API query. |
| **DEBT-02** | Duplicated API Configuration | Frontend | **High** | The API base URL `const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"` is hardcoded on every single page file. |
| **DEBT-03** | Lack of Pipeline Error Recovery | Backend | **High** | The sequential agent pipeline runs in a simple background thread. If a stage fails (e.g. Gemini rate limits), there is no retry logic or queue management. |
| **DEBT-04** | Incomplete Test Coverage | Backend Tests | **Medium** | Tests exist only for agents. There are no automated tests verifying API routers, file upload endpoints, database connection setups, or language translation routines. |
| **DEBT-05** | Raw JSONB Dictionary Handling | Backend ORM | **Medium** | The ORM model defines `dossier` as a plain `JSONB` column. Serialization and validation must be triggered manually via `model_dump` and `model_validate` everywhere. |
| **DEBT-06** | Hardcoded Verification Thresholds | Backend Agents | **Low** | The auto-rejection threshold (`60`) and photo-scoring weights are hardcoded in agent logic rather than configuration settings. |

---

## Technical Details & Refactoring Opportunities

### DEBT-02: Hardcoded Frontend Endpoint Configuration
* **Files**: `dashboard/page.tsx` (line 5), `review/page.tsx` (line 5), `submit/page.tsx` (line 5), `review/[id]/page.tsx` (line 5).
* **Impact**: If the API path changes (e.g., to an `/api/v1` namespace or a different production domain), developers must modify multiple files.
* **Refactoring Recommendation**: Create a single shared API client module (e.g. `frontend/src/lib/api.ts`) that exports an `apiClient` helper.

### DEBT-03: Background Task Reliability
* **Files**: `backend/app/api/routes/submissions.py` (line 73) calling `run_pipeline`.
* **Details**: FastAPI's `BackgroundTasks` run in the same application memory space. If the backend container restarts, any active evaluation pipelines are permanently lost and left in intermediate statuses (`pending` or `evaluation`) with no recovery.
* **Refactoring Recommendation**: In production, transition to a dedicated task queue (such as Celery, RQ, or Google Cloud Tasks) backed by a message broker.

### DEBT-05: Serialization Boilerplate
* **Files**: `backend/app/api/routes/submissions.py`, `backend/app/agents/pipeline.py`.
* **Details**: Whenever a dossier is loaded, the code performs:
  `dossier = CanonicalDossier.model_validate(submission.dossier)`
  And when saving:
  `dossier.model_dump(mode="json")`
* **Refactoring Recommendation**: Implement a custom SQLAlchemy `TypeDecorator` that handles automatic serialization and deserialization of the Pydantic `CanonicalDossier` object directly on the column definition.

---

## 3. Recommended Actions & Next Steps

1. **API Client Extraction (Immediate)**:
   Extract shared frontend variables and fetch configurations into a utility helper file.
2. **Expand API Integration Tests**:
   Add test coverage for API routers using `httpx.AsyncClient` and `FastAPI`'s `TestClient` to verify status codes and validation logic.
3. **Refactor List Payload**:
   Inject the dossier score directly into the GET `/submissions` database query return values.
