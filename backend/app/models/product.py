
from sqlalchemy import Boolean, Column, DateTime, Numeric, String
from sqlalchemy.sql import func

from backend.app.database import Base


class Product(Base):
    __tablename__ = "products"

    product_id = Column(String(30), primary_key=True, index=True)

    product_name = Column(String(150), nullable=False)
    category_name = Column(String(100), nullable=False)

    unit_price = Column(Numeric(12, 2), nullable=False)

    is_safety_sensitive = Column(
        Boolean,
        default=False,
        nullable=False
    )

    status = Column(String(30), default="ACTIVE", nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
