import json

import pytest

import app.ai as ai
from app.ai import mock_analysis
from app.config import Settings
from app.models import Event


def _make_event(severity: str) -> Event:
    return Event(
        source="web-server",
        event_type="failed_login",
        severity=severity,
        message="Five failed login attempts for admin",
    )


def _make_settings(**overrides) -> Settings:
    defaults = {"database_url": "postgresql+psycopg2://user:pass@localhost:5432/testdb"}
    return Settings(**{**defaults, **overrides})


class _FakeOpenAIResponse:
    def __init__(self, content: str):
        message = type("Message", (), {"content": content})()
        choice = type("Choice", (), {"message": message})()
        self.choices = [choice]


class _FakeCompletions:
    def __init__(self, content: str):
        self._content = content
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeOpenAIResponse(self._content)


class _FakeOpenAIClient:
    def __init__(self, content: str):
        self.chat = type("Chat", (), {"completions": _FakeCompletions(content)})()


class _FakeHttpResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"message": {"content": json.dumps(self._payload)}}


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


def test_analyze_event_deepseek_uses_mocked_openai_client(monkeypatch):
    payload = {"risk_level": "critical", "summary": "Connexion suspecte", "recommendations": ["Bloquer l'IP"]}
    monkeypatch.setattr(ai, "OpenAI", lambda api_key, base_url: _FakeOpenAIClient(json.dumps(payload)))
    settings = _make_settings(ai_provider="deepseek", deepseek_api_key="test-key")

    result = ai.analyze_event(_make_event("critical"), settings)

    assert result == payload


def test_analyze_event_deepseek_requires_api_key():
    settings = _make_settings(ai_provider="deepseek", deepseek_api_key=None)

    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        ai.analyze_event(_make_event("high"), settings)


def test_analyze_event_ollama_uses_mocked_http_post(monkeypatch):
    payload = {"risk_level": "low", "summary": "RAS", "recommendations": ["Surveiller"]}
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return _FakeHttpResponse(payload)

    monkeypatch.setattr(ai.httpx, "post", fake_post)
    settings = _make_settings(ai_provider="ollama", ollama_url="http://fake-ollama:11434")

    result = ai.analyze_event(_make_event("low"), settings)

    assert result == payload
    assert captured["url"] == "http://fake-ollama:11434/api/chat"


def test_analyze_event_rejects_unknown_provider():
    settings = _make_settings(ai_provider="unknown")

    with pytest.raises(ValueError, match="AI_PROVIDER"):
        ai.analyze_event(_make_event("low"), settings)
