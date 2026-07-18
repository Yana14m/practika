from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    BOT_TOKEN: str
    DB_PATH: str = "/data/max_bot.db"
    NOTIFY_DAYS_BEFORE: int = 1
    CHECK_INTERVAL_MINUTES: int = 15


settings = Settings()
