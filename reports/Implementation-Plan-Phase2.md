# Heritage Sentinel AI — Implementation Plan (Phase 2)

This document serves as the technical blueprint and architectural specification for the Phase 2 implementation of the Heritage Sentinel AI system. It outlines the system changes, files affected, risk levels, and roadmap for each planned improvement.

---

## Technical Audit & Current System State

An analysis of the existing codebase reveals a solid MVP foundation but significant gaps in security, production-level workflow gating, dataset coverage, and front-end usability.

*   **Frontend**: Built on Next.js 14 (App Router) with Tailwind CSS. Pages are structured, but lack a unified navigation layout, session context, or role checks. Client-side fetching executes separate N+1 requests for individual submission detail scores.
*   **Backend**: Powered by FastAPI and Uvicorn. Routing is standard but lacks JWT token validation or route-level dependency checks. Photo uploading is handled via a separate asynchronous API call.
*   **Database**: PostgreSQL managed by SQLAlchemy and Alembic. Submission records are persisted with a JSONB column (`dossier`) which stores the `CanonicalDossier` payload. There is no indexing on critical query fields (`status`, `created_at`).
*   **AI Pipeline**: A background queue runs sequentially: `IntakeProcessor` (translation) → `RegistryAgent` (BM25 + Gemini deduplication) → `EvaluationAgent` (Gemini evidence extraction + ScoringEngine) → `VerificationAgent` (Score-gating).
*   **Role Handling**: Unimplemented. All administrative endpoints are public. No user accounts or role permissions exist in the database or frontend.

---
## Implementation Strategy

The current system has a stable MVP with a working AI pipeline, backend APIs, database schema, and frontend. The objective of Phase 2 is to extend the platform while preserving all existing functionality.

### Guiding Principles

- Preserve existing working functionality wherever possible.
- Prefer additive changes over modifying stable code.
- Implement one feature at a time.
- Verify the system after each completed feature before proceeding.
- Keep the application in a deployable state throughout development.

### Regression Testing

After completing each feature, verify:

- Submission creation
- Photo upload
- RegistryAgent duplicate detection
- EvaluationAgent
- Scoring Engine
- VerificationAgent
- Review Queue
- Dashboard
- Existing API endpoints
- Frontend navigation

Do not begin the next feature until the current one passes verification.

### Backward Compatibility

- Do not break existing API contracts.
- Avoid destructive database changes.
- Extend existing models where possible.
- Preserve existing AI agent behaviour unless the new workflow explicitly requires changes.

### Branching Strategy

Each major feature should be implemented in its own feature branch and verified independently before merging.

### Rollback Strategy

Maintain a stable checkpoint before each implementation phase. If regressions occur, revert only the affected feature instead of rolling back unrelated work.

---

## Feature Plans & Design Specifications

## For the hackathon as the rule suggests that login pages are not required. Please don't implement the (RBAC) role based action changes. This is for futher scaling purposes only. And not to be implemented right now.

### 1. Proper Role-Based Access Control (RBAC)

#### Proposed Architecture
We will implement standard JWT-based authentication. Users will have accounts with designated roles that map to specific permissions.

```
                  ┌──────────────────────┐
                  │      Auth Service    │
                  │   (JWT Issue/Verify) │
                  └──────────┬───────────┘
                             │
     ┌───────────────────────┼───────────────────────┐
     ▼                       ▼                       ▼
Community Reporter      Archaeologist Reviewer    UNESCO Committee
(Access: /submit,       (Access: /review,         (Access: /committee,
  /dashboard/track)       /review/[id], /dashboard) /committee/review/[id])
```

#### Role Details
*   **Community Reporter**:
    *   *Accessible Pages*: `/submit` (Submit Candidate Site), `/dashboard/track/[id]` (Tracking Portal).
    *   *Restricted Pages*: `/review` (Review Queue), `/review/[id]` (Confidence Card Actions), `/dashboard` (Admin Stats), `/committee` (Committee Dashboard).
    *   *Permissions*: Create submissions, upload photos, fetch own submission status.
    *   *Required API Protection*: Can only invoke `POST /submissions` (unified with photo upload) and `GET /submissions/{id}` (restricted to their own submission_id).
