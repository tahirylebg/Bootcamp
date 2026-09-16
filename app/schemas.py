from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


Severity = Literal["info", "low", "medium", "high", "critical"]


class EventCreate(BaseModel):
    source: str = Field(min_length=1, max_length=100)
    event_type: str = Field(min_length=1, max_length=100)
    severity: Severity
    message: str = Field(min_length=1, max_length=10_000)
    ip_address: str | None = Field(default=None, max_length=45)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TextAnalysisRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)


class EventResponse(EventCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias="metadata_json",
        serialization_alias="metadata",
    )


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    provider: str
    risk_level: str
    summary: str
    recommendations: list[str]
    created_at: datetime


class IngestResponse(BaseModel):
    imported: int
    rejected: int
    errors: list[str]
