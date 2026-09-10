from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context_builders.vacancy_embedding_input import (
    VACANCY_EMBEDDING_INPUT_VERSION,
    build_vacancy_embedding_input,
)
from app.ai.embedding_executor import create_embedding
from app.core.config import settings
from app.models.vacancy import Vacancy, VacancyAnalysis
from app.models.vacancy_embedding import VacancyEmbedding


async def get_vacancy_embedding(
    db: AsyncSession,
    vacancy_id: int,
) -> VacancyEmbedding | None:
    """Get the stored embedding for a vacancy."""

    result = await db.execute(
        select(VacancyEmbedding).where(
            VacancyEmbedding.vacancy_id == vacancy_id,
        )
    )

    return result.scalar_one_or_none()


async def create_or_update_vacancy_embedding(
    db: AsyncSession,
    vacancy: Vacancy,
    vacancy_analysis: VacancyAnalysis,
) -> VacancyEmbedding:
    """Create, refresh, or reuse a vacancy embedding."""

    if vacancy.id is None or vacancy_analysis.id is None:
        raise ValueError(
            "Vacancy and vacancy analysis must be persisted"
        )

    if vacancy_analysis.vacancy_id != vacancy.id:
        raise ValueError(
            "Vacancy analysis does not belong to the vacancy"
        )

    source_text = build_vacancy_embedding_input(
        vacancy=vacancy,
        vacancy_analysis=vacancy_analysis,
    )

    vacancy_embedding = await get_vacancy_embedding(
        db=db,
        vacancy_id=vacancy.id,
    )

    embedding_is_current = (
        vacancy_embedding is not None
        and vacancy_embedding.source_text == source_text
        and vacancy_embedding.embedding_model
        == settings.openai_embedding_model
        and vacancy_embedding.embedding_input_version
        == VACANCY_EMBEDDING_INPUT_VERSION
    )

    if embedding_is_current:
        if (
            vacancy_embedding.vacancy_analysis_id
            != vacancy_analysis.id
        ):
            vacancy_embedding.vacancy_analysis_id = (
                vacancy_analysis.id
            )
            await db.commit()
            await db.refresh(vacancy_embedding)

        return vacancy_embedding

    embedding = await create_embedding(source_text)

    if vacancy_embedding is None:
        vacancy_embedding = VacancyEmbedding(
            vacancy_id=vacancy.id,
            vacancy_analysis_id=vacancy_analysis.id,
            source_text=source_text,
            embedding=embedding,
            embedding_model=settings.openai_embedding_model,
            embedding_input_version=(
                VACANCY_EMBEDDING_INPUT_VERSION
            ),
        )
        db.add(vacancy_embedding)
    else:
        vacancy_embedding.vacancy_analysis_id = (
            vacancy_analysis.id
        )
        vacancy_embedding.source_text = source_text
        vacancy_embedding.embedding = embedding
        vacancy_embedding.embedding_model = (
            settings.openai_embedding_model
        )
        vacancy_embedding.embedding_input_version = (
            VACANCY_EMBEDDING_INPUT_VERSION
        )

    await db.commit()
    await db.refresh(vacancy_embedding)

    return vacancy_embedding
