from pydantic import BaseModel, Field

from app.schemas.resume import ResumeDocumentRead, ResumeSectionRead
from app.schemas.resume_analysis import ResumeAnalysisRead


class ResumeFromTextRequest(BaseModel):
    """Schema for creating a resume from plain text."""

    raw_text: str = Field(..., min_length=50)
    file_name: str | None = None


class ResumeIngestionResponse(BaseModel):
    """Response schema for resume ingestion."""

    resume_document: ResumeDocumentRead
    resume_analysis: ResumeAnalysisRead
    resume_sections: list[ResumeSectionRead]