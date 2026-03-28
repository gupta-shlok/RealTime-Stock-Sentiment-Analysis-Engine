from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # Optional API key for /analyze-custom endpoint (free local dev: set any value or leave unset)
    api_key: str = "dev-key-optional"

    # Comma-separated list of allowed CORS origins
    # Default allows local dev; override in production via ALLOWED_ORIGINS env var
    allowed_origins: str = "http://localhost:3000"

    # Deployment context — used for logging/debugging
    deployment_env: str = "local"

    # Confidence threshold for sentiment aggregation (SENT-02, D-05)
    # Articles where max(softmax_output) < this value are excluded from aggregation.
    # Affects /sentiment-trends, /sector-sentiment, /stock-narrative.
    # Does NOT affect the raw score shown in /news (D-06).
    finbert_min_confidence: float = 0.55

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance. .env file is read exactly once."""
    return Settings()
