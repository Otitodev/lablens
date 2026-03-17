from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from anthropic import Anthropic
from pydantic import ValidationError

from app.config import Settings
from app.errors import ConfigurationError, InvalidLLMResponseError, LLMServiceError
from app.services.llm_protocol import parse_json_response

logger = logging.getLogger(__name__)


class AnthropicJSONService:
    def __init__(self, settings: Settings, client: Anthropic | None = None) -> None:
        self.settings = settings
        self.client = client or self._build_client()

    def _build_client(self) -> Anthropic:
        if not self.settings.anthropic_api_key:
            raise ConfigurationError("ANTHROPIC_API_KEY is required for LLM-backed tools.")
        return Anthropic(api_key=self.settings.anthropic_api_key, timeout=self.settings.request_timeout_seconds)

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
        logger.info("tool=%s request_id=%s llm_call_started", tool_name, request_id)
        try:
            response = self.client.messages.create(
                model=self.settings.model,
                max_tokens=1800,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": json.dumps(payload, ensure_ascii=True),
                    }
                ],
            )
        except Exception as exc:  # pragma: no cover - covered with mocks
            logger.exception("tool=%s request_id=%s llm_call_failed", tool_name, request_id)
            raise LLMServiceError(str(exc)) from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info("tool=%s request_id=%s latency_ms=%s llm_call_completed", tool_name, request_id, latency_ms)

        text = self._extract_text(response)
        parsed = parse_json_response(text)
        try:
            return response_model.model_validate(parsed)
        except ValidationError as exc:
            raise InvalidLLMResponseError(str(exc)) from exc

    @staticmethod
    def _extract_text(response: Any) -> str:
        blocks = getattr(response, "content", None)
        if not blocks:
            raise InvalidLLMResponseError("Response content was empty.")
        parts = [block.text for block in blocks if getattr(block, "type", "") == "text" and getattr(block, "text", None)]
        if not parts:
            raise InvalidLLMResponseError("Response did not contain text content.")
        return "\n".join(parts).strip()

