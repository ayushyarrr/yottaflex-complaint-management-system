
import shutil
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.app.database import get_db
from backend.app.main import app
from backend.app.models import Customer


SOURCE_DB = Path("complaints.db")
TEST_DB = Path("complaints_api_test.db")

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
        customer = db.query(Customer).first()

        if not customer:
            raise RuntimeError("No customer records found.")

        customer_id = customer.customer_id
    finally:
        db.close()

    print("Testing POST /api/complaints...")

    with TestClient(app) as client:
        response = client.post(
            "/api/complaints",
            json={
                "customer_id": customer_id,
                "description": (
                    "My delivery is late and the tracking "
                    "has not updated."
                ),
                "channel": "WEB",
                "sentiment": "NEUTRAL",
            },
        )

        print("HTTP status:", response.status_code)
        print("Response:", response.json())

        assert response.status_code == 201

        complaint_id = response.json()["complaint_id"]

        detail_response = client.get(
            f"/api/complaints/{complaint_id}"
        )

        print("\nTesting GET complaint details...")
        print("HTTP status:", detail_response.status_code)

        assert detail_response.status_code == 200

        detail = detail_response.json()

        assert detail["complaint_id"] == complaint_id
        assert detail["status"] == "ASSIGNED"
        assert len(detail["messages"]) == 2
        assert len(detail["events"]) == 5
        assert len(detail["assignment_history"]) == 1
        assert len(detail["sla_clocks"]) == 1

        print("Messages:", len(detail["messages"]))
        print("Events:", len(detail["events"]))
        print("Assignments:", len(detail["assignment_history"]))
        print("SLA clocks:", len(detail["sla_clocks"]))

        print("\nFULL API TEST PASSED")

finally:
    app.dependency_overrides.pop(get_db, None)

    engine.dispose()

    if TEST_DB.exists():
        TEST_DB.unlink()

    print("Temporary API test database removed.")
