import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_allow_local_imports_without_external_services():
    settings = Settings(
        ENV="development",
        GEMINI_API_KEY=None,
        DATABASE_URL=None,
        POSTGRES_USER=None,
        POSTGRES_PASSWORD=None,
        POSTGRES_DB=None,
    )

    assert settings.GEMINI_API_KEY == "dev-test-key-not-configured"
    assert settings.DATABASE_URL == "sqlite+aiosqlite:///:memory:"


def test_settings_require_gemini_key_in_production():
    with pytest.raises(ValidationError) as exc:
        Settings(
            ENV="production",
            GEMINI_API_KEY=None,
            DATABASE_URL="postgresql+asyncpg://user:pass@postgres:5432/db",
        )

    assert "GEMINI_API_KEY must be provided" in str(exc.value)


def test_settings_build_database_url_from_postgres_parts():
    settings = Settings(
        ENV="development",
        GEMINI_API_KEY="test-key",
        DATABASE_URL=None,
        POSTGRES_USER="heritage_user",
        POSTGRES_PASSWORD="heritage_pass",
        POSTGRES_DB="heritage_db",
    )

    assert settings.DATABASE_URL == "postgresql+asyncpg://heritage_user:heritage_pass@postgres:5432/heritage_db"
