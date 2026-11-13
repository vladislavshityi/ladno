from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[3]
DEV_JWT_SECRET = "dev-only-secret-change-me-in-production-please"
DEV_PII_KEY = "ZGV2LW9ubHkta2V5LWZvci1sb2NhbC1wZGF0YS0wMDA="


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR.parent / ".env", ".env"), extra="ignore"
    )

    app_env: Literal["dev", "prod"] = "prod"
    database_url: str = "postgresql+asyncpg://ladno:ladno@localhost:5432/ladno"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    jwt_secret: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    pii_encryption_key: str = DEV_PII_KEY

    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    telegram_auth_max_age_seconds: int = 60 * 60 * 24
    bot_api_token: str = ""

    llm_provider: Literal["openai", "ollama", "none"] = "none"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_vision_model: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_vision_model: str = ""
    llm_timeout_seconds: float = 60.0
    llm_requests_per_minute: int = 20

    region: str = "vladivostok"
    data_dir: Path = BACKEND_DIR / "data"
    templates_dir: Path = BACKEND_DIR / "templates"
    upload_dir: Path = BACKEND_DIR / "uploads"
    fonts_dir: Path = BACKEND_DIR / "assets" / "fonts"

    pos_url: str = "https://pos.gosuslugi.ru/"
    pos_text_limit: int = 1000
    gis_zhkh_url: str = "https://dom.gosuslugi.ru/"
    consent_version: str = "2026-11"

    # Отправка обращений по email: без smtp_host канал недоступен.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_tls: Literal["starttls", "ssl", "none"] = "starttls"
    email_sends_per_issue: int = 3

    @model_validator(mode="after")
    def _require_real_secrets_in_prod(self) -> Self:
        if self.app_env == "prod" and self.jwt_secret == DEV_JWT_SECRET:
            raise ValueError("В prod нужен собственный JWT_SECRET")
        if self.app_env == "prod" and self.pii_encryption_key == DEV_PII_KEY:
            raise ValueError("В prod нужен собственный PII_ENCRYPTION_KEY")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def region_dir(self) -> Path:
        return self.data_dir / "regions" / self.region


@lru_cache
def get_settings() -> Settings:
    return Settings()
