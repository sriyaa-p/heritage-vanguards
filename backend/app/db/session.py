from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Base is defined in app.models.dossier (single source of truth for metadata).
# Import it here so sync_db.py can reference session.Base and get the full
# metadata registry that includes UnescoSite (and any future ORM models).
from app.models.dossier import Base  # noqa: F401

engine = create_async_engine(settings.DATABASE_URL, echo=True)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
