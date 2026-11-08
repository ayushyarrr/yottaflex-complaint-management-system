from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StatusUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    new_status: Literal[
        "IN_PROGRESS",
        "PENDING_CUSTOMER",
        "CLOSED",
    ]

    performed_by: str = Field(
        min_length=1,
        max_length=100,
        description="Person or system initiating the status change.",
    )