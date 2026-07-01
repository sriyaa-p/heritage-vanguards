# Developer Workflows

Less-common but real operations for working in this codebase.

---

## Adding a New Alembic Migration

Migrations must be created inside the backend container (or with the backend
directory as the working directory and `DATABASE_URL` set).

```bash
# Inside Docker:
docker compose exec backend alembic revision --autogenerate -m "your description"

# This generates a file in backend/alembic/versions/
# Review it carefully — autogenerate may miss Postgres-specific features
```

**Current migration chain** (verify with `alembic history`):

```
d1637cbc70cb  — create submissions table
e4e3b1c6d6f2  — add unesco_sites + FTS
c7a8b9c1d2e3  — add reviewer_review/committee_review status enum values
```

**Important patterns from existing migrations**:

- `e4e3b1c6d6f2` uses `sa.inspect(conn)` to check if tables/columns/indexes
  already exist before creating them. Use this pattern for idempotent migrations.
- `c7a8b9c1d2e3` uses `op.get_context().autocommit_block()` because PostgreSQL
  `ALTER TYPE ... ADD VALUE` cannot run inside a transaction. Use this pattern
  when adding values to existing ENUM types.
- All migrations import from `sqlalchemy.dialects.postgresql` when using
  Postgres-specific features.

**Template**: `backend/alembic/script.py.mako` — the Mako template used by
`alembic revision` to generate new migration files.

**env.py details**: `backend/alembic/env.py` imports `Base` from
`app.db.session` and explicitly imports `app.models.submission` and
`app.models.dossier` (noqa) to register models with Base.metadata. If you add
a new ORM model, you must add a similar import in `env.py` for autogenerate
to detect it.

---

## Adding a New Agent Stage

1. **Create the agent file**: `backend/app/agents/your_agent.py`
   - Follow the existing pattern: module-level docstring, logging setup,
     a single entry function (`async def run_your_stage(dossier)` or sync)
   - If it calls Gemini, use the same client pattern:
     ```python
     from google import genai
     from google.genai import types as genai_types
     from app.core.config import settings
     
     _client = genai.Client(api_key=settings.GEMINI_API_KEY)
     _MODEL = "gemini-2.5-flash"
     ```

2. **Add Pydantic model if needed**: If your agent produces new data, add a
   Pydantic `BaseModel` in `models/dossier.py` and add it as an `Optional`
   field on `CanonicalDossier`.

3. **Wire into pipeline.py**:
   - Import your agent's entry function
   - Add a new stage block following the existing pattern:
     ```python
     # ── Stage N: YourAgent — description ──────────────────────────────
     log.info("Pipeline [N/M] YourAgent — %s", submission_id)
     try:
         dossier = await run_your_stage(dossier)
     except Exception as exc:
         log.error("Pipeline: YourAgent failed for %s — %s", submission_id, exc)
     await _persist(db, submission_id, dossier, SubmissionStatus.your_status)
     ```
   - Update the stage count in log messages (currently `[0/3]` through `[3/3]`)

4. **Add SubmissionStatus value if needed**: If the new stage needs a distinct
   status, add it to the `SubmissionStatus` enum in `models/dossier.py` AND
   create a new Alembic migration to add it to the PostgreSQL enum type
   (see the pattern in `c7a8b9c1d2e3`).

5. **Write tests**: Add tests in `tests/` following the existing patterns.

---

## Running a Single Test File

```bash
# From repo root (local):
pytest tests/test_evaluation_agent.py -v

# A specific test function:
pytest tests/test_evaluation_agent.py::test_function_name -v

# Inside Docker:
docker compose exec backend pytest /tests/test_evaluation_agent.py -v
```

Test configuration:
- `asyncio_mode = auto` — no need for `@pytest.mark.asyncio` decorator
  (though existing tests still use it)
- `pythonpath = backend` — allows `app.*` imports without sys.path hacks
- Tests use monkeypatch to stub Gemini calls and language detection

---

## Resetting Seed Data

```bash
# Option 1: Re-seed with --reset (truncates table first, then re-inserts)
docker compose exec backend python /scripts/seed_database.py --reset

# Option 2: Re-fetch UNESCO XML AND re-seed
docker compose exec backend python /scripts/fetch_unesco_data.py
docker compose exec backend python /scripts/seed_database.py

# Option 3: Nuclear — wipe the entire Postgres volume and restart
docker compose down -v   # removes postgres_data volume
docker compose up        # full rebuild: migrations → fetch → seed
```