*   **Archaeologist Reviewer**:
    *   *Accessible Pages*: `/review`, `/review/[id]`, `/dashboard` (Read-Only).
    *   *Restricted Pages*: `/committee`, `/committee/review/[id]`, `/submit`.
    *   *Permissions*: List pending submissions, view confidence cards, add evaluation notes, recommend and forward to committee, reject submissions.
    *   *Required API Protection*: Restricted to `GET /submissions` (filtered by review state), `GET /submissions/{id}`, `GET /submissions/stats`, and `PATCH /submissions/{id}/recommend` (new endpoint).
*   **UNESCO World Heritage Committee**:
    *   *Accessible Pages*: `/committee`, `/committee/review/[id]`, `/dashboard`.
    *   *Restricted Pages*: `/review/[id]` (Archaeologist Action form).
    *   *Permissions*: View recommended submissions, finalize decisions (Approve/Reject), add committee comments, view system statistics, read system audit logs.
    *   *Required API Protection*: Restricted to `GET /submissions` (filtered by committee review state), `PATCH /submissions/{id}/finalize` (new endpoint), `GET /submissions/audit-log` (new endpoint).

#### Technical Changes Required
*   **Database**:
    *   Add a new `users` table:
        *   `id` (`UUID`, Primary Key)
        *   `username` (`VARCHAR`, Unique, Indexed)
        *   `hashed_password` (`VARCHAR`)
        *   `role` (`VARCHAR`, Enforcing ENUM: `'reporter'`, `'reviewer'`, `'committee'`)
        *   `created_at` (`TIMESTAMP WITH TIME ZONE`)
    *   Create a migration script in Alembic to create the table and seed initial test users for each role.
*   **Backend & API**:
    *   Create `app/api/routes/auth.py` with `/auth/register` and `/auth/token` (OAuth2 password flow).
    *   Implement dependencies: `get_current_user` and `require_role(allowed_roles: list[str])` in `app/api/deps.py`.
    *   Update all routes in `app/api/routes/submissions.py` to require authentication and authorize via role guards.
*   **Frontend**:
    *   Create a shared Auth Context (`frontend/src/context/AuthContext.tsx`) to manage login, store JWT token (in local storage or HttpOnly cookies), and track user role.
    *   Implement `/login` page.
    *   Add layout route protection: Check role permissions on route entry and redirect unauthorized users to their respective home screen.

---

### 2. Complete Workflow Redesign

#### Proposed Submission Lifecycle
The submission state progression is updated to include a two-stage human review loop (Archaeologist evaluation followed by Committee authorization):

```
Reporter (Submit Form)
        │
        ▼
AI Pipeline (Intake, Duplicate Check, Scoring)
        │
        ├─────────► [Duplicate / Score < 25] ──► Auto-Rejected (Terminal)
        ▼
Reviewer Queue (Status: reviewer_review)
        │
        ├─────────► [Reject] ──────────────────► Rejected (Terminal)
        ▼
Committee Queue (Status: committee_review)
        │
        ├─────────► [Reject] ──────────────────► Rejected (Terminal)
        ▼
Final Decision (Status: approved) ─────────────► Approved (Terminal)
```

#### Status Transitions and Page Integration
*   `pending` / `registry_check` / `evaluation`: Submissions in progress in the background. Tracking is shown on the Reporter Dashboard `/dashboard/track/[id]`.
*   `reviewer_review`: Pipeline score is $\ge 25$. Submission is routed to the Archaeologist Review Queue (`/review`). The Reviewer opens `/review/[id]` to read the Confidence Card and make a recommendation.
*   `committee_review`: Archaeologist recommends the site. The submission is routed to the Committee Queue (`/committee`). A Committee member opens `/committee/review/[id]` to view the full dossier, the Archaeologist's comments, and make the final decision.
*   `approved`: Final committee approval. The site status updates to `approved`.
*   `rejected`: Rejection at any stage (duplicate check, score < 25, reviewer rejection, or committee rejection). The dossier stores the rejection reason and stage.

---

### 3. Reporter Dashboard

#### Specification
Reporters require a safe portal to track their submissions without exposing internal scoring details or admin-only decision actions.

#### Architectural Requirements
*   **Timeline / Progress Tracker**: Visual representation of the submission states (Submitted → AI Evaluation → Archaeologist Review → Committee Review → Final Designation).
*   **Status Indicators**: Modern colored states (e.g., green for approved, red for rejected, pulsing blue for active processing).
*   **Audit Feedback**: Show Reviewer and Committee comments on final decision, or system comments if auto-rejected.
*   **Dossier Summary**: Show the user's submitted description, coordinates, and translated text (if applicable).
*   *Security Constraint*: Hide exact score category breakdowns and prompt logic from the reporter to prevent gamification of the system.

