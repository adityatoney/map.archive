"""Application configuration via environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-to-a-random-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://medbed:medbed@db:5432/medbed"
    DATABASE_URL_SYNC: str = "postgresql://medbed:medbed@db:5432/medbed"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Neo4j
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "medbed_neo4j_pass"
    NEO4J_ENABLED: bool = True

    # ML Service
    ML_SERVICE_URL: str = "http://ml:8001"
    MODEL_NAME: str = "thomas-sounack/BioClinical-ModernBERT-base"
    MODEL_NAME_PROD: str = "thomas-sounack/BioClinical-ModernBERT-large"

    # Encryption (Fernet key for PHI fields)
    ENCRYPTION_KEY: str = "change-me-generate-a-real-fernet-key"

    # External APIs
    UMLS_API_KEY: str = "mock"
    # Claude model for LLM-powered analysis.
    # Auth is handled by the claude-proxy (macOS Keychain) in dev,
    # or ANTHROPIC_API_KEY in production.
    ANTHROPIC_API_KEY: str = ""  # Only needed in production (no Keychain)
    ANTHROPIC_MODEL: str = "claude-opus-4-6[1m]"
    KEGG_API_ENABLED: bool = True

    # UMLS cache (Redis DB 1, separate from Celery broker on DB 0)
    UMLS_CACHE_TTL: int = 2592000  # 30 days in seconds
    REDIS_CACHE_DB: int = 1

    # File storage
    UPLOAD_DIR: str = "/app/uploads"

    @property
    def is_mock_mode(self) -> bool:
        """Check if running with mock external services."""
        return self.UMLS_API_KEY == "mock"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
