from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate_profile import CandidateProfile
from app.schemas.candidate_profile import CandidateProfileCreate, CandidateProfileUpdate


async def get_candidate_profile_by_user_id(
    db: AsyncSession,
    user_id: int,
) -> CandidateProfile | None:
    """Get candidate profile by user id."""

    result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_candidate_profile(
    db: AsyncSession,
    user_id: int,
    data: CandidateProfileCreate,
) -> CandidateProfile:
    """Create candidate profile for a user."""

    candidate_profile = CandidateProfile(
        user_id=user_id,
        full_name=data.full_name,
        email=str(data.email),
        phone=data.phone,
        location=data.location,
        github_url=data.github_url,
        linkedin_url=data.linkedin_url,
        preferred_employment_types=data.preferred_employment_types,
        preferred_work_formats=data.preferred_work_formats,
        desired_salary_min=data.desired_salary_min,
    )

    db.add(candidate_profile)
    await db.commit()
    await db.refresh(candidate_profile)

    return candidate_profile


async def update_candidate_profile(
    db: AsyncSession,
    candidate_profile: CandidateProfile,
    data: CandidateProfileUpdate,
) -> CandidateProfile:
    """Update candidate profile."""

    update_data = data.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"] is not None:
        update_data["email"] = str(update_data["email"])

    for field_name, field_value in update_data.items():
        setattr(candidate_profile, field_name, field_value)

    await db.commit()
    await db.refresh(candidate_profile)

    return candidate_profile