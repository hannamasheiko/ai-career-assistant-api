from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.resume import ResumeDocumentRead
from app.schemas.resume_ingestion import ResumeIngestionResponse
from app.services.candidate_profile_service import get_candidate_profile_by_user_id
from app.services.resume_service import (
    create_resume_from_text,
    get_resume_document_with_details_for_user,
    get_resume_documents_for_user,
)

router = APIRouter(
    prefix="/resumes",
    tags=["resumes"],
)


@router.post(
    "/from-text",
    response_model=ResumeIngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_resume_from_plain_text(
    raw_text: str = Body(
        ...,
        media_type="text/plain",
        min_length=50,
        description="Plain resume text copied directly from a document.",
    ),
    file_name: str | None = Query(
        default=None,
        description="Optional original file name or label for this resume.",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create resume document, resume analysis and sections from plain text."""

    candidate_profile = await get_candidate_profile_by_user_id(
        db=db,
        user_id=current_user.id,
    )

    if candidate_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found. Create your profile first.",
        )


    resume_document, resume_analysis, resume_sections = await create_resume_from_text(
        db=db,
        candidate_profile=candidate_profile,
        raw_text=raw_text,
        file_name=file_name,
        )


    return ResumeIngestionResponse(
        resume_document=resume_document,
        resume_analysis=resume_analysis,
        resume_sections=resume_sections,
    )


@router.get(
    "",
    response_model=list[ResumeDocumentRead],
)
async def get_resume_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ResumeDocumentRead]:
    """Get resume documents for current authenticated user."""

    resume_documents = await get_resume_documents_for_user(
        db=db,
        user_id=current_user.id,
    )

    return resume_documents


@router.get(
    "/{resume_document_id}",
    response_model=ResumeIngestionResponse,
)
async def get_resume_document(
    resume_document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeIngestionResponse:
    """Get resume document with analysis and sections for current authenticated user."""

    resume_document = await get_resume_document_with_details_for_user(
        db=db,
        resume_document_id=resume_document_id,
        user_id=current_user.id,
    )

    if resume_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume document not found.",
        )

    return ResumeIngestionResponse(
        resume_document=resume_document,
        resume_analysis=resume_document.analysis,
        resume_sections=sorted(
            resume_document.sections,
            key=lambda section: section.order_index,
        ),
    )