The seed script does **upsert** by default — it matches on `(name, country)`
and updates existing rows rather than duplicating. `--reset` truncates the
table first with `TRUNCATE TABLE unesco_sites RESTART IDENTITY`.

---

## Troubleshooting Startup Failures

These failure modes are verified from `entrypoint.sh` and `docker-compose.yml`:

### "alembic upgrade head" fails

- **Cause**: Database not ready, or migration conflicts
- **Symptoms**: Container exits immediately with Alembic error
- **Fix**: `docker-compose.yml` has a `healthcheck` on the postgres service,
  and the backend `depends_on: postgres: condition: service_healthy`. If
  postgres is slow to start, the backend waits. If migrations have conflicts,
  check `alembic history` and resolve manually.

### "fetch_unesco_data.py failed — skipping seed"

- **Cause**: Network issue, UNESCO server down, or DNS failure inside container
- **Symptoms**: `entrypoint.sh` prints the WARNING and continues to start
  uvicorn. The `unesco_sites` table will be empty (or have stale data from a
  previous run).
- **Impact**: RegistryAgent will find no duplicates (everything passes through
  as non-duplicate). The rest of the pipeline works fine.
- **Fix**: This is a graceful degradation by design. Re-run the fetch manually
  once network is available:
  ```bash
  docker compose exec backend python /scripts/fetch_unesco_data.py
  docker compose exec backend python /scripts/seed_database.py
  ```

### Backend can't connect to Postgres

- **Cause**: `DATABASE_URL` misconfigured, or running outside Docker without
  Postgres credentials
- **Symptoms**: SQLAlchemy connection error
- **Fix**: Inside Docker, `DATABASE_URL` is constructed from env vars with
  host `postgres` (the Docker service name). Outside Docker, either set
  `DATABASE_URL` to point to a local Postgres, or omit it — config.py
  will fall back to SQLite in-memory (suitable for testing only, not real use).

### Frontend can't reach backend

- **Cause**: Backend not running, or CORS misconfigured
- **Symptoms**: Network errors in browser console
- **Fix**: Check that backend is running on port 8000. CORS is configured in
  `main.py` to allow `http://localhost:3000`. The frontend reads
  `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`).

---

## Development Rebuild Patterns

```bash
# Rebuild a single service after Dockerfile changes
docker compose build backend
docker compose up backend

# Watch mode (auto-sync code changes, auto-rebuild on Dockerfile change)
docker compose up --watch

# Full rebuild from scratch
docker compose down -v
docker compose build --no-cache
docker compose up
```

The `develop.watch` configuration in `docker-compose.yml`:
- `action: rebuild` for `backend/Dockerfile` and `backend/entrypoint.sh`
- `action: sync` for `./backend` → `/app` (live code reload)

---

## Working Outside Docker

For backend development without Docker:

```bash
cd backend
pip install -r ../requirements.txt

# Without Postgres — uses SQLite in-memory (tests only, not for real pipeline runs)
python main.py

# With local Postgres — set DATABASE_URL
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/heritage_db"
alembic upgrade head
python ../scripts/seed_database.py
uvicorn main:app --host 0.0.0.0 --port 8000
```

For frontend:

```bash
cd frontend
npm install
npm run dev    # starts Next.js dev server on port 3000
```

---

## Existing Test Patterns

Tests follow these conventions (verified from test files):

- **Helper factory**: `_make_dossier()` creates a minimal valid
  `CanonicalDossier` for testing
- **Monkeypatching Gemini**: Tests stub `_client.models.generate_content` or
  the agent-level functions to avoid real API calls
- **Monkeypatching lingua**: Tests stub `_detect_language` to control
  language detection behavior
- **SimpleNamespace for mocks**: Tests use `SimpleNamespace(text="...")` to
  simulate Gemini response objects
- **No DB fixtures**: Pipeline tests monkeypatch DB access. Config tests
  instantiate `Settings()` directly with constructor args.
- **Test fixture file**: `tests/fixtures/sample_dossier.json` provides a
  reference `CanonicalDossier` JSON at the `verification` stage
