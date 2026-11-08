
from sqlalchemy import Boolean, Column, Integer, String, Text

from backend.app.database import Base


class Team(Base):
    __tablename__ = "teams"

    team_id = Column(Integer, primary_key=True, autoincrement=True)

    team_name = Column(String(100), unique=True, nullable=False)

    description = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
