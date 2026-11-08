
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String
)
from sqlalchemy.sql import func

from backend.app.database import Base


class SLAClock(Base):
    __tablename__ = "sla_clocks"

    sla_id = Column(String(60), primary_key=True)

    complaint_id = Column(
        String(30),
        ForeignKey("complaints.complaint_id"),
        nullable=False,
        index=True
    )

    priority = Column(String(10), nullable=False)

    response_deadline = Column(DateTime(timezone=True), nullable=False)

    resolution_deadline = Column(DateTime(timezone=True), nullable=False)

    first_response_at = Column(DateTime(timezone=True), nullable=True)

    resolved_at = Column(DateTime(timezone=True), nullable=True)

    paused_at = Column(DateTime(timezone=True), nullable=True)

    total_paused_seconds = Column(Integer, default=0, nullable=False)

    response_breached = Column(Boolean, default=False, nullable=False)

    resolution_breached = Column(Boolean, default=False, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
