from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.resume import ResumeDocument
    from app.models.tracked_vacancy import TrackedVacancy


class CandidateProfile(Base):
    """Candidate profile with general career information used for resume analysis and vacancy matching."""

    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    experience_level: Mapped[str | None] = mapped_column(String(100), nullable=True)
    years_of_experience: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    english_level: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    desired_salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    skills: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

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

    resume_documents: Mapped[list["ResumeDocument"]] = relationship(
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )

    tracked_vacancies: Mapped[list["TrackedVacancy"]] = relationship(
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )