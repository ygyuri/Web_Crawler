"""Configuration management using Pydantic Settings v2."""

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class DatabaseSettings(BaseSettings):
    """MongoDB database configuration."""

    model_config = SettingsConfigDict(env_prefix="MONGODB_")

    url: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URL"
    )
    db_name: str = Field(
        default="books_crawler",
        description="Database name"
    )
    max_pool_size: int = Field(
        default=100,
        description="Maximum connection pool size"
    )
    min_pool_size: int = Field(
        default=10,
        description="Minimum connection pool size"
    )
    server_selection_timeout_ms: int = Field(
        default=5000,
        description="Server selection timeout (ms)"
    )
    connect_timeout_ms: int = Field(
        default=2000,
        description="Connect timeout (ms)"
    )
    socket_timeout_ms: int = Field(
        default=10000,
        description="Socket timeout (ms)"
    )
    max_idle_time_ms: int = Field(
        default=300000,
        description="Maximum idle time for pooled connections (ms)"
    )
    tls: bool = Field(
        default=False,
        description="Enable TLS for MongoDB connection"
    )
    tls_allow_invalid_certificates: bool = Field(
        default=False,
        description="Allow invalid TLS certificates (useful for testing only)"
    )


class APISettings(BaseSettings):
    """FastAPI application configuration."""

    model_config = SettingsConfigDict(env_prefix="API_")

    host: str = Field(
        default="0.0.0.0",
        description="API host address"
    )
    port: int = Field(
        default=8000,
        description="API port number"
    )
    api_key_header: str = Field(
        default="X-API-Key",
        description="Header name for API key authentication"
    )
    rate_limit: int = Field(
        default=100,
        description="Rate limit per hour per API key"
    )
    api_keys: List[str] = Field(
        default_factory=lambda: [],
        description="List of valid API keys (comma-separated in env)"
    )
    cors_origins: List[str] = Field(
        default_factory=lambda: ["*"],
        description="CORS allowed origins"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Parse comma-separated API keys from environment
        if isinstance(self.api_keys, str):
            self.api_keys = [key.strip() for key in self.api_keys.split(",") if key.strip()]


class CrawlerSettings(BaseSettings):
    """Web crawler configuration."""

    model_config = SettingsConfigDict(env_prefix="CRAWLER_")

    base_url: HttpUrl = Field(
        default="https://books.toscrape.com",
        description="Base URL of the target website"
    )
    max_concurrent_requests: int = Field(
        default=10,
        description="Maximum concurrent HTTP requests"
    )
    request_timeout: int = Field(
        default=30,
        description="HTTP request timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts"
    )
    retry_backoff: float = Field(
        default=2.0,
        description="Exponential backoff multiplier"
    )
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        description="Default User-Agent string for requests"
    )
    user_agents: List[str] = Field(
        default_factory=lambda: [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/118.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:117.0) Gecko/20100101 Firefox/117.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
        ],
        description="Pool of User-Agent strings to rotate per request"
    )
    respect_robots_txt: bool = Field(
        default=True,
        description="Whether to respect robots.txt"
    )
    circuit_breaker_failure_threshold: int = Field(
        default=5,
        description="Number of consecutive failures before opening the circuit"
    )
    circuit_breaker_reset_timeout: int = Field(
        default=60,
        description="Cooldown period in seconds before circuit transitions to half-open"
    )
    circuit_breaker_half_open_max_calls: int = Field(
        default=2,
        description="Maximum trial requests allowed while circuit is half-open"
    )
    recrawl_interval_hours: int = Field(
        default=12,
        description="Minimum hours before re-crawling a book that was recently fetched"
    )


class SchedulerSettings(BaseSettings):
    """Task scheduler configuration."""

    model_config = SettingsConfigDict(env_prefix="SCHEDULER_")

    crawl_schedule_hour: int = Field(
        default=2,
        description="Hour of day to run daily crawl (0-23)"
    )
    crawl_schedule_minute: int = Field(
        default=0,
        description="Minute of hour to run daily crawl (0-59)"
    )
    timezone: str = Field(
        default="UTC",
        description="Timezone for scheduler"
    )
    enable_email_alerts: bool = Field(
        default=False,
        description="Enable email alerts for significant changes"
    )
    smtp_host: str = Field(
        default="smtp.ethereal.email",
        description="SMTP server host"
    )
    smtp_port: int = Field(
        default=587,
        description="SMTP server port"
    )
    smtp_user: str = Field(
        default="",
        description="SMTP username"
    )
    smtp_password: str = Field(
        default="",
        description="SMTP password"
    )
    alert_email_to: str = Field(
        default="",
        description="Email address for alerts"
    )


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    model_config = SettingsConfigDict(env_prefix="LOG_")

    level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    file: str = Field(
        default="logs/crawler.log",
        description="Log file path"
    )
    file_rotation: str = Field(
        default="midnight",
        description="Log file rotation schedule"
    )
    file_retention: int = Field(
        default=30,
        description="Number of days to retain log files"
    )
    format: str = Field(
        default="json",
        description="Log format (json, text)"
    )
    include_timestamp: bool = Field(
        default=True,
        description="Include timestamp in logs"
    )


class Settings(BaseSettings):
    """Application-wide settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    api: APISettings = Field(default_factory=APISettings)
    crawler: CrawlerSettings = Field(default_factory=CrawlerSettings)
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    environment: str = Field(
        default="development",
        description="Environment (development, production, testing)"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )


# Global settings instance
settings = Settings()

