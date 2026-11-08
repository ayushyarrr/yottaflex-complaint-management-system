
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.sql import func

from backend.app.database import Base


class ComplaintMessage(Base):
    __tablename__ = "complaint_messages"

    message_id = Column(String(60), primary_key=True)

    complaint_id = Column(
        String(30),
        ForeignKey("complaints.complaint_id"),
        nullable=False,
        index=True
    )

    sender_type = Column(String(30), nullable=False)

    message_text = Column(Text, nullable=False)

    channel = Column(String(30), nullable=False)

    is_internal = Column(Boolean, default=False, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
