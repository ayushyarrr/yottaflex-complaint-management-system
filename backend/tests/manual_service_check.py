
import shutil
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.app.models import (
    Customer,
    Order,
    OrderItem,
    Complaint,
    ComplaintProduct,
)
from backend.app.services.complaint_service import create_complaint
from backend.app.schemas.complaint import ComplaintCreate


SOURCE_DB = Path("complaints.db")
TEST_DB = Path("complaints_service_test.db")

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

db = TestSession()

try:
    # Find an order that has at least one product.
    order = (
        db.query(Order)
        .join(OrderItem, Order.order_id == OrderItem.order_id)
        .first()
    )

    if not order:
        raise RuntimeError("No order with products was found.")

    order_customer = (
        db.query(Customer)
        .filter(Customer.customer_id == order.customer_id)
        .first()
    )

    if not order_customer:
        raise RuntimeError("The order's customer was not found.")

    print("Testing automatic product association...")

    payload = ComplaintCreate(
        customer_id=order.customer_id,
        order_id=order.order_id,
        description="I have an issue with my recent order.",
        channel="WEB",
        sentiment="NEUTRAL",
    )

    complaint = create_complaint(db, payload)

    expected_product_ids = {
        item.product_id
        for item in db.query(OrderItem)
        .filter(OrderItem.order_id == order.order_id)
        .all()
    }

    actual_product_ids = {
        link.product_id
        for link in db.query(ComplaintProduct)
        .filter(ComplaintProduct.complaint_id == complaint.complaint_id)
        .all()
    }

    print("Complaint ID:", complaint.complaint_id)
    print("Order ID:", order.order_id)
    print("Expected products:", len(expected_product_ids))
    print("Associated products:", len(actual_product_ids))

    assert expected_product_ids == actual_product_ids

    print("AUTOMATIC PRODUCT ASSOCIATION TEST PASSED")

    # Find a different customer to test order ownership.
    other_customer = (
        db.query(Customer)
        .filter(Customer.customer_id != order.customer_id)
        .first()
    )

    if not other_customer:
        raise RuntimeError("A second customer was not found.")

    print("\nTesting rejection of another customer's order...")

    complaint_count_before = db.query(Complaint).count()

    invalid_payload = ComplaintCreate(
        customer_id=other_customer.customer_id,
        order_id=order.order_id,
        description="I have an issue with this order.",
        channel="WEB",
        sentiment="NEUTRAL",
    )

    try:
        create_complaint(db, invalid_payload)
        raise AssertionError("An order belonging to another customer was accepted.")

    except HTTPException as error:
        assert error.status_code == 400
        print("Rejected with HTTP status:", error.status_code)
        print("Error:", error.detail)

    complaint_count_after = db.query(Complaint).count()

    assert complaint_count_before == complaint_count_after

    print("CROSS-CUSTOMER ORDER REJECTION TEST PASSED")

finally:
    db.close()
    engine.dispose()

    if TEST_DB.exists():
        TEST_DB.unlink()

    print("\nTemporary test database removed.")
