from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "GM AI"
    api_prefix: str = "/api"
    database_path: Path = PROJECT_ROOT / "data" / "campaign.db"
    library_path: Path = PROJECT_ROOT / "library"
    homebrew_path: Path = PROJECT_ROOT / "data" / "homebrew_packs"
    max_upload_mb: int = 40
    llm_provider: str = "mock"
    llm_base_url: str = "http://localhost:11434"
    llm_model: str = "llama3.1:8b"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_prefix="GM_AI_",
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
