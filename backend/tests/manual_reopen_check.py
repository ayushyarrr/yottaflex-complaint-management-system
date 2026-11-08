
import shutil
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.app.models import (
    Assignment,
    Complaint,
    ComplaintEvent,
    Resolution,
    SLAClock,
)
from backend.app.schemas.resolution import ResolutionCreate
from backend.app.schemas.reopen import ComplaintReopen
from backend.app.services.status_service import transition_complaint_status
from backend.app.services.resolution_service import resolve_complaint
from backend.app.services.reopen_service import reopen_complaint


SOURCE_DB = Path("complaints.db")
TEST_DB = Path("complaints_reopen_test.db")

if not SOURCE_DB.exists():
    raise FileNotFoundError(
        "complaints.db was not found. Run this test from the project root."
    )

shutil.copy2(SOURCE_DB, TEST_DB)

engine = create_engine(
    f"sqlite:///{TEST_DB.as_posix()}",
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def enable_foreign_keys(connection, connection_record):
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
db = Session()

try:
    complaint = (
        db.query(Complaint)
        .filter(Complaint.status == "ASSIGNED")
        .order_by(Complaint.complaint_id)
        .first()
    )

    assert complaint is not None, "No ASSIGNED complaint is available."

    complaint_id = complaint.complaint_id

    assignment = (
        db.query(Assignment)
        .filter(
            Assignment.complaint_id == complaint_id,
            Assignment.is_current.is_(True),
        )
        .first()
    )

    assert assignment is not None, "Complaint has no current assignment."

    agent_id = assignment.agent_id

    print(f"Testing complaint: {complaint_id}")

    # 1. Move complaint into IN_PROGRESS.
    transition_complaint_status(
        db=db,
        complaint_id=complaint_id,
        new_status="IN_PROGRESS",
        performed_by="Lifecycle Test",
    )

    print("Test 1: Start complaint — PASSED")

    # 2. Resolve it for the first time.
    first_resolution = resolve_complaint(
        db=db,
        complaint_id=complaint_id,
        payload=ResolutionCreate(
            resolution_type="REPAIR",
            resolution_description="The product issue was inspected and repaired.",
            resolved_by=agent_id,
        ),
    )

    first_resolution_id = first_resolution.resolution_id

    first_sla = (
        db.query(SLAClock)
        .filter(SLAClock.complaint_id == complaint_id)
        .order_by(SLAClock.created_at.desc())
        .first()
    )
    first_sla_id = first_sla.sla_id

    assert first_resolution_id == f"RES-{complaint_id}"
    assert first_resolution.is_final is True
    assert first_sla.resolved_at is not None

    print("Test 2: First resolution — PASSED")

    # 3. Reopen the complaint.
    reopened = reopen_complaint(
        db=db,
        complaint_id=complaint_id,
        payload=ComplaintReopen(
            reason="The customer reported that the same issue has returned.",
            performed_by="Lifecycle Test",
        ),
    )

    assert reopened.status == "IN_PROGRESS"

    db.refresh(first_resolution)
    db.refresh(first_sla)

    assert first_resolution.is_final is False
    assert first_sla.resolved_at is not None

    sla_clocks = (
        db.query(SLAClock)
        .filter(SLAClock.complaint_id == complaint_id)
        .order_by(SLAClock.created_at)
        .all()
    )

    assert len(sla_clocks) == 2
    assert sla_clocks[0].sla_id == first_sla_id
    assert sla_clocks[1].sla_id != first_sla_id
    assert sla_clocks[1].resolved_at is None

    print("Test 3: Reopen complaint and create a new SLA clock — PASSED")

    # 4. Resolve the reopened complaint again.
    second_resolution = resolve_complaint(
        db=db,
        complaint_id=complaint_id,
        payload=ResolutionCreate(
            resolution_type="REPLACEMENT",
            resolution_description="The product was replaced after the recurring issue.",
            resolved_by=agent_id,
        ),
    )

    assert second_resolution.resolution_id == f"RES-{complaint_id}-002"
    assert second_resolution.is_final is True

    db.refresh(first_resolution)

    assert first_resolution.is_final is False

    all_resolutions = (
        db.query(Resolution)
        .filter(Resolution.complaint_id == complaint_id)
        .order_by(Resolution.resolved_at)
        .all()
    )

    assert len(all_resolutions) == 2

    print("Test 4: Second resolution with a new ID — PASSED")

    # 5. Confirm the complaint and event history.
    db.refresh(reopened)

    assert reopened.status == "RESOLVED"

    events = (
        db.query(ComplaintEvent)
        .filter(ComplaintEvent.complaint_id == complaint_id)
        .order_by(ComplaintEvent.created_at)
        .all()
    )

    assert any(event.event_type == "COMPLAINT_REOPENED" for event in events)

    print("Test 5: Final status and event history — PASSED")

    print("\nALL REOPEN LIFECYCLE TESTS PASSED")

finally:
    db.close()
    engine.dispose()

    if TEST_DB.exists():
        TEST_DB.unlink()

    print("Temporary test database removed.")
