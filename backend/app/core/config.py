from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ResearchFlow AI"
    environment: str = "local"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/researchflow"
    frontend_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    seed_dir: Path = Field(default=ROOT_DIR / "data" / "seed")
    config_dir: Path = Field(default=ROOT_DIR / "config")
    demo_mode: bool = True
    run_inline: bool = True
    max_jobs_per_run: int = 40
    max_llm_calls_per_run: int = 40
    min_relevance: float = 0.55

    llm_enabled: bool = True
    gemini_api_key: str | None = None
    gemini_extraction_model: str = "gemini-2.5-flash-lite"
    gemini_report_model: str = "gemini-2.5-flash"
    ollama_base_url: str = "http://localhost:11434"

    admin_token: str = "change-me"
    sentry_dsn: str | None = None

    rate_limit_enabled: bool = True
    runs_per_hour_per_ip: int = 3
    runs_per_day_per_ip: int = 10
    runs_per_day_global: int = 100

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
