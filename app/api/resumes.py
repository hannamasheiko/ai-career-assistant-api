from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
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
async def create_resume_from_text_input(
    raw_text: str = Body(
        ...,
        media_type="text/plain",
        min_length=50,
        description="Plain resume text copied directly from a document.",
    ),
    candidate_profile_id: int | None = Query(default=None),
    file_name: str | None = Query(default="plain_text_resume.txt", max_length=255),
    db: AsyncSession = Depends(get_db),
):
    """Create a resume from plain text body without JSON escaping."""

    data = ResumeFromTextRequest(
        raw_text=raw_text,
        candidate_profile_id=candidate_profile_id,
        file_name=file_name,
    )

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