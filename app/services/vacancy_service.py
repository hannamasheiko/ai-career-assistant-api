from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chains.parse_vacancy_chain import parse_vacancy_chain
from app.models.vacancy import Vacancy


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
        position_title=parsed_vacancy.position_title,
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