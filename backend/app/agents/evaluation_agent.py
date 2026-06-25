"""
EvaluationAgent — Heritage Sentinel AI
---------------------------------------
Uses Gemini 2.5 Flash to extract structured evidence from a submission's
raw description and score it across five heritage criteria.

Scoring rubric (total = 100):
  Historic Features      0–30
  Cultural Significance  0–25
  Geographic Context     0–15
  Documentation          0–15
  Supporting Evidence    0–15
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from google import genai
from google.genai import types as genai_types

from app.core.config import settings
from app.models.dossier import CanonicalDossier, ExtractedEvidence, ScoringResult

log = logging.getLogger(__name__)

_client = genai.Client(api_key=settings.GEMINI_API_KEY)
_MODEL = "gemini-2.5-flash"

_SYSTEM_PROMPT = """
You are an expert UNESCO heritage site evaluator. Given a community submission about a
potential heritage site, extract structured evidence and assign scores.

Return a single JSON object with EXACTLY these keys — no extra text, no markdown fences:

{
  "historic_features": "<string: evidence of age, historical events, architectural periods>",
  "cultural_significance": "<string: religious, artistic, social, or intangible cultural value>",
  "geographic_context": "<string: landscape, location, ecological or territorial significance>",
  "documentation_quality": "<string: available records, academic studies, photographs, archives>",
  "supporting_evidence": "<string: assessment of photos and materials provided by the submitter>",
  "score_historic_features": <integer 0–30>,
  "score_cultural_significance": <integer 0–25>,
  "score_geographic_context": <integer 0–15>,
  "score_documentation": <integer 0–15>,
  "score_supporting_evidence": <integer 0–15>,
  "rationale": "<string: 2-3 sentences explaining the overall score and key strengths/gaps>"
}

Scoring guidance:
- Historic Features (0–30): 25–30 = internationally significant, 15–24 = regionally important, 0–14 = limited evidence
- Cultural Significance (0–25): 20–25 = profound living or historic significance, 10–19 = moderate, 0–9 = unclear
- Geographic Context (0–15): 12–15 = exceptional landscape or ecological value, 6–11 = notable, 0–5 = generic
- Documentation (0–15): 12–15 = extensive published records, 6–11 = partial, 0–5 = anecdotal only
- Supporting Evidence (0–15): 12–15 = high-quality photos with clear detail, 6–11 = adequate, 0–5 = absent or poor

Be honest and critical. Not every site deserves a high score.
""".strip()


def _extract_json(text: str) -> dict[str, Any]:
    """Pull the first JSON object out of Gemini's response text."""
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find a {...} block inside the text
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse JSON from Gemini response: {text[:300]}")


async def run_evaluation(dossier: CanonicalDossier) -> CanonicalDossier:
    """
    Call Gemini 2.5 Flash to evaluate the submission.
    Updates dossier.extracted_evidence and dossier.scoring in place.
    Returns the updated dossier.
    """
    meta = dossier.metadata
    raw = dossier.raw_evidence

    prompt = f"""
Site Name: {meta.location_name}
Country: {meta.country}
Submitted Description:
{raw.description}

Number of photos provided: {len(raw.photo_urls)}
""".strip()

    log.info("EvaluationAgent: calling Gemini for %s", meta.submission_id)

    try:
        response = _client.models.generate_content(
            model=_MODEL,
            contents=f"{_SYSTEM_PROMPT}\n\n---\n\n{prompt}",
            config=genai_types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=1024,
            ),
        )
        data = _extract_json(response.text)
    except Exception as exc:
        log.error("EvaluationAgent: Gemini call failed for %s — %s", meta.submission_id, exc)
        # Return conservative fallback scores so pipeline can continue
        data = {
            "historic_features": "Unable to extract — evaluation service unavailable.",
            "cultural_significance": "Unable to extract — evaluation service unavailable.",
            "geographic_context": "Unable to extract — evaluation service unavailable.",
            "documentation_quality": "Unable to extract — evaluation service unavailable.",
            "supporting_evidence": "Unable to extract — evaluation service unavailable.",
            "score_historic_features": 0,
            "score_cultural_significance": 0,
            "score_geographic_context": 0,
            "score_documentation": 0,
            "score_supporting_evidence": 0,
            "rationale": f"Evaluation could not be completed: {exc}",
        }

    extracted = ExtractedEvidence(
        historic_features=data.get("historic_features", ""),
        cultural_significance=data.get("cultural_significance", ""),
        geographic_context=data.get("geographic_context", ""),
        documentation_quality=data.get("documentation_quality", ""),
        supporting_evidence=data.get("supporting_evidence", ""),
    )

    hf = min(int(data.get("score_historic_features", 0)), 30)
    cs = min(int(data.get("score_cultural_significance", 0)), 25)
    gc = min(int(data.get("score_geographic_context", 0)), 15)
    doc = min(int(data.get("score_documentation", 0)), 15)
    se = min(int(data.get("score_supporting_evidence", 0)), 15)

    scoring = ScoringResult(
        historic_features=hf,
        cultural_significance=cs,
        geographic_context=gc,
        documentation=doc,
        supporting_evidence=se,
        total=hf + cs + gc + doc + se,
        rationale=data.get("rationale", ""),
    )

    dossier.extracted_evidence = extracted
    dossier.scoring = scoring

    log.info(
        "EvaluationAgent: %s scored %d/100",
        meta.submission_id,
        scoring.total,
    )
    return dossier
