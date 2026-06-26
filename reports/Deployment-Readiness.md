# Deployment Readiness Checklist

This report documents the deployment configuration, environment setup, Docker health status, and pre-demo readiness for Heritage Sentinel AI MVP.

---

## 1. Docker Compose Service Overview

| Service | Image / Build | Port | Health Check |
| :--- | :--- | :---: | :--- |
| `postgres` | `postgres:16-alpine` | 5432 | `pg_isready` (interval: 5s, retries: 5) ✅ |
| `backend` | `backend/Dockerfile` | 8000 | None configured ⚠️ |
| `frontend` | `frontend/Dockerfile` | 3000 | None configured ⚠️ |

### Findings
- ✅ PostgreSQL has a proper health check. `backend` correctly depends on `postgres` with `condition: service_healthy`.
- ⚠️ **Backend has no health check**: If the FastAPI app crashes silently after startup (e.g. bad Alembic migration, missing env var), Docker still considers the container "running". Add a health check:
  ```yaml
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 10s
    timeout: 5s
    retries: 3
  ```
- ⚠️ **Frontend has no health check**: No way to detect if the Next.js dev server fails to start. Add `curl -f http://localhost:3000` as a health check.
- ⚠️ **No resource limits**: No `mem_limit` or `cpus` constraints on any container. A runaway pipeline process could consume all available RAM.

---

## 2. Volume Mounts & Data Persistence

| Mount | Host Path | Container Path | Purpose |
| :--- | :--- | :--- | :--- |
| `postgres_data` | Docker named volume | `/var/lib/postgresql/data` | DB persistence across restarts ✅ |
| Backend code | `./backend` | `/app` | Live code reload ✅ |
| Data directory | `./data` | `/data` | UNESCO dataset + uploads ✅ |
| Scripts | `./scripts` | `/scripts` | Seed and utility scripts ✅ |
| Tests | `./tests` | `/tests` | Test suite access ✅ |
| Frontend code | `./frontend` | `/app` | Live code reload ✅ |
| node_modules | *(anonymous)* | `/app/node_modules` | Prevents host override ✅ |

### Findings
- ✅ `postgres_data` is a named Docker volume — database survives `docker compose down` (but NOT `docker compose down -v`).
- ✅ `./data` mount ensures `seed_database.py` inside the container always reads the host's `data/processed/unesco_sites_clean.json`.
- ⚠️ **Uploads not persisted beyond container**: Photo uploads go to `/data/uploads` which is volume-mounted from `./data/uploads`. If the `./data` directory is deleted on the host, all uploaded photos are lost. **Confirm `./data/uploads` exists and is gitignored before demo.**
- ⚠️ **Backend live-reload**: `./backend:/app` mount means any changes to backend Python files take effect immediately (Uvicorn `--reload` flag). Good for development; verify this flag is set in the Dockerfile or startup command.

---

## 3. Environment Variables Audit

### Required Variables (from `.env.example`)

| Variable | Used By | Status |
| :--- | :--- | :--- |
| `POSTGRES_USER` | `docker-compose.yml`, backend DB URL | Must be set in `.env` |
| `POSTGRES_PASSWORD` | `docker-compose.yml`, backend DB URL | Must be set in `.env` |
| `POSTGRES_DB` | `docker-compose.yml`, backend DB URL | Must be set in `.env` |
| `GEMINI_API_KEY` | `backend` container → all agents | Must be set in `.env` |
| `ENV` | `backend` container | Optional, defaults to `development` |
| `NEXT_PUBLIC_API_URL` | `frontend` container | Set to `http://localhost:8000` in compose |

