from datetime import datetime

from pydantic import BaseModel, Field


class VacancyFromTextRequest(BaseModel):
    """Request schema for creating a vacancy from copied vacancy page text."""

    raw_text: str = Field(..., min_length=1)
    source_url: str | None = None


class VacancyResponse(BaseModel):
    """Response schema for vacancy data."""

    id: int

    company_name: str | None
    position_title: str | None

    source: str | None
    source_url: str | None

    location: str | None
    work_format: str | None
    employment_type: str | None

    salary_min: int | None
    salary_max: int | None
    currency: str | None

    raw_text: str
    cleaned_text: str | None

    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class VacancyIngestionResponse(BaseModel):
    """Response schema for vacancy ingestion from text."""

    vacancy: VacancyResponse