import shutil
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.app.models import Complaint, ComplaintEvent, SLAClock
from backend.app.services.status_service import transition_complaint_status


SOURCE_DB = Path("complaints.db")
TEST_DB = Path("complaints_status_test.db")


if not SOURCE_DB.exists():
    raise FileNotFoundError("Original complaints.db was not found.")

shutil.copy2(SOURCE_DB, TEST_DB)

engine = create_engine(
    f"sqlite:///{TEST_DB.as_posix()}",
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def enable_foreign_keys(connection, record):
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSession = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


try:
    db = TestSession()

    try:
        # Find an assigned complaint with an SLA clock.
        complaint = (
            db.query(Complaint)
            .join(
                SLAClock,
                Complaint.complaint_id == SLAClock.complaint_id,
            )
            .filter(Complaint.status == "ASSIGNED")
            .first()
        )

        if not complaint:
            raise RuntimeError(
                "No ASSIGNED complaint with an SLA clock was found."
            )

        complaint_id = complaint.complaint_id

        print(f"Testing complaint: {complaint_id}")

        # Test 1: ASSIGNED -> IN_PROGRESS
        print("\nTest 1: Starting complaint...")

        result = transition_complaint_status(
            db,
            complaint_id,
            "IN_PROGRESS",
            "TEST_AGENT",
        )

        assert result.status == "IN_PROGRESS"
        print("PASSED: Complaint moved to IN_PROGRESS.")

        # Test 2: IN_PROGRESS -> PENDING_CUSTOMER
        print("\nTest 2: Pausing resolution SLA...")

        result = transition_complaint_status(
            db,
            complaint_id,
            "PENDING_CUSTOMER",
            "TEST_AGENT",
        )

        sla = (
            db.query(SLAClock)
            .filter(SLAClock.complaint_id == complaint_id)
            .order_by(SLAClock.created_at.desc())
            .first()
        )

        assert result.status == "PENDING_CUSTOMER"
        assert sla.paused_at is not None

        print("PASSED: Resolution SLA paused.")

        # Test 3: PENDING_CUSTOMER -> IN_PROGRESS
        print("\nTest 3: Resuming resolution SLA...")

        previous_deadline = sla.resolution_deadline

        result = transition_complaint_status(
            db,
            complaint_id,
            "IN_PROGRESS",
            "TEST_AGENT",
        )

        db.refresh(sla)

        assert result.status == "IN_PROGRESS"
        assert sla.paused_at is None
        assert sla.total_paused_seconds >= 0
        assert sla.resolution_deadline >= previous_deadline

        print("PASSED: Resolution SLA resumed.")
        print(f"Total paused seconds: {sla.total_paused_seconds}")

        # Test 4: Reject an invalid transition.
        print("\nTest 4: Rejecting an invalid transition...")

        try:
            transition_complaint_status(
                db,
                complaint_id,
                "CLOSED",
                "TEST_AGENT",
            )
            raise AssertionError("Invalid transition was accepted.")

        except HTTPException as error:
            assert error.status_code == 409
            print("PASSED: Invalid transition rejected with HTTP 409.")

        # Test 5: Verify event history.
        print("\nTest 5: Checking event history...")

        events = (
            db.query(ComplaintEvent)
            .filter(
                ComplaintEvent.complaint_id == complaint_id,
                ComplaintEvent.performed_by == "TEST_AGENT",
            )
            .order_by(ComplaintEvent.event_id.asc())
            .all()
        )

        transitions = [
            (event.old_value, event.new_value)
            for event in events
        ]

        expected = [
            ("ASSIGNED", "IN_PROGRESS"),
            ("IN_PROGRESS", "PENDING_CUSTOMER"),
            ("PENDING_CUSTOMER", "IN_PROGRESS"),
        ]

        assert transitions == expected

        print("PASSED: All three status transitions were recorded.")
        print("\nALL STATUS WORKFLOW TESTS PASSED")

    finally:
        db.close()

finally:
    engine.dispose()

    if TEST_DB.exists():
        TEST_DB.unlink()

    print("Temporary status test database removed.")