#### Technical Details
*   **Backend Endpoints**:
    *   `GET /submissions/{id}/public`: A new public-safe endpoint returning only metadata, raw evidence, and non-sensitive status details.
*   **Frontend Components**:
    *   `/dashboard/track/[id]/page.tsx`: The tracker page displaying the timeline, progress bar, and feedback panels.
    *   `TimelineStep`: A micro-animated vertical stepper showing the current position in the lifecycle.
*   **Database Fields**:
    *   No new database columns are needed since the existing JSONB `dossier` handles all metadata, raw evidence, and status metrics.

---

### 4. Reviewer Workflow

#### Specification
Archaeologists require a dedicated triage workflow to review AI-generated evidence and make a professional recommendation to the Committee.

#### Assessment
*   *What Currently Exists*: A basic review page (`/review`) showing all submissions and a detail page (`/review/[id]`) that directly allows approving/rejecting using a single PATCH endpoint.
*   *What Needs Modification*:
    *   Restrict the list of submissions in `/review` to only show status `reviewer_review` (awaiting review).
    *   Change the detail page (`/review/[id]`) action. Instead of directly setting the status to `approved`, the Reviewer's action will patch the status to `committee_review` (recommendation) or `rejected` (rejection).
    *   Add a mandatory Reviewer Note text area.
    *   Add a tab to see "Recommended by Me" (status `committee_review`) and "My Decisions" (approved/rejected).

#### Technical Details
*   **Backend Endpoint Changes**:
    *   Modify `PATCH /submissions/{id}/review` to accept `reviewer_notes` and update status to `committee_review` or `rejected`.
*   **Frontend changes**:
    *   Update `/review` queue page filters to handle the new status types.
    *   Update `/review/[id]` buttons: "Recommend & Forward" (green) and "Reject" (red).

---

### 5. UNESCO Committee Workflow

#### Specification
The Committee has the final authority to designate a site. They need a dashboard showing overall statistics and a queue of recommended dossiers.

#### Details
*   **Committee Dashboard (`/committee`)**:
    *   Displays aggregate statistics: total designated sites, pending recommendation count, pipeline volume, and system duplicate rate.
    *   List of recommended sites awaiting final approval (`status = committee_review`).
*   **Detailed View (`/committee/review/[id]`)**:
    *   Displays the full Confidence Card, scoring breakdown, and extracted AI evidence.
    *   Displays the Archaeologist's review notes and recommendation timestamp.
    *   Actions: "Final Approval" (sets status to `approved`) and "Final Reject" (sets status to `rejected`).
    *   Text box for "Committee Comments" which will be recorded in the dossier.
*   **System Audit History**:
    *   A list displaying past approvals, rejections, and auto-blocks, serving as a system-wide historical ledger.

#### Technical Details
*   **Backend Endpoints**:
    *   `PATCH /submissions/{id}/finalize`: Endpoint accepting final decision (`approved` / `rejected`) and committee comments.
    *   `GET /submissions/audit-log`: Retrieves a list of historical status change records.
*   **Frontend Components**:
    *   `/committee/page.tsx`: The main dashboard page.
    *   `/committee/review/[id]/page.tsx`: Detail review and approval console.
    *   `AuditHistoryTable`: Component for listing historical ledger events.

---

### 6. Supporting Evidence Bug

#### Root Cause Analysis
A race condition exists between the initial submission creation and the photo uploading flow.

1.  The client sends a `POST /submissions` containing only the description and metadata (without photo URLs).
2.  The backend database saves this record, and immediately fires `run_pipeline(submission_id)` as an asynchronous `BackgroundTask`.
3.  The pipeline thread runs Stage 0 (`IntakeProcessor`).
4.  Simultaneously, the frontend receives the response, retrieves the `submission_id`, and initiates a second request: `POST /submissions/{submission_id}/photos` to upload the image files.
5.  The photo upload endpoint reads the database record, saves files to disk, and updates `dossier.raw_evidence.photo_urls` with the upload URLs.
6.  Meanwhile, the background pipeline thread finishes Stage 0 (or Stage 1) and calls `_persist(db, submission_id, dossier, status)`. The pipeline holds a stale copy of the `dossier` in its thread memory where `photo_urls` is empty `[]`.
7.  This `_persist` call overwrites the database row, wiping out the photo URLs uploaded in step 5.
8.  When the pipeline reaches Stage 2 (`EvaluationAgent`) and loads a "fresh" submission copy from the database, it reads `photo_urls = []`. The photo count is 0, scoring engine awards 0 points, and no photos are shown in the final card.

