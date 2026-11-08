
import sys
from datetime import timezone

from backend.app.database import SessionLocal
from backend.app.models import (
    Complaint,
    ComplaintEvent,
    ComplaintMessage,
    SLAClock,
)


MANUAL_TEST_COMPLAINTS = {
    "CMP-2026-000002",
}


def normalize_datetime(value):
    if value is None:
        return None

    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    return value


def find_repair_candidates(db):
    clocks = (
        db.query(SLAClock)
        .order_by(
            SLAClock.complaint_id,
            SLAClock.created_at,
            SLAClock.sla_id,
        )
        .all()
    )

    complaints = {
        complaint.complaint_id: complaint
        for complaint in db.query(Complaint).all()
    }

    clocks_by_complaint = {}

    for clock in clocks:
        clocks_by_complaint.setdefault(
            clock.complaint_id, []
        ).append(clock)

    candidates = []

    for complaint_id, complaint_clocks in clocks_by_complaint.items():

        if complaint_id in MANUAL_TEST_COMPLAINTS:
            continue

        complaint = complaints.get(complaint_id)

        if complaint is None:
            continue

        reopen_events = (
            db.query(ComplaintEvent)
            .filter(
                ComplaintEvent.complaint_id == complaint_id,
                ComplaintEvent.event_type == "COMPLAINT_REOPENED",
            )
            .order_by(ComplaintEvent.created_at.asc())
            .all()
        )

        messages = (
            db.query(ComplaintMessage)
            .filter(
                ComplaintMessage.complaint_id == complaint_id,
                ComplaintMessage.sender_type == "AGENT",
                ComplaintMessage.is_internal.is_(False),
            )
            .order_by(
                ComplaintMessage.created_at.asc(),
                ComplaintMessage.message_id.asc(),
            )
            .all()
        )

        for index, clock in enumerate(complaint_clocks):

            # Never overwrite an existing response timestamp.
            if clock.first_response_at is not None:
                continue

            if index == 0:
                cycle_start = normalize_datetime(
                    complaint.created_at
                )
            else:
                reopen_index = index - 1

                if reopen_index < len(reopen_events):
                    cycle_start = normalize_datetime(
                        reopen_events[reopen_index].created_at
                    )
                else:
                    cycle_start = normalize_datetime(
                        clock.created_at
                    )

            cycle_end = None

            if index + 1 < len(complaint_clocks):
                next_reopen_index = index

                if next_reopen_index < len(reopen_events):
                    cycle_end = normalize_datetime(
                        reopen_events[next_reopen_index].created_at
                    )
                else:
                    cycle_end = normalize_datetime(
                        complaint_clocks[index + 1].created_at
                    )

            candidate = None

            for message in messages:
                message_time = normalize_datetime(
                    message.created_at
                )

                if message_time is None or cycle_start is None:
                    continue

                if message_time < cycle_start:
                    continue

                if cycle_end is not None and message_time >= cycle_end:
                    continue

                candidate = message
                break

            if candidate is None:
                continue

            response_time = normalize_datetime(
                candidate.created_at
            )

            deadline = normalize_datetime(
                clock.response_deadline
            )

            candidates.append({
                "clock": clock,
                "message": candidate,
                "response_time": response_time,
                "response_breached": response_time > deadline,
            })

    return candidates


def repair_sla_responses(apply_changes=False):
    db = SessionLocal()

    try:
        candidates = find_repair_candidates(db)

        print("\nSLA FIRST-RESPONSE REPAIR")
        print("=" * 65)
        print("Mode:", "APPLY CHANGES" if apply_changes else "PREVIEW ONLY")
        print("Repair candidates:", len(candidates))

        if not candidates:
            print("\nNo eligible records found.")
            return

        for item in candidates:
            clock = item["clock"]
            message = item["message"]

            print("\nComplaint:", clock.complaint_id)
            print("SLA:", clock.sla_id)
            print("Message:", message.message_id)
            print("Response timestamp:", item["response_time"])
            print("Response deadline:", clock.response_deadline)
            print("Response breached:", item["response_breached"])

        if not apply_changes:
            print("\nPREVIEW COMPLETE.")
            print("No database records were changed.")
            print("Review the candidates before applying the repair.")
            return

        updated = 0

        for item in candidates:
            clock = item["clock"]
            message = item["message"]

            # Recheck before modifying to avoid overwriting
            # a timestamp that may have been recorded meanwhile.
            if clock.first_response_at is not None:
                continue

            clock.first_response_at = item["response_time"]
            clock.response_breached = item["response_breached"]

            db.add(
                ComplaintEvent(
                    complaint_id=clock.complaint_id,
                    event_type="HISTORICAL_FIRST_RESPONSE_RECOVERED",
                    old_value=None,
                    new_value=message.message_id,
                    description=(
                        "Historical first-response timestamp recovered "
                        "from an existing customer-visible agent message. "
                        f"Response was "
                        f"{'late' if item['response_breached'] else 'within SLA'}."
                    ),
                    performed_by="SYSTEM",
                )
            )

            updated += 1

        db.commit()

        print("\nREPAIR COMPLETED SUCCESSFULLY.")
        print("SLA clocks updated:", updated)
        print("Historical audit events created:", updated)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    apply_changes = "--apply" in sys.argv
    repair_sla_responses(apply_changes)
