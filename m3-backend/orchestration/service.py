"""The M3 orchestration loop for ONE incident (leader's diagram steps 2-6):
   processed event -> M4 predict -> save -> M5 explain -> save -> status COMPLETE.
A failure at any stage keeps everything saved so far and records WHY, so it can be retried (reprocess)."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from hashlib import sha256
from typing import Any, Iterator

from sqlalchemy import text
from sqlalchemy.orm import Session

from db.models import IncidentPipeline, IncidentResult, ProcessedEvent, RcaResult, utcnow
from db.repository import to_contract
from orchestration.clients import AIServiceError, explain, predict

log = logging.getLogger("cf.orchestrator")


@contextmanager
def _incident_lock(session: Session, event_id: str) -> Iterator[bool]:
    """Try to acquire a non-blocking PostgreSQL lock for one incident."""
    engine = session.get_bind()
    if engine.dialect.name != "postgresql":
        # Keep SQLite-based unit and integration tests compatible.
        yield True
        return

    # Stable signed 64-bit key derived from the incident ID.
    lock_key = int.from_bytes(
        sha256(event_id.encode("utf-8")).digest()[:8],
        byteorder="big",
        signed=True,
    )

    with engine.connect() as connection:
        acquired = connection.execute(
            text("SELECT pg_try_advisory_lock(:lock_key)"),
            {"lock_key": lock_key},
        ).scalar_one()
        connection.commit()

        try:
            yield acquired
        finally:
            if acquired:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_key)"),
                    {"lock_key": lock_key},
                )
                connection.commit()


def _upsert(session: Session, model, event_id: str, **cols: Any) -> None:
    now = utcnow()
    row = session.get(model, event_id)
    if row is None:
        session.add(model(event_id=event_id, created_at=now, updated_at=now, **cols))
    else:
        for k, v in cols.items():
            setattr(row, k, v)
        row.updated_at = now


def mark_received(session: Session, event_id: str) -> None:
    now = utcnow()
    row = session.get(IncidentPipeline, event_id)
    if row is None:
        session.add(IncidentPipeline(event_id=event_id, status="RECEIVED", attempts=0, created_at=now, updated_at=now))
    else:
        row.status, row.error, row.updated_at = "RECEIVED", None, now
    session.commit()


def _set(session: Session, event_id: str, status: str, error: str | None = None) -> None:
    row = session.get(IncidentPipeline, event_id)
    row.status, row.error, row.updated_at = status, (error or None), utcnow()
    session.commit()


def run_orchestration(session: Session, event_id: str) -> str:
    """Run M4 and M5 under a per-incident lock, preserving prior results on retries."""
    ev = session.get(ProcessedEvent, event_id)
    if ev is None:
        raise LookupError(f"event {event_id} not found")

    if session.get(IncidentPipeline, event_id) is None:
        mark_received(session, event_id)

    with _incident_lock(session, event_id) as acquired:
        if not acquired:
            # Another worker owns this incident; this request did not run.
            log.info(
                "incident %s skipped: orchestration lock is already held",
                event_id,
            )
            return "ALREADY_PROCESSING"

        # Refresh state after acquiring the lock, in case another attempt finished.
        session.expire_all()
        ev = session.get(ProcessedEvent, event_id)
        if ev is None:
            raise LookupError(f"event {event_id} not found")

        had_prediction = session.get(IncidentResult, event_id) is not None
        had_rca = session.get(RcaResult, event_id) is not None

        row = session.get(IncidentPipeline, event_id)
        row.status = "PROCESSING"
        row.error = None
        row.attempts = (row.attempts or 0) + 1
        row.updated_at = utcnow()
        session.commit()

        event = to_contract(ev)

        try:
            pred = predict(event)
        except Exception as exc:  # noqa: BLE001
            return _fail(session, event_id, "M4_FAILED", exc)

        try:
            expl = explain(event, pred)
        except Exception as exc:  # noqa: BLE001
            if not had_prediction and not had_rca:
                try:
                    _upsert(
                        session,
                        IncidentResult,
                        event_id,
                        incident_type=pred["incident_type"],
                        anomaly_score=pred["anomaly_score"],
                        severity=pred["severity"],
                        extra=pred["extra"],
                    )
                    session.commit()
                except Exception:
                    session.rollback()
            return _fail(session, event_id, "M5_FAILED", exc)

        try:
            _upsert(
                session,
                IncidentResult,
                event_id,
                incident_type=pred["incident_type"],
                anomaly_score=pred["anomaly_score"],
                severity=pred["severity"],
                extra=pred["extra"],
            )
            _upsert(
                session,
                RcaResult,
                event_id,
                root_cause=expl["root_cause"],
                evidence=expl["evidence"],
                impact=expl["impact"],
                recommended_action=expl["recommended_action"],
                confidence=expl["confidence"],
                extra=expl["extra"],
            )

            row = session.get(IncidentPipeline, event_id)
            row.status = "COMPLETE"
            row.error = None
            row.updated_at = utcnow()
            session.commit()
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            return _fail(session, event_id, "M5_FAILED", exc)

        log.info("incident %s COMPLETE (severity=%s)", event_id, pred["severity"])
        return "COMPLETE"


def _fail(session: Session, event_id: str, status: str, exc: Exception) -> str:
    session.rollback()
    msg = str(exc) if isinstance(exc, AIServiceError) else f"unexpected {type(exc).__name__}: {exc}"
    log.error("incident %s %s: %s", event_id, status, msg)
    _set(session, event_id, status, msg[:1000])
    return status
