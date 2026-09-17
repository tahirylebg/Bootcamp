import json

import httpx
from openai import OpenAI

from app.config import Settings
from app.models import Event

SYSTEM_PROMPT = """Tu es un analyste SOC.
Analyse l'evenement fourni et reponds uniquement en JSON valide avec:
- risk_level: une valeur parmi low, medium, high, critical
- summary: une explication courte
- recommendations: une liste de mesures concretes
"""


def mock_analysis(event: Event) -> dict:
    risk = "high" if event.severity in {"high", "critical"} else event.severity
    return {
        "risk_level": risk,
        "summary": f"Evenement {event.event_type} recu depuis {event.source}.",
        "recommendations": [
            "Verifier la source et les journaux associes",
            "Documenter la decision de traitement",
        ],
    }


def analyze_event(event: Event, settings: Settings) -> dict:
    if settings.ai_provider == "mock":
        return mock_analysis(event)

    prompt = json.dumps(
        {
            "source": event.source,
            "event_type": event.event_type,
            "severity": event.severity,
            "message": event.message,
            "ip_address": event.ip_address,
            "metadata": event.metadata_json,
        },
        ensure_ascii=True,
    )

    if settings.ai_provider == "deepseek":
        if not settings.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY est requis avec AI_PROVIDER=deepseek")
        client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
        response = client.chat.completions.create(
            model=settings.deepseek_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        )
        return json.loads(response.choices[0].message.content or "{}")

    if settings.ai_provider == "ollama":
        response = httpx.post(
            f"{settings.ollama_url.rstrip('/')}/api/chat",
            json={
                "model": settings.ollama_model,
                "stream": False,
                "format": "json",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=60,
        )
        response.raise_for_status()
        return json.loads(response.json()["message"]["content"])

    raise ValueError("AI_PROVIDER doit valoir mock, deepseek ou ollama")
