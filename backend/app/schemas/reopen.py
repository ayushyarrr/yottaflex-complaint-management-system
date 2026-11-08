from pydantic import BaseModel, ConfigDict, Field


class ComplaintReopen(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    reason: str = Field(
        min_length=10,
        max_length=1000,
        description="Explain why the resolved complaint needs to be reopened.",
    )

    performed_by: str = Field(
        min_length=1,
        max_length=100,
        description="Person requesting or authorizing the reopening.",
    )