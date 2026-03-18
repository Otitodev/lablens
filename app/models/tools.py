from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.common import (
    AlertDirection,
    AlertSeverity,
    AnalyteInterpretation,
    ClinicalSex,
    ConfidenceLevel,
    FindingMagnitude,
    PanelType,
    ReferenceRange,
    ResultStatus,
    SummaryType,
    SyntheticId,
    UnitsType,
)


def _reject_phi_like_content(value: str) -> str:
    lowered = value.lower()
    blocked_terms = {
        "ssn",
        "social security",
        "date of birth",
        "dob",
        "mrn",
        "medical record",
        "address",
        "phone",
        "email",
    }
    if any(term in lowered for term in blocked_terms):
        raise ValueError("PHI-like content is not allowed. Use synthetic-only data.")
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InterpretLabPanelRequest(StrictModel):
    patient_id: SyntheticId
    panel: PanelType
    values: dict[str, float]
    units: UnitsType
    reference_ranges: dict[str, ReferenceRange]

    @field_validator("patient_id")
    @classmethod
    def validate_patient_id(cls, value: str) -> str:
        return _reject_phi_like_content(value)


class InterpretLabPanelResponse(StrictModel):
    patient_id: SyntheticId
    panel: str
    interpretations: list[AnalyteInterpretation]
    overall_assessment: str
    recommended_actions: list[str]


class CriticalValueItem(StrictModel):
    value: float
    unit: str
    reference_low: float
    reference_high: float
    critical_low: float | None = None
    critical_high: float | None = None


class FlagCriticalValuesRequest(StrictModel):
    patient_id: SyntheticId
    results: dict[str, CriticalValueItem] = Field(default_factory=dict)

    @field_validator("patient_id")
    @classmethod
    def validate_patient_id(cls, value: str) -> str:
        return _reject_phi_like_content(value)


class CriticalAlert(StrictModel):
    analyte: str
    value: float
    severity: AlertSeverity
    direction: AlertDirection
    message: str
    notify_immediately: bool


class FlagCriticalValuesResponse(StrictModel):
    patient_id: SyntheticId
    alert_count: int
    alerts: list[CriticalAlert]
    summary: str


class PatientContext(StrictModel):
    age_range: str
    sex: ClinicalSex
    clinical_indication: str

    @field_validator("age_range", "clinical_indication")
    @classmethod
    def validate_context_fields(cls, value: str) -> str:
        return _reject_phi_like_content(value)


class SummaryResultItem(StrictModel):
    value: float
    unit: str
    status: ResultStatus


class GenerateClinicalSummaryRequest(StrictModel):
    patient_id: SyntheticId
    patient_context: PatientContext
    results: dict[str, SummaryResultItem]
    summary_type: SummaryType

    @field_validator("patient_id")
    @classmethod
    def validate_patient_id(cls, value: str) -> str:
        return _reject_phi_like_content(value)


class GenerateClinicalSummaryResponse(StrictModel):
    patient_id: SyntheticId
    summary_type: str
    summary: str
    key_findings: list[str]
    word_count: int


class DifferentialClinicalContext(StrictModel):
    age_range: str
    sex: ClinicalSex
    presenting_complaint: str | None = None

    @field_validator("age_range")
    @classmethod
    def validate_age_range(cls, value: str) -> str:
        return _reject_phi_like_content(value)

    @field_validator("presenting_complaint")
    @classmethod
    def validate_complaint(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _reject_phi_like_content(value)


class AbnormalFinding(StrictModel):
    analyte: str
    value: float
    unit: str
    direction: str
    magnitude: FindingMagnitude

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, value: str) -> str:
        if value not in {"low", "high"}:
            raise ValueError("direction must be 'low' or 'high'")
        return value


class SuggestDifferentialsRequest(StrictModel):
    patient_id: SyntheticId
    abnormal_findings: list[AbnormalFinding]
    clinical_context: DifferentialClinicalContext
    max_differentials: int = Field(default=5, ge=1, le=10)

    @field_validator("patient_id")
    @classmethod
    def validate_patient_id(cls, value: str) -> str:
        return _reject_phi_like_content(value)


class DifferentialItem(StrictModel):
    rank: int = Field(ge=1)
    diagnosis: str
    supporting_findings: list[str]
    reasoning: str
    confidence: ConfidenceLevel
    suggested_confirmatory_tests: list[str]


class SuggestDifferentialsResponse(StrictModel):
    patient_id: SyntheticId
    differentials: list[DifferentialItem]
    clinical_caveat: str

    @model_validator(mode="after")
    def validate_ranks(self) -> "SuggestDifferentialsResponse":
        expected = list(range(1, len(self.differentials) + 1))
        received = [item.rank for item in self.differentials]
        if received != expected:
            raise ValueError("differentials must be ranked sequentially starting at 1")
        return self


class LLMInvocation(BaseModel):
    system_prompt: str
    user_payload: dict[str, Any]


class LLMMetadata(StrictModel):
    request_id: str
    tool_name: str
    latency_ms: int
