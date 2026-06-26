# UNESCO Dataset Integration & Environment Audit Report

## Objective
This report documents the complete environment and integration audit performed to determine why the local environment is still using the older/smaller UNESCO dataset instead of the expected ~1100-site dataset.

---

## 1. Git Status & Repository State
* **Current Branch**: `sriya-audit-tests` (created from `main`)
* **Working Tree Status**: Clean (except for untracked tests directory)
* **Latest Commits on main**: Fully up to date with `origin/main` (latest commit `9f7f6fc`).

### Command Output (`git status`)
```
On branch main
Your branch is up to date with 'origin/main'.

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	backend/tests/

nothing added to commit but untracked files present (use "git add" to track)
```

### Latest 10 Commits (`git log --oneline --decorate -10`)
```
9f7f6fc (HEAD -> main, origin/main, origin/HEAD) Merge pull request #23 from sriyaa-p/aishwarya-non-pdf-features
94c4b82 (origin/aishwarya-non-pdf-features) Merge branch 'main' into aishwarya-non-pdf-features
375df6d Merge pull request #22 from sriyaa-p/aishwarya-pdf-completion
c6c6e75 Add real-time pipeline status, live review queue, and live dashboard
f197a42 (origin/aishwarya-pdf-completion) Complete all PDF requirements — scoring engine, multilingual, photos, Gemini registry
cffa140 (origin/fix-audit-logger) Merge pull request #21 from sriyaa-p/aishwarya-evaluation-agent
696ce3d Merge pull request #20 from sriyaa-p/sriya-day1-report
9a7f94f (origin/sriya-day1-report, sriya-day1-report) Update Day 1 report after successful API and UI verification
84968c0 (origin/aishwarya-evaluation-agent) Add EvaluationAgent, VerificationAgent, and agent pipeline (Day 2)
a8187fd (test-integration-day-1) Merge pull request #13 from sriyaa-p/aishwarya-ui-skeleton
```

---

## 2. Dataset Analysis
### Local Dataset File Check
* **File Path**: `data/processed/unesco_sites_clean.json`
* **File Existence**: Yes
* **File Size**: `13713 bytes` (approx. 13K)
* **Number of JSON Records**: `41`
* **First Entry**: Taj Mahal (India)
* **Last Entry**: Timbuktu (Mali)

### Command Output
```bash
$ ls -lh data/processed/unesco_sites_clean.json
-rw-r--r--@ 1 sriya  staff    13K Jun 25 20:40 data/processed/unesco_sites_clean.json

$ python3 -c "import json; data=json.load(open('data/processed/unesco_sites_clean.json')); print(len(data)); print(data[0]); print(data[-1])"
41
{'name': 'Taj Mahal', 'country': 'India', 'region': 'Asia and the Pacific', 'inscription_year': 1983, 'criteria': 'i', 'description': 'Immense mausoleum of white marble built in Agra 1631-1648 by Mughal emperor Shah Jahan in memory of his favourite wife.'}
{'name': 'Timbuktu', 'country': 'Mali', 'region': 'Africa', 'inscription_year': 1988, 'criteria': 'ii,iv,v', 'description': 'A major intellectual and spiritual capital and centre for Islam throughout Africa in the 15th and 16th centuries, containing three great mosques.'}
```

### Git History of the Dataset File
An audit of `data/processed/unesco_sites_clean.json` history across all branches was executed.
Only three commits modified this file in the entire repository history:
1. `ba42c3e` Merge branch 'main' into ujjwal/fix-registry-agent-logic
2. `e5e15c8` fix(registry): wire UnescoSite ORM model, BM25 lookup, seed data, and tests - Ujjwal (contains **41** records)
3. `54aa33e` Add UNESCO dataset and seed script — Responsibility 3 (contains **60** records)

A larger dataset containing ~1100 sites was **never** committed to this repository.

---

## 3. Search Across Branches
All local and remote branches were inspected for different versions of the dataset:
* **41 Records**: `main`, `aishwarya-api-routes`, `aishwarya-evaluation-agent`, `aishwarya-non-pdf-features`, `aishwarya-pdf-completion`, `feature/dashboard-optimization`, `fix-audit-logger`, `sriya-day1-report`, `sriya-saved-frontend-modification`, `sriya/fix-seed-script`, `ujjwal/fix-registry-agent-logic`.
* **60 Records**: `aishwarya-dataset-seed`, `ujjwal-branch`.
* **No File**: All other branches.

No branch in this repository contains a dataset larger than 60 records.

---

## 4. Docker Analysis
* **Running Containers**: `postgres`, `backend`, and `frontend` are up.
* **Volume Mounts**: The backend service mounts `./data` on the host to `/data` in the container.
* **Stale Data inside Docker**: No. Because of the volume mount, the container directly reads the host's `data/processed/unesco_sites_clean.json` at `/data/processed/unesco_sites_clean.json`.
* **Container Record Count**: **41** (matching the host).

### Command Output
```bash
$ docker compose exec backend python -c "import json; data=json.load(open('/data/processed/unesco_sites_clean.json')); print(len(data))"
41
```

---

## 5. Seed Script Verification
Running the seed script verifies that it parses the volume-mounted dataset containing only 41 sites and seeds them (updating existing records in place).

### Command Output
```bash
$ docker compose exec backend python /scripts/seed_database.py
[seed] Loaded 41 sites from unesco_sites_clean.json
[seed] Schema verified / created.
[seed] Done — 0 inserted, 41 updated. Total rows in dataset: 41.
```

---

## 6. Root Cause
The root cause of the issue is:
* **The expected ~1100-site dataset was never committed to the repository.**
* The current `main` branch contains a small 41-site dataset which was checked in during database wiring and testing (commit `e5e15c8` by Ujjwal).
* Prior to that, the initial seed commit `54aa33e` contained only 60 sites.

---

## 7. Recommended Fix
1. **Provide and Commit the Dataset**: Overwrite the file `data/processed/unesco_sites_clean.json` with the complete cleaned ~1100-site UNESCO dataset, and commit it to a feature branch.
2. **Reseed Database**: Once the updated dataset is pulled, execute the seed script inside the running container with the `--reset` flag to truncate the old 41-site table and seed the full dataset:
   ```bash
   docker compose exec backend python /scripts/seed_database.py --reset
   ```
