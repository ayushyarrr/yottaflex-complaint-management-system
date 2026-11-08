
from sqlalchemy import Column, ForeignKey, Integer, String, Text

from backend.app.database import Base


class ComplaintProduct(Base):
    __tablename__ = "complaint_products"

    complaint_product_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    complaint_id = Column(
        String(30),
        ForeignKey("complaints.complaint_id"),
        nullable=False,
        index=True
    )

    product_id = Column(
        String(30),
        ForeignKey("products.product_id"),
        nullable=False,
        index=True
    )

    issue_description = Column(Text, nullable=True)
