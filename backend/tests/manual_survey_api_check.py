
import shutil
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.database import get_db
from backend.app.models import (
    Complaint,
    Resolution,
)


SOURCE_DB = Path("complaints.db")
TEST_DB = Path("complaints_survey_api_test.db")

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
        # Select a resolved complaint with a final resolution
        # and no survey already submitted.
        candidates = (
            db.query(Complaint)
            .filter(Complaint.status == "RESOLVED")
            .order_by(Complaint.complaint_id)
            .all()
        )

        selected = None

        for candidate in candidates:
            final_resolution = (
                db.query(Resolution)
                .filter(
                    Resolution.complaint_id == candidate.complaint_id,
                    Resolution.is_final.is_(True),
                )
                .order_by(Resolution.resolved_at.desc())
                .first()
            )

            if final_resolution is None:
                continue

            if final_resolution.resolution_id != (
                f"RES-{candidate.complaint_id}"
            ) and not final_resolution.resolution_id.startswith(
                f"RES-{candidate.complaint_id}-"
            ):
                continue

            from backend.app.models import Survey

            existing_survey = (
                db.query(Survey)
                .filter(
                    Survey.resolution_id == final_resolution.resolution_id
                )
                .first()
            )

            if existing_survey is None:
                selected = (candidate.complaint_id, final_resolution.resolution_id)
                break

        assert selected is not None, (
            "No suitable RESOLVED complaint with an unsurveyed final "
            "resolution was found."
        )

        complaint_id, resolution_id = selected

        # Find a different complaint's resolution for the ownership test.
        other_resolution = (
            db.query(Resolution)
            .filter(Resolution.complaint_id != complaint_id)
            .first()
        )

        assert other_resolution is not None, (
            "No second complaint resolution is available for the ownership test."
        )

        other_resolution_id = other_resolution.resolution_id

    finally:
        db.close()

    print(f"Testing complaint: {complaint_id}")
    print(f"Testing resolution: {resolution_id}")

    with TestClient(app) as client:

        # 1. Survey must be rejected while complaint is RESOLVED.
        response = client.post(
            f"/api/complaints/{complaint_id}/survey",
            json={
                "resolution_id": resolution_id,
                "rating": 5,
                "feedback": "Testing before closure.",
            },
        )

        assert response.status_code == 409, response.text

        print("Test 1: Reject survey before closure — PASSED")

        # 2. Close the complaint.
        response = client.patch(
            f"/api/complaints/{complaint_id}/status",
            json={
                "new_status": "CLOSED",
                "performed_by": "Survey API Test",
            },
        )

        assert response.status_code == 200, response.text
        assert response.json()["new_status"] == "CLOSED"

        print("Test 2: Close complaint through API — PASSED")

        # 3. Submit a valid survey.
        response = client.post(
            f"/api/complaints/{complaint_id}/survey",
            json={
                "resolution_id": resolution_id,
                "rating": 5,
                "feedback": "The issue was resolved satisfactorily.",
            },
        )

        assert response.status_code == 201, response.text

        survey_data = response.json()

        assert survey_data["resolution_id"] == resolution_id
        assert survey_data["rating"] == 5

        print("Test 3: Submit valid survey — PASSED")

        # 4. Reject a duplicate survey.
        response = client.post(
            f"/api/complaints/{complaint_id}/survey",
            json={
                "resolution_id": resolution_id,
                "rating": 4,
                "feedback": "Duplicate submission attempt.",
            },
        )

        assert response.status_code == 409, response.text

        print("Test 4: Reject duplicate survey — PASSED")

        # 5. Reject rating outside the 1–5 range.
        response = client.post(
            f"/api/complaints/{complaint_id}/survey",
            json={
                "resolution_id": resolution_id,
                "rating": 6,
                "feedback": "Invalid rating.",
            },
        )

        assert response.status_code == 422, response.text

        print("Test 5: Reject invalid rating — PASSED")

        # 6. Reject a resolution belonging to another complaint.
        response = client.post(
            f"/api/complaints/{complaint_id}/survey",
            json={
                "resolution_id": other_resolution_id,
                "rating": 4,
                "feedback": "Testing resolution ownership.",
            },
        )

        assert response.status_code == 404, response.text

        print("Test 6: Reject unrelated resolution — PASSED")

        # 7. Verify survey and event history.
        response = client.get(
            f"/api/complaints/{complaint_id}"
        )

        assert response.status_code == 200, response.text

        detail = response.json()

        resolution_history = [
            item for item in detail["resolutions"]
            if item["resolution_id"] == resolution_id
        ]

        assert len(resolution_history) == 1

        saved_survey = resolution_history[0]["survey"]

        assert saved_survey is not None
        assert saved_survey["rating"] == 5
        assert saved_survey["feedback"] == (
            "The issue was resolved satisfactorily."
        )

        survey_events = [
            item for item in detail["events"]
            if item["event_type"] == "SURVEY_SUBMITTED"
            and item["new_value"] == str(survey_data["survey_id"])
        ]

        assert len(survey_events) == 1

        print("Test 7: Verify survey and event history — PASSED")

    print("\nALL SURVEY API TESTS PASSED")

finally:
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()

    if TEST_DB.exists():
        TEST_DB.unlink()

    print("Temporary survey API database removed.")
