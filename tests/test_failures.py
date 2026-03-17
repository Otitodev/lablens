from __future__ import annotations

from fastapi.testclient import TestClient

from app.dependencies import get_tool_service
from app.errors import InvalidLLMResponseError, LLMServiceError
from app.main import app
from app.services.tool_service import ToolService


class RaisingLLMService:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    def generate_json(self, **kwargs):
        raise self.exc


def make_client(exc: Exception) -> TestClient:
    app.dependency_overrides[get_tool_service] = lambda: ToolService(llm_service=RaisingLLMService(exc))
    return TestClient(app)


def test_llm_timeout_error_returns_normalized_payload() -> None:
    client = make_client(LLMServiceError("Anthropic timeout"))
    response = client.post(
        "/tools/interpret_lab_panel",
        json={
            "patient_id": "SYN-001",
            "panel": "CBC",
            "values": {"WBC": 18.0},
            "units": "SI",
            "reference_ranges": {"WBC": {"low": 4.0, "high": 11.0}},
        },
    )
    app.dependency_overrides.clear()
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "llm_service_error"


def test_invalid_llm_response_returns_normalized_payload() -> None:
    client = make_client(InvalidLLMResponseError("bad json"))
    response = client.post(
        "/tools/generate_clinical_summary",
        json={
            "patient_id": "SYN-001",
            "patient_context": {
                "age_range": "60s",
                "sex": "male",
                "clinical_indication": "Synthetic indication",
            },
            "results": {
                "WBC": {"value": 18.0, "unit": "x10^9/L", "status": "high"}
            },
            "summary_type": "chart_note",
        },
    )
    app.dependency_overrides.clear()
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "invalid_llm_response"
