from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AppError(Exception):
    code: str
    message: str
    status_code: int = 400

    def to_response(self) -> dict:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }


class ConfigurationError(AppError):
    def __init__(self, message: str = "Application is not configured correctly.") -> None:
        super().__init__(
            code="configuration_error",
            message=message,
            status_code=500,
        )


class LLMServiceError(AppError):
    def __init__(self, message: str = "The reasoning service is unavailable.") -> None:
        super().__init__(
            code="llm_service_error",
            message=message,
            status_code=502,
        )


class InvalidLLMResponseError(AppError):
    def __init__(self, message: str = "The reasoning service returned an invalid response.") -> None:
        super().__init__(
            code="invalid_llm_response",
            message=message,
            status_code=502,
        )


class SharpContextError(AppError):
    """Raised when required SHARP context headers are missing or invalid."""

    def __init__(self, message: str = "Required SHARP context headers are missing.") -> None:
        super().__init__(
            code="sharp_context_error",
            message=message,
            status_code=403,
        )
