
import shutil
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.app.database import get_db
from backend.app.main import app
from backend.app.models import Customer


SOURCE_DB = Path("complaints.db")
TEST_DB = Path("complaints_validation_test.db")

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

    with TestClient(app) as client:

        # Test 1: Non-existent customer
        print("Testing non-existent customer...")

        response = client.post(
            "/api/complaints",
            json={
                "customer_id": "CUS-999999",
                "description": "My delivery is late and tracking is unavailable.",
                "channel": "WEB",
                "sentiment": "NEUTRAL",
            },
        )

        print("HTTP status:", response.status_code)
        assert response.status_code == 404

        # Test 2: Invalid channel
        print("\nTesting invalid channel...")

        response = client.post(
            "/api/complaints",
            json={
                "customer_id": customer_id,
                "description": "My delivery is late and tracking is unavailable.",
                "channel": "WHATSAPP",
                "sentiment": "NEUTRAL",
            },
        )

        print("HTTP status:", response.status_code)
        assert response.status_code == 422

        # Test 3: Missing description
        print("\nTesting missing description...")

        response = client.post(
            "/api/complaints",
            json={
                "customer_id": customer_id,
                "channel": "WEB",
                "sentiment": "NEUTRAL",
            },
        )

        print("HTTP status:", response.status_code)
        assert response.status_code == 422

        # Test 4: Description shorter than 10 characters
        print("\nTesting short description...")

        response = client.post(
            "/api/complaints",
            json={
                "customer_id": customer_id,
                "description": "Too short",
                "channel": "WEB",
                "sentiment": "NEUTRAL",
            },
        )

        print("HTTP status:", response.status_code)
        assert response.status_code == 422

        print("\nALL API VALIDATION TESTS PASSED")

finally:
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()

    if TEST_DB.exists():
        TEST_DB.unlink()

    print("Temporary validation database removed.")
