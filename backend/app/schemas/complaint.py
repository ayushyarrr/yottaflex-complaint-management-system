
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ComplaintCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    customer_id: str = Field(
        min_length=1,
        max_length=20,
        description="ID of the existing customer."
    )

    order_id: str | None = Field(
        default=None,
        max_length=30,
        description="Optional ID of an existing order."
    )

    product_ids: list[str] | None = Field(
        default=None,
        max_length=20,
        description=(
            "Optional product IDs. If omitted and an order is provided, "
            "products will be inherited from that order."
        )
    )

    description: str = Field(
        min_length=10,
        max_length=5000,
        description="Detailed description of the complaint."
    )

    channel: Literal["EMAIL", "PHONE", "CHAT", "WEB"]

    sentiment: Literal[
        "STRONGLY NEGATIVE",
        "NEGATIVE",
        "NEUTRAL",
        "POSITIVE"
    ] = "NEUTRAL"

    @field_validator("customer_id", "order_id")
    @classmethod
    def validate_identifiers(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Identifier cannot be empty.")
        return value

    @field_validator("product_ids")
    @classmethod
    def validate_product_ids(cls, value):
        if value is None:
            return None

        cleaned_ids = [product_id.strip() for product_id in value]

        if any(not product_id for product_id in cleaned_ids):
            raise ValueError("Product IDs cannot be empty.")

        if len(cleaned_ids) != len(set(cleaned_ids)):
            raise ValueError("Duplicate product IDs are not allowed.")

        return cleaned_ids

    @field_validator("description")
    @classmethod
    def validate_description(cls, value):
        if not value.strip():
            raise ValueError("Complaint description cannot be empty.")
        return value
