
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from backend.app.database import Base


class PriorityRule(Base):
    __tablename__ = "priority_rules"

    rule_id = Column(Integer, primary_key=True, autoincrement=True)

    rule_name = Column(String(100), nullable=False)
    condition_type = Column(String(50), nullable=False)
    condition_value = Column(String(100), nullable=False)

    score = Column(Integer, default=0, nullable=False)

    priority_override = Column(String(10), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    effective_from = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    effective_to = Column(DateTime(timezone=True), nullable=True)
