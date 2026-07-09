from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chains.parse_vacancy_chain import parse_vacancy_chain
from app.models.vacancy import Vacancy, VacancyAnalysis

from sqlalchemy import select
from app.ai.chains.analyze_vacancy_chain import (
    VACANCY_ANALYSIS_PROMPT_VERSION,
    analyze_vacancy_chain,
)
from app.core.config import settings


async def create_vacancy_from_text(
    db: AsyncSession,
    raw_text: str,
) -> Vacancy:
    """Create vacancy from copied vacancy page text."""

    parsed_vacancy = await parse_vacancy_chain(
        raw_text=raw_text,
    )

    vacancy = Vacancy(
        company_name=parsed_vacancy.company_name,
        position_title=parsed_vacancy.position_title or "Unknown Position",
        source=parsed_vacancy.source,
        source_url=parsed_vacancy.source_url,
        location=parsed_vacancy.location,
        work_format=parsed_vacancy.work_format,
        employment_type=parsed_vacancy.employment_type,
        salary_min=parsed_vacancy.salary_min,
        salary_max=parsed_vacancy.salary_max,
        currency=parsed_vacancy.currency,
        raw_text=raw_text,
        cleaned_text=parsed_vacancy.cleaned_text,
    )

    db.add(vacancy)
    await db.commit()
    await db.refresh(vacancy)

    return vacancy

async def create_vacancy_analysis(
    db: AsyncSession,
    vacancy_id: int,
) -> VacancyAnalysis:
    """Create AI-generated analysis for an existing vacancy."""

    result = await db.execute(
        select(Vacancy).where(Vacancy.id == vacancy_id)
    )
    vacancy = result.scalar_one_or_none()

    if vacancy is None:
        raise ValueError("Vacancy not found")

    parsed_analysis = await analyze_vacancy_chain(
        vacancy_text=vacancy.raw_text,
    )

    vacancy_analysis = VacancyAnalysis(
        vacancy_id=vacancy.id,
        experience_level=parsed_analysis.experience_level,
        english_level=parsed_analysis.english_level,
        required_skills=parsed_analysis.required_skills,
        optional_skills=parsed_analysis.optional_skills,
        responsibilities=parsed_analysis.responsibilities,
        red_flags=parsed_analysis.red_flags,
        green_flags=parsed_analysis.green_flags,
        summary=parsed_analysis.summary,
        recommendation=parsed_analysis.recommendation,
        ai_model=settings.openai_model,
        prompt_version=VACANCY_ANALYSIS_PROMPT_VERSION,
    )

    db.add(vacancy_analysis)
    await db.commit()
    await db.refresh(vacancy_analysis)

    return vacancy_analysis