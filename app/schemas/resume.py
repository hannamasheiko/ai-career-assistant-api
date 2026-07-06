from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResumeSectionBase(BaseModel):
    """Shared resume section fields."""

    section_type: str = Field(..., max_length=100)
    title: str | None = Field(default=None, max_length=255)
    content: str
    order_index: int = Field(default=0, ge=0)


class ResumeSectionCreate(ResumeSectionBase):
    """Schema for creating a resume section."""

    pass


class ResumeSectionUpdate(BaseModel):
    """Schema for updating a resume section."""

    section_type: str | None = Field(default=None, max_length=100)
    title: str | None = Field(default=None, max_length=255)
    content: str | None = None
    order_index: int | None = Field(default=None, ge=0)


class ResumeSectionRead(ResumeSectionBase):
    """Schema for returning a resume section."""

    id: int
    resume_document_id: int

    model_config = ConfigDict(from_attributes=True)


class ResumeDocumentBase(BaseModel):
    """Shared resume document fields."""

    file_name: str | None = Field(default=None, max_length=255)
    file_type: str | None = Field(default=None, max_length=100)
    source_type: str = Field(default="manual_text", max_length=100)
    raw_text: str
    is_active: bool = True


class ResumeDocumentCreate(ResumeDocumentBase):
    """Schema for creating a resume document."""

    candidate_profile_id: int
    sections: list[ResumeSectionCreate] | None = None


class ResumeDocumentUpdate(BaseModel):
    """Schema for updating a resume document."""

    file_name: str | None = Field(default=None, max_length=255)
    file_type: str | None = Field(default=None, max_length=100)
    source_type: str | None = Field(default=None, max_length=100)
    raw_text: str | None = None
    is_active: bool | None = None


class ResumeDocumentRead(ResumeDocumentBase):
    """Schema for returning a resume document without nested sections."""

    id: int
    candidate_profile_id: int
    uploaded_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResumeDocumentWithSections(ResumeDocumentRead):
    """Schema for returning a resume document with nested sections."""

    sections: list[ResumeSectionRead] = Field(default_factory=list)