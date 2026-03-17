from app.models.common import AlertSeverity, ResultStatus
from app.models.tools import CriticalValueItem
from app.services.status_logic import build_alert, classify_result, is_borderline


def test_classify_result_normal() -> None:
    assert classify_result(8.5, 4.0, 11.0) == ResultStatus.NORMAL


def test_classify_result_high() -> None:
    assert classify_result(15.0, 4.0, 11.0) == ResultStatus.HIGH


def test_classify_result_critical_low() -> None:
    assert classify_result(5.9, 12.0, 16.0, critical_low=6.0) == ResultStatus.CRITICAL_LOW


def test_borderline_detection() -> None:
    assert is_borderline(4.2, 4.0, 11.0) is True


def test_build_alert_creates_critical_message() -> None:
    alert = build_alert(
        "Platelets",
        CriticalValueItem(
            value=18,
            unit="x10^9/L",
            reference_low=150,
            reference_high=400,
            critical_low=20,
            critical_high=None,
        ),
    )
    assert alert is not None
    assert alert.severity == AlertSeverity.CRITICAL
    assert alert.notify_immediately is True
