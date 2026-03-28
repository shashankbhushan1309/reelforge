"""ReelForge shared configuration — loads all settings from environment variables."""

import os
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass
class DatabaseConfig:
    url: str = ""
    url_sync: str = ""

    def __post_init__(self):
        self.url = os.getenv("DATABASE_URL", "postgresql+asyncpg://reelforge:reelforge@localhost:5432/reelforge")
        self.url_sync = os.getenv("DATABASE_URL_SYNC", "postgresql://reelforge:reelforge@localhost:5432/reelforge")


@dataclass
class RedisConfig:
    url: str = ""

    def __post_init__(self):
        self.url = os.getenv("REDIS_URL", "redis://localhost:6379/0")


@dataclass
class R2Config:
    account_id: str = ""
    access_key_id: str = ""
    secret_access_key: str = ""
    bucket_name: str = ""
    public_url: str = ""

    def __post_init__(self):
        self.account_id = os.getenv("R2_ACCOUNT_ID", "")
        self.access_key_id = os.getenv("R2_ACCESS_KEY_ID", "")
        self.secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY", "")
        self.bucket_name = os.getenv("R2_BUCKET_NAME", "reelforge-media")
        self.public_url = os.getenv("R2_PUBLIC_URL", "https://media.reelforge.ai")

    @property
    def endpoint_url(self) -> str:
        return f"https://{self.account_id}.r2.cloudflarestorage.com"


@dataclass
class AIConfig:
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    def __post_init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")


@dataclass
class AuthConfig:
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    jwt_secret: str = ""

    def __post_init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL", "")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "")
        self.supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.jwt_secret = os.getenv("SUPABASE_JWT_SECRET", "")


@dataclass
class StripeConfig:
    secret_key: str = ""
    webhook_secret: str = ""
    price_creator: str = ""
    price_pro: str = ""
    price_studio: str = ""

    def __post_init__(self):
        self.secret_key = os.getenv("STRIPE_SECRET_KEY", "")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        self.price_creator = os.getenv("STRIPE_PRICE_CREATOR", "")
        self.price_pro = os.getenv("STRIPE_PRICE_PRO", "")
        self.price_studio = os.getenv("STRIPE_PRICE_STUDIO", "")


@dataclass
class AppConfig:
    env: str = "development"
    secret_key: str = "change-this"
    cors_origins: list[str] = field(default_factory=list)
    api_base_url: str = "http://localhost:8000"

    def __post_init__(self):
        self.env = os.getenv("APP_ENV", "development")
        self.secret_key = os.getenv("APP_SECRET_KEY", "change-this")
        origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
        self.cors_origins = [o.strip() for o in origins.split(",")]
        self.api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@dataclass
class Settings:
    db: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    r2: R2Config = field(default_factory=R2Config)
    ai: AIConfig = field(default_factory=AIConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    stripe: StripeConfig = field(default_factory=StripeConfig)
    app: AppConfig = field(default_factory=AppConfig)


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
