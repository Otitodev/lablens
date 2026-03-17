"""Tests for SHARP Extension Spec integration."""
from __future__ import annotations

import pytest

SHARP_HEADERS = {
    "X-FHIR-Server-URL": "https://fhir.example.org/R4",
    "X-FHIR-Access-Token": "Bearer test-token-synthetic",
    "X-Patient-ID": "SYN-001",
}

FLAG_BODY = {
    "patient_id": "SYN-001",
    "results": {
        "WBC": {
            "value": 2.1,
            "unit": "x10^9/L",
            "reference_low": 4.0,
            "reference_high": 11.0,
            "critical_low": 2.0,
            "critical_high": 30.0,
        }
    },
}


def test_mcp_initialize_returns_sharp_capability(client) -> None:
    """POST /mcp/initialize must advertise the SHARP capability block."""
    response = client.post("/mcp/initialize")
    assert response.status_code == 200
    payload = response.json()

    assert payload["protocolVersion"] == "2024-11-05"
    assert payload["serverInfo"]["name"] == "LabLens MCP"

    sharp = payload["capabilities"]["experimental"]["sharp"]
    assert sharp["version"] == "1.0"
    assert sharp["fhir_context_required"] is False
    assert "X-FHIR-Server-URL" in sharp["context_headers"]
    assert "X-FHIR-Access-Token" in sharp["context_headers"]
    assert "X-Patient-ID" in sharp["context_headers"]


def test_agent_card_advertises_sharp(client) -> None:
    """/.well-known/agent.json must include the SHARP capability block."""
    response = client.get("/.well-known/agent.json")
    assert response.status_code == 200
    card = response.json()
    sharp = card["capabilities"]["experimental"]["sharp"]
    assert sharp["fhir_context_required"] is False
    assert sharp["spec_url"] == "https://www.sharponmcp.com"


def test_tool_accepts_sharp_headers(client) -> None:
    """Tool endpoints must return 200 when SHARP headers are present."""
    response = client.post(
        "/tools/flag_critical_values",
        json=FLAG_BODY,
        headers=SHARP_HEADERS,
    )
    assert response.status_code == 200


def test_tool_works_without_sharp_headers(client) -> None:
    """SHARP headers are optional — tool endpoints must work without them."""
    response = client.post("/tools/flag_critical_values", json=FLAG_BODY)
    assert response.status_code == 200


def test_sharp_context_does_not_override_patient_id(client) -> None:
    """X-Patient-ID header does not override the validated patient_id in the body."""
    response = client.post(
        "/tools/flag_critical_values",
        json=FLAG_BODY,
        headers={**SHARP_HEADERS, "X-Patient-ID": "SYN-999"},
    )
    assert response.status_code == 200
    # Body patient_id governs the response — SHARP header is context only.
    assert response.json()["patient_id"] == "SYN-001"