#### Proposed Solution
We will transition the submission and photo upload flow to a single, unified HTTP multipart request.

*   **API Change**: Update `POST /submissions` to accept `Multipart/Form-Data` containing location name, country, description, and optional file uploads in a single request.
*   **Pipeline Change**: Since the submission is committed with all photo URLs pre-populated, the pipeline will always have the correct photo list. We can remove the redundant `fresh` load logic in Stage 2.
*   **Frontend Change**: Combine the metadata inputs and files into a single `FormData` payload on `/submit` form submission.

---

### 7. UNESCO Dataset Expansion

#### Specification
We will scale the UNESCO registry database from the current 220-site dummy dataset to the complete official UNESCO World Heritage list (~1,200 inscribed sites).

#### Details
*   **Dataset Source**: The UNESCO World Heritage Centre public database XML feed: `https://whc.unesco.org/en/list/xml`.
*   **Processing Requirements**:
    *   A parser script (`scripts/fetch_unesco_data.py`) will download and parse the XML document.
    *   Format attributes: split transboundary country lists (e.g., "India; Nepal" to lists), strip HTML tag markup from descriptions, format criterion strings.
    *   Write output to `data/processed/unesco_sites_clean.json`.
*   **Database Impact**: The `unesco_sites` table size will increase to ~1,200 rows. A composite index on `(name, country)` in `unesco_sites` is required to optimize lookups.
*   **Seed Process**: Update `scripts/seed_database.py` to run in reset mode during build/startup:
    `python scripts/seed_database.py --reset`
*   **Duplicate Detection Implications**:
    *   *Problem*: The current RegistryAgent queries all sites into memory on every request to compute BM25 scores. Doing this for 1,200+ rows is highly CPU-intensive and unscalable.
    *   *Fix*: Modify `RegistryAgent` to cache the BM25 corpus index in-memory as a singleton on application startup, or utilize PostgreSQL's built-in Full Text Search (FTS) index with `tsvector` on the name and description fields to query matching candidates in SQL. PostgreSQL FTS is highly recommended as it keeps the search database-native and performs at sub-millisecond speeds.

---

### 8. Navigation Improvements

#### Identification & Fixes
*   **Issue 1: Submitter Redirect**: Submitter is redirected to the admin-level review page (`/review/[id]`) showing decisions and scoring.
    *   *Fix*: Redirect submitters to `/dashboard/track/[id]`.
*   **Issue 2: Unified Navigation Header**: Missing navigation links to switch between Submit, Review, and Dashboard.
    *   *Fix*: Create a global header component `Header.tsx` in `frontend/src/components` and embed it in `frontend/src/app/layout.tsx`. Show navigation links depending on the logged-in user's role.
*   **Issue 3: Detail View Links**: Clicking cards on the dashboard should open the correct view based on the user's role.
    *   *Fix*: Clicking a card on `/dashboard` will direct reviewers to `/review/[id]` and committee members to `/committee/review/[id]`.
*   **Issue 4: Reset Button State**: "Submit another site" on `/submit` leaves previous input variables initialized.
    *   *Fix*: Explicitly clear form inputs, photos, and file ref variables in the `handleReset` method.

---

### 9. UI Improvements

#### Review and Prioritization
*   **High Priority (WCAG AA Accessibility)**:
    *   Ensure all text and badge combinations have contrast ratios $\ge 4.5:1$. Update evaluation badge styles from light yellow/gray text to darker variants (e.g., `text-yellow-800` on `bg-yellow-100`, `text-gray-800` on `bg-gray-100`).
    *   Add custom focus outline rings (`focus-visible:ring-2 focus-visible:ring-blue-500`) to all buttons and form inputs.
*   **Medium Priority (Layout & Responsiveness)**:
    *   Fix the progress tracker on `/submit` page to prevent overflowing. Make text labels hide or stack vertically on smaller viewports.
    *   Convert tables in `/dashboard` and `/review` into stacked responsive cards on mobile screens (`max-width: 640px`) to prevent horizontal scrolling.
