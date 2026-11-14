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
    # Если сервер не достаёт до api.telegram.org: прокси (socks5://… или http://…)
    # или свой адрес Bot API (например, зеркало). Пусто — прямое подключение.
    telegram_proxy: str = ""
    telegram_api_url: str = ""

    @property
    def app_is_https(self) -> bool:
        return self.public_url.startswith("https://")

    def app_url(self, path: str = "") -> str:
        return f"{self.public_url.rstrip('/')}{path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
