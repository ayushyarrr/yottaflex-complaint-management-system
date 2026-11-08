from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models import (
    Agent,
    Assignment,
    Complaint,
    ComplaintEvent,
    Resolution,
    SLAClock,
)
from backend.app.schemas.resolution import ResolutionCreate


def get_current_time():
    """Return UTC time as a naive datetime for SQLite compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_resolution_id(db: Session, complaint_id: str) -> str:
    """Generate a unique, sequential resolution ID for a complaint."""

    existing_ids = (
        db.query(Resolution.resolution_id)
        .filter(Resolution.complaint_id == complaint_id)
        .all()
    )

    if not existing_ids:
        return f"RES-{complaint_id}"

    return f"RES-{complaint_id}-{len(existing_ids) + 1:03d}"


def resolve_complaint(
    db: Session,
    complaint_id: str,
    payload: ResolutionCreate,
) -> Resolution:
    """Resolve an active complaint and preserve its resolution history."""

    try:
        complaint = (
            db.query(Complaint)
            .filter(Complaint.complaint_id == complaint_id)
            .with_for_update()
            .first()
        )

        if not complaint:
            raise HTTPException(
                status_code=404,
                detail="Complaint not found.",
            )

        if complaint.status != "IN_PROGRESS":
            raise HTTPException(
                status_code=409,
                detail="Only IN_PROGRESS complaints can be resolved.",
            )

        agent = (
            db.query(Agent)
            .filter(
                Agent.agent_id == payload.resolved_by,
                Agent.is_active.is_(True),
            )
            .first()
        )

        if not agent:
            raise HTTPException(
                status_code=404,
                detail="Active resolving agent not found.",
            )

        current_assignment = (
            db.query(Assignment)
            .filter(
                Assignment.complaint_id == complaint_id,
                Assignment.is_current.is_(True),
            )
            .first()
        )

        if not current_assignment:
            raise HTTPException(
                status_code=409,
                detail="Complaint has no current assignment.",
            )

        if current_assignment.agent_id != agent.agent_id:
            raise HTTPException(
                status_code=403,
                detail="Only the currently assigned agent can resolve this complaint.",
            )

        sla_clock = (
            db.query(SLAClock)
            .filter(SLAClock.complaint_id == complaint_id)
            .order_by(SLAClock.created_at.desc())
            .first()
        )

        if not sla_clock:
            raise HTTPException(
                status_code=409,
                detail="No SLA clock exists for this complaint.",
            )

        if sla_clock.paused_at is not None:
            raise HTTPException(
                status_code=409,
                detail="Resume the complaint before resolving it.",
            )

        now = get_current_time()
        old_status = complaint.status

        resolution = Resolution(
            resolution_id=generate_resolution_id(db, complaint_id),
            complaint_id=complaint_id,
            resolution_type=payload.resolution_type,
            resolution_description=payload.resolution_description,
            resolved_by=agent.agent_id,
            resolved_at=now,
            is_final=True,
        )

        db.add(resolution)

        complaint.status = "RESOLVED"
        complaint.updated_at = now

        sla_clock.resolved_at = now
        sla_clock.resolution_breached = (
            now > sla_clock.resolution_deadline
        )

        db.add(
            ComplaintEvent(
                complaint_id=complaint_id,
                event_type="STATUS_CHANGED",
                old_value=old_status,
                new_value="RESOLVED",
                description=(
                    f"Complaint resolved by {agent.agent_name}. "
                    f"Resolution type: {payload.resolution_type}."
                ),
                performed_by=agent.agent_name,
            )
        )

        db.commit()
        db.refresh(resolution)

        return resolution

    except Exception:
        db.rollback()
        raise