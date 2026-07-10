from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InteractionCreate(BaseModel):
    """Schema for creating an interaction related to a tracked vacancy."""

    interaction_type: str = Field(..., max_length=100)
    direction: str | None = Field(default=None, max_length=50)

    message_text: str | None = None
    summary: str | None = None

    occurred_at: datetime | None = None


class InteractionUpdate(BaseModel):
    """Schema for updating an interaction."""

    interaction_type: str | None = Field(default=None, max_length=100)
    direction: str | None = Field(default=None, max_length=50)

    message_text: str | None = None
    summary: str | None = None

    occurred_at: datetime | None = None


class InteractionResponse(BaseModel):
    """Response schema for interaction data."""

    id: int
    tracked_vacancy_id: int

    interaction_type: str
    direction: str | None

    message_text: str | None
    summary: str | None

    occurred_at: datetime | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

