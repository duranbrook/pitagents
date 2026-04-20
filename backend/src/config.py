from typing import Optional
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    DATABASE_URL: str  # required — no default, must be set via env

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Anthropic
    ANTHROPIC_API_KEY: SecretStr = SecretStr("")

    # Deepgram
    DEEPGRAM_API_KEY: SecretStr = SecretStr("")

    # AWS S3 / R2
    S3_BUCKET: str = ""
    S3_ENDPOINT_URL: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: SecretStr = SecretStr("")

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: SecretStr = SecretStr("")
    TWILIO_FROM_PHONE: str = ""

    # SendGrid
    SENDGRID_API_KEY: SecretStr = SecretStr("")

    # Auth — JWT_SECRET is required, no default
    JWT_SECRET: SecretStr  # required — must be set via env
    JWT_ALGORITHM: str = "HS256"
    # 7 days — appropriate for mobile clients that don't re-auth frequently
    JWT_EXPIRE_MINUTES: int = 10080

    # Pricing flag default (per-shop override takes precedence at runtime)
    DEFAULT_PRICING_SOURCE: str = "shop"

    # ALLDATA (optional — only needed when pricing_flag="alldata")
    ALLDATA_API_KEY: str = ""
    ALLDATA_API_URL: Optional[str] = None


settings = Settings()
