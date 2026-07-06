from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.tracked_vacancy import TrackedVacancy


class Interaction(Base):
    """Communication or event related to a tracked vacancy."""

    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(primary_key=True)

    tracked_vacancy_id: Mapped[int] = mapped_column(
        ForeignKey("tracked_vacancies.id", ondelete="CASCADE"),
        nullable=False,
    )

    interaction_type: Mapped[str] = mapped_column(String(100), nullable=False)
    direction: Mapped[str | None] = mapped_column(String(50), nullable=True)

    message_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
        back_populates="interactions",
    )