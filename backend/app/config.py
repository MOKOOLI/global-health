from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Dev default is SQLite so the API runs with zero setup.
    # In docker-compose this is overridden with PostgreSQL.
    database_url: str = "sqlite:///./globalhealth.db"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_timeout_s: float = 60.0
    cors_origins: str = "http://localhost:3000"
    # Behind a reverse proxy / the Next.js rewrite, the client IP is in X-Forwarded-For. Only enable when the
    # backend is NOT directly reachable from the internet (otherwise clients can spoof it).
    trust_proxy: bool = False
    redis_url: str | None = None  # shared rate limiting across workers/replicas
    ask_use_llm: bool = False  # let Ollama extract fields when the deterministic parser fails
    public_url: str = "http://localhost:3000"  # used in citations

    @field_validator("database_url")
    @classmethod
    def _driver(cls, v: str) -> str:
        """Managed hosts (Neon, Supabase, Render, Heroku) hand out postgres:// or postgresql:// URLs;
        SQLAlchemy needs the psycopg 3 driver name."""
        for old in ("postgres://", "postgresql://"):
            if v.startswith(old):
                return "postgresql+psycopg://" + v[len(old):]
        return v

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
