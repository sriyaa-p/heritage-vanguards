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
from rank_bm25 import BM25Okapi
from sqlalchemy import select

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


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


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
    """Ask Gemini to compare the submission against the top BM25 candidates."""
    candidate_text = "\n".join(
        f"  - {c['site_name']} ({c['country']}) — similarity: {c['similarity_score']:.2f}"
        for c in candidates
    )
    prompt = f"""
Submission:
  Site Name: {site_name}
  Country: {country}
  Description: {description[:500]}

Top Registry Candidates (BM25):
{candidate_text}

Is this submission a duplicate of any registry entry?
""".strip()

    response = _client.models.generate_content(
        model=_MODEL,
        contents=f"{_COMPARISON_PROMPT}\n\n---\n\n{prompt}",
        config=genai_types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=256,
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
    async with AsyncSessionLocal() as db:
        all_sites_result = await db.execute(select(UnescoSite))
        all_sites: list[UnescoSite] = list(all_sites_result.scalars().all())

        exact_stmt = select(UnescoSite).where(
            UnescoSite.name.ilike(f"%{site_name}%"),
            UnescoSite.country.ilike(f"%{country}%"),
        )
        exact_result = await db.execute(exact_stmt)
        sql_match: UnescoSite | None = exact_result.scalars().first()

    checked_at = datetime.now(timezone.utc).isoformat()

    # ── BM25 ranking ─────────────────────────────────────────────────────────
    top_candidates: list[dict[str, Any]] = []
    best_bm25_score: float = 0.0

    if all_sites:
        corpus = [_tokenize(s.name + " " + s.country) for s in all_sites]
        bm25 = BM25Okapi(corpus)
        scores = bm25.get_scores(_tokenize(site_name + " " + country))

        ranked = sorted(zip(scores, all_sites), key=lambda t: t[0], reverse=True)
        top_raw = ranked[0][0] if ranked else 1.0
        norm = (lambda s: round(s / top_raw, 4)) if top_raw > 0 else (lambda s: 0.0)

        top_candidates = [
            {"site_name": s.name, "country": s.country, "similarity_score": norm(sc)}
            for sc, s in ranked[:_TOP_N]
            if sc > 0
        ]
        best_bm25_score = top_candidates[0]["similarity_score"] if top_candidates else 0.0

    # ── Fast path: exact SQL match → no need for Gemini ──────────────────────
    if sql_match:
        log.info("RegistryAgent: SQL exact match found — %s", sql_match.name)
        return {
            "is_duplicate": True,
            "matched_site": sql_match.name,
            "similarity_score": 1.0,
            "top_candidates": top_candidates,
            "checked_at": checked_at,
        }

    # ── Gemini comparison: only when BM25 finds plausible candidates ─────────
    if top_candidates and best_bm25_score >= 0.3:
        log.info(
            "RegistryAgent: BM25 top score %.2f >= 0.3, asking Gemini to compare",
            best_bm25_score,
        )
        try:
            gemini_result = await _gemini_compare(
                site_name, country, description, top_candidates
            )
            is_dup = bool(gemini_result.get("is_duplicate", False))
            matched = gemini_result.get("matched_site") if is_dup else None
            confidence = float(gemini_result.get("confidence", best_bm25_score))

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
                "RegistryAgent: Gemini comparison failed (%s) — falling back to BM25 only", exc
            )

    # ── Default: not a duplicate ──────────────────────────────────────────────
    return {
        "is_duplicate": False,
        "matched_site": None,
        "similarity_score": best_bm25_score,
        "top_candidates": top_candidates,
        "checked_at": checked_at,
    }
