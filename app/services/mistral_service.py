from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from pydantic import ValidationError

from app.config import Settings
from app.errors import ConfigurationError, InvalidLLMResponseError, LLMServiceError
from app.services.llm_protocol import parse_json_response

logger = logging.getLogger(__name__)


class MistralJSONService:
    """LLM JSON service backed by Mistral AI via the mistralai SDK."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = self._build_client()

    def _build_client(self):
        try:
            from mistralai import Mistral  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ConfigurationError(
                "mistralai is not installed. Run: pip install mistralai"
            ) from exc

        if not self.settings.mistral_api_key:
            raise ConfigurationError("MISTRAL_API_KEY is required when LLM_PROVIDER=mistral.")

        return Mistral(api_key=self.settings.mistral_api_key)

    def generate_json(
        self,
        *,
        tool_name: str,
        system_prompt: str,
        payload: dict[str, Any],
        response_model: type,
    ):
        request_id = str(uuid.uuid4())
        started = time.perf_counter()
        logger.info("tool=%s request_id=%s provider=mistral llm_call_started", tool_name, request_id)

        try:
            response = self._client.chat.complete(
                model=self.settings.mistral_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=True)},
                ],
                response_format={"type": "json_object"},
                max_tokens=1800,
            )
        except Exception as exc:
            logger.exception("tool=%s request_id=%s provider=mistral llm_call_failed", tool_name, request_id)
            raise LLMServiceError(str(exc)) from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "tool=%s request_id=%s provider=mistral latency_ms=%s llm_call_completed",
            tool_name,
            request_id,
            latency_ms,
        )

        text = response.choices[0].message.content
        if not text:
            raise InvalidLLMResponseError("Mistral returned an empty response.")

        parsed = parse_json_response(text)
        try:
            return response_model.model_validate(parsed)
        except ValidationError as exc:
            raise InvalidLLMResponseError(str(exc)) from exc
