from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.generated_content import (
    GeneratedContentGenerateRequest,
    GeneratedContentResponse,
    GeneratedContentUpdate,
)
from app.services.generated_content_service import (
    generate_and_save_content,
    get_generated_content_for_user,
    get_generated_contents_for_tracked_vacancy,
    get_tracked_vacancy_for_generated_content,
    update_generated_content,
)

router = APIRouter(
    prefix="/tracked-vacancies",
    tags=["generated-content"],
)


@router.post(
    "/{tracked_vacancy_id}/generated-content/generate",
    response_model=GeneratedContentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_content_endpoint(
    tracked_vacancy_id: int,
    data: GeneratedContentGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GeneratedContentResponse:
    """Generate AI content for tracked vacancy."""

    tracked_vacancy = await get_tracked_vacancy_for_generated_content(
        db=db,
        tracked_vacancy_id=tracked_vacancy_id,
        user_id=current_user.id,
    )

    if tracked_vacancy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tracked vacancy not found.",
        )

    try:
        generated_content = await generate_and_save_content(
            db=db,
            tracked_vacancy=tracked_vacancy,
            data=data,
            ai_model=settings.openai_model,
            prompt_version="generated_content_cover_letter_v1",
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error

    return generated_content


@router.get(
    "/{tracked_vacancy_id}/generated-content",
    response_model=list[GeneratedContentResponse],
)
async def get_generated_contents_for_tracked_vacancy_endpoint(
    tracked_vacancy_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GeneratedContentResponse]:
    """Get generated contents for tracked vacancy."""

    tracked_vacancy = await get_tracked_vacancy_for_generated_content(
        db=db,
        tracked_vacancy_id=tracked_vacancy_id,
        user_id=current_user.id,
    )

    if tracked_vacancy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tracked vacancy not found.",
        )

    generated_contents = await get_generated_contents_for_tracked_vacancy(
        db=db,
        tracked_vacancy_id=tracked_vacancy.id,
        user_id=current_user.id,
    )

    return generated_contents


@router.get(
    "/generated-content/{generated_content_id}",
    response_model=GeneratedContentResponse,
)
async def get_generated_content_endpoint(
    generated_content_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GeneratedContentResponse:
    """Get generated content by id for current user."""

    generated_content = await get_generated_content_for_user(
        db=db,
        generated_content_id=generated_content_id,
        user_id=current_user.id,
    )

    if generated_content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated content not found.",
        )

    return generated_content


@router.patch(
    "/generated-content/{generated_content_id}",
    response_model=GeneratedContentResponse,
)
async def update_generated_content_endpoint(
    generated_content_id: int,
    data: GeneratedContentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GeneratedContentResponse:
    """Update generated content for current user."""

    generated_content = await get_generated_content_for_user(
        db=db,
        generated_content_id=generated_content_id,
        user_id=current_user.id,
    )

    if generated_content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated content not found.",
        )

    updated_generated_content = await update_generated_content(
        db=db,
        generated_content=generated_content,
        data=data,
    )

    return updated_generated_content