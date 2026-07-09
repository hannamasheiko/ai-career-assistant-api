from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.vacancy import VacancyIngestionResponse
from app.services.vacancy_service import create_vacancy_from_text

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
    raw_text: str = Body(
        ...,
        media_type="text/plain",
        min_length=50,
        description="Plain vacancy text copied directly from a job board page.",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create vacancy from plain text copied from a job board page."""

    try:
        vacancy = await create_vacancy_from_text(
            db=db,
            raw_text=raw_text,
        )
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error

    return VacancyIngestionResponse(
        vacancy=vacancy,
    )