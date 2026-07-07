from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.candidate_profile import (
    CandidateProfileCreate,
    CandidateProfileRead,
    CandidateProfileUpdate,
)
from app.services.candidate_profile_service import (
    create_candidate_profile,
    get_candidate_profile_by_user_id,
    update_candidate_profile,
)

router = APIRouter(
    prefix="/profile",
    tags=["profile"],
)


@router.post(
    "",
    response_model=CandidateProfileRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_my_candidate_profile(
    data: CandidateProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create candidate profile for current authenticated user."""

    existing_profile = await get_candidate_profile_by_user_id(
        db=db,
        user_id=current_user.id,
    )

    if existing_profile is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidate profile already exists for this user",
        )

    return await create_candidate_profile(
        db=db,
        user_id=current_user.id,
        data=data,
    )


@router.get(
    "/me",
    response_model=CandidateProfileRead,
)
async def read_my_candidate_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return candidate profile for current authenticated user."""

    candidate_profile = await get_candidate_profile_by_user_id(
        db=db,
        user_id=current_user.id,
    )

    if candidate_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found",
        )

    return candidate_profile


@router.patch(
    "/me",
    response_model=CandidateProfileRead,
)
async def update_my_candidate_profile(
    data: CandidateProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update candidate profile for current authenticated user."""

    candidate_profile = await get_candidate_profile_by_user_id(
        db=db,
        user_id=current_user.id,
    )

    if candidate_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found",
        )

    return await update_candidate_profile(
        db=db,
        candidate_profile=candidate_profile,
        data=data,
    )