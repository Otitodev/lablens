"""SHARP Extension Specs implementation for LabLens MCP.

SHARP (Standardized Healthcare Agent Remote Protocol) defines how healthcare
context — patient identifiers, FHIR server URLs, and FHIR access tokens — is
propagated across MCP tool invocations.

Reference: https://www.sharponmcp.com
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import Header

logger = logging.getLogger(__name__)

# SHARP header names as defined by the specification.
HEADER_FHIR_SERVER_URL = "x-fhir-server-url"
HEADER_FHIR_ACCESS_TOKEN = "x-fhir-access-token"
HEADER_PATIENT_ID = "x-patient-id"


@dataclass(frozen=True)
class SharpContext:
    """Healthcare context propagated via SHARP headers.

    All three fields are optional for this server because LabLens operates on
    synthetic data and does not require a live FHIR server connection. When
    present, they are validated, logged, and attached to tool invocations so
    that future FHIR-backed extensions can consume them without API changes.
    """

    fhir_server_url: str | None
    fhir_access_token: str | None
    patient_id: str | None

    @property
    def is_present(self) -> bool:
        """True if any SHARP context was supplied by the caller."""
        return any([self.fhir_server_url, self.fhir_access_token, self.patient_id])

    def to_log_dict(self) -> dict:
        """Safe representation for structured logging (token is redacted)."""
        return {
            "fhir_server_url": self.fhir_server_url,
            "fhir_access_token": "[REDACTED]" if self.fhir_access_token else None,
            "patient_id": self.patient_id,
        }


def extract_sharp_context(
    x_fhir_server_url: str | None = Header(default=None, alias="X-FHIR-Server-URL"),
    x_fhir_access_token: str | None = Header(default=None, alias="X-FHIR-Access-Token"),
    x_patient_id: str | None = Header(default=None, alias="X-Patient-ID"),
) -> SharpContext:
    """FastAPI dependency that extracts SHARP context headers from the request.

    All headers are optional. When present they are logged at DEBUG level so
    that platform operators can verify context propagation without exposing
    tokens in production logs.
    """
    ctx = SharpContext(
        fhir_server_url=x_fhir_server_url,
        fhir_access_token=x_fhir_access_token,
        patient_id=x_patient_id,
    )
    if ctx.is_present:
        logger.debug("SHARP context received: %s", ctx.to_log_dict())
    return ctx
