from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.interaction import Interaction
from app.models.resume import ResumeDocument
from app.models.tracked_vacancy import TrackedVacancy
from app.schemas.interaction import InteractionCreate, InteractionUpdate
from app.schemas.interaction_enums import InteractionType
from app.schemas.tracked_vacancy_enums import (
    TrackedVacancyDecision,
    TrackedVacancyPriority,
)
from app.services.interaction_rules import (
    find_direction_violation,
    find_status_violation,
    next_status,
)


class InvalidInteractionError(ValueError):
    """Interaction data violates a domain rule."""


class DuplicateResumeSentInteractionError(ValueError):
    """A resume-sent lifecycle event already exists."""


class InvalidInteractionTransitionError(ValueError):
    """Interaction cannot transition the tracked vacancy from its status."""


async def get_tracked_vacancy_for_interaction(
    db: AsyncSession,
    tracked_vacancy_id: int,
    user_id: int,
) -> TrackedVacancy | None:
    """Get tracked vacancy if it belongs to current user."""

    result = await db.execute(
        select(TrackedVacancy)
        .options(
            selectinload(TrackedVacancy.resume_document),
        )
        .where(
            TrackedVacancy.id == tracked_vacancy_id,
            TrackedVacancy.resume_document.has(
                ResumeDocument.candidate_profile.has(user_id=user_id)
            ),
        )
    )

    return result.scalar_one_or_none()


async def get_interaction_for_user(
    db: AsyncSession,
    interaction_id: int,
    user_id: int,
) -> Interaction | None:
    """Get interaction if it belongs to current user."""

    result = await db.execute(
        select(Interaction).where(
            Interaction.id == interaction_id,
            Interaction.tracked_vacancy.has(
                TrackedVacancy.resume_document.has(
                    ResumeDocument.candidate_profile.has(user_id=user_id)
                )
            ),
        )
    )

    return result.scalar_one_or_none()


async def get_interactions_for_tracked_vacancy(
    db: AsyncSession,
    tracked_vacancy_id: int,
    user_id: int,
) -> list[Interaction]:
    """Get interactions for tracked vacancy if it belongs to current user."""

    result = await db.execute(
        select(Interaction)
        .where(
            Interaction.tracked_vacancy_id == tracked_vacancy_id,
            Interaction.tracked_vacancy.has(
                TrackedVacancy.resume_document.has(
                    ResumeDocument.candidate_profile.has(user_id=user_id)
                )
            ),
        )
        .order_by(Interaction.occurred_at.desc().nullslast(), Interaction.created_at.desc())
    )

    return list(result.scalars().all())


async def create_interaction(
    db: AsyncSession,
    tracked_vacancy: TrackedVacancy,
    data: InteractionCreate,
) -> Interaction:
    """Create interaction for tracked vacancy."""

    direction_error = find_direction_violation(
        interaction_type=data.interaction_type,
        direction=data.direction,
    )

    if direction_error is not None:
        raise InvalidInteractionError(direction_error)

    status_error = find_status_violation(
        interaction_type=data.interaction_type,
        status=tracked_vacancy.status,
    )

    if status_error is not None:
        raise InvalidInteractionTransitionError(status_error)

    if data.interaction_type == InteractionType.RESUME_SENT:
        existing_result = await db.execute(
            select(Interaction.id).where(
                Interaction.tracked_vacancy_id == tracked_vacancy.id,
                Interaction.interaction_type == InteractionType.RESUME_SENT,
            )
        )

        if existing_result.scalar_one_or_none() is not None:
            raise DuplicateResumeSentInteractionError(
                "A resume_sent interaction already exists for this "
                "tracked vacancy."
            )

    interaction = Interaction(
        tracked_vacancy_id=tracked_vacancy.id,
        interaction_type=data.interaction_type,
        direction=data.direction,
        message_text=data.message_text,
        summary=data.summary,
        occurred_at=data.occurred_at,
    )

    db.add(interaction)

    tracked_vacancy.status = next_status(
        status=tracked_vacancy.status,
        interaction_type=data.interaction_type,
        direction=data.direction,
    )

    if data.interaction_type == InteractionType.RESUME_SENT:
        tracked_vacancy.applied_at = data.occurred_at

    if data.interaction_type == InteractionType.REJECTION:
        tracked_vacancy.priority = TrackedVacancyPriority.LOW
        tracked_vacancy.decision = TrackedVacancyDecision.NOT_INTERESTED
        tracked_vacancy.closed_at = data.occurred_at

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    await db.refresh(interaction)

    return interaction


async def update_interaction(
    db: AsyncSession,
    interaction: Interaction,
    data: InteractionUpdate,
) -> Interaction:
    """Update interaction."""

    update_data = data.model_dump(exclude_unset=True)

    for field_name, field_value in update_data.items():
        setattr(interaction, field_name, field_value)

    await db.commit()
    await db.refresh(interaction)

    return interaction
