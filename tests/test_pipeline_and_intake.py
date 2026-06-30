from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.models.dossier import (
    CanonicalDossier,
    Metadata,
    RawEvidence,
    RegistryCheck,
    ReviewDecision,
    SubmissionStatus,
)


def _make_dossier():
    return CanonicalDossier(
        metadata=Metadata(
            submission_id="SUB-PIPE-00000001",
            submitted_by="test_user",
            submitted_at=datetime.now(timezone.utc),
            location_name="Hampi Ruins",
            country="India",
            status=SubmissionStatus.pending,
        ),
        raw_evidence=RawEvidence(description="Ancient temple complex with historical significance."),
        review=ReviewDecision(),
    )


@pytest.mark.asyncio
async def test_intake_translates_non_english_submission(monkeypatch):
    from app.agents.intake_processor import run_intake
    import app.agents.intake_processor as intake

    dossier = _make_dossier()
    dossier.raw_evidence.description = "यह एक प्राचीन मंदिर है"

    monkeypatch.setattr(intake, "_detect_language", lambda _text: "hi")

    async def fake_translate(text, source_lang):
        assert source_lang == "hi"
        return "This is an ancient temple."

    monkeypatch.setattr(intake, "_translate_to_english", fake_translate)

    result = await run_intake(dossier)

    assert result.raw_evidence.language_detected == "hi"
    assert result.raw_evidence.translated_description == "This is an ancient temple."


@pytest.mark.asyncio
async def test_intake_keeps_english_submission_without_translation(monkeypatch):
    from app.agents.intake_processor import run_intake
    import app.agents.intake_processor as intake

    dossier = _make_dossier()
    monkeypatch.setattr(intake, "_detect_language", lambda _text: "en")

    async def fail_if_called(_text, _source_lang):
        raise AssertionError("English submissions should not be translated")

    monkeypatch.setattr(intake, "_translate_to_english", fail_if_called)

    result = await run_intake(dossier)

    assert result.raw_evidence.language_detected == "en"
    assert result.raw_evidence.translated_description == dossier.raw_evidence.description


class _FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_pipeline_runs_all_stages_for_new_submission(monkeypatch):
    import app.agents.pipeline as pipeline

    dossier = _make_dossier()
    persisted_statuses = []
    calls = []

    monkeypatch.setattr(pipeline, "AsyncSessionLocal", lambda: _FakeSession())

    async def fake_load(_db, _submission_id):
        return SimpleNamespace(dossier=dossier.model_dump(mode="json"))

    async def fake_persist(_db, _submission_id, updated_dossier, status):
        persisted_statuses.append(status)

    async def fake_intake(updated_dossier):
        calls.append("intake")
        updated_dossier.raw_evidence.translated_description = updated_dossier.raw_evidence.description
        return updated_dossier

    async def fake_lookup_unesco_registry(**_kwargs):
        calls.append("registry")
        return {"is_duplicate": False, "top_candidates": []}

    async def fake_evaluation(updated_dossier):
        calls.append("evaluation")
        return updated_dossier

    def fake_verification(updated_dossier):
        calls.append("verification")
        return updated_dossier, SubmissionStatus.verification

    monkeypatch.setattr(pipeline, "_load_submission", fake_load)
    monkeypatch.setattr(pipeline, "_persist", fake_persist)
    monkeypatch.setattr(pipeline, "run_intake", fake_intake)
    monkeypatch.setattr(pipeline, "lookup_unesco_registry", fake_lookup_unesco_registry)
    monkeypatch.setattr(pipeline, "run_evaluation", fake_evaluation)
    monkeypatch.setattr(pipeline, "run_verification", fake_verification)

    await pipeline.run_pipeline("SUB-PIPE-00000001")

    assert calls == ["intake", "registry", "evaluation", "verification"]
    assert persisted_statuses == [
        SubmissionStatus.registry_check,
        SubmissionStatus.registry_check,
        SubmissionStatus.evaluation,
        SubmissionStatus.evaluation,
        SubmissionStatus.verification,
    ]


@pytest.mark.asyncio
async def test_pipeline_skips_evaluation_for_duplicate_submission(monkeypatch):
    import app.agents.pipeline as pipeline

    dossier = _make_dossier()
    calls = []

    monkeypatch.setattr(pipeline, "AsyncSessionLocal", lambda: _FakeSession())
    monkeypatch.setattr(
        pipeline,
        "_load_submission",
        lambda _db, _submission_id: None,
    )

    async def fake_load(_db, _submission_id):
        return SimpleNamespace(dossier=dossier.model_dump(mode="json"))

    async def fake_persist(_db, _submission_id, updated_dossier, status):
        pass

    async def fake_intake(updated_dossier):
        return updated_dossier

    async def fake_lookup_unesco_registry(**_kwargs):
        calls.append("registry")
        return {
            "is_duplicate": True,
            "matched_site": "Hampi",
            "similarity_score": 1.0,
            "top_candidates": [],
        }

    async def fail_if_evaluated(_updated_dossier):
        raise AssertionError("Duplicate submissions should skip evaluation")

    def fake_verification(updated_dossier):
        calls.append("verification")
        assert isinstance(updated_dossier.registry_check, RegistryCheck)
        return updated_dossier, SubmissionStatus.rejected

    monkeypatch.setattr(pipeline, "_load_submission", fake_load)
    monkeypatch.setattr(pipeline, "_persist", fake_persist)
    monkeypatch.setattr(pipeline, "run_intake", fake_intake)
    monkeypatch.setattr(pipeline, "lookup_unesco_registry", fake_lookup_unesco_registry)
    monkeypatch.setattr(pipeline, "run_evaluation", fail_if_evaluated)
    monkeypatch.setattr(pipeline, "run_verification", fake_verification)

    await pipeline.run_pipeline("SUB-PIPE-00000001")

    assert calls == ["registry", "verification"]
