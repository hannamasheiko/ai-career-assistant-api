from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.tracked_vacancy import TrackedVacancy


class MatchAnalysis(Base):
    """AI-generated match analysis between a candidate  and a tracked vacancy."""

    __tablename__ = "match_analyses"

    __table_args__ = (
        UniqueConstraint(
            "tracked_vacancy_id",
            name="uq_match_analyses_tracked_vacancy_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    tracked_vacancy_id: Mapped[int] = mapped_column(
        ForeignKey("tracked_vacancies.id", ondelete="CASCADE"),
        nullable=False,
    )

    match_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(100), nullable=True)

    strong_matches: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    partial_matches: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    missing_skills: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    risk_points: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    reasoning_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    tracked_vacancy: Mapped["TrackedVacancy"] = relationship(
        back_populates="match_analyses",
    )