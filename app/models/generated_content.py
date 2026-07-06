from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.tracked_vacancy import TrackedVacancy


class GeneratedContent(Base):
    """AI-generated content connected to a tracked vacancy."""

    __tablename__ = "generated_contents"

    id: Mapped[int] = mapped_column(primary_key=True)

    tracked_vacancy_id: Mapped[int] = mapped_column(
        ForeignKey("tracked_vacancies.id", ondelete="CASCADE"),
        nullable=False,
    )

    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    generated_text: Mapped[str] = mapped_column(Text, nullable=False)

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
        back_populates="generated_contents",
    )