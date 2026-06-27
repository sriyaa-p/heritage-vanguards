from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # This now looks for a file named .env inside the SAME folder as where the app runs
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra="ignore")

    # API Keys & Environment
    GEMINI_API_KEY: str
    ENV: str = "development"

    # Database connection
    DATABASE_URL: Optional[str] = None
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        if not self.DATABASE_URL:
            # Note: Inside Docker, the database host is 'postgres', not 'localhost'
            db_host = "postgres" 
            if self.POSTGRES_USER and self.POSTGRES_PASSWORD and self.POSTGRES_DB:
                self.DATABASE_URL = (
                    f"postgresql+asyncpg://{self.POSTGRES_USER}:"
                    f"{self.POSTGRES_PASSWORD}@{db_host}:5432/{self.POSTGRES_DB}"
                )
            else:
                raise ValueError("DATABASE_URL or Postgres credentials must be provided.")
        return self

settings = Settings()