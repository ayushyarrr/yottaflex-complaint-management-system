
import shutil
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.database import get_db
from backend.app.models import Assignment, Complaint


SOURCE_DB = Path("complaints.db")
TEST_DB = Path("complaints_message_api_test.db")

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

    finally:
        db.close()

    print(f"Testing complaint: {complaint_id}")

    with TestClient(app) as client:

        # 1. Customer sends a public message.
        response = client.post(
            f"/api/complaints/{complaint_id}/messages",
            json={
                "sender_type": "CUSTOMER",
                "message_text": "I would like an update on my complaint.",
                "channel": "EMAIL",
                "is_internal": False,
            },
        )

        assert response.status_code == 201, response.text

        first_message = response.json()

        assert first_message["message_id"] == (
            f"MSG-{complaint_id}-004"
        )
        assert first_message["is_internal"] is False

        print("Test 1: Customer public message — PASSED")

        # 2. Assigned agent adds an internal note.
        response = client.post(
            f"/api/complaints/{complaint_id}/messages",
            json={
                "sender_type": "AGENT",
                "message_text": "Checking the order and refund records.",
                "channel": "WEB",
                "is_internal": True,
            },
        )

        assert response.status_code == 201, response.text

        second_message = response.json()

        assert second_message["message_id"] == (
            f"MSG-{complaint_id}-005"
        )
        assert second_message["is_internal"] is True

        print("Test 2: Agent internal note — PASSED")

        # 3. Customer attempts to submit an internal note.
        response = client.post(
            f"/api/complaints/{complaint_id}/messages",
            json={
                "sender_type": "CUSTOMER",
                "message_text": "This should not be accepted as internal.",
                "channel": "CHAT",
                "is_internal": True,
            },
        )

        assert response.status_code == 422, response.text

        print("Test 3: Reject customer internal note — PASSED")

        # 4. External caller attempts to submit a SYSTEM message.
        response = client.post(
            f"/api/complaints/{complaint_id}/messages",
            json={
                "sender_type": "SYSTEM",
                "message_text": "Attempted system message.",
                "channel": "WEB",
                "is_internal": True,
            },
        )

        assert response.status_code == 403, response.text

        print("Test 4: Reject externally submitted system message — PASSED")

        # 5. Nonexistent complaint must return 404.
        response = client.post(
            "/api/complaints/CMP-2099-999999/messages",
            json={
                "sender_type": "CUSTOMER",
                "message_text": "Testing a nonexistent complaint.",
                "channel": "EMAIL",
                "is_internal": False,
            },
        )

        assert response.status_code == 404, response.text

        print("Test 5: Reject nonexistent complaint — PASSED")

        # 6. Verify messages and events through complaint details.
        response = client.get(
            f"/api/complaints/{complaint_id}"
        )

        assert response.status_code == 200, response.text

        detail = response.json()

        added_messages = [
            message
            for message in detail["messages"]
            if message["message_id"] in {
                first_message["message_id"],
                second_message["message_id"],
            }
        ]

        assert len(added_messages) == 2

        message_events = [
            item
            for item in detail["events"]
            if item["event_type"] == "MESSAGE_ADDED"
            and item["new_value"] in {
                first_message["message_id"],
                second_message["message_id"],
            }
        ]

        assert len(message_events) == 2

        print("Test 6: Verify message and event history — PASSED")

    print("\nALL MESSAGE API TESTS PASSED")

finally:
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()

    if TEST_DB.exists():
        TEST_DB.unlink()

    print("Temporary message API database removed.")
