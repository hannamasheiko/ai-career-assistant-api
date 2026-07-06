from pydantic import BaseModel, Field


class ParsedCandidateProfile(BaseModel):
    """Structured candidate profile extracted from resume text by AI."""

    full_name: str = Field(..., max_length=255)
    target_role: str | None = Field(default=None, max_length=255)
    experience_level: str | None = Field(default=None, max_length=100)
    years_of_experience: float | None = Field(default=None, ge=0, le=99.9)
    english_level: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=255)
    desired_salary_min: int | None = Field(default=None, ge=0)
    skills: list[str] | None = None
    summary: str | None = None


class ParsedResumeSection(BaseModel):
    """Structured resume section extracted from resume text by AI."""

    section_type: str = Field(..., max_length=100)
    title: str | None = Field(default=None, max_length=255)
    content: str
    order_index: int = Field(default=0, ge=0)


class ParsedResume(BaseModel):
    """Structured AI output for resume parsing."""

    candidate_profile: ParsedCandidateProfile
    sections: list[ParsedResumeSection]