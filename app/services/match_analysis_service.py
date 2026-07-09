from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chains.parse_match_analysis_chain import parse_match_analysis_chain
from app.models.match_analysis import MatchAnalysis
from app.models.resume import ResumeDocument
from app.models.tracked_vacancy import TrackedVacancy
from app.schemas.ai_outputs import ParsedMatchAnalysis

from sqlalchemy.orm import selectinload

async def get_match_analysis_by_tracked_vacancy_id(
    db: AsyncSession,
    tracked_vacancy_id: int,
) -> MatchAnalysis | None:
    """Get match analysis by tracked vacancy id."""

    result = await db.execute(
        select(MatchAnalysis).where(
            MatchAnalysis.tracked_vacancy_id == tracked_vacancy_id,
        )
    )

    return result.scalar_one_or_none()


def build_resume_text_for_match_analysis(
    resume_document: ResumeDocument,
) -> str:
    """Build resume raw text for match analysis."""

    return resume_document.raw_text


def build_vacancy_text_for_match_analysis(
    tracked_vacancy: TrackedVacancy,
) -> str:
    """Build vacancy raw text for match analysis."""

    return tracked_vacancy.vacancy.raw_text

async def get_tracked_vacancy_for_match_analysis(
    db: AsyncSession,
    tracked_vacancy_id: int,
    user_id: int,
) -> TrackedVacancy | None:
    """Get tracked vacancy with resume document and vacancy for match analysis."""

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

async def create_or_update_match_analysis(
    db: AsyncSession,
    tracked_vacancy: TrackedVacancy,
    ai_model: str,
    prompt_version: str,
) -> MatchAnalysis:
    """Create or update match analysis for tracked vacancy."""

    resume_text = build_resume_text_for_match_analysis(
        resume_document=tracked_vacancy.resume_document,
    )

    vacancy_text = build_vacancy_text_for_match_analysis(
        tracked_vacancy=tracked_vacancy,
    )

    parsed_match_analysis: ParsedMatchAnalysis = await parse_match_analysis_chain(
        resume_text=resume_text,
        vacancy_text=vacancy_text,
    )

    existing_match_analysis = await get_match_analysis_by_tracked_vacancy_id(
        db=db,
        tracked_vacancy_id=tracked_vacancy.id,
    )

    if existing_match_analysis is None:
        match_analysis = MatchAnalysis(
            tracked_vacancy_id=tracked_vacancy.id,
            match_score=parsed_match_analysis.match_score,
            recommendation=parsed_match_analysis.recommendation,
            strong_matches=parsed_match_analysis.strong_matches,
            partial_matches=parsed_match_analysis.partial_matches,
            missing_skills=parsed_match_analysis.missing_skills,
            risk_points=parsed_match_analysis.risk_points,
            reasoning_summary=parsed_match_analysis.reasoning_summary,
            ai_model=ai_model,
            prompt_version=prompt_version,
        )

        db.add(match_analysis)
    else:
        match_analysis = existing_match_analysis

        match_analysis.match_score = parsed_match_analysis.match_score
        match_analysis.recommendation = parsed_match_analysis.recommendation
        match_analysis.strong_matches = parsed_match_analysis.strong_matches
        match_analysis.partial_matches = parsed_match_analysis.partial_matches
        match_analysis.missing_skills = parsed_match_analysis.missing_skills
        match_analysis.risk_points = parsed_match_analysis.risk_points
        match_analysis.reasoning_summary = parsed_match_analysis.reasoning_summary
        match_analysis.ai_model = ai_model
        match_analysis.prompt_version = prompt_version

    await db.commit()
    await db.refresh(match_analysis)

    return match_analysis

