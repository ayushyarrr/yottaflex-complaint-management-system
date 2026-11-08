from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models import (
    Assignment,
    Complaint,
    ComplaintEvent,
    Resolution,
    SLAClock,
)
from backend.app.schemas.reopen import ComplaintReopen
from backend.generator.generate_workflow import SLA_TARGETS


def get_current_time():
    """Return UTC time as a naive datetime for SQLite compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_sla_id(db: Session, complaint_id: str) -> str:
    """Generate a unique SLA clock ID for each complaint cycle."""
    existing_count = (
        db.query(SLAClock)
        .filter(SLAClock.complaint_id == complaint_id)
        .count()
    )

    cycle_number = existing_count + 1

    if cycle_number == 1:
        return f"SLA-{complaint_id}"

    return f"SLA-{complaint_id}-{cycle_number:03d}"


def reopen_complaint(
    db: Session,
    complaint_id: str,
    payload: ComplaintReopen,
) -> Complaint:
    """
    Reopen a resolved complaint.

    The previous resolution and SLA clock remain in the database.
    A new SLA clock is created for the reopened cycle.
    """

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

        if complaint.status != "RESOLVED":
            raise HTTPException(
                status_code=409,
                detail="Only resolved complaints can be reopened.",
            )

        previous_resolution = (
            db.query(Resolution)
            .filter(Resolution.complaint_id == complaint_id)
            .order_by(Resolution.resolved_at.desc())
            .first()
        )

        if not previous_resolution:
            raise HTTPException(
                status_code=409,
                detail="No previous resolution record was found.",
            )

        if not previous_resolution.is_final:
            raise HTTPException(
                status_code=409,
                detail="The latest resolution is already non-final.",
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

        now = get_current_time()
        old_status = complaint.status

        # Preserve the previous resolution as historical.
        previous_resolution.is_final = False

        # Create a fresh SLA cycle using the complaint's current priority.
        sla_target = SLA_TARGETS.get(complaint.priority)

        if not sla_target:
            raise HTTPException(
                status_code=409,
                detail="No SLA configuration exists for this priority.",
            )

        new_sla = SLAClock(
            sla_id=generate_sla_id(db, complaint_id),
            complaint_id=complaint_id,
            priority=complaint.priority,
            response_deadline=(
                now + timedelta(
                    minutes=sla_target["response_minutes"]
                )
            ),
            resolution_deadline=(
                now + timedelta(
                    hours=sla_target["resolution_hours"]
                )
            ),
            first_response_at=None,
            resolved_at=None,
            paused_at=None,
            total_paused_seconds=0,
            response_breached=False,
            resolution_breached=False,
        )

        db.add(new_sla)

        complaint.status = "IN_PROGRESS"
        complaint.updated_at = now

        # Preserve why the complaint was reopened.
        event = ComplaintEvent(
            complaint_id=complaint_id,
            event_type="COMPLAINT_REOPENED",
            old_value=old_status,
            new_value="IN_PROGRESS",
            description=payload.reason,
            performed_by=payload.performed_by,
        )

        db.add(event)

        db.commit()
        db.refresh(complaint)

        return complaint

    except Exception:
        db.rollback()
        raise