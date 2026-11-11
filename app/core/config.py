from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "PCMSC"
    app_env: Literal["development", "test", "production"] = "development"
    app_version: str = "0.1.0"
    log_level: str = "INFO"

    database_url: str = f"sqlite:///{(BASE_DIR / 'data' / 'pcmsc.db').as_posix()}"
    cors_origins: str = "http://localhost:8501"

    demo_mode: bool = True

    admin_api_key: str = "demo-admin-key"
    operator_api_key: str = "demo-operator-key"
    reviewer_api_key: str = "demo-reviewer-key"
    readonly_api_key: str = "demo-readonly-key"

    ai_provider: Literal["mock", "gemini"] = "mock"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"

    payment_provider: Literal["mock", "paypal"] = "mock"
    paypal_client_id: str | None = None
    paypal_client_secret: str | None = None
    paypal_base_url: str = "https://api-m.sandbox.paypal.com"

    evidence_dir_override: str | None = None

    @property
    def data_dir(self) -> Path:
        return BASE_DIR / "data"

    @property
    def evidence_dir(self) -> Path:
        if self.evidence_dir_override:
            return Path(self.evidence_dir_override)
        return self.data_dir / "evidence"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @field_validator("app_env", mode="before")
    @classmethod
    def normalize_app_env(cls, value: str) -> str:
        return str(value).lower()

    def validate_runtime(self) -> None:
        if self.app_env == "production":
            defaults = {
                "demo-admin-key",
                "demo-operator-key",
                "demo-reviewer-key",
                "demo-readonly-key",
            }
            configured = {
                self.admin_api_key,
                self.operator_api_key,
                self.reviewer_api_key,
                self.readonly_api_key,
            }
            if configured & defaults:
                raise RuntimeError("Default demo API keys are not allowed in production")
        if self.ai_provider == "gemini" and not self.gemini_api_key:
            raise RuntimeError("AI_PROVIDER=gemini requires GEMINI_API_KEY")
        if self.payment_provider == "paypal" and not (
            self.paypal_client_id and self.paypal_client_secret
        ):
            raise RuntimeError("PAYMENT_PROVIDER=paypal requires PayPal sandbox credentials")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_runtime()
    return settings
