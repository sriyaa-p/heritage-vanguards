"""
app/agents/registry_agents.py
------------------------------
RegistryAgent: checks whether a community submission duplicates an existing
UNESCO World Heritage Site.

Steps:
  1. Exact / fuzzy SQL lookup (ilike) on name + country.
  2. BM25 ranking across all site names to find near-matches and score them.
  3. Returns a dict compatible with the RegistryCheck Pydantic model.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from rank_bm25 import BM25Okapi
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.dossier import UnescoSite

# Number of BM25 top-candidates to include in the response
_TOP_N = 5


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + lowercase tokenizer for BM25."""
    return text.lower().split()


async def lookup_unesco_registry(site_name: str, country: str) -> dict[str, Any]:
    """Check the UNESCO registry for duplicates.

    Args:
        site_name: Name of the candidate heritage site.
        country:   Country where the site is located.

    Returns:
        A dict matching the ``RegistryCheck`` Pydantic model fields:
        ``is_duplicate``, ``matched_site``, ``similarity_score``,
        ``top_candidates``, ``checked_at``.
    """
    async with AsyncSessionLocal() as db:
        # ── 1. Fetch all known sites (needed for BM25 corpus) ────────────────
        all_sites_result = await db.execute(select(UnescoSite))
        all_sites: list[UnescoSite] = list(all_sites_result.scalars().all())

        # ── 2. Exact / fuzzy SQL match (ilike on name AND country) ───────────
        exact_stmt = select(UnescoSite).where(
            UnescoSite.name.ilike(f"%{site_name}%"),
            UnescoSite.country.ilike(f"%{country}%"),
        )
        exact_result = await db.execute(exact_stmt)
        exact_match: UnescoSite | None = exact_result.scalar_one_or_none()

    checked_at = datetime.now(timezone.utc).isoformat()

    # ── 3. BM25 ranking across all site names ────────────────────────────────
    top_candidates: list[dict[str, Any]] = []
    best_score: float = 0.0

    if all_sites:
        corpus = [_tokenize(s.name + " " + s.country) for s in all_sites]
        bm25 = BM25Okapi(corpus)
        query_tokens = _tokenize(site_name + " " + country)
        scores = bm25.get_scores(query_tokens)

        # Pair each site with its BM25 score and sort descending
        ranked = sorted(
            zip(scores, all_sites),
            key=lambda t: t[0],
            reverse=True,
        )

        # Normalise scores to [0, 1] relative to the top score
        top_raw_score = ranked[0][0] if ranked else 1.0
        normalise = (lambda s: round(s / top_raw_score, 4)) if top_raw_score > 0 else (lambda s: 0.0)

        top_candidates = [
            {
                "site_name": site.name,
                "country": site.country,
                "similarity_score": normalise(score),
            }
            for score, site in ranked[:_TOP_N]
            if score > 0
        ]
        best_score = top_candidates[0]["similarity_score"] if top_candidates else 0.0

    # ── 4. Build response ─────────────────────────────────────────────────────
    if exact_match:
        return {
            "is_duplicate": True,
            "matched_site": exact_match.name,
            "similarity_score": 1.0,
            "top_candidates": top_candidates,
            "checked_at": checked_at,
        }

    return {
        "is_duplicate": False,
        "matched_site": None,
        "similarity_score": best_score,
        "top_candidates": top_candidates,
        "checked_at": checked_at,
    }