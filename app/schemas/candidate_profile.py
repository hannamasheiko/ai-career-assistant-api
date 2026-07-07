from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CandidateProfileBase(BaseModel):
    """Shared candidate profile fields."""

    full_name: str = Field(..., max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=255)

    github_url: str | None = Field(default=None, max_length=500)
    linkedin_url: str | None = Field(default=None, max_length=500)

    preferred_employment_types: list[str] | None = None
    preferred_work_formats: list[str] | None = None
    desired_salary_min: int | None = Field(default=None, ge=0)


class CandidateProfileCreate(CandidateProfileBase):
    """Schema for creating a candidate profile."""

    pass


class CandidateProfileUpdate(BaseModel):
    """Schema for updating a candidate profile."""

    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=255)

    github_url: str | None = Field(default=None, max_length=500)
    linkedin_url: str | None = Field(default=None, max_length=500)

    preferred_employment_types: list[str] | None = None
    preferred_work_formats: list[str] | None = None
    desired_salary_min: int | None = Field(default=None, ge=0)


class CandidateProfileRead(CandidateProfileBase):
    """Schema for returning a candidate profile."""

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)