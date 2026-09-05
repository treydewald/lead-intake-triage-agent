from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Lead Intake Triage Agent API"
    environment: str = "development"

    # SQLite by default for zero-config local/demo runs; point DATABASE_URL at a
    # PostgreSQL DSN (e.g. postgresql+psycopg2://user:pass@host/db) for production.
    database_url: str = "sqlite:///./leads.db"

    # Local open-weight model via Ollama (default classification/enrichment path).
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"

    # Optional hosted-LLM fallback — only used if local tool-calling proves
    # insufficiently reliable for consistent classification (see project-definition.md).
    fallback_llm_api_key: str | None = None

    # HubSpot free-tier developer sandbox (Private App token — see backend/.env.example).
    hubspot_access_token: str | None = None
    hubspot_base_url: str = "https://api.hubapi.com"

    confidence_threshold: float = 0.7

    cors_origins: list[str] = ["http://localhost:5173"]

    # Optional Slack-compatible incoming webhook for external delivery of
    # awaiting_review notifications (Feature 10). Unset by default — free-by-default,
    # no paid delivery service required; a missing URL is a normal, expected config,
    # not an error.
    notification_webhook_url: str | None = None


settings = Settings()
