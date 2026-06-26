"""
EvaluationAgent — Heritage Sentinel AI
---------------------------------------
Implements the two-step evaluation architecture from PROJECT.md:

  Step 1 — Gemini 2.5 Flash extracts structured evidence (text only, no scores)
  Step 2 — Deterministic ScoringEngine assigns points from data/scoring_criteria.json

Gemini never assigns scores. The scoring engine applies fixed rules so that
identical inputs always produce identical scores (reproducibility requirement).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from google import genai
from google.genai import types as genai_types

from app.agents.scoring_engine import score_evidence
from app.core.config import settings
from app.models.dossier import CanonicalDossier, ExtractedEvidence

log = logging.getLogger(__name__)

_client = genai.Client(api_key=settings.GEMINI_API_KEY)
_MODEL = "gemini-2.5-flash"

_EXTRACTION_PROMPT = """
You are a UNESCO heritage site evidence analyst. Extract structured evidence
from the community submission below. Return ONLY a JSON object — no markdown,
no explanation, no extra text.

Required JSON keys:
{
  "historic_features": "<evidence of age, historical events, architectural periods, archaeological significance>",
  "cultural_significance": "<religious, artistic, social, intangible cultural value, living traditions>",
  "geographic_context": "<landscape, location, ecological or territorial significance, coordinates if mentioned>",
  "documentation_quality": "<available records, academic studies, government surveys, inscriptions, archives>",
  "supporting_evidence": "<assessment of photos and materials provided — quality, count, what they show>"
}

Rules:
- Extract only what is stated in the submission. Do not invent evidence.
- If a category has no evidence, write: "No evidence provided."
- Be specific — include dates, names, measurements when mentioned.
- Keep each field under 150 words.
""".strip()


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse JSON from Gemini response: {text[:300]}")


async def run_evaluation(dossier: CanonicalDossier) -> CanonicalDossier:
    """
    Two-step evaluation:
      1. Call Gemini to extract structured evidence text.
      2. Pass extracted evidence to the deterministic ScoringEngine.

    Updates dossier.extracted_evidence and dossier.scoring.
    Returns the updated dossier.
    """
    meta = dossier.metadata
    raw = dossier.raw_evidence

    # Build the submission context for Gemini
    description = raw.translated_description or raw.description
    submission_context = f"""
Site Name: {meta.location_name}
Country: {meta.country}
Description:
{description}
Number of photos submitted: {len(raw.photo_urls)}
""".strip()

    log.info("EvaluationAgent [1/2]: calling Gemini for evidence extraction — %s", meta.submission_id)

    try:
        response = _client.models.generate_content(
            model=_MODEL,
            contents=f"{_EXTRACTION_PROMPT}\n\n---\n\n{submission_context}",
            config=genai_types.GenerateContentConfig(
                temperature=0.1,   # Near-deterministic for consistent extraction
                max_output_tokens=1024,
            ),
        )
        data = _extract_json(response.text)
    except Exception as exc:
        log.error("EvaluationAgent: Gemini extraction failed for %s — %s", meta.submission_id, exc)
        data = {
            "historic_features": "Extraction unavailable — evaluation service error.",
            "cultural_significance": "Extraction unavailable — evaluation service error.",
            "geographic_context": "Extraction unavailable — evaluation service error.",
            "documentation_quality": "Extraction unavailable — evaluation service error.",
            "supporting_evidence": "Extraction unavailable — evaluation service error.",
        }

    extracted = ExtractedEvidence(
        historic_features=data.get("historic_features", "No evidence provided."),
        cultural_significance=data.get("cultural_significance", "No evidence provided."),
        geographic_context=data.get("geographic_context", "No evidence provided."),
        documentation_quality=data.get("documentation_quality", "No evidence provided."),
        supporting_evidence=data.get("supporting_evidence", "No evidence provided."),
    )

    dossier.extracted_evidence = extracted

    # Step 2: deterministic scoring — no Gemini involved
    log.info("EvaluationAgent [2/2]: deterministic scoring — %s", meta.submission_id)
    dossier.scoring = score_evidence(extracted, photo_count=len(raw.photo_urls))

    log.info(
        "EvaluationAgent complete: %s scored %d/100",
        meta.submission_id,
        dossier.scoring.total,
    )
    return dossier
