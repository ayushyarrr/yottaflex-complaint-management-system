
from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.sql import func

from backend.app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String(20), primary_key=True, index=True)

    full_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    phone = Column(String(20), nullable=False)

    region = Column(String(100), nullable=False)

    is_vulnerable = Column(Boolean, default=False, nullable=False)

    status = Column(String(20), default="ACTIVE", nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
