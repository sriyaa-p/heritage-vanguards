# Architecture Compliance Report

This report compares the active codebase implementation against the requirements and multi-agent architectural specifications documented in `PROJECT.md` and `AGENTS.md`.

---

## 1. Compliance Checklist

| Feature / Component | Implemented | Verified | Compliance Notes |
| :--- | :---: | :---: | :--- |
| **Intake Processor (Stage 0)** | Yes | Yes | Detects non-English inputs via `lingua` and translates to English using Gemini 2.5 Flash. |
| **RegistryAgent (Stage 1)** | Yes | Yes | Deduplicates submissions using a three-step workflow: exact SQL match, BM25 candidates, and Gemini comparison. |
| **EvaluationAgent (Stage 2)** | Yes | Yes | Calls Gemini to extract evidence text only (no scoring) into structured keys. |
| **Deterministic Scoring Engine** | Yes | Yes | Scores evidence deterministically using keywords from `data/scoring_criteria.json`. |
| **VerificationAgent (Stage 3)** | Yes | Yes | Packages the Confidence Card and routes based on score threshold (<60 is auto-rejected; >=60 goes to review). |
| **Multilingual Intake** | Yes | Yes | Handled successfully during the Stage 0 Intake. |
| **Live Pipeline Tracking** | Yes | Yes | Frontend `PipelineTracker` polls status and renders stages dynamically. |
| **Review Queue** | Yes | Yes | Displays submissions filtered by `verification` (Awaiting Review), `approved`, or `rejected`. |
| **Dashboard** | Yes | Yes | Displays metrics aggregated from database and recent submissions. |
| **Photo Upload** | Yes | Yes | Implemented via POST `/submissions/{id}/photos` and stored in a local directory. |
| **Confidence Card** | Yes | Yes | Details page renders score breakdown, registry check status, and extracted text. |
| **Background Processing** | Yes | Yes | Pipeline runs as a FastAPI `BackgroundTask`, separating HTTP response from agent logic. |
| **Database Schema** | Yes | Yes | Managed with SQLAlchemy and Alembic migrations. |
| **API Routes** | Yes | Yes | Standard endpoints for submit, list, detail, and review are configured. |

---

## 2. Detailed Compliance Analysis

### Three-Agent Workflow Alignment
The implementation adheres to the sequential flow:
1. **Deduplication Gate**: If a duplicate is identified by `RegistryAgent`, the pipeline halts subsequent agent executions (skips `EvaluationAgent`) and marks it as `rejected` in the database.
2. **Evidence-Scoring Separation**: Gemini is kept strictly as a text extraction assistant. All point calculations are offloaded to `ScoringEngine` in Python using keyword frequency rules defined in `scoring_criteria.json`. This meets the capstone's reproducibility and explainability requirements.
3. **HITL Gate**: Submissions scoring 60+ remain in the `verification` state. Human action is required to move them to `approved` or `rejected` states.

---

## 3. Deviations and Gaps Identified
* **Dataset Size Mismatch**: While the architecture specifies a "UNESCO World Heritage Sites Dataset", the local seeding process only seeds a mock 41-site list because the complete ~1100-site dataset has not been committed to the repository.
* **Lack of Threat Monitoring Agent**: The threat monitoring agent mentioned in future milestones is not yet started, but this matches the Hackathon MVP scope where only the three core agents (Registry, Evaluation, and Verification) are required.
