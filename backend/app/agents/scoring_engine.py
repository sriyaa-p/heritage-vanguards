"""
Deterministic Scoring Engine — Heritage Sentinel AI
-----------------------------------------------------
Reads data/scoring_criteria.json and scores Gemini-extracted evidence
using keyword signal matching. Identical inputs always produce identical
scores — no randomness, no model variance.

Architecture (per PROJECT.md):
  Gemini extracts evidence → Pydantic validates → this engine assigns scores
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Any

from app.models.dossier import ExtractedEvidence, ScoringResult

log = logging.getLogger(__name__)

_CRITERIA_PATH = os.path.join(
    os.path.dirname(__file__), "../../../../data/scoring_criteria.json"
)


@lru_cache(maxsize=1)
def _load_criteria() -> dict[str, Any]:
    path = os.path.abspath(_CRITERIA_PATH)
    with open(path) as f:
        return json.load(f)


def _score_field(text: str, category_criteria: dict) -> int:
    """
    Score a single evidence field against its tier definitions.
    Finds the highest tier whose signals appear in the text and
    returns a score proportional to signal density within that tier.
    """
    if not text or "unavailable" in text.lower():
        return 0

    text_lower = text.lower()
    tiers = category_criteria["tiers"]
    cat_max = category_criteria["max"]

    best_tier = None
    best_signal_count = 0

    for tier in tiers:
        if not tier["signals"]:
            continue
        found = sum(1 for signal in tier["signals"] if signal.lower() in text_lower)
        if found > 0 and (best_tier is None or found > best_signal_count):
            best_tier = tier
            best_signal_count = found

    if best_tier is None:
        # No signals found — minimum score
        lowest_tier = tiers[-1]
        return lowest_tier["min"]

    tier_min = best_tier["min"]
    tier_max = best_tier["max"]
    tier_range = tier_max - tier_min

    # Scale within the tier based on how many signals were found
    max_possible_signals = len(best_tier["signals"])
    density = min(best_signal_count / max(max_possible_signals, 1), 1.0)
    raw = tier_min + round(density * tier_range)

    # Clamp to category maximum
    return min(raw, cat_max)


def score_evidence(evidence: ExtractedEvidence, photo_count: int = 0) -> ScoringResult:
    """
    Apply deterministic scoring rules to extracted evidence.

    Args:
        evidence:    Pydantic model with five text fields from EvaluationAgent.
        photo_count: Number of photos submitted (boosts supporting_evidence score).

    Returns:
        ScoringResult with category scores, total, and rationale.
    """
    criteria = _load_criteria()["categories"]

    hf  = _score_field(evidence.historic_features,   criteria["historic_features"])
    cs  = _score_field(evidence.cultural_significance, criteria["cultural_significance"])
    gc  = _score_field(evidence.geographic_context,   criteria["geographic_context"])
    doc = _score_field(evidence.documentation_quality, criteria["documentation"])

    # Supporting evidence combines text quality + actual photo count
    se_text = _score_field(evidence.supporting_evidence, criteria["supporting_evidence"])
    photo_bonus = min(photo_count * 2, 5)  # up to +5 for photos
    se = min(se_text + photo_bonus, criteria["supporting_evidence"]["max"])

    total = hf + cs + gc + doc + se

    confidence = "High" if total >= 80 else "Moderate" if total >= 60 else "Low"

    rationale = (
        f"Heritage Score: {total}/100 ({confidence} Confidence). "
        f"Historic Features: {hf}/30 — "
        f"Cultural Significance: {cs}/25 — "
        f"Geographic Context: {gc}/15 — "
        f"Documentation: {doc}/15 — "
        f"Supporting Evidence: {se}/15."
    )

    log.info(
        "ScoringEngine: hf=%d cs=%d gc=%d doc=%d se=%d total=%d",
        hf, cs, gc, doc, se, total,
    )

    return ScoringResult(
        historic_features=hf,
        cultural_significance=cs,
        geographic_context=gc,
        documentation=doc,
        supporting_evidence=se,
        total=total,
        rationale=rationale,
    )
