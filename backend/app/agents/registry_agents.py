"""
RegistryAgent — Heritage Sentinel AI
--------------------------------------
Checks whether a community submission duplicates an existing UNESCO site.

Three-step process (per PROJECT.md):
  1. BM25 retrieval — fast keyword ranking across all UNESCO sites
  2. SQL ilike — exact/fuzzy name+country match as a quick gate
  3. Gemini comparison — LLM compares submission against top BM25 candidates
     to make a final, semantically-aware duplicate determination
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from google import genai
from google.genai import types as genai_types
import sqlalchemy as sa
from sqlalchemy import select, func

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.dossier import UnescoSite

log = logging.getLogger(__name__)

_TOP_N = 5
_client = genai.Client(api_key=settings.GEMINI_API_KEY)
_MODEL = "gemini-2.5-flash"

_COMPARISON_PROMPT = """
You are a UNESCO heritage registry specialist. Determine whether a community
submission refers to an already-documented UNESCO World Heritage Site.

Return ONLY a JSON object with exactly these keys:
{
  "is_duplicate": <true or false>,
  "confidence": <float 0.0–1.0>,
  "matched_site": "<exact site name from the registry, or null>",
  "reasoning": "<one sentence explaining your decision>"
}

Rules:
- is_duplicate = true ONLY if the submission clearly refers to the same
  physical site as a registry entry (same location, same monument/area).
- Minor name spelling differences do not make it a duplicate.
- A site NEAR a UNESCO site is NOT a duplicate unless it is the same site.
- If uncertain, set is_duplicate = false.
""".strip()


def _parse_gemini_json(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse JSON: {text[:200]}")


async def _gemini_compare(
    site_name: str,
    country: str,
    description: str,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Ask Gemini to compare the submission against the top FTS candidates."""
    candidate_text = "\n".join(
        f"  - {c['site_name']} ({c['country']}) — similarity: {c['similarity_score']:.4f}"
        for c in candidates
    )
    prompt = f"""
Submission:
  Site Name: {site_name}
  Country: {country}
  Description: {description[:500]}

Top Registry Candidates (FTS):
{candidate_text}

Is this submission a duplicate of any registry entry?
""".strip()

    response = _client.models.generate_content(
        model=_MODEL,
        contents=f"{_COMPARISON_PROMPT}\n\n---\n\n{prompt}",
        config=genai_types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=256,
            thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
        ),
    )
    return _parse_gemini_json(response.text)


async def lookup_unesco_registry(
    site_name: str,
    country: str,
    description: str = "",
) -> dict[str, Any]:
    """
    Full three-step registry check.

    Args:
        site_name:   Name of the candidate heritage site.
        country:     Country where the site is located.
        description: Raw submission description (used for Gemini comparison).

    Returns:
        Dict matching the RegistryCheck Pydantic model.
    """
    checked_at = datetime.now(timezone.utc).isoformat()
    sql_match: UnescoSite | None = None
    top_candidates: list[dict[str, Any]] = []
    best_fts_score: float = 0.0

    async with AsyncSessionLocal() as db:
        # ── Step 1: Exact SQL match (fast path) ────────────────────────────────
        # Only do an ilike match when the site name is meaningful (>=4 chars).
        if len(site_name.strip()) >= 4:
            exact_stmt = select(UnescoSite).where(
                UnescoSite.name.ilike(f"%{site_name}%"),
                UnescoSite.country.ilike(f"%{country}%"),
            )
            exact_result = await db.execute(exact_stmt)
            sql_match = exact_result.scalars().first()

        if sql_match:
            log.info("RegistryAgent: SQL exact match found — %s", sql_match.name)
            return {
                "is_duplicate": True,
                "matched_site": sql_match.name,
                "similarity_score": 1.0,
                "top_candidates": [
                    {
                        "site_name": sql_match.name,
                        "country": sql_match.country,
                        "similarity_score": 1.0,
                    }
                ],
                "checked_at": checked_at,
            }

        # ── Step 2: PostgreSQL Full Text Search (FTS) ──────────────────────────
        query_text = f"{site_name} {country}".strip()
        if query_text:
            # Check if we are running under SQLite (e.g. in unit tests)
            bind = db.sync_session.bind if hasattr(db, "sync_session") else db.bind
            is_sqlite = (bind.dialect.name == "sqlite") if bind else False

            if is_sqlite:
                # Fallback for SQLite unit tests: fetch all and do simple word overlap matching
                all_sites_result = await db.execute(select(UnescoSite))
                all_sites = all_sites_result.scalars().all()
                query_words = set(query_text.lower().split())
                for s in all_sites:
                    site_words = set((s.name + " " + s.country + " " + (s.description or "")).lower().split())
                    overlap = len(query_words & site_words)
                    if overlap > 0:
                        score = round(overlap / max(len(query_words), 1), 4)
                        top_candidates.append({
                            "site_name": s.name,
                            "country": s.country,
                            "similarity_score": score,
                        })
                top_candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
                top_candidates = top_candidates[:_TOP_N]
            else:
                # plainto_tsquery converts plain text to a valid tsquery (ANDing all words)
                ts_query = func.plainto_tsquery("english", query_text)
                fts_stmt = (
                    select(
                        UnescoSite.name,
                        UnescoSite.country,
                        func.ts_rank(UnescoSite.search_vector, ts_query).label("rank")
                    )
                    .where(UnescoSite.search_vector.op("@@")(ts_query))
                    .order_by(sa.desc("rank"))
                    .limit(_TOP_N)
                )
                fts_result = await db.execute(fts_stmt)
                for row in fts_result.all():
                    rank = round(float(row.rank), 4)
                    top_candidates.append({
                        "site_name": row.name,
                        "country": row.country,
                        "similarity_score": min(rank, 1.0),
                    })

            if top_candidates:
                best_fts_score = top_candidates[0]["similarity_score"]

    # ── Step 3: Gemini comparison: only when FTS finds plausible candidates ──
    # ts_rank scores are smaller than BM25, so we use a lower threshold (>= 0.01)
    if top_candidates and best_fts_score >= 0.01:
        log.info(
            "RegistryAgent: FTS top score %.4f >= 0.01, asking Gemini to compare",
            best_fts_score,
        )
        try:
            gemini_result = await _gemini_compare(
                site_name, country, description, top_candidates
            )
            is_dup = bool(gemini_result.get("is_duplicate", False))
            matched = gemini_result.get("matched_site") if is_dup else None
            confidence = float(gemini_result.get("confidence", best_fts_score))

            log.info(
                "RegistryAgent: Gemini says is_duplicate=%s (confidence=%.2f)",
                is_dup, confidence,
            )
            return {
                "is_duplicate": is_dup,
                "matched_site": matched,
                "similarity_score": confidence,
                "top_candidates": top_candidates,
                "checked_at": checked_at,
            }
        except Exception as exc:
            log.warning(
                "RegistryAgent: Gemini comparison failed (%s) — falling back to FTS only", exc
            )

    # ── Default: not a duplicate ──────────────────────────────────────────────
    return {
        "is_duplicate": False,
        "matched_site": None,
        "similarity_score": best_fts_score,
        "top_candidates": top_candidates,
        "checked_at": checked_at,
    }
