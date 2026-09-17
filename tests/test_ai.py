from app.ai import mock_analysis
from app.models import Event


def _make_event(severity: str) -> Event:
    return Event(
        source="web-server",
        event_type="failed_login",
        severity=severity,
        message="Five failed login attempts for admin",
    )


def test_mock_analysis_escalates_high_and_critical_severity():
    for severity in ("high", "critical"):
        result = mock_analysis(_make_event(severity))
        assert result["risk_level"] == "high"


def test_mock_analysis_keeps_lower_severity_unchanged():
    result = mock_analysis(_make_event("low"))

    assert result["risk_level"] == "low"


def test_mock_analysis_returns_expected_shape():
    result = mock_analysis(_make_event("medium"))

    assert set(result.keys()) == {"risk_level", "summary", "recommendations"}
    assert "failed_login" in result["summary"]
    assert isinstance(result["recommendations"], list)
    assert len(result["recommendations"]) > 0
