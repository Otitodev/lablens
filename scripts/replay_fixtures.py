from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic"


def build_requests(payload: dict) -> list[tuple[str, dict]]:
    patient_id = payload["patient_id"]
    patient_context = payload["patient_context"]
    panels = payload["panels"]
    requests: list[tuple[str, dict]] = []

    if "CBC" in panels or "LFT" in panels or "RENAL" in panels or "THYROID" in panels or "MIXED" in panels:
        panel_name = next(name for name in ["CBC", "LFT", "RENAL", "THYROID", "MIXED"] if name in panels)
        panel = panels[panel_name]
        requests.append(
            (
                "/tools/interpret_lab_panel",
                {
                    "patient_id": patient_id,
                    "panel": panel_name,
                    "values": panel["values"],
                    "units": panel["units"],
                    "reference_ranges": panel["reference_ranges"],
                },
            )
        )

    critical_panel = next((value for value in panels.values() if "results" in value), None)
    if critical_panel:
        requests.append(
            (
                "/tools/flag_critical_values",
                {
                    "patient_id": patient_id,
                    "results": critical_panel["results"],
                },
            )
        )

    summary_panel = next((value for value in panels.values() if "values" in value), None)
    if summary_panel:
        results = {}
        for analyte, value in summary_panel["values"].items():
            results[analyte] = {
                "value": value,
                "unit": summary_panel["units"],
                "status": "normal",
            }
        requests.append(
            (
                "/tools/generate_clinical_summary",
                {
                    "patient_id": patient_id,
                    "patient_context": patient_context,
                    "results": results,
                    "summary_type": "chart_note",
                },
            )
        )

    requests.append(
        (
            "/tools/suggest_differentials",
            {
                "patient_id": patient_id,
                "abnormal_findings": panels["differentials"]["abnormal_findings"],
                "clinical_context": panels["differentials"]["clinical_context"],
                "max_differentials": 5,
            },
        )
    )
    return requests


def main() -> None:
    client = TestClient(app)
    for path in sorted(FIXTURE_DIR.glob("SYN-*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        print(f"\n== {path.name} ==")
        for endpoint, body in build_requests(payload):
            response = client.post(endpoint, json=body)
            print(endpoint, response.status_code)


if __name__ == "__main__":
    main()
