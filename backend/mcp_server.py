"""                                                                         
Heritage Sentinel AI — MCP Server                                            
---------------------------------------------------------------------------  
Exposes Heritage Sentinel data and tools via the Model Context Protocol      
(MCP) so that any MCP-compatible AI agent (e.g. Gemini via ADK, Claude,      
etc.) can interact with the Heritage Sentinel pipeline programmatically.     
                                                                             
Tools exposed:                                                               
  1. list_submissions        — paginated list of all submissions             
  2. get_submission          — full dossier for a single submission          
  3. search_unesco_sites     — full-text search across UNESCO registry       
  4. get_scoring_criteria    — returns the scoring rubric (JSON)             
  5. submit_candidate_site   — create a new heritage submission              
  6. record_review_decision  — approve / reject / escalate a submission      
                                                                             
Run standalone:                                                              
    python backend/mcp_server.py                    # stdio transport (default)
    python backend/mcp_server.py --transport sse    # SSE transport on :8001 
                                                                             
Or mount inside the existing FastAPI app (see main.py note at the bottom).  
"""                                                                         
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Make sure the repo root is importable when the file is run directly.
# backend/mcp_server.py  ->  repo root is two levels up.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import httpx
from mcp.server.fastmcp import FastMCP

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — all values fall back to sensible defaults so the MCP server
# can be started even without Docker (e.g. for local development / testing).
# ---------------------------------------------------------------------------
API_BASE_URL: str = os.getenv("HERITAGE_API_URL", "http://localhost:8000")
SCORING_CRITERIA_PATH: Path = (
    _REPO_ROOT / "data" / "scoring_criteria.json"
)

# ---------------------------------------------------------------------------
# FastMCP application
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="heritage-sentinel",
    instructions=(
        "You are interacting with the Heritage Sentinel AI system. "
        "Use the available tools to query UNESCO World Heritage candidate "
        "submissions, retrieve scoring criteria, search the UNESCO registry, "
        "and record reviewer decisions. "
        "Always present heritage scores and confidence levels clearly to the "
        "human reviewer. "
        "Never autonomously approve or reject a submission — the final "
        "decision must always be made by a human expert."
    ),
)


# ---------------------------------------------------------------------------
# Helper — shared async HTTP client
# ---------------------------------------------------------------------------
async def _get(path: str, params: dict | None = None) -> Any:
    """Perform a GET against the Heritage Sentinel FastAPI backend."""
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as client:
        resp = await client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()


async def _patch(path: str, payload: dict) -> Any:
    """Perform a PATCH against the Heritage Sentinel FastAPI backend."""
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as client:
        resp = await client.patch(path, json=payload)
        resp.raise_for_status()
        return resp.json()


async def _post(path: str, payload: dict) -> Any:
    """Perform a POST against the Heritage Sentinel FastAPI backend."""
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as client:
        resp = await client.post(path, json=payload)
        resp.raise_for_status()
        return resp.json()


# ===========================================================================
# Tool 1 — list_submissions
# ===========================================================================
@mcp.tool()
async def list_submissions(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
) -> dict:
    """
    Return a paginated list of heritage candidate submissions.

    Args:
        page:      Page number (1-based). Default 1.
        page_size: Number of results per page (max 100). Default 20.
        status:    Optional filter by pipeline status. Allowed values:
                   pending | registry_check | evaluation | reviewer_review |
                   committee_review | approved | rejected

    Returns:
        A dict with keys:
            items      — list of submission summaries
            total      — total number of matching submissions
            page       — current page
            page_size  — page size used
    """
    params: dict = {"page": page, "page_size": page_size}
    if status:
        params["status"] = status
    return await _get("/submissions", params=params)


# ===========================================================================
# Tool 2 — get_submission
# ===========================================================================
@mcp.tool()
async def get_submission(submission_id: str) -> dict:
    """
    Retrieve the full Canonical Dossier for a single heritage submission,
    including the heritage score, confidence level, evidence breakdown, and
    any reviewer decisions made so far.

    Args:
        submission_id: The submission identifier (e.g. SUB-2026-07-ABCD1234).

    Returns:
        The complete dossier as a nested dict, including:
            - metadata.status        current pipeline stage
            - scoring.total          heritage score (0-100)
            - scoring.*              per-category scores
            - registry_check         duplicate detection results
            - extracted_evidence     Gemini-extracted evidence per dimension
            - review                 reviewer decision (if any)
            - committee_review       committee decision (if any)
    """
    return await _get(f"/submissions/{submission_id}")


