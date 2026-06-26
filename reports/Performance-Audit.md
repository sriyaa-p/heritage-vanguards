# Performance Audit Report

This report evaluates performance bottlenecks across the backend API, database interaction patterns, and frontend fetching behaviors, with specific recommendations for optimization.

---

## Ranked Findings Summary

| Finding ID | Title | Component | Severity | Description |
| :--- | :--- | :--- | :--- | :--- |
| **PERF-01** | Frontend N+1 REST API Calls | Frontend / API | **Critical** | The list views fetch the list of submissions and then execute a separate `GET /submissions/{id}` for every row to extract the heritage score. |
| **PERF-02** | On-the-Fly BM25 Index Compilation | Backend / RegistryAgent | **High** | The entire UNESCO registry database is fetched and tokenized to build the BM25 index on every duplicate check. |
| **PERF-03** | Database Seeding N+1 Queries | Backend / Scripts | **High** | The database seeding script queries the database for each record individually to check for duplicates before inserting. |
| **PERF-04** | Duplicate SQL Query in Registry Check | Backend / RegistryAgent | **Medium** | Registry checks run two SQL queries (`select all` and `select exact match`) when the exact check could be done in memory. |
| **PERF-05** | Missing API Pagination | Backend / API | **Medium** | The `GET /submissions` list endpoint does not support pagination, returning all records in a single payload. |

---

## Detailed Findings & Impact Analysis

### PERF-01: Frontend N+1 REST API Calls (Critical)
* **Location**: `frontend/src/app/dashboard/page.tsx` (lines 67-84) and `frontend/src/app/review/page.tsx` (lines 49-66)
* **Mechanism**: 
  ```typescript
  const listRes = await fetch(`${API}/submissions`);
  const listData = await listRes.json();
  const enriched = await Promise.all(
    listData.map(async (row: any) => {
      const detail = await fetch(`${API}/submissions/${row.submission_id}`);
      const d = await detail.json();
      score = d.dossier?.scoring?.total ?? null;
      ...
  ```
* **Impact**: If the database contains 100 submissions, loading the review page triggers **101 HTTP requests** (1 list request + 100 individual detail requests). This leads to substantial user-facing delay, connection pooling bottlenecks on the backend, and high DB query volumes.

---

### PERF-02: On-the-Fly BM25 Index Compilation (High)
* **Location**: `backend/app/agents/registry_agents.py` (lines 123-124, 139-142)
* **Mechanism**:
  ```python
  all_sites_result = await db.execute(select(UnescoSite))
  all_sites = list(all_sites_result.scalars().all())
  ...
  corpus = [_tokenize(s.name + " " + s.country) for s in all_sites]
  bm25 = BM25Okapi(corpus)
  ```
* **Impact**: Every incoming submission triggers a full database scan of all `unesco_sites` and rebuilds the BM25 token index from scratch in Python. When scaled to the full ~1100-site dataset, this results in significant CPU and memory overhead on every request.

---

### PERF-03: Database Seeding N+1 Queries (High)
* **Location**: `scripts/seed_database.py` (lines 58-86)
* **Mechanism**:
  ```python
  for raw in records:
      stmt = select(UnescoSite).where(UnescoSite.name == raw["name"]).where(UnescoSite.country == raw["country"])
      result = await session.execute(stmt)
  ```
* **Impact**: Inserting the full dataset makes 1 SELECT query per site to verify if it exists, followed by individual insert/update operations. While acceptable for a 41-site mock, this creates massive database transaction latency when seeding the complete ~1100-site dataset.

---

### PERF-04: Duplicate SQL Query in Registry Check (Medium)
* **Location**: `backend/app/agents/registry_agents.py` (lines 123-131)
* **Mechanism**:
  The script first queries all sites (`select(UnescoSite)`) and immediately executes a second query checking for an exact/fuzzy name and country match in SQL (`UnescoSite.name.ilike(...)`).
* **Impact**: Since the entire table is already loaded into the memory variable `all_sites`, the exact string matching check could be performed in Python, saving a redundant SQL execution.

---

### PERF-05: Missing API Pagination (Medium)
* **Location**: `backend/app/api/routes/submissions.py` (lines 126-149)
* **Mechanism**:
  `select(Submission).order_by(Submission.created_at.desc())` is executed and returned directly without limit or offset.
* **Impact**: Large dataset returns result in enormous payloads, excessive memory footprint on the API layer, and slow page loading on the frontend.

---

## Optimization Recommendations

1. **Enrich List Endpoint (Fixes PERF-01)**:
   Modify the GET `/submissions` API route to return the calculated `score` directly from the `dossier` column. For example:
   ```python
   # In backend
   return [
       {
           ...
           "score": r.dossier.get("scoring", {}).get("total")
       }
       for r in rows
   ]
   ```
   This will completely eliminate the frontend enrichment loop, dropping requests from `N + 1` to `1`.

2. **Leverage Postgres Full-Text Search or Cache BM25 (Fixes PERF-02 & PERF-04)**:
   * Keep the BM25 index cached in-memory (e.g. as a singleton or class attribute) and update it only when new sites are added.
   * Alternatively, migrate the duplicate search logic to use PostgreSQL's built-in full-text search or trigram similarity (`pg_trgm`) index. This offloads similarity matching to the database engine and avoids loading all rows into python memory.

3. **Optimize Seed Script to Bulk Upsert (Fixes PERF-03)**:
   * Fetch all existing site names and countries in a single bulk query: `select(UnescoSite.name, UnescoSite.country)`.
   * Compare records in Python memory to separate them into inserts and updates, and execute them in bulk (`session.add_all()` or `execute(insert(UnescoSite), [...])`).
