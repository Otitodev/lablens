"""Shared protocol that all LLM JSON services must satisfy.

Any class implementing `generate_json` with this signature can be used as
the reasoning backend for ToolService — Anthropic, Gemini, or a mock.
"""
from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable

from app.errors import InvalidLLMResponseError


@runtime_checkable
class LLMJSONService(Protocol):
    def generate_json(
        self,
        *,
        tool_name: str,
        system_prompt: str,
        payload: dict[str, Any],
        response_model: type,
    ) -> Any:
        ...


def parse_json_response(text: str) -> dict[str, Any]:
    """Parse a JSON string from an LLM response, tolerating markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise InvalidLLMResponseError("Response body was not valid JSON.")
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise InvalidLLMResponseError("Response body was not valid JSON.") from exc
