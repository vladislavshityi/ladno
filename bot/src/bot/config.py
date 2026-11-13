from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    telegram_bot_token: str
    bot_api_token: str
    backend_url: str = "http://localhost:8000"
    # Адрес сайта: Mini App открывается по нему. Кнопки web_app Telegram принимает только с https.
    public_url: str = ""
    reminder_interval_minutes: int = 30

    @property
    def app_is_https(self) -> bool:
        return self.public_url.startswith("https://")

    def app_url(self, path: str = "") -> str:
        return f"{self.public_url.rstrip('/')}{path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
