from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ResolutionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    resolution_type: Literal[
        "REFUND",
        "REPLACEMENT",
        "REPAIR",
        "INFORMATION",
        "OTHER",
    ]

    resolution_description: str = Field(
        min_length=10,
        max_length=3000,
        description="Explain how the complaint was resolved.",
    )

    resolved_by: int = Field(
        gt=0,
        description="ID of the agent resolving the complaint.",
    )