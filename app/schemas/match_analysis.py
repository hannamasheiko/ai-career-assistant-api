from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MatchAnalysisResponse(BaseModel):
    """Response schema for match analysis data."""

    id: int
    tracked_vacancy_id: int

    match_score: int | None = Field(default=None, ge=0, le=100)
    recommendation: str | None

    strong_matches: list[str] | None
    partial_matches: list[str] | None
    missing_skills: list[str] | None
    risk_points: list[str] | None

    reasoning_summary: str | None

    ai_model: str | None
    prompt_version: str | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)