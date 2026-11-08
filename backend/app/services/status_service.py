from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models import Complaint, ComplaintEvent, SLAClock


ALLOWED_TRANSITIONS = {
    "ASSIGNED": {"IN_PROGRESS"},
    "IN_PROGRESS": {"PENDING_CUSTOMER"},
    "PENDING_CUSTOMER": {"IN_PROGRESS"},
    "RESOLVED": {"CLOSED"},
    "CLOSED": set(),
}


def get_current_time():
    """
    Return UTC time as a naive datetime.

    SQLite does not reliably preserve timezone information,
    so this keeps datetime arithmetic consistent with stored values.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def transition_complaint_status(
    db: Session,
    complaint_id: str,
    new_status: str,
    performed_by: str,
) -> Complaint:
    """
    Validate and apply a complaint status transition.

    Every successful transition is recorded as a ComplaintEvent.
    Resolution and reopening are handled separately.
    """

    new_status = new_status.strip().upper()
    performed_by = performed_by.strip()

    if not performed_by:
        raise HTTPException(
            status_code=422,
            detail="The person performing the transition is required.",
        )

    if new_status not in ALLOWED_TRANSITIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported complaint status: {new_status}.",
        )

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

        current_status = complaint.status

        allowed_next_statuses = ALLOWED_TRANSITIONS.get(
            current_status,
            set(),
        )

        if new_status not in allowed_next_statuses:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Transition from {current_status} "
                    f"to {new_status} is not allowed."
                ),
            )

        now = get_current_time()

        # Get the most recent SLA clock for this complaint.
        sla_clock = (
            db.query(SLAClock)
            .filter(SLAClock.complaint_id == complaint_id)
            .order_by(SLAClock.created_at.desc())
            .first()
        )

        # Pause the resolution SLA when waiting for the customer.
        if new_status == "PENDING_CUSTOMER":
            if not sla_clock:
                raise HTTPException(
                    status_code=409,
                    detail="No SLA clock exists for this complaint.",
                )

            if sla_clock.paused_at is not None:
                raise HTTPException(
                    status_code=409,
                    detail="The resolution SLA is already paused.",
                )

            sla_clock.paused_at = now

        # Resume the resolution SLA when the customer responds.
        elif (
            current_status == "PENDING_CUSTOMER"
            and new_status == "IN_PROGRESS"
        ):
            if not sla_clock:
                raise HTTPException(
                    status_code=409,
                    detail="No SLA clock exists for this complaint.",
                )

            if sla_clock.paused_at is None:
                raise HTTPException(
                    status_code=409,
                    detail="The resolution SLA is not currently paused.",
                )

            paused_seconds = max(
                0,
                int((now - sla_clock.paused_at).total_seconds()),
            )

            sla_clock.total_paused_seconds += paused_seconds

            sla_clock.resolution_deadline += timedelta(
                seconds=paused_seconds
            )

            sla_clock.paused_at = None

        # Update the current status.
        complaint.status = new_status
        complaint.updated_at = now

        # Preserve the transition in the event history.
        event = ComplaintEvent(
            complaint_id=complaint_id,
            event_type="STATUS_CHANGED",
            old_value=current_status,
            new_value=new_status,
            description=(
                f"Complaint status changed from "
                f"{current_status} to {new_status}."
            ),
            performed_by=performed_by,
        )

        db.add(event)
        db.commit()
        db.refresh(complaint)

        return complaint

    except Exception:
        db.rollback()
        raise