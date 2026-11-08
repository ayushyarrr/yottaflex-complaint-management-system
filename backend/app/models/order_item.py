
from sqlalchemy import Column, ForeignKey, Integer, Numeric

from backend.app.database import Base


class OrderItem(Base):
    __tablename__ = "order_items"

    order_item_id = Column(Integer, primary_key=True, autoincrement=True)

    order_id = Column(
        ForeignKey("orders.order_id"),
        nullable=False,
        index=True
    )

    product_id = Column(
        ForeignKey("products.product_id"),
        nullable=False,
        index=True
    )

    quantity = Column(Integer, nullable=False)

    unit_price = Column(Numeric(12, 2), nullable=False)

    line_total = Column(Numeric(12, 2), nullable=False)
