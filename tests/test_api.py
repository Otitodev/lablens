from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_health_and_agent_card(client) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    card = client.get("/.well-known/agent.json")
    assert card.status_code == 200
    payload = card.json()
    assert payload["name"] == "LabLens MCP"
    assert "flag_critical_values" in payload["tools"]


def test_flag_critical_values_endpoint(client) -> None:
    fixture = load_fixture("SYN-001.json")
    coag = fixture["panels"]["COAG"]
    response = client.post(
        "/tools/flag_critical_values",
        json={"patient_id": fixture["patient_id"], "results": coag["results"]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["alert_count"] >= 1
    assert payload["alerts"][0]["severity"] in {"critical", "abnormal", "borderline"}


def test_interpret_lab_panel_contract(client) -> None:
    fixture = load_fixture("SYN-003.json")
    lft = fixture["panels"]["LFT"]
    response = client.post(
        "/tools/interpret_lab_panel",
        json={
            "patient_id": fixture["patient_id"],
            "panel": "LFT",
            "values": lft["values"],
            "units": lft["units"],
            "reference_ranges": lft["reference_ranges"],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["patient_id"] == "SYN-003"
    assert payload["interpretations"]


def test_generate_clinical_summary_contract(client) -> None:
    fixture = load_fixture("SYN-004.json")
    cbc = fixture["panels"]["CBC"]
    body = {
        "patient_id": fixture["patient_id"],
        "patient_context": fixture["patient_context"],
        "results": {
            analyte: {"value": value, "unit": cbc["units"], "status": "low"}
            for analyte, value in cbc["values"].items()
        },
        "summary_type": "chart_note",
    }
    response = client.post("/tools/generate_clinical_summary", json=body)
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]
    assert payload["word_count"] == len(payload["summary"].split())


def test_suggest_differentials_contract(client) -> None:
    fixture = load_fixture("SYN-008.json")
    body = {
        "patient_id": fixture["patient_id"],
        "abnormal_findings": fixture["panels"]["differentials"]["abnormal_findings"],
        "clinical_context": fixture["panels"]["differentials"]["clinical_context"],
        "max_differentials": 3,
    }
    response = client.post("/tools/suggest_differentials", json=body)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["differentials"]) == 3
    assert payload["differentials"][0]["rank"] == 1
    assert payload["clinical_caveat"]


def test_validation_error_shape(client) -> None:
    response = client.post("/tools/flag_critical_values", json={"patient_id": "SYN-001"})
    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"


def test_phi_like_patient_id_rejected(client) -> None:
    response = client.post(
        "/tools/flag_critical_values",
        json={
            "patient_id": "dob-1990-01-01",
            "results": {
                "WBC": {
                    "value": 9.0,
                    "unit": "x10^9/L",
                    "reference_low": 4.0,
                    "reference_high": 11.0,
                    "critical_low": 1.0,
                    "critical_high": 30.0,
                }
            },
        },
    )
    assert response.status_code == 422


@pytest.mark.parametrize("fixture_name", [f"SYN-00{i}.json" for i in range(1, 9)])
def test_fixture_based_differential_calls(client, fixture_name: str) -> None:
    fixture = load_fixture(fixture_name)
    body = {
        "patient_id": fixture["patient_id"],
        "abnormal_findings": fixture["panels"]["differentials"]["abnormal_findings"],
        "clinical_context": fixture["panels"]["differentials"]["clinical_context"],
        "max_differentials": 5,
    }
    response = client.post("/tools/suggest_differentials", json=body)
    assert response.status_code == 200
    payload = response.json()
    assert payload["patient_id"] == fixture["patient_id"]


@pytest.mark.parametrize("fixture_name", [f"SYN-00{i}.json" for i in range(1, 9)])
def test_fixture_summary_calls(client, fixture_name: str) -> None:
    fixture = load_fixture(fixture_name)
    panel = next(value for value in fixture["panels"].values() if "values" in value)
    body = {
        "patient_id": fixture["patient_id"],
        "patient_context": fixture["patient_context"],
        "results": {
            analyte: {"value": value, "unit": panel["units"], "status": "normal"}
            for analyte, value in panel["values"].items()
        },
        "summary_type": "patient_facing",
    }
    response = client.post("/tools/generate_clinical_summary", json=body)
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary_type"] == "patient_facing"

