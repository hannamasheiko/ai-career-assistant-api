from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from app.schemas.interaction_enums import (
    InteractionDirection,
    InteractionType,
)


class InteractionCreate(BaseModel):
    """Schema for creating an interaction related to a tracked vacancy."""

    interaction_type: InteractionType
    direction: InteractionDirection | None = None

    message_text: str | None = None
    summary: str | None = None

    occurred_at: datetime | None = None


class InteractionUpdate(BaseModel):
    """Schema for updating an interaction."""

    interaction_type: InteractionType | None = None
    direction: InteractionDirection | None = None

    message_text: str | None = None
    summary: str | None = None

    occurred_at: datetime | None = None


class InteractionResponse(BaseModel):
    """Response schema for interaction data."""

    id: int
    tracked_vacancy_id: int

    interaction_type: InteractionType
    direction: InteractionDirection | None

    message_text: str | None
    summary: str | None

    occurred_at: datetime | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

