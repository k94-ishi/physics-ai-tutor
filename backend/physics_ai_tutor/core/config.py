from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Physics AI Tutor"
    environment: str = "development"
    # DB
    database_url: str
    # API
    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"
    # JWT
    jwt_secret_key: str
    jwt_algorithm: str
    jwt_access_token_expire_minutes: int
    jwt_refresh_threshold_minutes: int = 10
    jwt_issuer: str = "physics-ai-tutor"
    # Cookie
    cookie_secure: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


settings = Settings()
