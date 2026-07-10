from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.chains.generate_content_chain import generate_content_chain
from app.models.generated_content import GeneratedContent
from app.models.match_analysis import MatchAnalysis
from app.models.resume import ResumeDocument
from app.models.tracked_vacancy import TrackedVacancy
from app.schemas.generated_content import GeneratedContentGenerateRequest, GeneratedContentUpdate
from app.schemas.ai_outputs import ParsedGeneratedContent


async def get_tracked_vacancy_for_generated_content(
    db: AsyncSession,
    tracked_vacancy_id: int,
    user_id: int,
) -> TrackedVacancy | None:
    """Get tracked vacancy with resume document and vacancy for generated content."""

    result = await db.execute(
        select(TrackedVacancy)
        .options(
            selectinload(TrackedVacancy.resume_document),
            selectinload(TrackedVacancy.vacancy),
        )
        .where(
            TrackedVacancy.id == tracked_vacancy_id,
            TrackedVacancy.resume_document.has(
                ResumeDocument.candidate_profile.has(user_id=user_id)
            ),
        )
    )

    return result.scalar_one_or_none()


async def get_match_analysis_for_generated_content(
    db: AsyncSession,
    tracked_vacancy_id: int,
) -> MatchAnalysis | None:
    """Get match analysis for generated content context."""

    result = await db.execute(
        select(MatchAnalysis).where(
            MatchAnalysis.tracked_vacancy_id == tracked_vacancy_id,
        )
    )

    return result.scalar_one_or_none()


async def get_generated_content_for_user(
    db: AsyncSession,
    generated_content_id: int,
    user_id: int,
) -> GeneratedContent | None:
    """Get generated content if it belongs to current user."""

    result = await db.execute(
        select(GeneratedContent).where(
            GeneratedContent.id == generated_content_id,
            GeneratedContent.tracked_vacancy.has(
                TrackedVacancy.resume_document.has(
                    ResumeDocument.candidate_profile.has(user_id=user_id)
                )
            ),
        )
    )

    return result.scalar_one_or_none()


async def get_generated_contents_for_tracked_vacancy(
    db: AsyncSession,
    tracked_vacancy_id: int,
    user_id: int,
) -> list[GeneratedContent]:
    """Get generated contents for tracked vacancy if it belongs to current user."""

    result = await db.execute(
        select(GeneratedContent)
        .where(
            GeneratedContent.tracked_vacancy_id == tracked_vacancy_id,
            GeneratedContent.tracked_vacancy.has(
                TrackedVacancy.resume_document.has(
                    ResumeDocument.candidate_profile.has(user_id=user_id)
                )
            ),
        )
        .order_by(GeneratedContent.created_at.desc())
    )

    return list(result.scalars().all())


def build_resume_text_for_generated_content(
    resume_document: ResumeDocument,
) -> str:
    """Build resume raw text for generated content."""

    return resume_document.raw_text


def build_vacancy_text_for_generated_content(
    tracked_vacancy: TrackedVacancy,
) -> str:
    """Build vacancy raw text for generated content."""

    return tracked_vacancy.vacancy.raw_text


def build_match_analysis_text_for_generated_content(
    match_analysis: MatchAnalysis | None,
) -> str | None:
    """Build match analysis text for generated content."""

    if match_analysis is None:
        return None

    parts: list[str] = []

    if match_analysis.match_score is not None:
        parts.append(f"Match score: {match_analysis.match_score}")

    if match_analysis.recommendation:
        parts.append(f"Recommendation: {match_analysis.recommendation}")

    if match_analysis.strong_matches:
        parts.append(f"Strong matches: {', '.join(match_analysis.strong_matches)}")

    if match_analysis.partial_matches:
        parts.append(f"Partial matches: {', '.join(match_analysis.partial_matches)}")

    if match_analysis.missing_skills:
        parts.append(f"Missing skills: {', '.join(match_analysis.missing_skills)}")

    if match_analysis.risk_points:
        parts.append(f"Risk points: {', '.join(match_analysis.risk_points)}")

    if match_analysis.reasoning_summary:
        parts.append(f"Reasoning summary: {match_analysis.reasoning_summary}")

    return "\n".join(parts)


def build_prompt_context(
    tracked_vacancy: TrackedVacancy,
    match_analysis: MatchAnalysis | None,
    data: GeneratedContentGenerateRequest,
) -> dict[str, Any]:
    """Build prompt context snapshot for generated content."""

    return {
        "content_type": data.content_type,
        "language": data.language,
        "tone": data.tone,
        "extra_instructions": data.extra_instructions,
        "resume_document_id": tracked_vacancy.resume_document_id,
        "vacancy_id": tracked_vacancy.vacancy_id,
        "match_analysis_id": match_analysis.id if match_analysis else None,
    }


async def generate_and_save_content(
    db: AsyncSession,
    tracked_vacancy: TrackedVacancy,
    data: GeneratedContentGenerateRequest,
    ai_model: str,
    prompt_version: str,
) -> GeneratedContent:
    """Generate AI content and save it to the database."""

    if data.content_type != "cover_letter":
        raise ValueError(f"Unsupported generated content type: {data.content_type}")

    match_analysis = await get_match_analysis_for_generated_content(
        db=db,
        tracked_vacancy_id=tracked_vacancy.id,
    )

    resume_text = build_resume_text_for_generated_content(
        resume_document=tracked_vacancy.resume_document,
    )

    vacancy_text = build_vacancy_text_for_generated_content(
        tracked_vacancy=tracked_vacancy,
    )

    match_analysis_text = build_match_analysis_text_for_generated_content(
        match_analysis=match_analysis,
    )

    parsed_generated_content: ParsedGeneratedContent = await generate_content_chain(
        content_type=data.content_type,
        resume_text=resume_text,
        vacancy_text=vacancy_text,
        match_analysis_text=match_analysis_text,
        language=data.language,
        tone=data.tone,
        extra_instructions=data.extra_instructions,
    )

    generated_content = GeneratedContent(
        tracked_vacancy_id=tracked_vacancy.id,
        content_type=data.content_type,
        prompt_context=build_prompt_context(
            tracked_vacancy=tracked_vacancy,
            match_analysis=match_analysis,
            data=data,
        ),
        generated_text=parsed_generated_content.generated_text,
        ai_model=ai_model,
        prompt_version=prompt_version,
    )

    db.add(generated_content)
    await db.commit()
    await db.refresh(generated_content)

    return generated_content


async def update_generated_content(
    db: AsyncSession,
    generated_content: GeneratedContent,
    data: GeneratedContentUpdate,
) -> GeneratedContent:
    """Update generated content."""

    update_data = data.model_dump(exclude_unset=True)

    for field_name, field_value in update_data.items():
        setattr(generated_content, field_name, field_value)

    await db.commit()
    await db.refresh(generated_content)

    return generated_content
