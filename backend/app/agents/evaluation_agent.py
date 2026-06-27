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

# Minimum combined length (site name + description) to proceed with Gemini evaluation.
# Inputs shorter than this are clearly junk (e.g. "A", "B", "C") and get auto-zero.
_MIN_INPUT_LENGTH = 20

from google import genai
from google.genai import types as genai_types

from app.agents.scoring_engine import score_evidence
from app.core.config import settings
from app.models.dossier import CanonicalDossier, ExtractedEvidence

log = logging.getLogger(__name__)

_client = genai.Client(api_key=settings.GEMINI_API_KEY)
_MODEL = "gemini-2.5-flash"

_EXTRACTION_PROMPT = """
You are a UNESCO World Heritage Site nomination analyst applying the Operational Guidelines (WHC.25/01).
Extract structured evidence from the community submission below across all three UNESCO nomination pillars:
  1. Outstanding Universal Value (OUV criteria i–x)
  2. Integrity (wholeness and intactness of the property)
  3. Authenticity (original materials, form, design, and use)

Return ONLY a JSON object — no markdown, no explanation, no extra text.

Required JSON keys:
{
  "historic_features": "<Evidence of OUV criteria i, iii, iv: human creative genius, unique cultural testimony, outstanding architectural/historical examples. Include dates, dynasty names, archaeological findings, construction periods.>",
  "cultural_significance": "<Evidence of OUV criteria ii, v, vi: cultural exchange, living traditions, intangible heritage, traditional land use, direct association with events/beliefs/artistic works.>",
  "integrity": "<UNESCO Integrity: Is the property whole and intact? Evidence of conservation status, protected boundaries, buffer zones, absence of adverse development, legal protection, or threats such as encroachment or neglect.>",
  "authenticity": "<UNESCO Authenticity (cultural properties): Evidence that cultural values are truthfully expressed through original materials, form, design, traditional use, setting, or craftsmanship. Note any reconstruction or alteration.>",
  "geographic_context": "<Evidence of OUV criteria vii–x: superlative natural phenomena, geological significance, ecological processes, biodiversity, threatened or endemic species, landscape setting and coordinates.>",
  "documentation_quality": "<Available academic studies, archaeological surveys, government records, ICOMOS/IUCN evaluations, peer-reviewed publications, archives, inscriptions, or other formal documentation.>",
  "management_protection": "<Evidence of a management plan, legal protection framework, conservation authority, national legislation protecting the site, government oversight, or heritage designation.>",
  "supporting_evidence": "<Assessment of photos and visual materials provided — count, quality, what they show (interior, exterior, aerial, inscriptions, etc.)>."
}

Rules:
- Extract only what is stated in the submission. Do not invent evidence.
- If a category has no evidence, write: "No evidence provided."
- Be specific — include dates, names, measurements, criteria references when mentioned.
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

    # ── Minimum input quality gate ────────────────────────────────────────────
    # If the submission is trivially short (single letters, empty fields), skip
    # Gemini entirely — the LLM will hallucinate significance for junk inputs.
    combined_input = (meta.location_name.strip() + " " + description.strip()).strip()
    if len(combined_input) < _MIN_INPUT_LENGTH:
        log.warning(
            "EvaluationAgent: input too short (%d chars) for %s — skipping Gemini, scoring zero",
            len(combined_input), meta.submission_id,
        )
        _no_evidence = "Insufficient input — submission too short to evaluate."
        dossier.extracted_evidence = ExtractedEvidence(
            historic_features=_no_evidence,
            cultural_significance=_no_evidence,
            integrity=_no_evidence,
            authenticity=_no_evidence,
            geographic_context=_no_evidence,
            documentation_quality=_no_evidence,
            management_protection=_no_evidence,
            supporting_evidence=_no_evidence,
        )
        from app.models.dossier import ScoringResult
        dossier.scoring = ScoringResult(
            historic_features=0, cultural_significance=0, integrity=0,
            authenticity=0, geographic_context=0, documentation=0,
            management_protection=0, supporting_evidence=0, total=0,
            rationale="Submission rejected before evaluation: input too short to assess heritage value.",
        )
        return dossier
    # ─────────────────────────────────────────────────────────────────────────

    log.info("EvaluationAgent [1/2]: calling Gemini for evidence extraction — %s", meta.submission_id)

    try:
        response = _client.models.generate_content(
            model=_MODEL,
            contents=f"{_EXTRACTION_PROMPT}\n\n---\n\n{submission_context}",
            config=genai_types.GenerateContentConfig(
                temperature=0.1,   # Near-deterministic for consistent extraction
                max_output_tokens=1024,
                thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
            ),
        )
        data = _extract_json(response.text)
    except Exception as exc:
        log.error("EvaluationAgent: Gemini extraction failed for %s — %s", meta.submission_id, exc)
        data = {
            "historic_features": "Extraction unavailable — evaluation service error.",
            "cultural_significance": "Extraction unavailable — evaluation service error.",
            "integrity": "Extraction unavailable — evaluation service error.",
            "authenticity": "Extraction unavailable — evaluation service error.",
            "geographic_context": "Extraction unavailable — evaluation service error.",
            "documentation_quality": "Extraction unavailable — evaluation service error.",
            "management_protection": "Extraction unavailable — evaluation service error.",
            "supporting_evidence": "Extraction unavailable — evaluation service error.",
        }

    extracted = ExtractedEvidence(
        historic_features=data.get("historic_features", "No evidence provided."),
        cultural_significance=data.get("cultural_significance", "No evidence provided."),
        integrity=data.get("integrity", "No evidence provided."),
        authenticity=data.get("authenticity", "No evidence provided."),
        geographic_context=data.get("geographic_context", "No evidence provided."),
        documentation_quality=data.get("documentation_quality", "No evidence provided."),
        management_protection=data.get("management_protection", "No evidence provided."),
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
