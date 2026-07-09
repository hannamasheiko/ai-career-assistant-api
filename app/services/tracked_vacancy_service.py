from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume import ResumeDocument
from app.models.tracked_vacancy import TrackedVacancy
from app.models.vacancy import Vacancy
from app.schemas.tracked_vacancy import TrackedVacancyCreate, TrackedVacancyUpdate


async def get_resume_document_for_user(
    db: AsyncSession,
    resume_document_id: int,
    user_id: int,
) -> ResumeDocument | None:
    """Get resume document if it belongs to current user."""

    result = await db.execute(
        select(ResumeDocument).where(
            ResumeDocument.id == resume_document_id,
            ResumeDocument.candidate_profile.has(user_id=user_id),
        )
    )

    return result.scalar_one_or_none()


async def get_vacancy_by_id(
    db: AsyncSession,
    vacancy_id: int,
) -> Vacancy | None:
    """Get vacancy by id."""

    result = await db.execute(
        select(Vacancy).where(Vacancy.id == vacancy_id)
    )

    return result.scalar_one_or_none()


async def get_tracked_vacancy_for_user(
    db: AsyncSession,
    tracked_vacancy_id: int,
    user_id: int,
) -> TrackedVacancy | None:
    """Get tracked vacancy if it belongs to current user."""

    result = await db.execute(
        select(TrackedVacancy).where(
            TrackedVacancy.id == tracked_vacancy_id,
            TrackedVacancy.resume_document.has(
                ResumeDocument.candidate_profile.has(user_id=user_id)
            ),
        )
    )

    return result.scalar_one_or_none()


async def get_tracked_vacancies_for_user(
    db: AsyncSession,
    user_id: int,
) -> list[TrackedVacancy]:
    """Get all tracked vacancies for current user."""

    result = await db.execute(
        select(TrackedVacancy).where(
            TrackedVacancy.resume_document.has(
                ResumeDocument.candidate_profile.has(user_id=user_id)
            )
        )
    )

    return list(result.scalars().all())


async def get_existing_tracked_vacancy(
    db: AsyncSession,
    resume_document_id: int,
    vacancy_id: int,
) -> TrackedVacancy | None:
    """Get existing tracked vacancy for resume and vacancy pair."""

    result = await db.execute(
        select(TrackedVacancy).where(
            TrackedVacancy.resume_document_id == resume_document_id,
            TrackedVacancy.vacancy_id == vacancy_id,
        )
    )

    return result.scalar_one_or_none()


async def create_tracked_vacancy(
    db: AsyncSession,
    data: TrackedVacancyCreate,
) -> TrackedVacancy:
    """Create tracked vacancy."""

    tracked_vacancy = TrackedVacancy(
        resume_document_id=data.resume_document_id,
        vacancy_id=data.vacancy_id,
        status=data.status,
        priority=data.priority,
        decision=data.decision,
        notes=data.notes,
        applied_at=data.applied_at,
        last_contact_at=data.last_contact_at,
        next_action_at=data.next_action_at,
    )

    db.add(tracked_vacancy)
    await db.commit()
    await db.refresh(tracked_vacancy)

    return tracked_vacancy


async def update_tracked_vacancy(
    db: AsyncSession,
    tracked_vacancy: TrackedVacancy,
    data: TrackedVacancyUpdate,
) -> TrackedVacancy:
    """Update tracked vacancy."""

    update_data = data.model_dump(exclude_unset=True)

    for field_name, field_value in update_data.items():
        setattr(tracked_vacancy, field_name, field_value)

    await db.commit()
    await db.refresh(tracked_vacancy)

    return tracked_vacancy