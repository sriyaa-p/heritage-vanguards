from types import SimpleNamespace

import pytest

from app.models.dossier import SubmissionStatus


class _FakeResult:
    def __init__(self, rows=None, scalars=None):
        self._rows = rows or []
        self._scalars = scalars or []

    def all(self):
        return self._rows

    def scalars(self):
        return SimpleNamespace(all=lambda: self._scalars)


class _FakeStatsDB:
    async def execute(self, _query):
        rows = [
            SimpleNamespace(status=SubmissionStatus.rejected, count=3),
            SimpleNamespace(status=SubmissionStatus.verification, count=2),
            SimpleNamespace(status=SubmissionStatus.approved, count=1),
        ]
        rejected_submissions = [
            SimpleNamespace(dossier={"registry_check": {"is_duplicate": True}}),
            SimpleNamespace(dossier={"registry_check": {"is_duplicate": False}}),
            SimpleNamespace(dossier={"review": {"reviewer_notes": "insufficient evidence"}}),
        ]
        if not hasattr(self, "_calls"):
            self._calls = 0
        self._calls += 1
        return _FakeResult(rows=rows) if self._calls == 1 else _FakeResult(scalars=rejected_submissions)


@pytest.mark.asyncio
async def test_stats_counts_only_duplicate_rejections_as_duplicates_blocked():
    from app.api.routes.submissions import get_stats

    stats = await get_stats(db=_FakeStatsDB())

    assert stats["rejected"] == 3
    assert stats["duplicates_blocked"] == 1


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok():
    from main import health

    assert await health() == {"status": "ok", "service": "heritage-sentinel-ai"}
