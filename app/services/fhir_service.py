"""FHIR client service for LabLens MCP.

Fetches patient laboratory Observation resources from a FHIR R4 server
using context supplied via SHARP headers. When SHARP context is absent the
caller falls back to request-body data — no FHIR server is required.

Tested against:
  - HAPI FHIR public R4  (https://hapi.fhir.org/baseR4)  — no auth
  - Epic sandbox R4       (https://fhir.epic.com/...)      — Bearer token
  - Any standards-compliant FHIR R4 server
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx

from app.services.epic_oauth_service import EpicOAuthService
from app.sharp import SharpContext

logger = logging.getLogger(__name__)

# Laboratory category — full URL required by Epic R4; short form works on HAPI
_LABORATORY_CATEGORY = "http://terminology.hl7.org/CodeSystem/observation-category|laboratory"
_DEFAULT_TIMEOUT = 15.0


@dataclass
class FHIRLabObservation:
    """A single lab result extracted from a FHIR Observation resource."""

    analyte: str
    value: float
    unit: str
    status: str  # FHIR status: final | preliminary | amended …
    reference_low: float | None = None
    reference_high: float | None = None
    loinc_code: str | None = None


@dataclass
class FHIRPatientLabs:
    """All lab observations fetched for a patient."""

    patient_id: str
    fhir_server_url: str
    observations: list[FHIRLabObservation] = field(default_factory=list)

    @property
    def has_results(self) -> bool:
        return bool(self.observations)


class FHIRService:
    """Fetches laboratory Observations from a FHIR R4 server."""

    def __init__(
        self,
        timeout: float = _DEFAULT_TIMEOUT,
        oauth_service: EpicOAuthService | None = None,
    ) -> None:
        self._timeout = timeout
        self._oauth_service = oauth_service

    def fetch_labs(self, sharp: SharpContext) -> FHIRPatientLabs | None:
        """Return lab observations for the patient in *sharp*, or None.

        Returns None (rather than raising) when context is incomplete so
        callers can transparently fall back to request-body data.
        """
        if not sharp.fhir_server_url or not sharp.patient_id:
            return None

        base = sharp.fhir_server_url.rstrip("/")
        url = f"{base}/Observation"
        params = {
            "patient": sharp.patient_id,
            "category": _LABORATORY_CATEGORY,
            "_count": "100",
            "_sort": "-date",
        }
        headers = {"Accept": "application/fhir+json"}
        token: str | None = sharp.fhir_access_token  # per-request token has priority

        # Auto-inject Epic OAuth token when no header token and URL matches Epic base
        if not token and self._oauth_service:
            from app.config import get_settings
            if base == get_settings().epic_fhir_base_url.rstrip("/"):
                try:
                    token = self._oauth_service.get_access_token()
                    logger.debug("epic_oauth auto_injected_token patient_id=%s", sharp.patient_id)
                except Exception as exc:
                    logger.warning("epic_oauth auto_inject_failed error=%s", exc)

        if token:
            headers["Authorization"] = f"Bearer {token}"

        logger.info(
            "fhir_fetch patient_id=%s server=%s",
            sharp.patient_id,
            base,
        )

        try:
            response = httpx.get(url, params=params, headers=headers, timeout=self._timeout)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning("fhir_fetch failed status=%s url=%s", exc.response.status_code, url)
            return None
        except httpx.RequestError as exc:
            logger.warning("fhir_fetch request_error url=%s error=%s", url, exc)
            return None

        bundle = response.json()
        observations = _parse_bundle(bundle)
        logger.info(
            "fhir_fetch patient_id=%s observations_found=%d",
            sharp.patient_id,
            len(observations),
        )
        return FHIRPatientLabs(
            patient_id=sharp.patient_id,
            fhir_server_url=base,
            observations=observations,
        )


# ---------------------------------------------------------------------------
# Internal FHIR bundle parsing
# ---------------------------------------------------------------------------

def _parse_bundle(bundle: dict) -> list[FHIRLabObservation]:
    entries = bundle.get("entry", [])
    results: list[FHIRLabObservation] = []
    for entry in entries:
        resource = entry.get("resource", {})
        if resource.get("resourceType") != "Observation":
            continue
        obs = _parse_observation(resource)
        if obs:
            results.append(obs)
    return results


def _parse_observation(resource: dict) -> FHIRLabObservation | None:
    # Must have a numeric value
    vq = resource.get("valueQuantity")
    if not vq or vq.get("value") is None:
        return None

    try:
        value = float(vq["value"])
    except (TypeError, ValueError):
        return None

    unit = vq.get("unit") or vq.get("code") or ""

    # Analyte name: prefer display from coding, fall back to text
    analyte = _extract_analyte_name(resource.get("code", {}))
    if not analyte:
        return None

    loinc_code = _extract_loinc(resource.get("code", {}))
    status = resource.get("status", "unknown")

    # Reference range (first entry only)
    ref_low: float | None = None
    ref_high: float | None = None
    ref_ranges = resource.get("referenceRange", [])
    if ref_ranges:
        ref = ref_ranges[0]
        if "low" in ref:
            try:
                ref_low = float(ref["low"]["value"])
            except (TypeError, ValueError, KeyError):
                pass
        if "high" in ref:
            try:
                ref_high = float(ref["high"]["value"])
            except (TypeError, ValueError, KeyError):
                pass

    return FHIRLabObservation(
        analyte=analyte,
        value=value,
        unit=unit,
        status=status,
        reference_low=ref_low,
        reference_high=ref_high,
        loinc_code=loinc_code,
    )


def _extract_analyte_name(code_block: dict) -> str:
    text = code_block.get("text")
    if text:
        return text
    for coding in code_block.get("coding", []):
        display = coding.get("display")
        if display:
            return display
    return ""


def _extract_loinc(code_block: dict) -> str | None:
    for coding in code_block.get("coding", []):
        if coding.get("system", "").endswith("loinc.org"):
            return coding.get("code")
    return None
