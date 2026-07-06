from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CandidateProfileBase(BaseModel):
    """Shared candidate profile fields."""

    full_name: str = Field(..., max_length=255)
    target_role: str | None = Field(default=None, max_length=255)
    experience_level: str | None = Field(default=None, max_length=100)
    years_of_experience: Decimal | None = Field(default=None, ge=0, max_digits=4, decimal_places=1)
    english_level: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=255)
    desired_salary_min: int | None = Field(default=None, ge=0)
    skills: list[str] | None = None
    summary: str | None = None


class CandidateProfileCreate(CandidateProfileBase):
    """Schema for creating a candidate profile."""

    pass


class CandidateProfileUpdate(BaseModel):
    """Schema for updating a candidate profile."""

    full_name: str | None = Field(default=None, max_length=255)
    target_role: str | None = Field(default=None, max_length=255)
    experience_level: str | None = Field(default=None, max_length=100)
    years_of_experience: Decimal | None = Field(default=None, ge=0, max_digits=4, decimal_places=1)
    english_level: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=255)
    desired_salary_min: int | None = Field(default=None, ge=0)
    skills: list[str] | None = None
    summary: str | None = None


class CandidateProfileRead(CandidateProfileBase):
    """Schema for returning a candidate profile."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)