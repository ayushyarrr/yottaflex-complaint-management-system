
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ComplaintMessageCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    sender_type: Literal["CUSTOMER", "AGENT", "SYSTEM"]

    message_text: str = Field(
        min_length=2,
        max_length=5000,
        description="Content of the complaint message."
    )

    channel: Literal["EMAIL", "PHONE", "CHAT", "WEB"]

    is_internal: bool = Field(
        default=False,
        description="True for internal notes that are not customer-visible."
    )

    @field_validator("message_text")
    @classmethod
    def validate_message_text(cls, value):
        if not value.strip():
            raise ValueError("Message cannot be empty.")
        return value
