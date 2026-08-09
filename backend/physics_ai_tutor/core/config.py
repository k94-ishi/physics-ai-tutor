from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Physics AI Tutor"
    environment: str = "development"
    embedding_model: str = "text-embedding-3-small"
    database_url: str
    openai_api_key: str

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


settings = Settings()
