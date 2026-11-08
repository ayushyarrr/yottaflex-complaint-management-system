
from datetime import timedelta, timezone

from sqlalchemy.exc import SQLAlchemyError

from backend.app.database import SessionLocal
from backend.app.models import (
    Assignment,
    Category,
    Complaint,
    ComplaintEvent,
    ComplaintMessage,
    Resolution,
    SLAClock,
    Survey,
)
from backend.generator.lifecycle_config import get_status_distribution


RESOLUTION_TYPES = {
    "REFUND": "REFUND",
    "PAYMENT": "PAYMENT_CORRECTION",
    "DELIVERY": "DELIVERY_CORRECTION",
    "MISSING ITEM": "REPLACEMENT",
    "DAMAGED PRODUCT": "REPLACEMENT",
    "PRODUCT SAFETY": "SAFETY_ESCALATION",
    "CANCELLATION": "CANCELLATION",
    "WARRANTY": "REPAIR_OR_REPLACEMENT",
    "ACCOUNT": "ACCOUNT_ASSISTANCE",
    "OTHER": "GENERAL_ASSISTANCE",
}

RESOLUTION_DESCRIPTIONS = {
    "REFUND": (
        "The refund request was reviewed and the appropriate "
        "refund action was recorded."
    ),
    "PAYMENT_CORRECTION": (
        "The payment discrepancy was reviewed and corrective "
        "action was recorded."
    ),
    "DELIVERY_CORRECTION": (
        "The delivery issue was investigated and corrective "
        "action was recorded."
    ),
    "REPLACEMENT": (
        "The product issue was reviewed and a replacement "
        "action was recorded."
    ),
    "SAFETY_ESCALATION": (
        "The safety complaint was reviewed and escalated "
        "through the safety response process."
    ),
    "CANCELLATION": (
        "The cancellation request was reviewed and processed."
    ),
    "REPAIR_OR_REPLACEMENT": (
        "The warranty request was reviewed and a repair or "
        "replacement action was recorded."
    ),
    "ACCOUNT_ASSISTANCE": (
        "The account issue was reviewed and assistance was provided."
    ),
    "GENERAL_ASSISTANCE": (
        "The complaint was reviewed and an appropriate "
        "response was recorded."
    ),
}


def normalize_datetime(value):
    """Normalize datetimes to UTC without timezone information."""

    if value is None:
        return None

    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    return value


def add_event(
    db,
    complaint_id,
    event_type,
    old_value,
    new_value,
    description,
    performed_by,
    created_at,
):
    """Append an immutable workflow event."""

    db.add(
        ComplaintEvent(
            complaint_id=complaint_id,
            event_type=event_type,
            old_value=old_value,
            new_value=new_value,
            description=description,
            performed_by=performed_by,
            created_at=created_at,
        )
    )


def configure_agent_message(
    db,
    complaint_id,
    response_time=None,
):
    """
    Configure the generated agent message to match the simulated
    lifecycle.

    If no response_time is supplied, retain it as an internal note.
    Otherwise, make it customer-visible at the specified timestamp.
    """

    messages = (
        db.query(ComplaintMessage)
        .filter(
            ComplaintMessage.complaint_id == complaint_id,
            ComplaintMessage.sender_type == "AGENT",
        )
        .order_by(
            ComplaintMessage.created_at.asc(),
            ComplaintMessage.message_id.asc(),
        )
        .all()
    )

    if not messages:
        raise ValueError(
            f"No generated agent message found for {complaint_id}."
        )

    # Keep all generated agent messages internal initially.
    for message in messages:
        message.is_internal = True

    if response_time is not None:
        first_message = messages[0]
        first_message.is_internal = False
        first_message.created_at = response_time


