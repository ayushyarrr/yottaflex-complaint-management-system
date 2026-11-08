import shutil
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.app.database import get_db
from backend.app.main import app
from backend.app.models import Complaint, Assignment, SLAClock


SOURCE_DB = Path("complaints.db")
TEST_DB = Path("complaints_resolution_api_test.db")

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
            raise RuntimeError("No suitable complaint found.")

        complaint_id = complaint.complaint_id

        assignment = (
            db.query(Assignment)
            .filter(
                Assignment.complaint_id == complaint_id,
                Assignment.is_current.is_(True),
            )
            .first()
        )

        agent_id = assignment.agent_id

    finally:
        db.close()

    print(f"Testing complaint: {complaint_id}")
    print(f"Assigned agent ID: {agent_id}")

    with TestClient(app) as client:

        # Test 1: Move complaint to IN_PROGRESS.
        print("\nTest 1: Starting complaint...")

        response = client.patch(
            f"/api/complaints/{complaint_id}/status",
            json={
                "new_status": "IN_PROGRESS",
                "performed_by": "TEST_AGENT",
            },
        )

        print("HTTP status:", response.status_code)
        assert response.status_code == 200, response.text

        print("PASSED: Complaint started.")

        # Test 2: Resolve complaint.
        print("\nTest 2: Resolving complaint through API...")

        resolution_payload = {
            "resolution_type": "REFUND",
            "resolution_description": (
                "Refund processed successfully. "
                "Customer notified about the transaction."
            ),
            "resolved_by": agent_id,
        }

        response = client.post(
            f"/api/complaints/{complaint_id}/resolve",
            json=resolution_payload,
        )

        print("HTTP status:", response.status_code)
        assert response.status_code == 201, response.text

        result = response.json()

        assert result["complaint_id"] == complaint_id
        assert result["resolution_id"] == f"RES-{complaint_id}"
        assert result["status"] == "RESOLVED"
        assert result["is_final"] is True

        print("PASSED: Resolution created.")
        print("Resolution ID:", result["resolution_id"])

        # Test 3: Verify complaint details.
        print("\nTest 3: Checking complaint history...")

        response = client.get(
            f"/api/complaints/{complaint_id}"
        )

        assert response.status_code == 200, response.text

        detail = response.json()

        assert detail["status"] == "RESOLVED"
        assert len(detail["resolutions"]) >= 1
        assert detail["resolutions"][-1]["resolution_type"] == "REFUND"
        assert detail["sla_clocks"][-1]["resolved_at"] is not None

        print("PASSED: Resolution and SLA history verified.")

        # Test 4: Reject duplicate resolution.
        print("\nTest 4: Rejecting duplicate resolution...")

        response = client.post(
            f"/api/complaints/{complaint_id}/resolve",
            json=resolution_payload,
        )

        print("HTTP status:", response.status_code)
        assert response.status_code == 409

        print("PASSED: Duplicate resolution rejected.")

        # Test 5: Reject invalid resolution type.
        print("\nTest 5: Rejecting invalid resolution type...")

        invalid_payload = {
            "resolution_type": "MAGIC",
            "resolution_description": (
                "This resolution type should not be accepted."
            ),
            "resolved_by": agent_id,
        }

        response = client.post(
            f"/api/complaints/{complaint_id}/resolve",
            json=invalid_payload,
        )

        print("HTTP status:", response.status_code)
        assert response.status_code == 422

        print("PASSED: Invalid resolution type rejected.")

    print("\nALL RESOLUTION API TESTS PASSED")

finally:
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()

    if TEST_DB.exists():
        TEST_DB.unlink()

    print("Temporary resolution API database removed.")