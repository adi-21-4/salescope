from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://insights:insights@localhost:5432/insights_picker"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    cors_origins: list[str] = ["http://localhost:5173"]

    # LLM config is unused until M4, kept here so env wiring doesn't change later.
    llm_provider: str = "anthropic"
    anthropic_api_key: str | None = None


settings = Settings()
