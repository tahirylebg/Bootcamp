import csv
import io
import json

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import analyze_event
from app.config import get_settings
from app.db import Base, engine, get_db
from app.models import Analysis, Event
from app.schemas import AnalysisResponse, EventCreate, EventResponse, IngestResponse, TextAnalysisRequest


app = FastAPI(
    title="Bootcamp Security Logs API",
    description="Ingestion, validation and AI-assisted analysis of technical events.",
    version="1.0.0",
)


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED, tags=["events"])
def create_event(payload: EventCreate, database: Session = Depends(get_db)) -> Event:
    event = Event(
        source=payload.source,
        event_type=payload.event_type,
        severity=payload.severity,
        message=payload.message,
        ip_address=payload.ip_address,
        metadata_json=payload.metadata,
    )
    database.add(event)
    database.commit()
    database.refresh(event)
    return event


@app.get("/events", response_model=list[EventResponse], tags=["events"])
def list_events(
    limit: int = Query(default=50, ge=1, le=500),
    database: Session = Depends(get_db),
) -> list[Event]:
    return list(database.scalars(select(Event).order_by(Event.created_at.desc()).limit(limit)))


@app.post("/analyze-text", response_model=AnalysisResponse, tags=["analysis"])
def analyze_text(payload: TextAnalysisRequest, database: Session = Depends(get_db)) -> Analysis:
    event = Event(
        source="swagger",
        event_type="text_analysis",
        severity="medium",
        message=payload.text,
        metadata_json={},
    )
    database.add(event)
    database.flush()
    try:
        result = analyze_event(event, get_settings())
    except (ValueError, json.JSONDecodeError) as error:
        database.rollback()
        raise HTTPException(status_code=502, detail=str(error)) from error
    analysis = Analysis(event_id=event.id, provider=get_settings().ai_provider,
                        risk_level=result["risk_level"], summary=result["summary"],
                        recommendations=result["recommendations"])
    database.add(analysis)
    database.commit()
    database.refresh(analysis)
    return analysis


@app.get("/alerts", response_model=list[AnalysisResponse], tags=["analysis"])
def list_alerts(
    risk_level: str | None = Query(default=None, pattern="^(low|medium|high|critical)$"),
    database: Session = Depends(get_db),
) -> list[Analysis]:
    query = select(Analysis).order_by(Analysis.created_at.desc())
    if risk_level:
        query = query.where(Analysis.risk_level == risk_level)
    return list(database.scalars(query))


@app.post("/ingest", response_model=IngestResponse, tags=["ingestion"])
def ingest_file(file: UploadFile = File(...), database: Session = Depends(get_db)) -> IngestResponse:
    if file.content_type not in {"application/json", "text/csv", "application/csv"}:
        raise HTTPException(status_code=415, detail="Utilisez un fichier JSON ou CSV")
    raw = file.file.read()
    try:
        if file.content_type == "application/json":
            records = json.loads(raw)
            records = records if isinstance(records, list) else [records]
        else:
            records = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
    except (UnicodeDecodeError, json.JSONDecodeError, csv.Error) as error:
        raise HTTPException(status_code=400, detail=f"Fichier illisible: {error}") from error

    imported, rejected, errors = 0, 0, []
    for index, record in enumerate(records, start=1):
        try:
            if isinstance(record.get("metadata"), str):
                record["metadata"] = json.loads(record["metadata"] or "{}")
            payload = EventCreate.model_validate(record)
            database.add(Event(source=payload.source, event_type=payload.event_type,
                                severity=payload.severity, message=payload.message,
                                ip_address=payload.ip_address, metadata_json=payload.metadata))
            imported += 1
        except ValueError as error:
            rejected += 1
            errors.append(f"Ligne {index}: {error}")
    database.commit()
    return IngestResponse(imported=imported, rejected=rejected, errors=errors[:20])
