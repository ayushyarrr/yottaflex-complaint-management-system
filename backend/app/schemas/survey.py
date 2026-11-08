
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SurveyCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    resolution_id: str = Field(
        min_length=1,
        max_length=60,
        description="ID of the resolution being evaluated."
    )

    rating: int = Field(
        ge=1,
        le=5,
        description="Customer satisfaction rating from 1 to 5."
    )

    feedback: str | None = Field(
        default=None,
        max_length=3000,
        description="Optional customer feedback."
    )

    @field_validator("resolution_id")
    @classmethod
    def validate_resolution_id(cls, value):
        if not value.strip():
            raise ValueError("Resolution ID cannot be empty.")
        return value

    @field_validator("feedback")
    @classmethod
    def validate_feedback(cls, value):
        if value is not None and not value.strip():
            return None
        return value
