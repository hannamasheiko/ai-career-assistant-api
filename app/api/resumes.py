from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.resume_ingestion import ResumeFromTextRequest, ResumeIngestionResponse
from app.services.resume_service import create_resume_from_text

router = APIRouter(
    prefix="/resumes",
    tags=["resumes"],
)


@router.post(
    "/from-text",
    response_model=ResumeIngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_resume_from_raw_text(
    data: ResumeFromTextRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        candidate_profile, resume_document, resume_sections = await create_resume_from_text(
            db=db,
            data=data,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return ResumeIngestionResponse(
        candidate_profile=candidate_profile,
        resume_document=resume_document,
        resume_sections=resume_sections,
    )