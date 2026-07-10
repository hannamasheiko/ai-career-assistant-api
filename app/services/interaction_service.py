from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.interaction import Interaction
from app.models.resume import ResumeDocument
from app.models.tracked_vacancy import TrackedVacancy
from app.schemas.interaction import InteractionCreate, InteractionUpdate


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

    interaction = Interaction(
        tracked_vacancy_id=tracked_vacancy.id,
        interaction_type=data.interaction_type,
        direction=data.direction,
        message_text=data.message_text,
        summary=data.summary,
        occurred_at=data.occurred_at,
    )

    db.add(interaction)

    if data.occurred_at is not None:
        tracked_vacancy.last_contact_at = data.occurred_at

    await db.commit()
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

