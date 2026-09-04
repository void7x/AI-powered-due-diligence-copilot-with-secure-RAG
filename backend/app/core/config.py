"""Application configuration loaded from environment variables / .env files."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
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
    debug: bool = True

    # Security
    secret_key: str = Field(default="dev-insecure-secret-change-me")
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
    create_demo_user: bool = True
    demo_email: str = "demo@example.com"
    demo_password: str = "demo1234"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
