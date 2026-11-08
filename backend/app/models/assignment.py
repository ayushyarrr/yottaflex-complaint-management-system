
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text
)
from sqlalchemy.sql import func

from backend.app.database import Base


class Assignment(Base):
    __tablename__ = "assignments"

    assignment_id = Column(Integer, primary_key=True, autoincrement=True)

    complaint_id = Column(
        String(30),
        ForeignKey("complaints.complaint_id"),
        nullable=False,
        index=True
    )

    team_id = Column(
        Integer,
        ForeignKey("teams.team_id"),
        nullable=False
    )

    agent_id = Column(
        Integer,
        ForeignKey("agents.agent_id"),
        nullable=False
    )

    assigned_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    assigned_by = Column(String(100), nullable=False)

    reason = Column(Text, nullable=True)

    is_current = Column(Boolean, default=True, nullable=False)
