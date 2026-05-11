from functools import lru_cache
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    environment: str = "development"
    secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── CORS ─────────────────────────────────────────────────────────────────
    allowed_origins: list[str] = ["http://localhost:3000"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # ── OAuth — Google ────────────────────────────────────────────────────────
    google_client_id: str = ""
    google_client_secret: str = ""

    @property
    def google_oauth_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    # ── Stripe ────────────────────────────────────────────────────────────────
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_pro_price_id: str = ""

    @property
    def stripe_enabled(self) -> bool:
        return bool(self.stripe_secret_key)

    # ── Email (Resend) ────────────────────────────────────────────────────────
    resend_api_key: str = ""
    email_from_address: str = "noreply@trellis.com"
    email_from_name: str = "Trellis"

    @property
    def email_enabled(self) -> bool:
        return bool(self.resend_api_key)

    # ── Frontend ──────────────────────────────────────────────────────────────
    frontend_url: str = "http://localhost:3000"

    @property
    def password_reset_url(self) -> str:
        return f"{self.frontend_url}/reset-password"

    @property
    def invite_url(self) -> str:
        return f"{self.frontend_url}/invite"

    # ── Validation ────────────────────────────────────────────────────────────
    @model_validator(mode="after")
    def warn_insecure_defaults(self) -> "Settings":
        if self.is_production:
            if self.secret_key == "changeme-in-production":
                raise ValueError("SECRET_KEY must be changed in production")
            if not self.stripe_enabled:
                raise ValueError("Stripe must be configured in production")
            if not self.email_enabled:
                raise ValueError("Email (Resend) must be configured in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()