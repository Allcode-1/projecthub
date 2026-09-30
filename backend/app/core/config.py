from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parent.parent.parent

load_dotenv(BASE_DIR.parent / ".env")
load_dotenv(BASE_DIR / ".env", override=True)


class Auth_JWT(BaseModel):
    public_key_path: Path = BASE_DIR / "certs" / "public.pem"
    private_key_path: Path = BASE_DIR / "certs" / "private.pem"
    algorithm: str = "RS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30


class DatabaseSettings(BaseModel):
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout_seconds: float = 30.0
    pool_recycle_seconds: int = 1800
    pool_pre_ping: bool = True
    pool_use_lifo: bool = True
    connect_timeout_seconds: int = 5
    statement_timeout_ms: int = 30_000


class PaginationSettings(BaseModel):
    default_limit: int = 50
    max_limit: int = 100


class RateLimitSettings(BaseModel):
    login_ip_limit: int = 10
    login_ip_window_seconds: int = 60
    login_username_limit: int = 5
    login_username_window_seconds: int = 300
    register_ip_limit: int = 10
    register_ip_window_seconds: int = 300
    refresh_ip_limit: int = 60
    refresh_ip_window_seconds: int = 60
    logout_ip_limit: int = 60
    logout_ip_window_seconds: int = 60
    authenticated_mutation_user_limit: int = 120
    authenticated_mutation_user_window_seconds: int = 60
    authenticated_mutation_ip_limit: int = 300
    authenticated_mutation_ip_window_seconds: int = 60


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BASE_DIR.parent / ".env", BASE_DIR / ".env"),
        env_nested_delimiter="__",
        extra="ignore",
    )

    app_name: str = "ProjectHub"
    log_level: str = "INFO"
    healthcheck_timeout_seconds: float = 1.0
    readiness_require_redis: bool = True
    readiness_require_rabbitmq: bool = False

    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost",
    ]
    auth_jwt: Auth_JWT = Auth_JWT()
    database: DatabaseSettings = DatabaseSettings()
    pagination: PaginationSettings = PaginationSettings()
    rate_limit: RateLimitSettings = RateLimitSettings()
    database_url: str | None = None
    redis_url: str = "redis://localhost:6390/0"

    celery_broker_url: str = "amqp://guest:guest@localhost:5672//"

    sender_email: str = Field(validation_alias="SENDER_EMAIL")
    smtp_password: SecretStr = Field(validation_alias="SMTP_PASSWORD")
    smtp_hostname: str = "smtp.gmail.com"
    smtp_port: int = 587


settings = Settings()  # type: ignore[call-arg]
