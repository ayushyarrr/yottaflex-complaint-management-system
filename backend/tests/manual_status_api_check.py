import shutil
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.app.database import get_db
from backend.app.main import app
from backend.app.models import Complaint, SLAClock


SOURCE_DB = Path("complaints.db")
TEST_DB = Path("complaints_status_api_test.db")


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


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

try:
    db = TestSession()

    try:
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

    finally:
        db.close()

    print(f"Testing complaint: {complaint_id}")

    with TestClient(app) as client:

        # Test 1: ASSIGNED -> IN_PROGRESS
        print("\nTest 1: Starting complaint through API...")

        response = client.patch(
            f"/api/complaints/{complaint_id}/status",
            json={
                "new_status": "IN_PROGRESS",
                "performed_by": "TEST_AGENT",
            },
        )

        print("HTTP status:", response.status_code)
        assert response.status_code == 200, response.text

        result = response.json()
        assert result["old_status"] == "ASSIGNED"
        assert result["new_status"] == "IN_PROGRESS"

        print("PASSED: API updated complaint status.")

        # Test 2: IN_PROGRESS -> PENDING_CUSTOMER
        print("\nTest 2: Pausing SLA through API...")

        response = client.patch(
            f"/api/complaints/{complaint_id}/status",
            json={
                "new_status": "PENDING_CUSTOMER",
                "performed_by": "TEST_AGENT",
            },
        )

        print("HTTP status:", response.status_code)
        assert response.status_code == 200, response.text
        assert response.json()["new_status"] == "PENDING_CUSTOMER"

        db = TestSession()

        try:
            sla = (
                db.query(SLAClock)
                .filter(SLAClock.complaint_id == complaint_id)
                .order_by(SLAClock.created_at.desc())
                .first()
            )

            assert sla is not None
            assert sla.paused_at is not None

        finally:
            db.close()

        print("PASSED: SLA pause recorded.")

        # Test 3: PENDING_CUSTOMER -> IN_PROGRESS
        print("\nTest 3: Resuming SLA through API...")

        response = client.patch(
            f"/api/complaints/{complaint_id}/status",
            json={
                "new_status": "IN_PROGRESS",
                "performed_by": "TEST_AGENT",
            },
        )

        print("HTTP status:", response.status_code)
        assert response.status_code == 200, response.text
        assert response.json()["new_status"] == "IN_PROGRESS"

        db = TestSession()

        try:
            sla = (
                db.query(SLAClock)
                .filter(SLAClock.complaint_id == complaint_id)
                .order_by(SLAClock.created_at.desc())
                .first()
            )

            assert sla.paused_at is None
            assert sla.total_paused_seconds >= 0

        finally:
            db.close()

        print("PASSED: SLA resumed.")

        # Test 4: Reject an invalid transition.
        print("\nTest 4: Rejecting invalid transition through API...")

        response = client.patch(
            f"/api/complaints/{complaint_id}/status",
            json={
                "new_status": "CLOSED",
                "performed_by": "TEST_AGENT",
            },
        )

        print("HTTP status:", response.status_code)
        assert response.status_code == 409

        print("PASSED: Invalid transition rejected.")

        # Test 5: Verify event history through API.
        print("\nTest 5: Checking event history through API...")

        response = client.get(
            f"/api/complaints/{complaint_id}"
        )

        assert response.status_code == 200, response.text

        events = [
            item
            for item in response.json()["events"]
            if item["performed_by"] == "TEST_AGENT"
        ]

        transitions = [
            (item["old_value"], item["new_value"])
            for item in events
        ]

        expected = [
            ("ASSIGNED", "IN_PROGRESS"),
            ("IN_PROGRESS", "PENDING_CUSTOMER"),
            ("PENDING_CUSTOMER", "IN_PROGRESS"),
        ]

        assert transitions == expected

        print("PASSED: All status events are preserved.")

    print("\nALL STATUS API TESTS PASSED")

finally:
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()

    if TEST_DB.exists():
        TEST_DB.unlink()

    print("Temporary status API database removed.")