
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text

from backend.app.database import Base


class Survey(Base):
    __tablename__ = "surveys"

    __table_args__ = (
        CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="check_survey_rating"
        ),
    )

    survey_id = Column(Integer, primary_key=True, autoincrement=True)

    resolution_id = Column(
        String(60),
        ForeignKey("resolutions.resolution_id"),
        nullable=False,
        unique=True
    )

    complaint_id = Column(
        String(30),
        ForeignKey("complaints.complaint_id"),
        nullable=False
    )

    rating = Column(Integer, nullable=False)

    feedback = Column(Text, nullable=True)

    submitted_at = Column(DateTime(timezone=True), nullable=False)
