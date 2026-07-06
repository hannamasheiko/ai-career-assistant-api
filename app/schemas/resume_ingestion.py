from pydantic import BaseModel, Field

from app.schemas.candidate_profile import CandidateProfileRead
from app.schemas.resume import ResumeDocumentRead, ResumeSectionRead


class ResumeFromTextRequest(BaseModel):
    """Request schema for adding a resume from raw text."""

    raw_text: str = Field(..., min_length=50)
    candidate_profile_id: int | None = None
    file_name: str | None = Field(default=None, max_length=255)


class ResumeIngestionResponse(BaseModel):
    """Response schema for resume ingestion flow."""

    candidate_profile: CandidateProfileRead
    resume_document: ResumeDocumentRead
    resume_sections: list[ResumeSectionRead]