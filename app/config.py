from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Anthropic
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    model: str = Field(default="claude-sonnet-4-5-20251022", alias="MODEL")

    # Google Gemini
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.0-flash", alias="GEMINI_MODEL")

    # OpenAI
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    # Mistral
    mistral_api_key: str | None = Field(default=None, alias="MISTRAL_API_KEY")
    mistral_model: str = Field(default="mistral-small-latest", alias="MISTRAL_MODEL")

    # Epic FHIR Sandbox OAuth (SMART on FHIR — Backend Systems / JWT assertion)
    epic_client_id: str | None = Field(default=None, alias="EPIC_CLIENT_ID")
    # Deprecated: client_secret replaced by JWT assertion. Kept so existing
    # .env files with EPIC_CLIENT_SECRET do not cause a validation error.
    epic_client_secret: str | None = Field(default=None, alias="EPIC_CLIENT_SECRET")
    epic_private_key: str | None = Field(default=None, alias="EPIC_PRIVATE_KEY")
    epic_kid: str = Field(default="lablens-1", alias="EPIC_KID")
    epic_token_url: str = Field(
        default="https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token",
        alias="EPIC_TOKEN_URL",
    )
    epic_fhir_base_url: str = Field(
        default="https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4",
        alias="EPIC_FHIR_BASE_URL",
    )

    @property
    def epic_configured(self) -> bool:
        return bool(self.epic_client_id and self.epic_private_key)

    # Provider selection: "anthropic" | "gemini" | "openai" | "mistral"
    llm_provider: Literal["anthropic", "gemini", "openai", "mistral"] = Field(
        default="anthropic", alias="LLM_PROVIDER"
    )

    port: int = Field(default=8000, alias="PORT")
    environment: Literal["development", "production"] = Field(
        default="development",
        alias="ENVIRONMENT",
    )
    request_timeout_seconds: float = 30.0
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
