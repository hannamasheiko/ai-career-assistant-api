from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.tracked_vacancy import (
    TrackedVacancyCreate,
    TrackedVacancyResponse,
    TrackedVacancyUpdate,
)
from app.services.tracked_vacancy_service import (
    create_tracked_vacancy,
    get_existing_tracked_vacancy,
    get_resume_document_for_user,
    get_tracked_vacancies_for_user,
    get_tracked_vacancy_for_user,
    get_vacancy_by_id,
    update_tracked_vacancy,
)

router = APIRouter(
    prefix="/tracked-vacancies",
    tags=["tracked-vacancies"],
)


@router.post(
    "",
    response_model=TrackedVacancyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tracked_vacancy_endpoint(
    data: TrackedVacancyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrackedVacancyResponse:
    """Create tracked vacancy for current user."""

    resume_document = await get_resume_document_for_user(
        db=db,
        resume_document_id=data.resume_document_id,
        user_id=current_user.id,
    )

    if resume_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume document not found.",
        )

    vacancy = await get_vacancy_by_id(
        db=db,
        vacancy_id=data.vacancy_id,
    )

    if vacancy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vacancy not found.",
        )

    existing_tracked_vacancy = await get_existing_tracked_vacancy(
        db=db,
        resume_document_id=data.resume_document_id,
        vacancy_id=data.vacancy_id,
    )

    if existing_tracked_vacancy is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This vacancy is already tracked for this resume.",
        )

    tracked_vacancy = await create_tracked_vacancy(
        db=db,
        data=data,
    )

    return tracked_vacancy


@router.get(
    "",
    response_model=list[TrackedVacancyResponse],
)
async def get_tracked_vacancies_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TrackedVacancyResponse]:
    """Get tracked vacancies for current user."""

    tracked_vacancies = await get_tracked_vacancies_for_user(
        db=db,
        user_id=current_user.id,
    )

    return tracked_vacancies


@router.get(
    "/{tracked_vacancy_id}",
    response_model=TrackedVacancyResponse,
)
async def get_tracked_vacancy_endpoint(
    tracked_vacancy_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrackedVacancyResponse:
    """Get tracked vacancy by id for current user."""

    tracked_vacancy = await get_tracked_vacancy_for_user(
        db=db,
        tracked_vacancy_id=tracked_vacancy_id,
        user_id=current_user.id,
    )

    if tracked_vacancy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tracked vacancy not found.",
        )

    return tracked_vacancy


@router.patch(
    "/{tracked_vacancy_id}",
    response_model=TrackedVacancyResponse,
)
async def update_tracked_vacancy_endpoint(
    tracked_vacancy_id: int,
    data: TrackedVacancyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrackedVacancyResponse:
    """Update tracked vacancy for current user."""

    tracked_vacancy = await get_tracked_vacancy_for_user(
        db=db,
        tracked_vacancy_id=tracked_vacancy_id,
        user_id=current_user.id,
    )

    if tracked_vacancy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tracked vacancy not found.",
        )

    updated_tracked_vacancy = await update_tracked_vacancy(
        db=db,
        tracked_vacancy=tracked_vacancy,
        data=data,
    )

    return updated_tracked_vacancy