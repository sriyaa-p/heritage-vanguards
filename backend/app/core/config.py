from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # This now looks for a file named .env inside the SAME folder as where the app runs
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra="ignore")

    # API Keys & Environment
    GEMINI_API_KEY: Optional[str] = None
    ENV: str = "development"

    # File storage
    UPLOADS_DIR: str = "/data/uploads"

    # Rate limits
    RATE_LIMIT_SUBMISSION_PER_MIN: int = 10
    RATE_LIMIT_UPLOAD_PER_MIN: int = 20
    RATE_LIMIT_HEALTH_PER_MIN: int = 60

    # Input limits
    MAX_DESCRIPTION_LENGTH: int = 10000
    MAX_PHOTO_SIZE_MB: int = 10
    MAX_PHOTOS_PER_SUBMISSION: int = 5

    # Database connection
    DATABASE_URL: Optional[str] = None
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None

    @model_validator(mode="after")
    def validate_environment(self) -> "Settings":
        if self.ENV in {"production", "staging"} and (
            not self.GEMINI_API_KEY or self.GEMINI_API_KEY == "your_gemini_api_key_here"
        ):
            raise ValueError("GEMINI_API_KEY must be provided outside local development/test environments.")

        if not self.GEMINI_API_KEY:
            # Allows unit tests and local imports to run without a real API key.
            # Real Gemini calls will still fail unless the key is configured.
            self.GEMINI_API_KEY = "dev-test-key-not-configured"

        if not self.DATABASE_URL:
            # Note: Inside Docker, the database host is 'postgres', not 'localhost'
            db_host = "postgres"
            if self.POSTGRES_USER and self.POSTGRES_PASSWORD and self.POSTGRES_DB:
                self.DATABASE_URL = (
                    f"postgresql+asyncpg://{self.POSTGRES_USER}:"
                    f"{self.POSTGRES_PASSWORD}@{db_host}:5432/{self.POSTGRES_DB}"
                )
            elif self.ENV in {"production", "staging"}:
                raise ValueError("DATABASE_URL or Postgres credentials must be provided.")
            else:
                self.DATABASE_URL = "sqlite+aiosqlite:///:memory:"
        return self

settings = Settings()
