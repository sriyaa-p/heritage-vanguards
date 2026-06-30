import sys
from datetime import datetime
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.models.dossier import RegistryCheck, UnescoSite  # noqa: E402

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
_test_engine = create_async_engine(TEST_DB_URL, echo=False)
_TestSession = sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="module", autouse=True)
async def create_tables():
    async with _test_engine.begin() as conn:
        await conn.run_sync(UnescoSite.__table__.create)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(UnescoSite.__table__.drop)
    await _test_engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def seed_sites():
    rows = [
        UnescoSite(name="Taj Mahal", country="India", region="Asia and the Pacific",
                   inscription_year=1983, criteria="i",
                   description="Immense mausoleum of white marble in Agra."),
        UnescoSite(name="Ellora Caves", country="India", region="Asia and the Pacific",
                   inscription_year=1983, criteria="i,iii,vi",
                   description="Rock-cut temples representing Buddhist Hindu and Jain art."),
        UnescoSite(name="Ajanta Caves", country="India", region="Asia and the Pacific",
                   inscription_year=1983, criteria="i,ii,iii,vi",
                   description="Masterpieces of Buddhist religious art."),
        UnescoSite(name="Petra", country="Jordan", region="Arab States",
                   inscription_year=1985, criteria="i,iii,iv",
                   description="Capital of the Nabataean Empire carved in rock."),
        UnescoSite(name="Colosseum", country="Italy", region="Europe and North America",
                   inscription_year=1980, criteria="i,ii,iii,iv,vi",
                   description="The largest ancient amphitheatre ever built in Rome."),
    ]
    async with _TestSession() as session:
        session.add_all(rows)
        await session.commit()
    yield
    async with _TestSession() as session:
        await session.execute(delete(UnescoSite))
        await session.commit()


import app.agents.registry_agents as _agent  # noqa: E402


@pytest.fixture(autouse=True)
def patch_session(monkeypatch):
    monkeypatch.setattr(_agent, "AsyncSessionLocal", _TestSession)


@pytest.mark.asyncio
async def test_exact_duplicate_detected():
    result = await _agent.lookup_unesco_registry("Taj Mahal", "India")
    assert result["is_duplicate"] is True
    assert result["matched_site"] == "Taj Mahal"
    assert result["similarity_score"] == 1.0
    assert result["checked_at"] is not None


@pytest.mark.asyncio
async def test_partial_name_match_is_duplicate():
    result = await _agent.lookup_unesco_registry("Taj", "India")
    assert result["is_duplicate"] is True
    assert "Taj" in result["matched_site"]


@pytest.mark.asyncio
async def test_non_duplicate_returns_false():
    result = await _agent.lookup_unesco_registry("Hampi Temple Complex", "India")
    assert result["is_duplicate"] is False
    assert result["matched_site"] is None


@pytest.mark.asyncio
async def test_top_candidates_populated():
    result = await _agent.lookup_unesco_registry("Ancient Cave Temples", "India")
    assert isinstance(result["top_candidates"], list)
    assert len(result["top_candidates"]) > 0
    for c in result["top_candidates"]:
        assert "site_name" in c
        assert "country" in c
        assert 0.0 <= c["similarity_score"] <= 1.0


@pytest.mark.asyncio
async def test_checked_at_is_iso_timestamp():
    result = await _agent.lookup_unesco_registry("Unknown Ruin", "France")
    assert result["checked_at"] is not None
    parsed = datetime.fromisoformat(result["checked_at"])
    assert parsed is not None


@pytest.mark.asyncio
async def test_result_validates_as_registry_check():
    result = await _agent.lookup_unesco_registry("Ellora Temples", "India")
    rc = RegistryCheck(**result)
    assert isinstance(rc.is_duplicate, bool)


@pytest.mark.asyncio
async def test_country_mismatch_not_duplicate():
    result = await _agent.lookup_unesco_registry("Taj Mahal", "China")
    assert result["is_duplicate"] is False
