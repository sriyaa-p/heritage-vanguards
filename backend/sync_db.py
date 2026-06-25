import asyncio
from app.db.session import engine, Base
from app.models.dossier import UnescoSite

async def sync_database():
    print("Connecting to database and creating tables...")
    async with engine.begin() as conn:
        # This command looks at your models and creates tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)
        print("Table 'unesco_sites' created successfully!")

if __name__ == "__main__":
    asyncio.run(sync_database())