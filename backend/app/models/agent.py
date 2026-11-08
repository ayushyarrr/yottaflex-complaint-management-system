
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String

from backend.app.database import Base


class Agent(Base):
    __tablename__ = "agents"

    agent_id = Column(Integer, primary_key=True, autoincrement=True)

    agent_name = Column(String(100), nullable=False)

    team_id = Column(
        Integer,
        ForeignKey("teams.team_id"),
        nullable=False,
        index=True
    )

    workload_capacity = Column(Integer, default=10, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
