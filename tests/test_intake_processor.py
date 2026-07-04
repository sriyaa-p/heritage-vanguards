"""
Tests for IntakeProcessor — Heritage Sentinel AI

Covers:
  - Language detection (English, non-English, failure)
  - Translation routing (skip for English, call for non-English)
  - Translation failure fallback
  - Dossier mutation correctness

All tests run without a real Gemini key — external calls are mocked.
"""

from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from app.agents.intake_processor import run_intake, _detect_language, _translate_to_english
from app.models.dossier import (
    CanonicalDossier,
    Metadata,
    RawEvidence,
    SubmissionStatus,
)


def _make_dossier(description="Ancient ruins of the Vijayanagara Empire."):
    return CanonicalDossier(
        metadata=Metadata(
            submission_id="SUB-TEST-00000001",
            submitted_by="test_user",
            submitted_at=datetime.now(timezone.utc),
            location_name="Hampi",
            country="India",
            status=SubmissionStatus.pending,
        ),
        raw_evidence=RawEvidence(description=description),
    )


# ── Language detection unit tests ───────────────────────────────────────────

class TestDetectLanguage:
    """Unit tests for _detect_language(text)."""

    def test_detects_english(self):
        result = _detect_language("This is a heritage site in India.")
        assert result == "en"

    def test_detects_non_english(self):
        """Spanish text should be detected as Spanish (or at least not 'en' or 'unknown')."""
        result = _detect_language("Estas son ruinas antiguas en la India.")
        assert result != "en"
        assert result != "unknown"
        # Should be a valid ISO 639-1 code
        assert len(result) == 2

    def test_returns_unknown_on_empty_text(self):
        result = _detect_language("")
        assert result == "unknown"


# ── Translation unit tests ─────────────────────────────────────────────────

class TestTranslateToEnglish:
    """Unit tests for _translate_to_english(text, source_lang)."""

    @pytest.mark.asyncio
    async def test_translation_success(self):
        """Mocked Gemini returns translated text."""
        mock_response = AsyncMock()
        mock_response.text = "Ancient ruins in India."

        with patch("app.agents.intake_processor._client") as mock_client:
            mock_client.models.generate_content = MagicMock(return_value=mock_response)
            result = await _translate_to_english("Ruinas antiguas en la India.", "es")

        assert result == "Ancient ruins in India."

    @pytest.mark.asyncio
    async def test_translation_failure_fallback(self):
        """Gemini failure → returns original text as fallback."""
        with patch("app.agents.intake_processor._client") as mock_client:
            mock_client.models.generate_content = MagicMock(side_effect=Exception("API timeout"))
            result = await _translate_to_english("Texto original", "es")

        assert result == "Texto original"


# ── End-to-end run_intake tests ────────────────────────────────────────────

class TestRunIntake:
    """End-to-end tests for run_intake(dossier)."""

    @pytest.mark.asyncio
    async def test_english_no_translation(self):
        """English text → language_detected='en', translated_description = original."""
        dossier = _make_dossier(description="Ancient ruins in India.")

        with patch("app.agents.intake_processor._detect_language", return_value="en"):
            result = await run_intake(dossier)

        assert result.raw_evidence.language_detected == "en"
        assert result.raw_evidence.translated_description == "Ancient ruins in India."

    @pytest.mark.asyncio
    async def test_non_english_calls_translation(self):
        """Non-English text → translation called, result stored."""
        dossier = _make_dossier(description="Ruinas antiguas en la India.")

        with patch("app.agents.intake_processor._detect_language", return_value="es"):
            with patch(
                "app.agents.intake_processor._translate_to_english",
                return_value="Ancient ruins in India.",
            ) as mock_translate:
                result = await run_intake(dossier)

        assert result.raw_evidence.language_detected == "es"
        assert result.raw_evidence.translated_description == "Ancient ruins in India."
        mock_translate.assert_awaited_once_with("Ruinas antiguas en la India.", "es")

    @pytest.mark.asyncio
    async def test_unknown_language_no_translation(self):
        """Language detection fails → language_detected='unknown', no translation."""
        dossier = _make_dossier(description="Some text.")

        with patch("app.agents.intake_processor._detect_language", return_value="unknown"):
            result = await run_intake(dossier)

        assert result.raw_evidence.language_detected == "unknown"
        assert result.raw_evidence.translated_description == "Some text."

    @pytest.mark.asyncio
    async def test_preserves_dossier_identity(self):
        """run_intake returns the same dossier object (mutated, not replaced)."""
        dossier = _make_dossier()
        original_id = id(dossier)

        with patch("app.agents.intake_processor._detect_language", return_value="en"):
            result = await run_intake(dossier)

        assert id(result) == original_id
