"""
scripts/seed_database.py
------------------------
Reads data/processed/unesco_sites_clean.json and inserts every site as a
UnescoSite row into PostgreSQL.  Safe to run multiple times — existing rows
are matched on (name, country) and updated in place rather than duplicated.

Usage (from repo root, with .env present):
    python scripts/seed_database.py              # upsert mode (default)
    python scripts/seed_database.py --reset      # truncate table first, then insert
"""

import asyncio
import json
import sys
from pathlib import Path

# ── Make sure the backend package is importable when run from repo root ──────
REPO_ROOT = Path(__file__).resolve().parent.parent
if (REPO_ROOT / "backend").exists():
    sys.path.insert(0, str(REPO_ROOT / "backend"))
elif Path("/app").exists():
    sys.path.insert(0, "/app")


from sqlalchemy import text                          # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession      # noqa: E402

from app.db.session import engine, Base              # noqa: E402  (Base re-exported here)
from app.models.dossier import UnescoSite            # noqa: E402

DATA_FILE = REPO_ROOT / "data" / "processed" / "unesco_sites_clean.json"


async def seed(reset: bool = False) -> None:
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found at {DATA_FILE}. "
            "Run the data-preparation step first or check the file path."
        )

    records = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    print(f"[seed] Loaded {len(records)} sites from {DATA_FILE.name}")

    # ── Ensure tables exist ──────────────────────────────────────────────────
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("[seed] Schema verified / created.")

        if reset:
            await conn.execute(text("TRUNCATE TABLE unesco_sites RESTART IDENTITY"))
            print("[seed] Table truncated (--reset mode).")

    # ── Upsert rows ─────────────────────────────────────────────────────────
    inserted = 0
    updated = 0

    async with AsyncSession(engine, expire_on_commit=False) as session:
        for raw in records:
            # Try to find an existing row by (name, country) to avoid dupes
            from sqlalchemy import select
            stmt = (
                select(UnescoSite)
                .where(UnescoSite.name == raw["name"])
                .where(UnescoSite.country == raw["country"])
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.region = raw.get("region")
                existing.inscription_year = raw.get("inscription_year")
                existing.criteria = raw.get("criteria")
                existing.description = raw.get("description")
                updated += 1
            else:
                site = UnescoSite(
                    name=raw["name"],
                    country=raw["country"],
                    region=raw.get("region"),
                    inscription_year=raw.get("inscription_year"),
                    criteria=raw.get("criteria"),
                    description=raw.get("description"),
                )
                session.add(site)
                inserted += 1

        await session.commit()

    print(
        f"[seed] Done — {inserted} inserted, {updated} updated. "
        f"Total rows in dataset: {len(records)}."
    )


if __name__ == "__main__":
    reset_flag = "--reset" in sys.argv
    if reset_flag:
        print("[seed] Running in RESET mode — existing rows will be deleted first.")
    asyncio.run(seed(reset=reset_flag))
