"""
SentinelOS — Centralized Configuration

All environment variables are validated here at startup.
If a required variable is missing or invalid, the application
fails immediately with a clear error — not silently at runtime.

Usage:
    from shared.config.settings import get_settings
    settings = get_settings()
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL connection configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    host: str = Field(default="localhost", alias="POSTGRES_HOST")
    port: int = Field(default=5432, alias="POSTGRES_PORT")
    name: str = Field(default="sentinelos", alias="POSTGRES_DB")
    user: str = Field(default="sentinel", alias="POSTGRES_USER")
    password: str = Field(default="sentinel_secret", alias="POSTGRES_PASSWORD")
    pool_size: int = Field(default=10, alias="POSTGRES_POOL_SIZE")
    max_overflow: int = Field(default=20, alias="POSTGRES_MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, alias="POSTGRES_POOL_TIMEOUT")

    @computed_field  # type: ignore[misc]
    @property
    def async_url(self) -> str:
        """Async DSN for SQLAlchemy with asyncpg driver."""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )

    @computed_field  # type: ignore[misc]
    @property
    def sync_url(self) -> str:
        """Sync DSN for Alembic migrations (uses psycopg2)."""
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


class RedpandaSettings(BaseSettings):
    """Redpanda (Kafka-compatible) broker configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    brokers: str = Field(default="localhost:19092", alias="REDPANDA_BROKERS")
    topic_agent_events: str = Field(
        default="sentinel.agent.events",
        alias="REDPANDA_TOPIC_AGENT_EVENTS",
    )
    topic_dlq: str = Field(
        default="sentinel.agent.events.dlq",
        alias="REDPANDA_TOPIC_DLQ",
    )
    consumer_group: str = Field(
        default="sentinel-control-plane",
        alias="REDPANDA_CONSUMER_GROUP",
    )
    worker_consumer_group: str = Field(
        default="sentinel-runtime-worker",
        alias="REDPANDA_WORKER_CONSUMER_GROUP",
    )

    @computed_field  # type: ignore[misc]
    @property
    def broker_list(self) -> list[str]:
        """Return brokers as a list for aiokafka."""
        return [b.strip() for b in self.brokers.split(",")]


class OtelSettings(BaseSettings):
    """OpenTelemetry observability configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    enabled: bool = Field(default=False, alias="OTEL_ENABLED")
    service_name: str = Field(
        default="sentinelos-control-plane",
        alias="OTEL_SERVICE_NAME",
    )
    otlp_endpoint: str = Field(
        default="http://localhost:4317",
        alias="OTEL_EXPORTER_OTLP_ENDPOINT",
    )
    trace_sample_rate: float = Field(
        default=1.0,
        alias="OTEL_TRACE_SAMPLE_RATE",
        ge=0.0,
        le=1.0,
    )


class OllamaSettings(BaseSettings):
    """Ollama local LLM runtime configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    base_url: str = Field(
        default="http://localhost:11434",
        alias="OLLAMA_BASE_URL",
    )
    default_model: str = Field(
        default="llama3.2",
        alias="OLLAMA_DEFAULT_MODEL",
    )
    timeout_seconds: int = Field(
        default=120,
        alias="OLLAMA_TIMEOUT_SECONDS",
    )


class Settings(BaseSettings):
    """
    Root settings object.

    Composes all subsystem settings into a single entrypoint.
    Validated once at startup via get_settings().
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application identity
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        alias="APP_ENV",
    )
    app_name: str = Field(default="SentinelOS", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        alias="LOG_LEVEL",
    )

    # Control Plane API
    control_plane_host: str = Field(default="0.0.0.0", alias="CONTROL_PLANE_HOST")
    control_plane_port: int = Field(default=8000, alias="CONTROL_PLANE_PORT")

    # Subsystem settings — composed, not inherited
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redpanda: RedpandaSettings = Field(default_factory=RedpandaSettings)
    otel: OtelSettings = Field(default_factory=OtelSettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)

    @model_validator(mode="after")
    def validate_production_constraints(self) -> "Settings":
        """
        Enforce stricter rules in production environments.
        Fail fast at startup rather than at runtime.
        """
        if self.app_env == "production":
            if self.debug:
                raise ValueError("DEBUG must be False in production")
            if not self.otel.enabled:
                raise ValueError("OTEL_ENABLED must be True in production")
            if self.database.password == "sentinel_secret":
                raise ValueError(
                    "Default database password must be changed in production"
                )
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return cached Settings instance.

    lru_cache ensures we parse environment variables exactly once
    per process lifetime. Call get_settings() freely — it's cheap
    after the first call.
    """
    return Settings()
