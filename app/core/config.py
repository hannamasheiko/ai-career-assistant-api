from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "AI Career Assistant API"
    api_version: str = "0.1.0"
    environment: str = "development"
    database_url: str
    test_database_url: str | None = None

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_timeout: float = 90.0
    openai_max_retries: int = 2

    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        """Parse the comma-separated CORS_ALLOWED_ORIGINS setting into a list."""

        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]


settings = Settings()