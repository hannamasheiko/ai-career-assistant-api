from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.generated_content import GeneratedContent
    from app.models.interaction import Interaction
    from app.models.match_analysis import MatchAnalysis
    from app.models.resume import ResumeDocument
    from app.models.vacancy import Vacancy


class TrackedVacancy(Base):
    """Tracked vacancy connected to a specific resume document and used for job search workflow."""

    __tablename__ = "tracked_vacancies"

    __table_args__ = (
        UniqueConstraint(
            "resume_document_id",
            "vacancy_id",
            name="uq_tracked_vacancies_resume_document_id_vacancy_id",
        ),
        CheckConstraint(
            """
            status IN (
                'saved',
                'analyzed',
                'resume_sent',
                'recruiter_contact',
                'screening',
                'interview',
                'test_task',
                'offer',
                'rejected',
                'discarded',
                'closed'
            )
            """,
            name="ck_tracked_vacancies_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high')",
            name="ck_tracked_vacancies_priority",
        ),
        CheckConstraint(
            """
            decision IN (
                'interested',
                'consider_later',
                'not_interested'
            )
            """,
            name="ck_tracked_vacancies_decision",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    resume_document_id: Mapped[int] = mapped_column(
        ForeignKey("resume_documents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    vacancy_id: Mapped[int] = mapped_column(
        ForeignKey("vacancies.id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(100),
        server_default="saved",
        nullable=False,
    )

    priority: Mapped[str] = mapped_column(
        String(100),
        server_default="low",
        nullable=False,
    )

    decision: Mapped[str] = mapped_column(
        String(100),
        server_default="interested",
        nullable=False,
    )

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

    resume_document: Mapped["ResumeDocument"] = relationship(
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