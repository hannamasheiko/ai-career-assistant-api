from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.tracked_vacancy import TrackedVacancy


class Vacancy(Base):
    """Vacancy with raw text, cleaned text, and basic job information."""

    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(primary_key=True)

    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position_title: Mapped[str] = mapped_column(String(255), nullable=False)

    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    work_format: Mapped[str | None] = mapped_column(String(100), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(20), nullable=True)

    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    cleaned_text: Mapped[str | None] = mapped_column(Text, nullable=True)

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

    analyses: Mapped[list["VacancyAnalysis"]] = relationship(
        back_populates="vacancy",
        cascade="all, delete-orphan",
    )

    tracked_vacancies: Mapped[list["TrackedVacancy"]] = relationship(
        back_populates="vacancy",
        cascade="all, delete-orphan",
    )


class VacancyAnalysis(Base):
    """AI-generated structured analysis of a vacancy."""

    __tablename__ = "vacancy_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)

    vacancy_id: Mapped[int] = mapped_column(
        ForeignKey("vacancies.id", ondelete="CASCADE"),
        nullable=False,
    )

    experience_level: Mapped[str | None] = mapped_column(String(100), nullable=True)
    english_level: Mapped[str | None] = mapped_column(String(100), nullable=True)

    required_skills: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    optional_skills: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    responsibilities: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    red_flags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    green_flags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(100), nullable=True)

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

    vacancy: Mapped["Vacancy"] = relationship(
        back_populates="analyses",
    )