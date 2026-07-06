from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chains.parse_resume_chain import parse_resume_chain
from app.models.candidate_profile import CandidateProfile
from app.models.resume import ResumeDocument, ResumeSection
from app.schemas.resume_ingestion import ResumeFromTextRequest


async def create_resume_from_text(
    db: AsyncSession,
    data: ResumeFromTextRequest,
) -> tuple[CandidateProfile, ResumeDocument, list[ResumeSection]]:
    """Create or update candidate profile and save resume document with parsed sections."""

    parsed_resume = await parse_resume_chain(data.raw_text)

    if data.candidate_profile_id is None:
        candidate_profile = CandidateProfile(
            full_name=parsed_resume.candidate_profile.full_name,
            target_role=parsed_resume.candidate_profile.target_role,
            experience_level=parsed_resume.candidate_profile.experience_level,
            years_of_experience=parsed_resume.candidate_profile.years_of_experience,
            english_level=parsed_resume.candidate_profile.english_level,
            location=parsed_resume.candidate_profile.location,
            desired_salary_min=parsed_resume.candidate_profile.desired_salary_min,
            skills=parsed_resume.candidate_profile.skills,
            summary=parsed_resume.candidate_profile.summary,
        )
        db.add(candidate_profile)
        await db.flush()
    else:
        candidate_profile = await db.get(CandidateProfile, data.candidate_profile_id)

        if candidate_profile is None:
            raise ValueError("Candidate profile not found")

        candidate_profile.full_name = parsed_resume.candidate_profile.full_name
        candidate_profile.target_role = parsed_resume.candidate_profile.target_role
        candidate_profile.experience_level = parsed_resume.candidate_profile.experience_level
        candidate_profile.years_of_experience = parsed_resume.candidate_profile.years_of_experience
        candidate_profile.english_level = parsed_resume.candidate_profile.english_level
        candidate_profile.location = parsed_resume.candidate_profile.location
        candidate_profile.desired_salary_min = parsed_resume.candidate_profile.desired_salary_min
        candidate_profile.skills = parsed_resume.candidate_profile.skills
        candidate_profile.summary = parsed_resume.candidate_profile.summary

    resume_document = ResumeDocument(
        candidate_profile_id=candidate_profile.id,
        file_name=data.file_name,
        file_type=None,
        source_type="manual_text",
        raw_text=data.raw_text,
        is_active=True,
    )
    db.add(resume_document)
    await db.flush()

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

    await db.refresh(candidate_profile)
    await db.refresh(resume_document)

    for section in resume_sections:
        await db.refresh(section)

    return candidate_profile, resume_document, resume_sections