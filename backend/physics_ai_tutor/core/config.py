from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Physics AI Tutor"
    environment: str = "development"
    # DB
    database_url: str
    # API
    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_chat_model: str = "deepseek-chat"
    deepseek_max_tokens: int = 1500
    # Rate limiting
    trust_forwarded_for: bool = True
    # AI pre-review of new answers (one extra LLM call per generation)
    ai_review_enabled: bool = False
    # JWT
    jwt_secret_key: str
    jwt_algorithm: str
    jwt_access_token_expire_minutes: int
    jwt_refresh_threshold_minutes: int = 10
    jwt_issuer: str = "physics-ai-tutor"
    # Cookie
    cookie_secure: bool = False
    same_site: Literal["lax", "strict", "none"] | None = None
    # CORS
    backend_cors_origins: list[str] = ["http://loaclhost:8000"]
    # Google Sign-In (students); disabled unless all three are set
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = None
    # Where the browser is sent after the Google callback
    frontend_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


settings = Settings()
