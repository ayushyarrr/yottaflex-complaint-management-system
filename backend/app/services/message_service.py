
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models import (
    Agent,
    Assignment,
    Complaint,
    ComplaintEvent,
    ComplaintMessage,
    SLAClock,
)
from backend.app.schemas.message import ComplaintMessageCreate


def get_current_time():
    """Return current UTC time in SQLite-compatible format."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_message_id(db: Session, complaint_id: str) -> str:
    existing_ids = {
        message_id
        for (message_id,) in (
            db.query(ComplaintMessage.message_id)
            .filter(ComplaintMessage.complaint_id == complaint_id)
            .all()
        )
    }

    number = 1
    while True:
        candidate = f"MSG-{complaint_id}-{number:03d}"
        if candidate not in existing_ids:
            return candidate
        number += 1


def add_complaint_message(
    db: Session,
    complaint_id: str,
    payload: ComplaintMessageCreate,
):
    try:
        complaint = (
            db.query(Complaint)
            .filter(Complaint.complaint_id == complaint_id)
            .first()
        )

        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found.")

        if payload.sender_type == "SYSTEM":
            raise HTTPException(
                status_code=403,
                detail="System messages cannot be submitted through this endpoint.",
            )

        if payload.sender_type == "CUSTOMER" and payload.is_internal:
            raise HTTPException(
                status_code=422,
                detail="Customer messages cannot be marked as internal.",
            )

        if payload.sender_type == "AGENT":
            assignment = (
                db.query(Assignment)
                .filter(
                    Assignment.complaint_id == complaint_id,
                    Assignment.is_current.is_(True),
                )
                .first()
            )

            if not assignment:
                raise HTTPException(
                    status_code=409,
                    detail="No agent is currently assigned to this complaint.",
                )

            agent = (
                db.query(Agent)
                .filter(
                    Agent.agent_id == assignment.agent_id,
                    Agent.is_active.is_(True),
                )
                .first()
            )

            if not agent:
                raise HTTPException(
                    status_code=409,
                    detail="The assigned agent is not active.",
                )

        message_id = generate_message_id(db, complaint_id)
        current_time = get_current_time()

        message = ComplaintMessage(
            message_id=message_id,
            complaint_id=complaint_id,
            sender_type=payload.sender_type,
            message_text=payload.message_text,
            channel=payload.channel,
            is_internal=payload.is_internal,
            created_at=current_time,
        )

        db.add(message)

        if payload.sender_type == "AGENT" and not payload.is_internal:
            sla_clock = (
                db.query(SLAClock)
                .filter(SLAClock.complaint_id == complaint_id)
                .order_by(
                    SLAClock.created_at.desc(),
                    SLAClock.sla_id.desc(),
                )
                .first()
            )

            if sla_clock and sla_clock.first_response_at is None:
                deadline = sla_clock.response_deadline

                if deadline.tzinfo is not None:
                    deadline = deadline.astimezone(timezone.utc).replace(
                        tzinfo=None
                    )

                sla_clock.first_response_at = current_time
                sla_clock.response_breached = current_time > deadline

                db.add(
                    ComplaintEvent(
                        complaint_id=complaint_id,
                        event_type="FIRST_RESPONSE",
                        old_value=None,
                        new_value=message_id,
                        description=(
                            "First customer-visible agent response recorded. "
                            f"Response was "
                            f"{'late' if sla_clock.response_breached else 'within SLA'}."
                        ),
                        performed_by="AGENT",
                    )
                )

        db.add(
            ComplaintEvent(
                complaint_id=complaint_id,
                event_type="MESSAGE_ADDED",
                old_value=None,
                new_value=message_id,
                description=(
                    f"{payload.sender_type} added a "
                    f"{'internal note' if payload.is_internal else 'message'} "
                    f"through {payload.channel}."
                ),
                performed_by=payload.sender_type,
            )
        )

        db.commit()
        db.refresh(message)

        return message

    except Exception:
        db.rollback()
        raise
