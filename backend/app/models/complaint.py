
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text
)
from sqlalchemy.sql import func

from backend.app.database import Base


class Complaint(Base):
    __tablename__ = "complaints"

    complaint_id = Column(String(30), primary_key=True, index=True)

    customer_id = Column(
        String(20),
        ForeignKey("customers.customer_id"),
        nullable=False,
        index=True
    )

    order_id = Column(
        String(30),
        ForeignKey("orders.order_id"),
        nullable=True
    )

    category_id = Column(
        Integer,
        ForeignKey("categories.category_id"),
        nullable=False
    )

    description = Column(Text, nullable=False)

    channel = Column(String(30), nullable=False)

    sentiment = Column(String(30), nullable=False)

    severity = Column(String(30), nullable=False)

    priority = Column(String(10), nullable=False)

    status = Column(String(30), default="NEW", nullable=False)

    recurrence_count = Column(Integer, default=1, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
