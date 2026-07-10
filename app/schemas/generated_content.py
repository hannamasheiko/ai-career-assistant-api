from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GeneratedContentGenerateRequest(BaseModel):
    """Request schema for AI-generated content generation."""

    content_type: str = Field(..., max_length=100)
    language: str = Field(default="uk", max_length=20)
    tone: str | None = Field(default="professional", max_length=100)
    extra_instructions: str | None = None


class GeneratedContentUpdate(BaseModel):
    """Schema for updating generated content."""

    generated_text: str | None = None
    prompt_context: dict[str, Any] | None = None


class GeneratedContentResponse(BaseModel):
    """Response schema for generated content data."""

    id: int
    tracked_vacancy_id: int

    content_type: str
    prompt_context: dict[str, Any] | None
    generated_text: str

    ai_model: str | None
    prompt_version: str | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

