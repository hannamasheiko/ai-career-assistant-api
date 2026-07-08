from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chains.parse_resume_chain import parse_resume_chain
from app.core.config import settings
from app.models.candidate_profile import CandidateProfile
from app.models.resume import ResumeDocument, ResumeSection
from app.models.resume_analysis import ResumeAnalysis
from app.services.experience_calculator import calculate_years_of_experience


async def create_resume_from_text(
    db: AsyncSession,
    candidate_profile: CandidateProfile,
    raw_text: str,
    file_name: str | None = None,
) -> tuple[ResumeDocument, ResumeAnalysis, list[ResumeSection]]:
    """Create resume document, resume analysis and resume sections from raw text."""

    parsed_resume = await parse_resume_chain(raw_text)

    parsed_analysis = parsed_resume.resume_analysis

    years_of_experience = calculate_years_of_experience(
        parsed_resume.work_experience_periods,
    )

    resume_document = ResumeDocument(
        candidate_profile_id=candidate_profile.id,
        file_name=file_name,
        file_type=None,
        source_type="manual_text",
        raw_text=raw_text,
        is_active=True,
    )
    db.add(resume_document)
    await db.flush()

    resume_analysis = ResumeAnalysis(
        resume_document_id=resume_document.id,
        full_name=parsed_analysis.full_name,
        target_role=parsed_analysis.target_role,
        years_of_experience=years_of_experience,
        english_level=parsed_analysis.english_level,
        location=parsed_analysis.location,
        skills=parsed_analysis.skills,
        summary=parsed_analysis.summary,
        education_level=parsed_analysis.education_level,
        education_summary=parsed_analysis.education_summary,
        languages=parsed_analysis.languages,
        ai_model=settings.openai_model,
        prompt_version="resume_parsing_v1",
    )
    db.add(resume_analysis)

    resume_sections = [
        ResumeSection(
            resume_document_id=resume_document.id,
            section_type=section.section_type,
            title=section.title,
            content=section.content,
            order_index=section.order_index,
        )
        for section in parsed_resume.sections
    ]

    db.add_all(resume_sections)

    await db.commit()

    await db.refresh(resume_document)
    await db.refresh(resume_analysis)

    for section in resume_sections:
        await db.refresh(section)

    return resume_document, resume_analysis, resume_sections