
from sqlalchemy import Column, ForeignKey, Integer

from backend.app.database import Base


class PriorityDecisionRule(Base):
    __tablename__ = "priority_decision_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)

    decision_id = Column(
        Integer,
        ForeignKey("priority_decisions.decision_id"),
        nullable=False,
        index=True
    )

    rule_id = Column(
        Integer,
        ForeignKey("priority_rules.rule_id"),
        nullable=False,
        index=True
    )
