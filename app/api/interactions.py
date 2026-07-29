from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.interaction import (
    InteractionCreate,
    InteractionResponse,
    InteractionUpdate,
)
from app.services.interaction_service import (
    create_interaction,
    get_interaction_for_user,
    get_interactions_for_tracked_vacancy,
    get_tracked_vacancy_for_interaction,
    update_interaction,
)


router = APIRouter(
    prefix="/tracked-vacancies",
    tags=["interactions"],
)

@router.post(
    "/{tracked_vacancy_id}/interactions",
    response_model=InteractionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_interaction_endpoint(
    tracked_vacancy_id: int,
    data: InteractionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InteractionResponse:
    """Create interaction for tracked vacancy."""

    tracked_vacancy = await get_tracked_vacancy_for_interaction(
        db=db,
        tracked_vacancy_id=tracked_vacancy_id,
        user_id=current_user.id,
    )

    if tracked_vacancy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tracked vacancy not found.",
        )

    interaction = await create_interaction(
        db=db,
        tracked_vacancy=tracked_vacancy,
        data=data,
    )

    return interaction

@router.get(
    "/{tracked_vacancy_id}/interactions",
    response_model=list[InteractionResponse],
)
async def get_interactions_for_tracked_vacancy_endpoint(
    tracked_vacancy_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[InteractionResponse]:
    """Get interactions for tracked vacancy."""

    tracked_vacancy = await get_tracked_vacancy_for_interaction(
        db=db,
        tracked_vacancy_id=tracked_vacancy_id,
        user_id=current_user.id,
    )

    if tracked_vacancy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tracked vacancy not found.",
        )

    interactions = await get_interactions_for_tracked_vacancy(
        db=db,
        tracked_vacancy_id=tracked_vacancy.id,
        user_id=current_user.id,
    )

    return interactions

@router.get(
    "/interactions/{interaction_id}",
    response_model=InteractionResponse,
)
async def get_interaction_endpoint(
    interaction_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InteractionResponse:
    """Get interaction by id for current user."""

    interaction = await get_interaction_for_user(
        db=db,
        interaction_id=interaction_id,
        user_id=current_user.id,
    )

    if interaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interaction not found.",
        )

    return interaction

@router.patch(
    "/interactions/{interaction_id}",
    response_model=InteractionResponse,
)
async def update_interaction_endpoint(
    interaction_id: int,
    data: InteractionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InteractionResponse:
    """Update interaction for current user."""

    interaction = await get_interaction_for_user(
        db=db,
        interaction_id=interaction_id,
        user_id=current_user.id,
    )

    if interaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interaction not found.",
        )

    updated_interaction = await update_interaction(
        db=db,
        interaction=interaction,
        data=data,
    )

    return updated_interaction
