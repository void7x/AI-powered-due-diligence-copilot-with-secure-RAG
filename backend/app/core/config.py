"""Application configuration loaded from environment variables / .env files."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import secrets

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]   # backend/
ROOT_DIR = BACKEND_DIR.parent                       # repository root


class Settings(BaseSettings):
    """All runtime configuration. Secrets are never hard-coded."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", str(ROOT_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "AI Due Diligence Copilot"
    environment: str = "development"
    debug: bool = False

    # Security
    # In development/tests, an ephemeral key is generated when SECRET_KEY is absent.
    # Production-like environments must provide an explicit secret.
    secret_key: str | None = Field(default=None)
    access_token_expire_minutes: int = 720

    # Database (PostgreSQL + pgvector in production; SQLite fallback for dev/tests)
    database_url: str = f"sqlite:///{ROOT_DIR / 'data' / 'app.db'}"

    # Files
    upload_dir: Path = ROOT_DIR / "data" / "uploads"
    max_upload_mb: int = 50

    # CORS
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # AI providers: auto | openai | offline
    ai_provider: str = "auto"
    embedding_provider: str = "auto"
    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536
    llm_temperature: float = 0.1
    llm_timeout_seconds: int = 90

    # Chunking / retrieval
    chunk_size_tokens: int = 450
    chunk_overlap_tokens: int = 60
    retrieval_top_k: int = 8
    retrieval_candidate_k: int = 40
    reranker: str = "none"  # none | llm

    # Risk rule thresholds (configurable per deployment)
    concentration_threshold_pct: float = 30.0
    current_ratio_floor: float = 1.2
    quick_ratio_floor: float = 1.0
    leverage_gap_threshold: float = 0.10        # debt growth minus revenue growth (fraction)
    margin_decline_threshold_pts: float = 1.5   # percentage points
    intl_revenue_threshold_pct: float = 35.0
    interest_to_ebitda_threshold: float = 0.30

    # Demo bootstrap (development convenience)
    create_demo_user: bool = False
    demo_email: str = "demo@example.com"
    demo_password: str = ""

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        environment = self.environment.strip().lower()
        production_like = environment in {"production", "prod", "staging"}

        if self.secret_key is not None:
            self.secret_key = self.secret_key.strip()

        if production_like and not self.secret_key:
            raise ValueError("SECRET_KEY must be explicitly configured in production-like environments")

        if not self.secret_key:
            self.secret_key = secrets.token_urlsafe(32)

        if self.create_demo_user and not self.demo_password:
            raise ValueError("DEMO_PASSWORD must be configured when CREATE_DEMO_USER=true")

        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
