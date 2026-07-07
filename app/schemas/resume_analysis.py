from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ResumeAnalysisBase(BaseModel):
    """Shared resume analysis fields."""

    full_name: str = Field(..., max_length=255)
    target_role: str | None = Field(default=None, max_length=255)
    years_of_experience: Decimal | None = Field(default=None, ge=0, max_digits=4, decimal_places=1)
    english_level: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=255)

    skills: list[str] | None = None
    summary: str | None = None

    education_level: str | None = Field(default=None, max_length=100)
    education_summary: str | None = None
    languages: list[str] | None = None

    ai_model: str | None = Field(default=None, max_length=100)
    prompt_version: str | None = Field(default=None, max_length=100)


class ResumeAnalysisCreate(ResumeAnalysisBase):
    """Schema for creating resume analysis."""

    resume_document_id: int


class ResumeAnalysisRead(ResumeAnalysisBase):
    """Schema for returning resume analysis."""

    id: int
    resume_document_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

