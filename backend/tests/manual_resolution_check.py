import shutil
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.app.models import (
    Agent,
    Assignment,
    Complaint,
    Resolution,
    SLAClock,
)
from backend.app.schemas.resolution import ResolutionCreate
from backend.app.services.resolution_service import resolve_complaint
from backend.app.services.status_service import transition_complaint_status


SOURCE_DB = Path("complaints.db")
TEST_DB = Path("complaints_resolution_test.db")

if not SOURCE_DB.exists():
    raise FileNotFoundError("Original complaints.db was not found.")

if TEST_DB.exists():
    TEST_DB.unlink()

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
        complaint = (
            db.query(Complaint)
            .join(
                Assignment,
                Complaint.complaint_id == Assignment.complaint_id,
            )
            .join(
                SLAClock,
                Complaint.complaint_id == SLAClock.complaint_id,
            )
            .filter(
                Complaint.status == "ASSIGNED",
                Assignment.is_current.is_(True),
            )
            .first()
        )

        if not complaint:
            raise RuntimeError(
                "No suitable ASSIGNED complaint was found."
            )

        complaint_id = complaint.complaint_id

        assignment = (
            db.query(Assignment)
            .filter(
                Assignment.complaint_id == complaint_id,
                Assignment.is_current.is_(True),
            )
            .first()
        )

        agent = (
            db.query(Agent)
            .filter(Agent.agent_id == assignment.agent_id)
            .first()
        )

        agent_id = agent.agent_id
        agent_name = agent.agent_name

        print(f"Testing complaint: {complaint_id}")
        print(f"Assigned agent: {agent_name} (ID: {agent_id})")

    finally:
        db.close()

    # Step 1: Move the complaint to IN_PROGRESS.
    print("\nTest 1: Starting complaint...")

    db = TestSession()

    try:
        result = transition_complaint_status(
            db=db,
            complaint_id=complaint_id,
            new_status="IN_PROGRESS",
            performed_by=agent_name,
        )

        assert result.status == "IN_PROGRESS"
        print("PASSED: Complaint moved to IN_PROGRESS.")

    finally:
        db.close()

    # Step 2: Resolve the complaint.
    print("\nTest 2: Resolving complaint...")

    db = TestSession()

    try:
        payload = ResolutionCreate(
            resolution_type="REFUND",
            resolution_description=(
                "The refund was processed successfully "
                "and the customer was notified."
            ),
            resolved_by=agent_id,
        )

        resolution = resolve_complaint(
            db=db,
            complaint_id=complaint_id,
            payload=payload,
        )

        resolution_id = resolution.resolution_id

        assert resolution_id == f"RES-{complaint_id}"
        assert resolution.is_final is True

        print("PASSED: Resolution record created.")
        print("Resolution ID:", resolution_id)

    finally:
        db.close()

    # Step 3: Verify complaint status and SLA.
    print("\nTest 3: Verifying complaint and SLA...")

    db = TestSession()

    try:
        complaint = (
            db.query(Complaint)
            .filter(Complaint.complaint_id == complaint_id)
            .first()
        )

        sla = (
            db.query(SLAClock)
            .filter(SLAClock.complaint_id == complaint_id)
            .order_by(SLAClock.created_at.desc())
            .first()
        )

        assert complaint.status == "RESOLVED"
        assert sla.resolved_at is not None

        print("PASSED: Complaint status is RESOLVED.")
        print("PASSED: SLA resolution timestamp recorded.")

    finally:
        db.close()

    # Step 4: Reject resolving the same complaint again.
    print("\nTest 4: Rejecting duplicate resolution...")

    db = TestSession()

    try:
        try:
            resolve_complaint(
                db=db,
                complaint_id=complaint_id,
                payload=ResolutionCreate(
                    resolution_type="REPAIR",
                    resolution_description=(
                        "Attempting a second resolution "
                        "without reopening the complaint."
                    ),
                    resolved_by=agent_id,
                ),
            )

            raise AssertionError(
                "Duplicate resolution was unexpectedly accepted."
            )

        except HTTPException as error:
            assert error.status_code == 409
            print("PASSED: Duplicate resolution rejected.")

    finally:
        db.close()

    print("\nALL RESOLUTION SERVICE TESTS PASSED")

finally:
    engine.dispose()

    if TEST_DB.exists():
        TEST_DB.unlink()

    print("Temporary resolution test database removed.")