from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TrackedVacancyCreate(BaseModel):
    """Schema for creating a tracked vacancy."""

    resume_document_id: int
    vacancy_id: int

    status: str = Field(default="saved", max_length=100)
    priority: str | None = Field(default=None, max_length=100)
    decision: str | None = Field(default=None, max_length=100)
    notes: str | None = None

    applied_at: datetime | None = None
    last_contact_at: datetime | None = None
    next_action_at: datetime | None = None


class TrackedVacancyUpdate(BaseModel):
    """Schema for updating a tracked vacancy."""

    status: str | None = Field(default=None, max_length=100)
    priority: str | None = Field(default=None, max_length=100)
    decision: str | None = Field(default=None, max_length=100)
    notes: str | None = None

    applied_at: datetime | None = None
    last_contact_at: datetime | None = None
    next_action_at: datetime | None = None


class TrackedVacancyResponse(BaseModel):
    """Response schema for tracked vacancy data."""

    id: int

    resume_document_id: int
    vacancy_id: int

    status: str
    priority: str | None
    decision: str | None
    notes: str | None

    applied_at: datetime | None
    last_contact_at: datetime | None
    next_action_at: datetime | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

