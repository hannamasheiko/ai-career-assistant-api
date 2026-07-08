from pydantic import BaseModel, Field


class ParsedResumeAnalysis(BaseModel):
    """Structured resume analysis extracted from resume text by AI."""

    full_name: str = Field(..., max_length=255)
    target_role: str | None = Field(default=None, max_length=255)
    years_of_experience: float | None = Field(default=None, ge=0, le=99.9)
    english_level: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=255)

    skills: list[str] | None = None
    summary: str | None = None

    education_level: str | None = Field(default=None, max_length=100)
    education_summary: str | None = None
    languages: list[str] | None = None


class ParsedResumeSection(BaseModel):
    """Structured resume section extracted from resume text by AI."""

    section_type: str = Field(..., max_length=100)
    title: str | None = Field(default=None, max_length=255)
    content: str
    order_index: int = Field(default=0, ge=0)

class ParsedWorkExperiencePeriod(BaseModel):
    """Structured work experience period extracted from resume text by AI."""

    company_name: str | None = Field(default=None, max_length=255)
    position_title: str | None = Field(default=None, max_length=255)

    start_month: int | None = Field(default=None, ge=1, le=12)
    start_year: int | None = Field(default=None, ge=1950, le=2100)

    end_month: int | None = Field(default=None, ge=1, le=12)
    end_year: int | None = Field(default=None, ge=1950, le=2100)

    is_current: bool = False
    is_commercial: bool = True

class ParsedResume(BaseModel):
    """Structured AI output for resume parsing."""

    work_experience_periods: list[ParsedWorkExperiencePeriod] | None = None
    resume_analysis: ParsedResumeAnalysis
    sections: list[ParsedResumeSection]