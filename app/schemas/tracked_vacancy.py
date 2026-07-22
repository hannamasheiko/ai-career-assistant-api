from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.tracked_vacancy_enums import (
    TrackedVacancyDecision,
    TrackedVacancyPriority,
    TrackedVacancyStatus,
)


class TrackedVacancyCreate(BaseModel):
    """Schema for creating a tracked vacancy."""

    resume_document_id: int
    vacancy_id: int

    status: TrackedVacancyStatus = TrackedVacancyStatus.SAVED
    priority: TrackedVacancyPriority = TrackedVacancyPriority.LOW
    decision: TrackedVacancyDecision = TrackedVacancyDecision.INTERESTED

    notes: str | None = None

    applied_at: datetime | None = None
    last_contact_at: datetime | None = None
    next_action_at: datetime | None = None


class TrackedVacancyUpdate(BaseModel):
    """Schema for updating a tracked vacancy."""

    status: TrackedVacancyStatus | None = None
    priority: TrackedVacancyPriority | None = None
    decision: TrackedVacancyDecision | None = None

    notes: str | None = None

    applied_at: datetime | None = None
    last_contact_at: datetime | None = None
    next_action_at: datetime | None = None


class TrackedVacancyResponse(BaseModel):
    """Response schema for tracked vacancy data."""

    id: int

    resume_document_id: int
    vacancy_id: int

    status: TrackedVacancyStatus
    priority: TrackedVacancyPriority
    decision: TrackedVacancyDecision

    notes: str | None

    applied_at: datetime | None
    last_contact_at: datetime | None
    next_action_at: datetime | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

