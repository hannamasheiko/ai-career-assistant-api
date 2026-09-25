from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume import ResumeDocument
from app.models.tracked_vacancy import TrackedVacancy
from app.models.vacancy import Vacancy
from app.schemas.tracked_vacancy import TrackedVacancyCreate, TrackedVacancyUpdate
from app.schemas.tracked_vacancy_enums import TrackedVacancyStatus


class InvalidTrackedVacancyStatusChangeError(ValueError):
    """Status cannot be set manually."""


# Statuses the user sets by hand, from any other status.
MANUAL_CLOSING_STATUSES = frozenset(
    {TrackedVacancyStatus.DISCARDED, TrackedVacancyStatus.CLOSED}
)

# Where a manually closed tracked vacancy can be sent back.
REOPEN_STATUSES = frozenset(
    {TrackedVacancyStatus.SAVED, TrackedVacancyStatus.ANALYZED}
)


def validate_manual_status_change(
    current_status: TrackedVacancyStatus,
    new_status: TrackedVacancyStatus,
) -> None:
    """Allow only discarded/closed and the return from them by hand.

    Every other status is produced by interactions, never set directly.
    """

    if new_status == current_status:
        return

    if new_status in MANUAL_CLOSING_STATUSES:
        return

    if (
        current_status in MANUAL_CLOSING_STATUSES
        and new_status in REOPEN_STATUSES
    ):
        return

    raise InvalidTrackedVacancyStatusChangeError(
        "Tracked vacancy status cannot be changed manually from "
        f"{current_status} to {new_status}. Only discarded and closed can "
        "be set manually; the other statuses come from interactions."
    )


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
        closed_at=data.closed_at,
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
    new_status = update_data.get("status")

    if new_status is not None and new_status != tracked_vacancy.status:
        validate_manual_status_change(
            current_status=tracked_vacancy.status,
            new_status=new_status,
        )

        if new_status in MANUAL_CLOSING_STATUSES:
            update_data.setdefault("closed_at", datetime.now(timezone.utc))
        elif tracked_vacancy.status in MANUAL_CLOSING_STATUSES:
            update_data.setdefault("closed_at", None)

    for field_name, field_value in update_data.items():
        setattr(tracked_vacancy, field_name, field_value)

    await db.commit()
    await db.refresh(tracked_vacancy)

    return tracked_vacancy
