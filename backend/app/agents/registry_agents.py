from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import engine
from app.models.dossier import UnescoSite

async def lookup_unesco_registry(site_name: str, country: str) -> dict:
    async with AsyncSession(engine) as db:
        stmt = select(UnescoSite).where(
            UnescoSite.name.ilike(f"%{site_name}%"),
            UnescoSite.country.ilike(f"%{country}%")
        )
        result = await db.execute(stmt)
        match = result.scalar_one_or_none()
    
    if match:
        return {"is_duplicate": True, "matched_site": match.name}
    return {"is_duplicate": False}