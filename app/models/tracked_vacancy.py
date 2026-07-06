from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.candidate_profile import CandidateProfile
    from app.models.generated_content import GeneratedContent
    from app.models.match_analysis import MatchAnalysis
    from app.models.vacancy import Vacancy
    from app.models.interaction import Interaction


class TrackedVacancy(Base):
    """Tracked vacancy connected to a candidate profile and used for job search workflow."""

    __tablename__ = "tracked_vacancies"

    id: Mapped[int] = mapped_column(primary_key=True)

    candidate_profile_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    vacancy_id: Mapped[int] = mapped_column(
        ForeignKey("vacancies.id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(String(100), server_default="saved", nullable=False)
    priority: Mapped[str | None] = mapped_column(String(100), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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

    candidate_profile: Mapped["CandidateProfile"] = relationship(
        back_populates="tracked_vacancies",
    )

    vacancy: Mapped["Vacancy"] = relationship(
        back_populates="tracked_vacancies",
    )

    match_analyses: Mapped[list["MatchAnalysis"]] = relationship(
        back_populates="tracked_vacancy",
        cascade="all, delete-orphan",
    )

    generated_contents: Mapped[list["GeneratedContent"]] = relationship(
        back_populates="tracked_vacancy",
        cascade="all, delete-orphan",
    )
    interactions: Mapped[list["Interaction"]] = relationship(
        back_populates="tracked_vacancy",
        cascade="all, delete-orphan",
    )