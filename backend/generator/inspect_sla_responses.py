
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
        from datetime import timezone
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    return value


def inspect_sla_responses():
    db = SessionLocal()

    try:
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

        missing_count = 0
        repair_candidates = []
        skipped_manual_tests = 0

        print("\nSLA RESPONSE INSPECTION — CYCLE-AWARE")
        print("=" * 70)

        clocks_by_complaint = {}

        for clock in clocks:
            clocks_by_complaint.setdefault(
                clock.complaint_id, []
            ).append(clock)

        for complaint_id, complaint_clocks in clocks_by_complaint.items():

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

                if clock.first_response_at is not None:
                    continue

                missing_count += 1

                if complaint_id in MANUAL_TEST_COMPLAINTS:
                    skipped_manual_tests += 1
                    continue

                # First cycle begins when the complaint was created.
                if index == 0:
                    cycle_start = normalize_datetime(
                        complaint.created_at
                    )
                else:
                    # Later cycles begin at their corresponding
                    # complaint-reopened event.
                    reopen_index = index - 1

                    if reopen_index < len(reopen_events):
                        cycle_start = normalize_datetime(
                            reopen_events[reopen_index].created_at
                        )
                    else:
                        # Fallback if a historical reopen event
                        # is missing.
                        cycle_start = normalize_datetime(
                            clock.created_at
                        )

                # The next SLA cycle marks the end of this cycle.
                cycle_end = None

                if index + 1 < len(complaint_clocks):
                    next_clock = complaint_clocks[index + 1]

                    next_reopen_index = index

                    if next_reopen_index < len(reopen_events):
                        cycle_end = normalize_datetime(
                            reopen_events[next_reopen_index].created_at
                        )
                    else:
                        cycle_end = normalize_datetime(
                            next_clock.created_at
                        )

                # Find an agent message inside this SLA cycle.
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

                would_be_late = response_time > deadline

                repair_candidates.append(
                    (clock, candidate, would_be_late)
                )

        print(f"Total SLA clocks: {len(clocks)}")
        print(f"Missing first-response timestamps: {missing_count}")
        print(f"Potential repair candidates: {len(repair_candidates)}")
        print(f"Manual test clocks skipped: {skipped_manual_tests}")

        for clock, message, would_be_late in repair_candidates:
            print("\nComplaint:", clock.complaint_id)
            print("SLA ID:", clock.sla_id)
            print("Response deadline:", clock.response_deadline)
            print("Candidate message:", message.message_id)
            print("Candidate timestamp:", message.created_at)
            print("Would be late:", would_be_late)

        print("\nInspection complete.")
        print("No database records were changed.")

    finally:
        db.close()


if __name__ == "__main__":
    inspect_sla_responses()