def generate_lifecycle():
    db = SessionLocal()

    try:
        complaints = (
            db.query(Complaint)
            .order_by(Complaint.complaint_id)
            .all()
        )

        if not complaints:
            raise ValueError(
                "No complaints found. Generate complaints first."
            )

        planned_statuses = get_status_distribution(len(complaints))

        if len(planned_statuses) != len(complaints):
            raise ValueError(
                "Lifecycle distribution does not match complaint count."
            )

        existing_counts = {
            "events": db.query(ComplaintEvent).count(),
            "resolutions": db.query(Resolution).count(),
            "surveys": db.query(Survey).count(),
        }

        if any(existing_counts.values()):
            print("Lifecycle records already exist.")
            print("No records were changed or added.")
            print(existing_counts)
            return

        if any(complaint.status != "NEW" for complaint in complaints):
            raise ValueError(
                "Expected every complaint to have NEW status "
                "before lifecycle simulation."
            )

        # Determine the expected assignment count from the lifecycle plan.
        expected_assignments = sum(
            status != "NEW" for status in planned_statuses
        )

        assignment_records = (
            db.query(Assignment)
            .filter(Assignment.is_current.is_(True))
            .all()
        )

        assignments = {
            item.complaint_id: item
            for item in assignment_records
        }

        if len(assignment_records) != expected_assignments:
            raise ValueError(
                f"Expected {expected_assignments} current assignments, "
                f"found {len(assignment_records)}."
            )

        if len(assignments) != len(assignment_records):
            raise ValueError(
                "Multiple current assignments found for a complaint."
            )

        sla_records = db.query(SLAClock).all()

        sla_clocks = {
            item.complaint_id: item
            for item in sla_records
        }

        if len(sla_records) != len(complaints):
            raise ValueError(
                f"Expected {len(complaints)} SLA clocks, "
                f"found {len(sla_records)}."
            )

        if len(sla_clocks) != len(sla_records):
            raise ValueError(
                "Multiple SLA clocks found for a complaint."
            )

        categories = {
            category.category_id: category.category_name.upper()
            for category in db.query(Category).all()
        }

        counts = {
            "NEW": 0,
            "ASSIGNED": 0,
            "IN_PROGRESS": 0,
            "PENDING_CUSTOMER": 0,
            "RESOLVED": 0,
            "CLOSED": 0,
        }

        event_count = 0
        resolution_count = 0
        survey_count = 0
        public_responses = 0

        for index, complaint in enumerate(complaints):
            final_status = planned_statuses[index]
            counts[final_status] += 1

            if complaint.created_at is None:
                raise ValueError(
                    f"Missing creation timestamp for "
                    f"{complaint.complaint_id}."
                )

            created_time = normalize_datetime(complaint.created_at)

            sla = sla_clocks.get(complaint.complaint_id)

            if sla is None:
                raise ValueError(
                    f"Missing SLA clock for {complaint.complaint_id}."
                )

            # Record complaint creation in the audit history.
            add_event(
                db,
                complaint.complaint_id,
                "COMPLAINT_CREATED",
                None,
                "NEW",
                "Complaint was registered in the complaint management system.",
                "SYSTEM",
                created_time,
            )
            event_count += 1

            # NEW complaints remain unassigned.
            if final_status == "NEW":
                if complaint.complaint_id in assignments:
                    raise ValueError(
                        f"NEW complaint has an assignment: "
                        f"{complaint.complaint_id}"
                    )

                configure_agent_message(
                    db,
                    complaint.complaint_id,
                )

                complaint.status = "NEW"
                complaint.updated_at = created_time

                sla.first_response_at = None
                sla.resolved_at = None
                sla.paused_at = None
                sla.total_paused_seconds = 0
                sla.response_breached = False
                sla.resolution_breached = False

                continue

            assignment = assignments.get(complaint.complaint_id)

            if assignment is None:
                raise ValueError(
                    f"Missing assignment for {complaint.complaint_id}."
                )

            if assignment.agent_id is None:
                raise ValueError(
                    f"Missing assigned agent for "
                    f"{complaint.complaint_id}."
                )

            if assignment.assigned_at is None:
                raise ValueError(
                    f"Missing assignment timestamp for "
                    f"{complaint.complaint_id}."
                )

            assigned_time = normalize_datetime(
                assignment.assigned_at
            )

            if assigned_time < created_time:
                raise ValueError(
                    f"Assignment precedes complaint creation: "
                    f"{complaint.complaint_id}"
                )

            category_name = categories.get(complaint.category_id)

            if category_name is None:
                raise ValueError(
                    f"Category not found for {complaint.complaint_id}."
                )

            agent_actor = f"AGENT-{assignment.agent_id}"

            # Every non-NEW complaint receives an assignment event.
            add_event(
                db,
                complaint.complaint_id,
                "STATUS_CHANGED",
                "NEW",
                "ASSIGNED",
                "Complaint assigned to its responsible team and agent.",
                "SYSTEM",
                assigned_time,
            )
            event_count += 1

            # ASSIGNED means work has not started and no public
            # agent response has been sent yet.
            if final_status == "ASSIGNED":
                configure_agent_message(
                    db,
                    complaint.complaint_id,
                )

                complaint.status = "ASSIGNED"
                complaint.updated_at = assigned_time

                sla.first_response_at = None
                sla.resolved_at = None
                sla.paused_at = None
                sla.total_paused_seconds = 0
                sla.response_breached = False
                sla.resolution_breached = False

                continue

            # Simulate a first response five minutes after assignment.
            response_time = assigned_time + timedelta(minutes=5)

            configure_agent_message(
                db,
                complaint.complaint_id,
                response_time=response_time,
            )

            add_event(
                db,
                complaint.complaint_id,
                "FIRST_RESPONSE",
                None,
                "RESPONDED",
                "An agent sent the first response to the customer.",
                agent_actor,
                response_time,
            )
            event_count += 1
            public_responses += 1

            sla.first_response_at = response_time
            sla.response_breached = (
                response_time > normalize_datetime(sla.response_deadline)
            )

            # Simulate the agent starting work ten minutes after assignment.
            in_progress_time = assigned_time + timedelta(minutes=10)

            add_event(
                db,
                complaint.complaint_id,
                "STATUS_CHANGED",
                "ASSIGNED",
                "IN_PROGRESS",
                "Agent started investigating the complaint.",
                agent_actor,
                in_progress_time,
            )
            event_count += 1

            if final_status == "IN_PROGRESS":
                complaint.status = "IN_PROGRESS"
                complaint.updated_at = in_progress_time

                sla.resolved_at = None
                sla.paused_at = None
                sla.total_paused_seconds = 0
                sla.resolution_breached = False

                continue

            if final_status == "PENDING_CUSTOMER":
                pending_time = assigned_time + timedelta(minutes=30)

                add_event(
                    db,
                    complaint.complaint_id,
                    "STATUS_CHANGED",
                    "IN_PROGRESS",
                    "PENDING_CUSTOMER",
                    "Further information is required from the customer.",
                    agent_actor,
                    pending_time,
                )
                event_count += 1

                complaint.status = "PENDING_CUSTOMER"
                complaint.updated_at = pending_time

                # Resolution SLA pauses while waiting for the customer.
                # Response SLA is not paused.
                sla.paused_at = pending_time
                sla.resolved_at = None
                sla.total_paused_seconds = 0
                sla.resolution_breached = False

                continue

            if final_status not in ("RESOLVED", "CLOSED"):
                raise ValueError(
                    f"Unsupported lifecycle status: {final_status}"
                )

            # Simulate resolution one hour after assignment.
            resolved_time = assigned_time + timedelta(minutes=60)

            resolution_type = RESOLUTION_TYPES.get(
                category_name,
                "GENERAL_ASSISTANCE",
            )

            resolution_id = f"RES-{complaint.complaint_id}"

            add_event(
                db,
                complaint.complaint_id,
                "STATUS_CHANGED",
                "IN_PROGRESS",
                "RESOLVED",
                "The complaint has been resolved.",
                agent_actor,
                resolved_time,
            )
            event_count += 1

            resolution = Resolution(
                resolution_id=resolution_id,
                complaint_id=complaint.complaint_id,
                resolution_type=resolution_type,
                resolution_description=RESOLUTION_DESCRIPTIONS[
                    resolution_type
                ],
                resolved_by=assignment.agent_id,
                resolved_at=resolved_time,
                is_final=True,
            )

            db.add(resolution)
            resolution_count += 1

            sla.resolved_at = resolved_time
            sla.paused_at = None
            sla.total_paused_seconds = 0
            sla.resolution_breached = (
                resolved_time
                > normalize_datetime(sla.resolution_deadline)
            )

            complaint.status = "RESOLVED"
            complaint.updated_at = resolved_time

            if final_status == "RESOLVED":
                continue

            # CLOSED complaints receive a closure event after resolution.
            closed_time = resolved_time + timedelta(minutes=10)

            add_event(
                db,
                complaint.complaint_id,
                "STATUS_CHANGED",
                "RESOLVED",
                "CLOSED",
                "The resolved complaint was formally closed.",
                "SYSTEM",
                closed_time,
            )
            event_count += 1

            complaint.status = "CLOSED"
            complaint.updated_at = closed_time

            # Create a survey for every second CLOSED complaint.
            # Surveys are always submitted after closure.
            if index % 2 == 0:
                rating = 5 if index % 4 == 0 else 4

                db.add(
                    Survey(
                        resolution_id=resolution_id,
                        complaint_id=complaint.complaint_id,
                        rating=rating,
                        feedback=(
                            "The issue was handled satisfactorily."
                            if rating == 5
                            else (
                                "The issue was resolved and "
                                "communication was helpful."
                            )
                        ),
                        submitted_at=closed_time + timedelta(minutes=15),
                    )
                )
                survey_count += 1

                add_event(
                    db,
                    complaint.complaint_id,
                    "SURVEY_SUBMITTED",
                    None,
                    "SUBMITTED",
                    "The customer submitted a post-resolution survey.",
                    "CUSTOMER",
                    closed_time + timedelta(minutes=15),
                )
                event_count += 1

        db.commit()

        print("\nLifecycle generation completed successfully.")
        print(f"Complaints processed: {len(complaints)}")

        print("\nFinal status distribution:")

        for status, count in counts.items():
            print(f"{status}: {count}")

        print("\nGenerated workflow records:")
        print(f"Lifecycle events: {event_count}")
        print(f"Resolution records: {resolution_count}")
        print(f"Survey records: {survey_count}")
        print(f"Customer-visible agent responses: {public_responses}")

        print("\nAssignment and SLA totals:")
        print(f"Current assignments: {len(assignments)}")
        print(f"SLA clocks: {len(sla_clocks)}")

    except (SQLAlchemyError, ValueError):
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    generate_lifecycle()
