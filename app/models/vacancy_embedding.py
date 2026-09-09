from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.vacancy import Vacancy, VacancyAnalysis


class VacancyEmbedding(Base):
    """Vector representation of the current analysis of a vacancy."""

    __tablename__ = "vacancy_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)

    vacancy_id: Mapped[int] = mapped_column(
        ForeignKey("vacancies.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    vacancy_analysis_id: Mapped[int] = mapped_column(
        ForeignKey("vacancy_analyses.id", ondelete="CASCADE"),
        nullable=False,
    )

    source_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    embedding: Mapped[list[float]] = mapped_column(
        VECTOR(1536),
        nullable=False,
    )

    embedding_model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    embedding_input_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

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
        back_populates="embedding",
    )

    vacancy_analysis: Mapped["VacancyAnalysis"] = relationship(
        back_populates="embedding",
    )
