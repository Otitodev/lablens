import logging
from functools import lru_cache

from app.config import get_settings
from app.errors import ConfigurationError
from app.services.anthropic_service import AnthropicJSONService
from app.services.epic_oauth_service import EpicOAuthService
from app.services.fhir_service import FHIRService
from app.services.gemini_service import GeminiJSONService
from app.services.openai_service import OpenAIJSONService
from app.services.mistral_service import MistralJSONService
from app.services.tool_service import ToolService

logger = logging.getLogger(__name__)


@lru_cache
def get_anthropic_service() -> AnthropicJSONService:
    return AnthropicJSONService(get_settings())


@lru_cache
def get_gemini_service() -> GeminiJSONService:
    return GeminiJSONService(get_settings())


@lru_cache
def get_openai_service() -> OpenAIJSONService:
    return OpenAIJSONService(get_settings())


@lru_cache
def get_mistral_service() -> MistralJSONService:
    return MistralJSONService(get_settings())


def get_llm_service():
    settings = get_settings()
    provider = settings.llm_provider
    logger.debug("LLM provider selected: %s", provider)

    if provider == "gemini":
        try:
            return get_gemini_service()
        except ConfigurationError:
            return None

    if provider == "openai":
        try:
            return get_openai_service()
        except ConfigurationError:
            return None

    if provider == "mistral":
        try:
            return get_mistral_service()
        except ConfigurationError:
            return None

    # Default: anthropic
    try:
        return get_anthropic_service()
    except ConfigurationError:
        return None


@lru_cache
def get_epic_oauth_service() -> EpicOAuthService | None:
    settings = get_settings()
    if not settings.epic_configured:
        return None
    logger.info(
        "EpicOAuthService initialised client_id=%s token_url=%s",
        settings.epic_client_id,
        settings.epic_token_url,
    )
    return EpicOAuthService(settings)


@lru_cache
def get_fhir_service() -> FHIRService:
    return FHIRService(oauth_service=get_epic_oauth_service())


def get_tool_service() -> ToolService:
    return ToolService(llm_service=get_llm_service(), fhir_service=get_fhir_service())
