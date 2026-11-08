
import shutil
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.database import get_db
from backend.app.models import Assignment, Complaint


SOURCE_DB = Path("complaints.db")
TEST_DB = Path("complaints_reopen_api_test.db")

if not SOURCE_DB.exists():
    raise FileNotFoundError("complaints.db was not found.")

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


def override_get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

try:
    db = Session()

    try:
        complaint = (
            db.query(Complaint)
            .filter(Complaint.status == "ASSIGNED")
            .order_by(Complaint.complaint_id)
            .first()
        )

        assert complaint is not None, "No ASSIGNED complaint found."

        complaint_id = complaint.complaint_id

        assignment = (
            db.query(Assignment)
            .filter(
                Assignment.complaint_id == complaint_id,
                Assignment.is_current.is_(True),
            )
            .first()
        )

        assert assignment is not None, "No current assignment found."

        agent_id = assignment.agent_id

    finally:
        db.close()

    print(f"Testing complaint: {complaint_id}")

    with TestClient(app) as client:

        # 1. Start the complaint.
        response = client.patch(
            f"/api/complaints/{complaint_id}/status",
            json={
                "new_status": "IN_PROGRESS",
                "performed_by": "API Lifecycle Test",
            },
        )

        assert response.status_code == 200, response.text
        print("Test 1: Start complaint through API — PASSED")

        # 2. Resolve the complaint.
        response = client.post(
            f"/api/complaints/{complaint_id}/resolve",
            json={
                "resolution_type": "REPAIR",
                "resolution_description": (
                    "The product issue was inspected and repaired."
                ),
                "resolved_by": agent_id,
            },
        )

        assert response.status_code == 201, response.text
        first_resolution_id = response.json()["resolution_id"]

        print("Test 2: Resolve complaint through API — PASSED")

        # 3. Reopen the complaint through the new endpoint.
        response = client.post(
            f"/api/complaints/{complaint_id}/reopen",
            json={
                "reason": (
                    "The customer reported that the same issue has returned."
                ),
                "performed_by": "API Lifecycle Test",
            },
        )

        assert response.status_code == 200, response.text
        assert response.json()["status"] == "IN_PROGRESS"

        print("Test 3: Reopen complaint through API — PASSED")

        # 4. Reject another reopening while already IN_PROGRESS.
        response = client.post(
            f"/api/complaints/{complaint_id}/reopen",
            json={
                "reason": "Testing an invalid duplicate reopening request.",
                "performed_by": "API Lifecycle Test",
            },
        )

        assert response.status_code == 409, response.text

        print("Test 4: Reject invalid duplicate reopening — PASSED")

        # 5. Verify complete complaint history.
        response = client.get(
            f"/api/complaints/{complaint_id}"
        )

        assert response.status_code == 200, response.text

        detail = response.json()

        assert detail["status"] == "IN_PROGRESS"
        assert len(detail["resolutions"]) == 1
        assert detail["resolutions"][0]["resolution_id"] == first_resolution_id
        assert detail["resolutions"][0]["is_final"] is False
        assert len(detail["sla_clocks"]) == 2

        assert any(
            item["event_type"] == "COMPLAINT_REOPENED"
            for item in detail["events"]
        )

        print("Test 5: Verify complaint history through API — PASSED")

    print("\nALL REOPEN API TESTS PASSED")

finally:
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()

    if TEST_DB.exists():
        TEST_DB.unlink()

    print("Temporary API test database removed.")
