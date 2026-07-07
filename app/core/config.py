from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "AI Career Assistant API"
    api_version: str = "0.1.0"
    environment: str = "development"
    database_url: str

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()