# API Audit Report

This report documents the verification of all backend API endpoints including validation, status codes, and error handling.

## API Endpoint Verification Summary

| Endpoint | Method | Status | Result | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `/submissions` | `POST` | **PASS** | `201 Created` | Returns `submission_id`, `status` ("pending"), and `created_at` immediately. Fires background pipeline task. |
| `/submissions` | `POST` | **PASS** | `422 Unprocessable Entity` | Returned when required fields (`location_name` or `description`) are missing. |
| `/submissions/{id}/photos` | `POST` | **PASS** | `200 OK` | Saves files to disk and appends URLs to the dossier. |
| `/submissions/{id}/photos` | `POST` | **PASS** | `404 Not Found` | Returned when attempting to upload photos for a non-existent submission ID. |
| `/submissions/{id}/photos` | `POST` | **PASS** | `422 Unprocessable Entity` | Returned when `files` parameter is missing. |
| `/submissions` | `GET` | **PASS** | `200 OK` | Returns a list of all submissions sorted by creation date (descending). |
| `/submissions?status={status}`| `GET` | **PASS** | `200 OK` | Correctly filters submissions list by status (e.g. `verification`, `approved`). |
| `/submissions?status={status}`| `GET` | **PASS** | `400 Bad Request` | Returns `400` with message `Invalid status: {status}` if the status is not a valid enum value. |
| `/submissions/stats` | `GET` | **PASS** | `200 OK` | Returns aggregate counts grouped by status, including `total` and `duplicates_blocked`. |
| `/submissions/{id}` | `GET` | **PASS** | `200 OK` | Returns the full JSON payload of the submission and its Pydantic-validated `dossier`. |
| `/submissions/{id}` | `GET` | **PASS** | `404 Not Found` | Returns `404` when the submission ID does not exist in the database. |
| `/submissions/{id}/review` | `PATCH` | **PASS** | `200 OK` | Updates status to `approved` or `rejected`, records notes and reviewer metadata. |
| `/submissions/{id}/review` | `PATCH` | **PASS** | `400 Bad Request` | Returns `400` with message `decision must be 'approved' or 'rejected'` if decision query parameter is invalid. |
| `/submissions/{id}/review` | `PATCH` | **PASS** | `404 Not Found` | Returns `404` if the submission ID is not found. |

---

## Detailed Payload Analysis

### 1. Missing Required Fields during POST `/submissions`
* **Request**: `POST /submissions` with `{"country": "India"}`
* **Response Status**: `422 Unprocessable Entity`
* **Response Body**:
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "location_name"],
      "msg": "Field required",
      "input": {"country": "India"}
    },
    {
      "type": "missing",
      "loc": ["body", "description"],
      "msg": "Field required",
      "input": {"country": "India"}
    }
  ]
}
```

### 2. Invalid Review Decision during PATCH `/submissions/{id}/review`
* **Request**: `PATCH /submissions/SUB-2026-06-DF1D2859/review?decision=maybe`
* **Response Status**: `400 Bad Request`
* **Response Body**:
```json
{
  "detail": "decision must be 'approved' or 'rejected'"
}
```

### 3. Missing ID during GET `/submissions/{id}`
* **Request**: `GET /submissions/SUB-NOT-EXIST`
* **Response Status**: `404 Not Found`
* **Response Body**:
```json
{
  "detail": "Submission not found"
}
```
