"""Configuración global vía pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    environment: Literal["local", "dev", "staging", "production"] = "local"
    log_level: str = "INFO"
    app_name: str = "BigotesyPaticas API"
    app_version: str = "0.1.0"

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:3100"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:devpass@localhost:5432/bp_dev"
    database_url_sync: str = "postgresql+psycopg://postgres:devpass@localhost:5432/bp_dev"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 480  # 8 horas — jornada laboral completa
    jwt_refresh_token_expire_days: int = 30  # 30 días — refresh dura un mes

    # Bootstrap admin
    admin_email: str = "admin@bigotesypaticas.com"
    admin_password: str = "ChangeMe!2026"

    # Object storage
    s3_endpoint: str = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_uploads: str = "bp-uploads"
    s3_bucket_public: str = "bp-public"
    s3_public_url: str = "http://localhost:9000"

    # Sheets ETL
    sheet_url: str = ""
    google_service_account_json: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @field_validator("jwt_secret")
    @classmethod
    def _check_jwt_secret(cls, v: str) -> str:
        # En producción, NO permitir el dev secret
        if v == "dev-only-change-me":
            import os

            if os.getenv("ENVIRONMENT") == "production":
                raise ValueError("JWT_SECRET debe configurarse en producción.")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
