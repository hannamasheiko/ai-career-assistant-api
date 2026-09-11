from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AIPrerequisiteError
from app.models.tracked_vacancy import TrackedVacancy
from app.models.vacancy_embedding import VacancyEmbedding
from app.services.tracked_vacancy_service import (
    get_tracked_vacancy_for_user,
)
from app.services.vacancy_embedding_service import (
    get_vacancy_embedding,
)
from sqlalchemy import func, select

from app.ai.context_builders.vacancy_embedding_input import (
    VACANCY_EMBEDDING_INPUT_VERSION,
)
from app.core.config import settings
from app.models.candidate_profile import CandidateProfile
from app.models.interaction import Interaction
from app.models.resume import ResumeDocument
from app.models.vacancy import Vacancy
from app.schemas.interaction_enums import (
    InteractionDirection,
    InteractionType,
)


DEFAULT_HISTORICAL_APPLICATION_LIMIT = 3


@dataclass(frozen=True)
class HistoricalApplicationMatch:
    """Historical application selected by vacancy similarity."""

    interaction_id: int
    tracked_vacancy_id: int
    vacancy_id: int

    company_name: str | None
    position_title: str
    vacancy_embedding_source_text: str
    message_text: str

    similarity: float

async def _get_current_retrieval_context(
    db: AsyncSession,
    user_id: int,
    current_tracked_vacancy_id: int,
) -> tuple[TrackedVacancy, VacancyEmbedding]:
    """Get the current tracked vacancy and its embedding."""

    tracked_vacancy = await get_tracked_vacancy_for_user(
        db=db,
        tracked_vacancy_id=current_tracked_vacancy_id,
        user_id=user_id,
    )

    if tracked_vacancy is None:
        raise AIPrerequisiteError(
            "Tracked vacancy is not available for retrieval"
        )

    vacancy_embedding = await get_vacancy_embedding(
        db=db,
        vacancy_id=tracked_vacancy.vacancy_id,
    )

    if vacancy_embedding is None:
        raise AIPrerequisiteError(
            "Vacancy embedding is required for retrieval"
        )

    return tracked_vacancy, vacancy_embedding

async def find_similar_historical_applications(
    db: AsyncSession,
    user_id: int,
    current_tracked_vacancy_id: int,
    limit: int = DEFAULT_HISTORICAL_APPLICATION_LIMIT,
) -> list[HistoricalApplicationMatch]:
    """Find similar historical applications for a tracked vacancy."""

    if limit <= 0:
        raise ValueError("Retrieval limit must be greater than zero")

    (
        current_tracked_vacancy,
        current_embedding,
    ) = await _get_current_retrieval_context(
        db=db,
        user_id=user_id,
        current_tracked_vacancy_id=current_tracked_vacancy_id,
    )

    if (
        current_embedding.embedding_model
        != settings.openai_embedding_model
        or current_embedding.embedding_input_version
        != VACANCY_EMBEDDING_INPUT_VERSION
    ):
        raise AIPrerequisiteError(
            "Current vacancy embedding is outdated"
        )

    cosine_distance = (
        VacancyEmbedding.embedding.cosine_distance(
            current_embedding.embedding
        )
    )

    similarity = (1 - cosine_distance).label("similarity")

    result = await db.execute(
        select(
            Interaction.id.label("interaction_id"),
            TrackedVacancy.id.label("tracked_vacancy_id"),
            Vacancy.id.label("vacancy_id"),
            Vacancy.company_name,
            Vacancy.position_title,
            VacancyEmbedding.source_text.label(
                "vacancy_embedding_source_text"
            ),
            Interaction.message_text,
            similarity,
        )
        .select_from(VacancyEmbedding)
        .join(
            Vacancy,
            Vacancy.id == VacancyEmbedding.vacancy_id,
        )
        .join(
            TrackedVacancy,
            TrackedVacancy.vacancy_id == Vacancy.id,
        )
        .join(
            ResumeDocument,
            ResumeDocument.id
            == TrackedVacancy.resume_document_id,
        )
        .join(
            CandidateProfile,
            CandidateProfile.id
            == ResumeDocument.candidate_profile_id,
        )
        .join(
            Interaction,
            Interaction.tracked_vacancy_id
            == TrackedVacancy.id,
        )
        .where(
            CandidateProfile.user_id == user_id,
            Vacancy.id
            != current_tracked_vacancy.vacancy_id,
            Interaction.interaction_type
            == InteractionType.RESUME_SENT,
            Interaction.direction
            == InteractionDirection.OUTGOING,
            func.nullif(
                func.btrim(
                    Interaction.message_text,
                    " \t\n\r\f\v",
                ),
                "",
            ).is_not(None),
            VacancyEmbedding.embedding_model
            == settings.openai_embedding_model,
            VacancyEmbedding.embedding_input_version
            == VACANCY_EMBEDDING_INPUT_VERSION,
        )
        .order_by(
            cosine_distance.asc(),
            Interaction.id.asc(),
        )
        .limit(limit)
    )

    return [
        HistoricalApplicationMatch(
            interaction_id=row.interaction_id,
            tracked_vacancy_id=row.tracked_vacancy_id,
            vacancy_id=row.vacancy_id,
            company_name=row.company_name,
            position_title=row.position_title,
            vacancy_embedding_source_text=(
                row.vacancy_embedding_source_text
            ),
            message_text=row.message_text,
            similarity=float(row.similarity),
        )
        for row in result
    ]
