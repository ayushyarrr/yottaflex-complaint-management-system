
from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy.sql import func

from backend.app.database import Base


class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String(30), primary_key=True, index=True)

    customer_id = Column(
        String(20),
        ForeignKey("customers.customer_id"),
        nullable=False,
        index=True
    )

    order_date = Column(DateTime(timezone=True), nullable=False)

    total_amount = Column(Numeric(12, 2), nullable=False)

    payment_status = Column(String(30), nullable=False)

    order_status = Column(String(30), nullable=False)

    shipping_region = Column(String(100), nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
