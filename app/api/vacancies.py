from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.vacancy import (
    VacancyAnalysisIngestionResponse,
    VacancyIngestionResponse,
)
from app.services.vacancy_service import (
    create_vacancy_analysis,
    create_vacancy_from_text,
)

router = APIRouter(
    prefix="/vacancies",
    tags=["vacancies"],
)


@router.post(
    "/from-text",
    response_model=VacancyIngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_vacancy_from_plain_text(
    raw_text: str = Body(..., media_type="text/plain"),
    analyze: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create vacancy from plain text and optionally generate AI vacancy analysis."""

    try:
        vacancy = await create_vacancy_from_text(
            db=db,
            raw_text=raw_text,
        )

        analysis = None

        if analyze:
            analysis = await create_vacancy_analysis(
                db=db,
                vacancy_id=vacancy.id,
            )

    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error

    return VacancyIngestionResponse(
        vacancy=vacancy,
        analysis=analysis,
    )


@router.post(
    "/{vacancy_id}/analysis",
    response_model=VacancyAnalysisIngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_vacancy_analysis(
    vacancy_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate AI analysis for an existing vacancy."""

    try:
        analysis = await create_vacancy_analysis(
            db=db,
            vacancy_id=vacancy_id,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error

    return VacancyAnalysisIngestionResponse(
        analysis=analysis,
    )