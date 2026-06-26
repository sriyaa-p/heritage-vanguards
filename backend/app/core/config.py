from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Can be set directly (e.g. by Docker Compose) or built from parts below
    DATABASE_URL: Optional[str] = None

    # Postgres component vars (used in .env; Docker Compose composes DATABASE_URL)
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None

    GEMINI_API_KEY: str
    ENV: str = "development"

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        if not self.DATABASE_URL:
            if self.POSTGRES_USER and self.POSTGRES_PASSWORD and self.POSTGRES_DB:
                self.DATABASE_URL = (
                    f"postgresql+asyncpg://{self.POSTGRES_USER}:"
                    f"{self.POSTGRES_PASSWORD}@localhost:5432/{self.POSTGRES_DB}"
                )
            else:
                raise ValueError(
                    "DATABASE_URL must be set, or POSTGRES_USER / POSTGRES_PASSWORD "
                    "/ POSTGRES_DB must all be provided."
                )
        return self


settings = Settings()
