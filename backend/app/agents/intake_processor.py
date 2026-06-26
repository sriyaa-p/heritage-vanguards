"""
Intake Processor — Heritage Sentinel AI
-----------------------------------------
Handles multilingual submissions before the agent pipeline runs.

Steps:
  1. Detect the language of the description using lingua-language-detector
  2. If non-English, translate to English using Gemini 2.5 Flash
  3. Store language_detected and translated_description in raw_evidence

This ensures all downstream agents (RegistryAgent, EvaluationAgent) work
on English text regardless of the submission language.
"""

from __future__ import annotations

import logging

from google import genai
from google.genai import types as genai_types

from app.core.config import settings
from app.models.dossier import CanonicalDossier

log = logging.getLogger(__name__)

_client = genai.Client(api_key=settings.GEMINI_API_KEY)
_MODEL = "gemini-2.5-flash"


def _detect_language(text: str) -> str:
    """
    Detect the language of text using lingua-language-detector.
    Returns ISO 639-1 code (e.g. 'en', 'hi', 'fr') or 'unknown'.
    """
    try:
        from lingua import LanguageDetectorBuilder
        detector = (
            LanguageDetectorBuilder
            .from_all_languages()
            .with_minimum_relative_distance(0.9)
            .build()
        )
        language = detector.detect_language_of(text)
        if language:
            return language.iso_code_639_1.name.lower()
    except Exception as exc:
        log.warning("Language detection failed: %s", exc)
    return "unknown"


async def _translate_to_english(text: str, source_lang: str) -> str:
    """Translate text to English using Gemini."""
    prompt = (
        f"Translate the following text from {source_lang} to English. "
        f"Return only the translation, no explanation.\n\n{text}"
    )
    try:
        response = _client.models.generate_content(
            model=_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(temperature=0.1, max_output_tokens=1024),
        )
        return response.text.strip()
    except Exception as exc:
        log.error("Translation failed: %s", exc)
        return text  # Fall back to original if translation fails


async def run_intake(dossier: CanonicalDossier) -> CanonicalDossier:
    """
    Detect language and translate if needed.
    Updates dossier.raw_evidence.language_detected and translated_description.
    """
    raw = dossier.raw_evidence
    description = raw.description

    log.info("IntakeProcessor: detecting language for %s", dossier.metadata.submission_id)
    lang = _detect_language(description)
    raw.language_detected = lang

    if lang not in ("en", "unknown"):
        log.info("IntakeProcessor: translating from %s to English", lang)
        raw.translated_description = await _translate_to_english(description, lang)
    else:
        raw.translated_description = description

    return dossier
