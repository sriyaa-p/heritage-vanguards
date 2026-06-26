# Database Audit Report

This report evaluates the PostgreSQL database schema design, index usage, constraints, and query execution efficiency.

---

## 1. Schema Analysis

The system contains two primary user-defined tables: `submissions` and `unesco_sites`, managed via Alembic migrations.

### Table: `submissions`
Used to store candidate heritage site submissions. The raw data, evidence, scoring, and review details are consolidated inside a `JSONB` column named `dossier`.
* **Primary Key**: `id` (`uuid`, non-sequential)
* **Unique Key**: `submission_id` (`varchar`)
* **JSONB Column**: `dossier`

### Table: `unesco_sites`
Stores the ground-truth UNESCO World Heritage Sites dataset, used for duplicate checks.
* **Primary Key**: `id` (`integer`, auto-incrementing serial)
* **Indexed Fields**: `name` (`varchar(512)`), `country` (`varchar(256)`)

---

## 2. Index Audit Findings

### A. Redundant / Duplicate Indexes
* **Finding**: The `unesco_sites` table contains a redundant index: `ix_unesco_sites_id`.
* **Details**: 
  ```sql
  Indexes:
      "unesco_sites_pkey" PRIMARY KEY, btree (id)
      "ix_unesco_sites_id" btree (id)
  ```
* **Cause**: In `app/models/dossier.py`, the `id` column is defined as:
  `id = Column(Integer, primary_key=True, index=True)`
  SQLAlchemy compiles `primary_key=True` into a Primary Key constraint, which automatically generates a unique B-tree index in PostgreSQL. Specifying `index=True` in addition to `primary_key=True` creates an additional redundant index on the same column.
* **Impact**: Redundant indexes increase disk usage and write overhead during insert/update operations.

### B. Missing Indexes on Frequent Filter Columns
* **Finding**: No index exists on the `status` column in the `submissions` table.
* **Query Patterns**: 
  1. `select * from submissions where status = :status` (used in review queue views).
  2. `select status, count(*) from submissions group by status` (used in dashboard stats).
* **Impact**: Postgres must perform a Sequential Scan (Seq Scan) over the entire table on every statistics fetch or status-specific queue list.

### C. Missing Sort Index
* **Finding**: No index exists on the `created_at` column in `submissions`.
* **Query Patterns**:
  * `select * from submissions order by created_at desc` (used in default queues and dashboard views).
* **Impact**: Forces an in-memory/on-disk sort operation for large datasets.

### D. Missing Composite Index for Seeding Check
* **Finding**: No composite index exists on `(name, country)` in `unesco_sites`.
* **Query Patterns**:
  * `select * from unesco_sites where name = :name and country = :country` (executed for every record during seeding).
* **Impact**: Forces lookups to scan the individual index `ix_unesco_sites_name` and filter by country, or do a sequential scan.

### E. JSONB Indexing Gaps
* **Finding**: The `dossier` column is not indexed for nested JSONB queries.
* **Impact**: If features are added to search submissions by submitter (`dossier->'metadata'->>'submitted_by'`) or location name, queries will result in full table scans.

---

## 3. Query Efficiency (EXPLAIN Analysed)

Executing `EXPLAIN` on typical query patterns reveals:

### Status Stats Query
```sql
EXPLAIN SELECT status, count(*) FROM submissions GROUP BY status;
```
* **Execution Plan**:
  ```text
  HashAggregate  (cost=1.06..1.08 rows=2 width=12)
    Group Key: status
    ->  Seq Scan on submissions  (cost=0.00..1.05 rows=5 width=4)
  ```
* **Analysis**: Because the table has no index on `status`, it relies on a `Seq Scan` (Sequential Scan). As submission count grows, this aggregate cost will scale linearly with the table size.

---

## 4. Recommendations for Schema Improvement

1. **Remove Duplicate Index**:
   Change the column definition in `app/models/dossier.py`:
   ```python
   # Remove index=True since primary_key=True already indexes it
   id = Column(Integer, primary_key=True)
   ```

2. **Add Status and Created_At Indexes**:
   Create a composite index on `(status, created_at DESC)` in `submissions` to cover both queue filtering and ordering in a single index:
   ```python
   # In models/submission.py
   __table_args__ = (
       Index("ix_submissions_status_created_at", "status", created_at.desc()),
   )
   ```

3. **Add Composite Index on UnescoSite**:
   Add a unique constraint or composite index on `(name, country)` in `unesco_sites` to speed up deduplication lookups during seeding and prevent database-level double-inserts.
