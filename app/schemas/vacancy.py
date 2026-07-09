from datetime import datetime

from pydantic import BaseModel, Field


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
    analysis: VacancyAnalysisResponse | None = None

class VacancyAnalysisResponse(BaseModel):
    """Response schema for AI-generated vacancy analysis."""

    id: int
    vacancy_id: int

    experience_level: str | None
    english_level: str | None

    required_skills: list[str] | None
    optional_skills: list[str] | None
    responsibilities: list[str] | None
    red_flags: list[str] | None
    green_flags: list[str] | None

    summary: str | None
    recommendation: str | None

    ai_model: str | None
    prompt_version: str | None

    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }

class VacancyAnalysisIngestionResponse(BaseModel):
    """Response schema for vacancy analysis generation."""

    analysis: VacancyAnalysisResponse

