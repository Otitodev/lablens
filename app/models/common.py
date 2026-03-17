from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, StringConstraints
from typing_extensions import Annotated


SyntheticId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=64)]


class PanelType(str, Enum):
    CBC = "CBC"
    LFT = "LFT"
    RENAL = "RENAL"
    COAG = "COAG"
    THYROID = "THYROID"
    MIXED = "MIXED"
    IRON = "IRON"
    GLUCOSE = "GLUCOSE"
    ABG = "ABG"
    LIPID = "LIPID"


class UnitsType(str, Enum):
    SI = "SI"
    CONVENTIONAL = "conventional"


class ResultStatus(str, Enum):
    NORMAL = "normal"
    LOW = "low"
    HIGH = "high"
    CRITICAL_LOW = "critical_low"
    CRITICAL_HIGH = "critical_high"


class ClinicalSex(str, Enum):
    MALE = "male"
    FEMALE = "female"
    UNSPECIFIED = "unspecified"


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    ABNORMAL = "abnormal"
    BORDERLINE = "borderline"


class AlertDirection(str, Enum):
    LOW = "low"
    HIGH = "high"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


class FindingMagnitude(str, Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class SummaryType(str, Enum):
    CHART_NOTE = "chart_note"
    REFERRAL = "referral"
    PATIENT_FACING = "patient_facing"


class ReferenceRange(BaseModel):
    low: float
    high: float


class AnalyteInterpretation(BaseModel):
    analyte: str
    value: float
    status: ResultStatus
    commentary: str
    clinical_significance: str


class APIErrorDetail(BaseModel):
    code: str = Field(..., examples=["validation_error"])
    message: str


class APIErrorResponse(BaseModel):
    error: APIErrorDetail