# ===========================================================================
# Tool 3 — search_unesco_sites
# ===========================================================================
@mcp.tool()
async def search_unesco_sites(query: str, limit: int = 10) -> dict:
    """
    Full-text search across the ~1,200 UNESCO World Heritage Sites dataset
    stored in the Heritage Sentinel database.

    Useful for:
      - Checking whether a candidate site already exists in the registry.
      - Finding similar heritage sites for context during evaluation.
      - Retrieving reference data for a particular country or region.

    Args:
        query: Free-text search string (site name, country, description).
        limit: Maximum number of results to return (default 10, max 50).

    Returns:
        A dict with key 'results' — a list of matching UNESCO site records,
        each containing: name, country, category, year_inscribed, criteria.
    """
    return await _get("/submissions/search/unesco", params={"q": query, "limit": limit})


# ===========================================================================
# Tool 4 — get_scoring_criteria
# ===========================================================================
@mcp.tool()
async def get_scoring_criteria() -> dict:
    """
    Return the full Heritage Sentinel scoring rubric — 8 UNESCO-aligned
    evaluation dimensions with their maximum point values, tier definitions,
    and keyword signals used by the deterministic scoring engine.

    This tool reads directly from data/scoring_criteria.json so it works
    even when the FastAPI backend is offline.

    Categories returned:
        historic_features       (max 25 pts)
        cultural_significance   (max 20 pts)
        integrity               (max 15 pts)
        authenticity            (max 15 pts)
        geographic_context      (max 10 pts)
        documentation_quality   (max 10 pts)
        management_protection   (max  5 pts)
        supporting_evidence     (max 15 pts)
        TOTAL                   (max 100 pts)

    Confidence levels:
        Low      —  0-59
        Moderate — 60-79
        High     — 80-100
    """
    if SCORING_CRITERIA_PATH.exists():
        with SCORING_CRITERIA_PATH.open(encoding="utf-8") as fh:
            return json.load(fh)
    # Fallback: ask the backend (future endpoint)
    return await _get("/submissions/scoring-criteria")


# ===========================================================================
# Tool 5 — submit_candidate_site
# ===========================================================================
@mcp.tool()
async def submit_candidate_site(
    location_name: str,
    country: str,
    description: str,
    submitted_by: str = "mcp-agent",
) -> dict:
    """
    Create a new heritage candidate submission and trigger the full
    Heritage Sentinel AI pipeline asynchronously.

    The pipeline stages run in background:
        1. IntakeProcessor  — language detection + translation
        2. RegistryAgent    — BM25 + Gemini duplicate detection
        3. EvaluationAgent  — evidence extraction + deterministic scoring
        4. VerificationAgent — confidence card + HITL routing

    Args:
        location_name:  Name of the candidate heritage site.
        country:        Country or region where the site is located.
        description:    Detailed description of the site's heritage significance.
        submitted_by:   Identifier for who is submitting (default: mcp-agent).

    Returns:
        A dict containing:
            submission_id   — unique ID for tracking this submission
            status          — initial pipeline status (always 'pending')
            message         — confirmation message

    IMPORTANT: This tool initiates AI evaluation. The pipeline runs
    asynchronously — poll get_submission() to track progress.
    Human expert review is always required before a site is approved.
    """
    payload = {
        "location_name": location_name,
        "country": country,
        "description": description,
        "submitted_by": submitted_by,
    }
    return await _post("/submissions", payload)


# ===========================================================================
# Tool 6 — record_review_decision
# ===========================================================================
@mcp.tool()
async def record_review_decision(
    submission_id: str,
    decision: str,
    notes: str = "",
    reviewer_id: str = "mcp-reviewer",
) -> dict:
    """
    Record a human reviewer's decision for a submission that has reached
    the 'reviewer_review' stage of the pipeline.

    IMPORTANT: This tool must only be called when a human expert has
    reviewed the Confidence Card and made a deliberate decision.
    The AI agent must NEVER call this autonomously — it must present
    the dossier to the human and wait for explicit confirmation.

    Args:
        submission_id: The submission to update.
        decision:      One of: 'approved' | 'rejected' | 'committee_review'
                       - approved         — reviewer confirms heritage value
                       - rejected         — reviewer dismisses the submission
                       - committee_review — escalate to UNESCO committee
        notes:         Optional reviewer notes / justification.
        reviewer_id:   Identifier for the reviewing expert.

    Returns:
        Updated submission summary with new status and decision recorded.
    """
    allowed = {"approved", "rejected", "committee_review"}
    if decision not in allowed:
        return {
            "error": f"Invalid decision '{decision}'. Must be one of: {sorted(allowed)}"
        }
    payload = {
        "decision": decision,
        "notes": notes,
        "reviewer_id": reviewer_id,
    }
    return await _patch(f"/submissions/{submission_id}/review", payload)


# ===========================================================================
# Entrypoint
# ===========================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Heritage Sentinel MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="MCP transport to use (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for SSE transport (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port for SSE transport (default: 8001)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.transport == "sse":
        log.info(
            "Starting Heritage Sentinel MCP Server (SSE) on %s:%s",
            args.host,
            args.port,
        )
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        log.info("Starting Heritage Sentinel MCP Server (stdio)")
        mcp.run(transport="stdio")
