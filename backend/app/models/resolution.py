
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from backend.app.database import Base


class Resolution(Base):
    __tablename__ = "resolutions"

    resolution_id = Column(String(60), primary_key=True)

    complaint_id = Column(
        String(30),
        ForeignKey("complaints.complaint_id"),
        nullable=False,
        index=True
    )

    resolution_type = Column(String(50), nullable=False)

    resolution_description = Column(Text, nullable=False)

    resolved_by = Column(
        Integer,
        ForeignKey("agents.agent_id"),
        nullable=False
    )

    resolved_at = Column(DateTime(timezone=True), nullable=False)

    is_final = Column(Boolean, default=False, nullable=False)
