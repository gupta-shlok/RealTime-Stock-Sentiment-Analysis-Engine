from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # Required — server will refuse to start if API_KEY is not set in environment
    api_key: str

    # Comma-separated list of allowed CORS origins
    # Default allows local dev; override in production via ALLOWED_ORIGINS env var
    allowed_origins: str = "http://localhost:3000"

    # Deployment context — used for logging/debugging
    deployment_env: str = "local"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance. .env file is read exactly once."""
    return Settings()