### Findings
- ✅ `.env` is in `.gitignore` — secrets are not committed.
- ✅ `.env.example` template exists for onboarding new contributors.
- ⚠️ **`NEXT_PUBLIC_API_URL` is hardcoded in `docker-compose.yml`** as `http://localhost:8000`. This works for local development where the browser makes requests directly to the host port, but will break in a deployed environment where the backend is on a different domain. Update before any cloud deployment.
- ⚠️ **No `.env` validation on startup**: If `GEMINI_API_KEY` is missing or blank, the backend starts successfully but all agent pipeline runs will fail silently at the Gemini call. Add a startup check:
  ```python
  # In backend/app/core/config.py or main.py
  if not settings.GEMINI_API_KEY:
      raise RuntimeError("GEMINI_API_KEY is not set — agents will not function.")
  ```

---

## 4. Database State Checklist

| Check | Status |
| :--- | :--- |
| Alembic migrations run on startup | ✅ Confirmed (Day 1 report) |
| `submissions` table exists | ✅ |
| `unesco_sites` table exists | ✅ |
| UNESCO sites seeded | ✅ 41 sites (see Dataset-Audit-Report.md) |
| Full ~1100 site dataset committed | ❌ Not yet committed |

> ⚠️ **Pre-demo action required**: Run the seed script before demo to ensure the database has the latest data:
> ```bash
> docker compose exec backend python /scripts/seed_database.py
> ```

---

## 5. API Readiness

| Endpoint | Verified | Notes |
| :--- | :---: | :--- |
| `POST /submissions` | ✅ | Returns 201 + submission_id |
| `POST /submissions/{id}/photos` | ✅ | Saves files to `/data/uploads/` |
| `GET /submissions` | ✅ | Returns sorted list |
| `GET /submissions?status=` | ✅ | Filters by status enum |
| `GET /submissions/stats` | ✅ | Dashboard aggregates |
| `GET /submissions/{id}` | ✅ | Full dossier detail |
| `PATCH /submissions/{id}/review` | ✅ | Approve / reject |

---

## 6. Frontend Pages Readiness

| Page | Route | Verified | Notes |
| :--- | :--- | :---: | :--- |
| Landing / Home | `/` | ✅ | Loads without errors |
| Submit | `/submit` | ✅ | Form works, pipeline fires |
| Review Queue | `/review` | ✅ | Tabs for pending/approved/rejected |
| Review Detail | `/review/[id]` | ✅ | Confidence Card renders |
| Dashboard | `/dashboard` | ✅ | Stats and recent submissions |

---

## 7. Pre-Demo Checklist

Run through this checklist before the hackathon demo:

- [ ] `cp .env.example .env` and fill in `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `GEMINI_API_KEY`
- [ ] `docker compose up --build` — wait for all three containers to be running
- [ ] Verify `postgres` health: `docker compose ps` shows `postgres` as healthy
- [ ] Run seed script: `docker compose exec backend python /scripts/seed_database.py`
- [ ] Verify 41 sites seeded: check script output `Done — X inserted, Y updated`
- [ ] Open `http://localhost:3000` — confirm frontend loads without console errors
- [ ] Submit a test candidate site via `/submit` — note the `submission_id`
- [ ] Poll `GET http://localhost:8000/submissions/{id}` and confirm status progresses to `verification` or `rejected`
- [ ] Open `http://localhost:3000/review` — confirm the submission appears in the queue
- [ ] Approve or reject via the frontend — confirm status updates on the dashboard
- [ ] Confirm `http://localhost:3000/dashboard` shows updated stats

---

## 8. Known Risks for Demo Day

| Risk | Severity | Mitigation |
| :--- | :--- | :--- |
| Gemini API rate limit during live demo | High | Prepare a canned submission result screenshot as fallback |
| Docker cold start on demo machine takes > 2 min | Medium | Run `docker compose up` 10 minutes before demo |
| Missing `.env` file on demo machine | High | Keep `.env` pre-filled in a secure location, never in git |
| `data/uploads` directory missing | Low | `os.makedirs` in the route creates it automatically |
| Database empty (no sites seeded) | High | Run seed script after `docker compose up` every time |
| `pytest` fails on host (known issue) | Low | Always run tests inside Docker: `docker compose exec backend pytest /tests` |
