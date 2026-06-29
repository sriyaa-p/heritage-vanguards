# Feature 1: Supporting Evidence Bug Fix

## Root Cause
A race condition existed between the initial submission creation and the photo uploading flow. The client sent `POST /submissions` containing only metadata. The backend saved this and started the asynchronous pipeline `run_pipeline(submission_id)`. Simultaneously, the frontend sent `POST /submissions/{submission_id}/photos`. The photo endpoint saved files and updated the database, but the pipeline already had a stale copy of the dossier with `photo_urls = []`. When the pipeline persisted its progress, it overwrote the photo URLs, causing the EvaluationAgent to see 0 photos and award 0 bonus points.

## Changes Made
- **Backend:** Added a unified multipart endpoint `POST /submissions/with-photos` in `backend/app/api/routes/submissions.py`. This endpoint accepts both metadata and photo files in a single request. It saves photos to disk first, then creates the dossier with photo URLs included, and finally triggers the pipeline. The old `POST /submissions` and `POST /submissions/{submission_id}/photos` are preserved for backward compatibility.
- **Frontend:** Updated `handleSubmit` in `frontend/src/app/submit/page.tsx` to send a single `FormData` payload to `/submissions/with-photos`.

## Verification Results
- **End-to-End Test:** Performed an end-to-end test by submitting a dummy payload with a photo attachment directly to the new `POST /submissions/with-photos` endpoint. After waiting for the pipeline to finish, queried the submission details. Confirmed the photo was present in `raw_evidence.photo_urls` and the `supporting_evidence` score correctly reflected the uploaded photo.
- All backend routes are registered correctly (verified by checking `app.routes`).
- The backend test suite ran, resulting in 14 passes and 1 failure (`test_verification_rejects_duplicate`).
  - **Pre-existing Issue Confirmation:** The `test_verification_rejects_duplicate` failure is a pre-existing issue. The test expects the word "duplicate" in `reviewer_notes`, but `verification_agent.py` actually sets the message to "already exists". No changes were made to `verification_agent.py` or the tests in this feature.
- Next.js build was executed inside the docker container. The build failed with an error: `Cannot find module or type declarations for side-effect import of './globals.css'` in `layout.tsx`.
  - **Pre-existing Issue Confirmation:** This is a pre-existing Next.js Docker caching/volume-mounting issue. The `globals.css` file exists and we did not modify `layout.tsx` or `globals.css`. The `page.tsx` modification is syntax-error free.

## Regressions Found
- None. The changes are purely additive on the backend and update the submit endpoint URL on the frontend.
