from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    GEMINI_API_KEY: str
    ENV: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
