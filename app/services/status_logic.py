from __future__ import annotations

from app.models.common import AlertDirection, AlertSeverity, ResultStatus
from app.models.tools import CriticalAlert, CriticalValueItem


def classify_result(
    value: float,
    reference_low: float,
    reference_high: float,
    critical_low: float | None = None,
    critical_high: float | None = None,
) -> ResultStatus:
    if critical_low is not None and value <= critical_low:
        return ResultStatus.CRITICAL_LOW
    if critical_high is not None and value >= critical_high:
        return ResultStatus.CRITICAL_HIGH
    if value < reference_low:
        return ResultStatus.LOW
    if value > reference_high:
        return ResultStatus.HIGH
    return ResultStatus.NORMAL


def is_borderline(value: float, reference_low: float, reference_high: float, margin: float = 0.1) -> bool:
    if reference_high <= reference_low:
        return False
    span = reference_high - reference_low
    low_band = reference_low + (span * margin)
    high_band = reference_high - (span * margin)
    return reference_low <= value <= low_band or high_band <= value <= reference_high


def build_alert(analyte: str, item: CriticalValueItem) -> CriticalAlert | None:
    status = classify_result(
        value=item.value,
        reference_low=item.reference_low,
        reference_high=item.reference_high,
        critical_low=item.critical_low,
        critical_high=item.critical_high,
    )
    if status == ResultStatus.NORMAL:
        if not is_borderline(item.value, item.reference_low, item.reference_high):
            return None
        severity = AlertSeverity.BORDERLINE
        direction = (
            AlertDirection.LOW
            if item.value <= (item.reference_low + item.reference_high) / 2
            else AlertDirection.HIGH
        )
        message = (
            f"{analyte} is near the {'lower' if direction == AlertDirection.LOW else 'upper'} "
            "reference boundary; monitor for trend progression."
        )
        return CriticalAlert(
            analyte=analyte,
            value=item.value,
            severity=severity,
            direction=direction,
            message=message,
            notify_immediately=False,
        )

    if status in {ResultStatus.CRITICAL_LOW, ResultStatus.CRITICAL_HIGH}:
        severity = AlertSeverity.CRITICAL
        direction = AlertDirection.LOW if status == ResultStatus.CRITICAL_LOW else AlertDirection.HIGH
        message = (
            f"{analyte} is critically {direction.value} and requires immediate clinician notification."
        )
        return CriticalAlert(
            analyte=analyte,
            value=item.value,
            severity=severity,
            direction=direction,
            message=message,
            notify_immediately=True,
        )

    severity = AlertSeverity.ABNORMAL
    direction = AlertDirection.LOW if status == ResultStatus.LOW else AlertDirection.HIGH
    message = f"{analyte} is {direction.value} relative to the reference range and should be clinically reviewed."
    return CriticalAlert(
        analyte=analyte,
        value=item.value,
        severity=severity,
        direction=direction,
        message=message,
        notify_immediately=False,
    )


def alert_sort_key(alert: CriticalAlert) -> tuple[int, float]:
    severity_weight = {
        AlertSeverity.CRITICAL: 0,
        AlertSeverity.ABNORMAL: 1,
        AlertSeverity.BORDERLINE: 2,
    }[alert.severity]
    return severity_weight, -abs(alert.value)
