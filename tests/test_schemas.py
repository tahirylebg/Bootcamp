import pytest
from pydantic import ValidationError

from app.schemas import EventCreate


def test_event_create_accepts_valid_payload():
    event = EventCreate(
        source="web-server",
        event_type="failed_login",
        severity="high",
        message="Five failed login attempts for admin",
        ip_address="203.0.113.10",
        metadata={"username": "admin", "attempts": 5},
    )

    assert event.source == "web-server"
    assert event.severity == "high"
    assert event.metadata == {"username": "admin", "attempts": 5}


def test_event_create_rejects_invalid_severity():
    with pytest.raises(ValidationError):
        EventCreate(
            source="web-server",
            event_type="failed_login",
            severity="catastrophic",
            message="Five failed login attempts for admin",
        )


def test_event_create_rejects_empty_message():
    with pytest.raises(ValidationError):
        EventCreate(
            source="web-server",
            event_type="failed_login",
            severity="low",
            message="",
        )
