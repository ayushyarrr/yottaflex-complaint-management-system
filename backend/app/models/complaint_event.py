
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from backend.app.database import Base


class ComplaintEvent(Base):
    __tablename__ = "complaint_events"

    event_id = Column(Integer, primary_key=True, autoincrement=True)

    complaint_id = Column(
        String(30),
        ForeignKey("complaints.complaint_id"),
        nullable=False,
        index=True
    )

    event_type = Column(String(50), nullable=False)

    old_value = Column(String(100), nullable=True)

    new_value = Column(String(100), nullable=True)

    description = Column(Text, nullable=True)

    performed_by = Column(String(100), nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
