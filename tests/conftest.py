from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_tool_service
from app.main import app
from app.services.tool_service import ToolService

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic"


class MockLLMService:
    def generate_json(self, *, tool_name: str, system_prompt: str, payload: dict[str, Any], response_model: type):
        patient_id = payload["patient_id"]
        if tool_name == "interpret_lab_panel":
            analytes = payload["analytes"]
            return response_model.model_validate(
                {
                    "patient_id": patient_id,
                    "panel": payload["panel"],
                    "interpretations": [
                        {
                            "analyte": item["analyte"],
                            "value": item["value"],
                            "status": item["status"],
                            "commentary": f"{item['analyte']} is {item['status']} in this synthetic panel.",
                            "clinical_significance": "Requires clinical correlation with the overall pattern.",
                        }
                        for item in analytes
                    ],
                    "overall_assessment": "Synthetic panel reviewed with clinically relevant abnormalities highlighted.",
                    "recommended_actions": ["Correlate with the clinical picture.", "Review abnormal trends promptly."],
                }
            )
        if tool_name == "generate_clinical_summary":
            summary_type = payload["summary_type"]
            if summary_type == "patient_facing":
                summary = (
                    "These synthetic lab results show some abnormal values that a clinician should review. "
                    "They are not from a real patient and are being used only for demonstration."
                )
            else:
                summary = (
                    "Synthetic laboratory results demonstrate clinically significant abnormalities that warrant "
                    "correlation with the presenting complaint and interval trend review."
                )
            return response_model.model_validate(
                {
                    "patient_id": patient_id,
                    "summary_type": summary_type,
                    "summary": summary,
                    "key_findings": ["Abnormal values detected", "Synthetic clinical summary generated"],
                    "word_count": len(summary.split()),
                }
            )
        if tool_name == "suggest_differentials":
            max_items = payload["max_differentials"]
            findings = payload["abnormal_findings"]
            diagnoses = [
                "Disseminated intravascular coagulation",
                "Chronic kidney disease",
                "Hepatic dysfunction",
                "Iron deficiency anaemia",
                "Thrombotic microangiopathy",
            ]
            differentials = []
            for index, diagnosis in enumerate(diagnoses[:max_items], start=1):
                support = [f"{finding['analyte']} is {finding['direction']}" for finding in findings[:2]] or [
                    "No major abnormality supplied"
                ]
                differentials.append(
                    {
                        "rank": index,
                        "diagnosis": diagnosis,
                        "supporting_findings": support,
                        "reasoning": "Pattern-based synthetic reasoning suggests this diagnosis should be considered.",
                        "confidence": "moderate",
                        "suggested_confirmatory_tests": ["Repeat panel", "Peripheral smear"],
                    }
                )
            return response_model.model_validate(
                {
                    "patient_id": patient_id,
                    "differentials": differentials,
                    "clinical_caveat": "AI-generated output; review by a qualified clinician is required.",
                }
            )
        raise AssertionError(f"Unexpected tool name {tool_name}")


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[get_tool_service] = lambda: ToolService(llm_service=MockLLMService())
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def fixtures() -> list[dict[str, Any]]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(FIXTURE_DIR.glob("SYN-*.json"))]
