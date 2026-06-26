# Integration Test Report

This report documents the verification of the complete end-to-end multi-agent pipeline and human-in-the-loop review workflow.

## Summary
* **Date of Audit**: June 26, 2026
* **Status**: **PASS**
* **System Version**: MVP 0.1.0

---

## Verified Integration Workflow Steps

### 1. Services Startup
* **Backend**: Starts successfully on port `8000` via Uvicorn.
* **Frontend**: Starts successfully on port `3000` via Next.js dev server.
* **Database**: PostgreSQL starts on port `5432` and health checks pass.
* **Result**: **PASS**

### 2. Database Reachability
* Alembic migrations run successfully during container startup.
* Seed script connects to database and updates/inserts data correctly.
* **Result**: **PASS**

### 3. Duplicate Detection Workflow (RegistryAgent)
* **Test Case**: Submitted a candidate site named "Ajanta Caves" (already in the UNESCO registry of 41 clean sites).
* **Expected Result**: Immediate 201 response, pipeline runs, detects duplicate via exact SQL search / BM25, and VerificationAgent auto-rejects.
* **Actual Result**: **PASS**
* **Command Output (Submission Check)**:
```json
{
  "submission_id": "SUB-2026-06-9A0DF987",
  "status": "rejected",
  "dossier": {
    "review": {
      "decision": "rejected",
      "reviewer_id": "system",
      "reviewer_notes": "Auto-rejected: duplicate of existing UNESCO site 'Ajanta Caves'."
    },
    "registry_check": {
      "is_duplicate": true,
      "matched_site": "Ajanta Caves",
      "similarity_score": 1.0,
      "top_candidates": [
        {"country": "India", "site_name": "Ajanta Caves", "similarity_score": 1.0},
        {"country": "India", "site_name": "Ellora Caves", "similarity_score": 0.5252}
      ]
    }
  }
}
```

### 4. High-Scoring Review Workflow (Evaluation & Verification Agent)
* **Test Case**: Submitted a site not in the registry ("Ancient Temple of the Sun") with detailed historical and cultural keyword signals.
* **Expected Result**: Duplicate check returns `is_duplicate=false`. EvaluationAgent extracts evidence and deterministically scores it >= 60. VerificationAgent sets status to `verification`. Review Queue shows the item.
* **Actual Result**: **PASS** (Score: `83/100` - High Confidence. Status changed to `verification`).
* **Command Output (Submission Detail)**:
```json
{
  "submission_id": "SUB-2026-06-DF1D2859",
  "status": "verification",
  "dossier": {
    "review": {
      "decision": "pending",
      "reviewer_notes": "High Confidence (83/100). Awaiting archaeologist review."
    },
    "scoring": {
      "total": 83,
      "historic_features": 27,
      "cultural_significance": 22,
      "geographic_context": 13,
      "documentation": 14,
      "supporting_evidence": 7
    }
  }
}
```

### 5. Review Queue and Confidence Card Rendering
* Review Queue endpoint (`GET /submissions?status=verification`) returned the pending submission.
* Frontend Confidence Card detail page (`/review/SUB-2026-06-DF1D2859`) loaded successfully with the score breakdown and evidence summary.
* **Result**: **PASS**

### 6. Human-in-the-Loop Review (Approve/Reject Flow)
* **Test Case**: Call PATCH `/submissions/SUB-2026-06-DF1D2859/review?decision=approved` to simulate archaeologist approval.
* **Expected Result**: Submission status changes to `approved` in DB. Stats update on the dashboard.
* **Actual Result**: **PASS** (Response: `{"submission_id":"SUB-2026-06-DF1D2859","status":"approved"}`).
* **Dashboard Stats verification**:
  * Prior Stats: `{"total":3, "approved":2, "rejected":1}`
  * Post Stats: `{"total":5, "approved":3, "rejected":2}` (includes the Ajanta duplicate auto-rejection and Statue of Liberty auto-rejection).
  * **Result**: **PASS**

---

## Errors and Incidents Detected
* **Local Test Suite Failures on Host**: Running `pytest` locally on host fails due to missing packages (`pytest_asyncio` and `lingua`). However, running `pytest` inside the docker container works perfectly and all 14 tests pass.
* **UX Incident**: If the pipeline is running in the background, opening the review detail page displays "Pipeline in progress" and doesn't poll or auto-refresh once the pipeline finishes. The user must manually reload the page.
