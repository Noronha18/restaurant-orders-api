from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/restaurant_orders"
    # Segredo compartilhado com o gateway para assinar os webhooks (HMAC-SHA256). Obrigatório.
    WEBHOOK_SECRET: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