*   **Low Priority (UX Polish)**:
    *   Replace plain loading spinners with modern skeleton loaders (`animate-pulse`) representing the cards/tables being loaded.
    *   Create custom empty states with graphics for the review queues.

---

## Technical Design Matrix

| Feature | Files to Change | Effort | Risk | Risk Rationale | Dependencies |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **RBAC Setup** | `backend/app/models/user.py`<br>`backend/app/api/deps.py`<br>`frontend/src/context/AuthContext.tsx` | **Medium** | **Medium** | Modifies backend API dependencies. Secures all endpoints. Must be robust to prevent auth bypass. | None |
| **Workflow Redesign** | `backend/app/models/dossier.py`<br>`backend/app/agents/pipeline.py`<br>`backend/app/agents/verification_agent.py` | **Medium** | **Medium** | Modifies state machine values and transitions. Affects existing database data schema. | RBAC Setup |
| **Reporter Dashboard** | `frontend/src/app/dashboard/track/[id]/page.tsx`<br>`backend/app/api/routes/submissions.py` | **Small** | **Low** | Read-only view for submitters. Low impact on backend systems. | Workflow Redesign |
| **Reviewer Queue** | `frontend/src/app/review/page.tsx`<br>`frontend/src/app/review/[id]/page.tsx` | **Small** | **Low** | Adapts existing review page. Simple API PATCH request modification. | Workflow Redesign |
| **Committee Workflow** | `frontend/src/app/committee/page.tsx`<br>`frontend/src/app/committee/review/[id]/page.tsx` | **Medium** | **Low** | Introduces new pages and dashboards. High frontend code addition but low system risk. | Workflow Redesign |
| **Supporting Evidence Bug** | `backend/app/api/routes/submissions.py`<br>`frontend/src/app/submit/page.tsx` | **Small** | **Medium** | Modifies submission API payload structure. Ensures file transfer stability. | None |
| **UNESCO Dataset Expansion** | `scripts/fetch_unesco_data.py`<br>`scripts/seed_database.py`<br>`backend/app/agents/registry_agents.py` | **Medium** | **High** | Changes duplicate checking from memory to database-driven. Risk of query timeouts if SQL indexing is incorrect. | None |
| **Navigation & UI** | `frontend/src/app/layout.tsx`<br>`frontend/src/components/Header.tsx` | **Small** | **Low** | General layout adjustments. Low security or backend impact. | All dashboard features |

---

## Recommended Roadmap & Implementation Order

```
[Supporting Evidence Bug Fix]
         │
         ▼
[UNESCO Dataset Expansion] ──────► [SQL Indexing & RegistryAgent Optimization]
         │
         ▼
[RBAC Setup & Authentication Layer]
         │
         ▼
[Workflow State Redesign & DB enum migration]
         │
         ▼
[Reviewer Workflow updates] ──► [Committee Dashboard Setup] ──► [Reporter Timeline Tracker]
         │
         ▼
[Navigation & UI Polish (A11y, contrast, mobile tables)]
```

### Phase 1: Critical Bug Fixes & Dataset Scaling
1.  Fix the **Supporting Evidence Bug** by merging file upload and site creation into a single unified multipart request.
2.  Deploy the **UNESCO Dataset Parser** to fetch, process, and seed 1,200+ official sites.
3.  Optimize **RegistryAgent** using PostgreSQL Full Text Search (FTS) indexing on `unesco_sites` table.

### Phase 2: Security & Authentication (RBAC)
1.  Implement the database `users` schema, Alembic migration, and mock user seeding.
2.  Add authentication middleware (JWT verification) to backend APIs.
3.  Implement frontend `/login` and Auth context. Wrap layouts in route authentication guards.

### Phase 3: Workflow Redesign & State Migration
1.  Update `SubmissionStatus` and `CanonicalDossier` schemas to support the new state transitions (`reviewer_review`, `committee_review`).
2.  Refactor `VerificationAgent` threshold gating and pipeline stage persistence.

### Phase 4: UI & Dashboard Integration
1.  Implement the **Reviewer Queue** update, transitioning "approval" to "recommendation".
2.  Develop the **UNESCO Committee Dashboard** and decision detail page.
3.  Construct the **Reporter Tracking Dashboard** using the public-safe API.
4.  Add global **Header navigation** and protect links based on roles.
5.  Polish components for accessibility (WCAG AA compliance, focus rings) and mobile responsive scaling.
