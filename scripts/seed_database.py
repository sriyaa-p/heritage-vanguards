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
sys.path.insert(0, str(REPO_ROOT / "backend"))

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
Seed the heritage_sites table from data/processed/unesco_sites_clean.json.

Usage (from project root):
    docker compose exec backend python /scripts/seed_database.py

Or with a local Python environment:
    DATABASE_URL=postgresql://heritage_user:heritage_pass@localhost:5432/heritage_db \
    python scripts/seed_database.py
"""

import json
import os
import sys
import psycopg2
from psycopg2.extras import execute_values

DATA_FILE = os.path.join(os.path.dirname(__file__), "../data/processed/unesco_sites_clean.json")


def get_connection():
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set.")
        sys.exit(1)
    return psycopg2.connect(db_url)


def create_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS heritage_sites (
            id              INTEGER PRIMARY KEY,
            site_name       TEXT NOT NULL,
            country         TEXT NOT NULL,
            category        TEXT,
            year_inscribed  INTEGER,
            lat             DOUBLE PRECISION,
            lon             DOUBLE PRECISION,
            description     TEXT,
            search_text     TEXT GENERATED ALWAYS AS (
                                lower(site_name || ' ' || country || ' ' || coalesce(description, ''))
                            ) STORED
        );
        CREATE INDEX IF NOT EXISTS idx_heritage_sites_country ON heritage_sites(country);
        CREATE INDEX IF NOT EXISTS idx_heritage_sites_search  ON heritage_sites USING gin(to_tsvector('english', search_text));
    """)


def seed(cursor, sites):
    rows = [
        (
            s["id"],
            s["site_name"],
            s["country"],
            s.get("category"),
            s.get("year_inscribed"),
            s.get("lat"),
            s.get("lon"),
            s.get("description"),
        )
        for s in sites
    ]
    execute_values(
        cursor,
        """
        INSERT INTO heritage_sites (id, site_name, country, category, year_inscribed, lat, lon, description)
        VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            site_name      = EXCLUDED.site_name,
            country        = EXCLUDED.country,
            category       = EXCLUDED.category,
            year_inscribed = EXCLUDED.year_inscribed,
            lat            = EXCLUDED.lat,
            lon            = EXCLUDED.lon,
            description    = EXCLUDED.description
        """,
        rows,
    )


def main():
    print(f"Loading dataset from {DATA_FILE} ...")
    with open(DATA_FILE) as f:
        sites = json.load(f)
    print(f"  {len(sites)} sites loaded.")

    print("Connecting to database ...")
    conn = get_connection()
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            print("Creating heritage_sites table if not exists ...")
            create_table(cur)
            print(f"Seeding {len(sites)} sites ...")
            seed(cur, sites)
            conn.commit()
            cur.execute("SELECT COUNT(*) FROM heritage_sites;")
            count = cur.fetchone()[0]
            print(f"Done. heritage_sites table now contains {count} rows.")
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
