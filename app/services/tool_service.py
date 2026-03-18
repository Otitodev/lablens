from __future__ import annotations

import logging

from app.errors import ConfigurationError
from app.models.common import ResultStatus
from app.models.tools import (
    CriticalValueItem,
    FlagCriticalValuesRequest,
    FlagCriticalValuesResponse,
    GenerateClinicalSummaryRequest,
    GenerateClinicalSummaryResponse,
    InterpretLabPanelRequest,
    InterpretLabPanelResponse,
    SuggestDifferentialsRequest,
    SuggestDifferentialsResponse,
)
from app.services.anthropic_service import AnthropicJSONService
from app.services.fhir_service import FHIRService
from app.services.prompts import (
    GENERATE_CLINICAL_SUMMARY_PROMPT,
    INTERPRET_LAB_PANEL_PROMPT,
    SUGGEST_DIFFERENTIALS_PROMPT,
)
from app.services.status_logic import alert_sort_key, build_alert, classify_result
from app.sharp import SharpContext

logger = logging.getLogger(__name__)


class ToolService:
    def __init__(
        self,
        llm_service: AnthropicJSONService | None = None,
        fhir_service: FHIRService | None = None,
    ) -> None:
        self.llm_service = llm_service
        self.fhir_service = fhir_service

    def flag_critical_values(
        self,
        request: FlagCriticalValuesRequest,
        sharp: SharpContext | None = None,
    ) -> FlagCriticalValuesResponse:
        self._log_sharp(sharp, "flag_critical_values")

        results = dict(request.results)

        # If no results were provided in the request body, try FHIR
        if not results and sharp and self.fhir_service:
            patient_labs = self.fhir_service.fetch_labs(sharp)
            if patient_labs and patient_labs.has_results:
                logger.info(
                    "flag_critical_values using FHIR data patient_id=%s count=%d",
                    sharp.patient_id,
                    len(patient_labs.observations),
                )
                for obs in patient_labs.observations:
                    if obs.reference_low is None or obs.reference_high is None:
                        continue
                    results[obs.analyte] = CriticalValueItem(
                        value=obs.value,
                        unit=obs.unit,
                        reference_low=obs.reference_low,
                        reference_high=obs.reference_high,
                    )

        alerts = []
        for analyte, item in results.items():
            alert = build_alert(analyte, item)
            if alert:
                alerts.append(alert)
        alerts.sort(key=alert_sort_key)

        if not alerts:
            summary = "No abnormal, critical, or borderline alerts were identified in this synthetic result set."
        else:
            critical_count = sum(1 for alert in alerts if alert.notify_immediately)
            summary = (
                f"Identified {len(alerts)} alert(s) in total, including {critical_count} "
                "requiring immediate notification."
            )
        return FlagCriticalValuesResponse(
            patient_id=request.patient_id,
            alert_count=len(alerts),
            alerts=alerts,
            summary=summary,
        )

    def interpret_lab_panel(
        self,
        request: InterpretLabPanelRequest,
        sharp: SharpContext | None = None,
    ) -> InterpretLabPanelResponse:
        self._log_sharp(sharp, "interpret_lab_panel")
        llm = self._require_llm()
        interpreted_values = []
        for analyte, value in request.values.items():
            reference = request.reference_ranges.get(analyte)
            if not reference:
                continue
            status = classify_result(value, reference.low, reference.high)
            interpreted_values.append(
                {
                    "analyte": analyte,
                    "value": value,
                    "status": status.value,
                    "reference_range": reference.model_dump(),
                }
            )
        payload = {
            "patient_id": request.patient_id,
            "panel": request.panel.value,
            "units": request.units.value,
            "analytes": interpreted_values,
            "output_schema": InterpretLabPanelResponse.model_json_schema(),
        }
        self._attach_fhir_context(payload, sharp)
        return llm.generate_json(
            tool_name="interpret_lab_panel",
            system_prompt=INTERPRET_LAB_PANEL_PROMPT,
            payload=payload,
            response_model=InterpretLabPanelResponse,
        )

    def generate_clinical_summary(
        self,
        request: GenerateClinicalSummaryRequest,
        sharp: SharpContext | None = None,
    ) -> GenerateClinicalSummaryResponse:
        self._log_sharp(sharp, "generate_clinical_summary")
        llm = self._require_llm()
        payload = {
            "patient_id": request.patient_id,
            "patient_context": request.patient_context.model_dump(),
            "results": {name: item.model_dump() for name, item in request.results.items()},
            "summary_type": request.summary_type.value,
            "output_schema": GenerateClinicalSummaryResponse.model_json_schema(),
        }
        self._attach_fhir_context(payload, sharp)
        response = llm.generate_json(
            tool_name="generate_clinical_summary",
            system_prompt=GENERATE_CLINICAL_SUMMARY_PROMPT,
            payload=payload,
            response_model=GenerateClinicalSummaryResponse,
        )
        word_count = len(response.summary.split())
        return response.model_copy(update={"word_count": word_count})

    def suggest_differentials(
        self,
        request: SuggestDifferentialsRequest,
        sharp: SharpContext | None = None,
    ) -> SuggestDifferentialsResponse:
        self._log_sharp(sharp, "suggest_differentials")
        llm = self._require_llm()
        payload = {
            "patient_id": request.patient_id,
            "abnormal_findings": [item.model_dump() for item in request.abnormal_findings],
            "clinical_context": request.clinical_context.model_dump(),
            "max_differentials": request.max_differentials,
            "output_schema": SuggestDifferentialsResponse.model_json_schema(),
        }
        self._attach_fhir_context(payload, sharp)
        response = llm.generate_json(
            tool_name="suggest_differentials",
            system_prompt=SUGGEST_DIFFERENTIALS_PROMPT,
            payload=payload,
            response_model=SuggestDifferentialsResponse,
        )
        capped = response.differentials[: request.max_differentials]
        ranked = [item.model_copy(update={"rank": idx}) for idx, item in enumerate(capped, start=1)]
        caveat = response.clinical_caveat or "AI-generated output; review by a qualified clinician is required."
        return response.model_copy(update={"differentials": ranked, "clinical_caveat": caveat})

    def _require_llm(self):
        if not self.llm_service:
            raise ConfigurationError("LLM-backed tool requested without an LLM service configured.")
        return self.llm_service

    def _log_sharp(self, sharp: SharpContext | None, tool_name: str) -> None:
        if sharp and sharp.is_present:
            logger.info(
                "SHARP context on tool=%s patient_id=%s fhir_server=%s",
                tool_name,
                sharp.patient_id,
                sharp.fhir_server_url,
            )

    def _attach_fhir_context(self, payload: dict, sharp: SharpContext | None) -> None:
        """If SHARP context is present, fetch FHIR observations and attach them
        to the LLM payload as supplementary clinical context."""
        if not sharp or not self.fhir_service:
            return
        patient_labs = self.fhir_service.fetch_labs(sharp)
        if not patient_labs or not patient_labs.has_results:
            return
        payload["fhir_observations"] = [
            {
                "analyte": obs.analyte,
                "value": obs.value,
                "unit": obs.unit,
                "loinc_code": obs.loinc_code,
                "reference_low": obs.reference_low,
                "reference_high": obs.reference_high,
                "status": obs.status,
            }
            for obs in patient_labs.observations
        ]
        logger.info(
            "fhir_context_attached tool payload patient_id=%s observations=%d",
            sharp.patient_id,
            len(patient_labs.observations),
        )
