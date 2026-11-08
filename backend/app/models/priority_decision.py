
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from backend.app.database import Base


class PriorityDecision(Base):
    __tablename__ = "priority_decisions"

    decision_id = Column(Integer, primary_key=True, autoincrement=True)

    complaint_id = Column(
        String(30),
        ForeignKey("complaints.complaint_id"),
        nullable=False,
        index=True
    )

    calculated_score = Column(Integer, nullable=False)

    assigned_priority = Column(String(10), nullable=False)

    safety_override_applied = Column(
        String(10),
        nullable=True
    )

    explanation = Column(String(500), nullable=False)

    decided_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
