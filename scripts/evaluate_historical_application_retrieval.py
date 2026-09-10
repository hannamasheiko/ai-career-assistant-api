import asyncio
from collections import Counter
from statistics import mean

from sqlalchemy import exists, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app import models  # noqa: F401
from app.ai.context_builders.vacancy_embedding_input import (
    VACANCY_EMBEDDING_INPUT_VERSION,
)
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.candidate_profile import CandidateProfile
from app.models.interaction import Interaction
from app.models.resume import ResumeDocument
from app.models.tracked_vacancy import TrackedVacancy
from app.models.vacancy import Vacancy
from app.models.vacancy_embedding import VacancyEmbedding
from app.schemas.interaction_enums import (
    InteractionDirection,
    InteractionType,
)
from app.services.historical_application_retrieval_service import (
    find_similar_historical_applications,
)


RETRIEVAL_LIMIT = 3
WHITESPACE_CHARACTERS = " \t\n\r\f\v"


async def _load_evaluation_vacancies(db: AsyncSession):
    has_valid_application = exists(
        select(Interaction.id).where(
            Interaction.tracked_vacancy_id == TrackedVacancy.id,
            Interaction.interaction_type == InteractionType.RESUME_SENT,
            Interaction.direction == InteractionDirection.OUTGOING,
            func.nullif(
                func.btrim(
                    Interaction.message_text,
                    WHITESPACE_CHARACTERS,
                ),
                "",
            ).is_not(None),
        )
    )

    result = await db.execute(
        select(
            TrackedVacancy.id.label("tracked_vacancy_id"),
            CandidateProfile.user_id,
            Vacancy.company_name,
            Vacancy.position_title,
        )
        .join(
            ResumeDocument,
            ResumeDocument.id == TrackedVacancy.resume_document_id,
        )
        .join(
            CandidateProfile,
            CandidateProfile.id == ResumeDocument.candidate_profile_id,
        )
        .join(Vacancy, Vacancy.id == TrackedVacancy.vacancy_id)
        .join(
            VacancyEmbedding,
            VacancyEmbedding.vacancy_id == Vacancy.id,
        )
        .where(
            has_valid_application,
            VacancyEmbedding.embedding_model
            == settings.openai_embedding_model,
            VacancyEmbedding.embedding_input_version
            == VACANCY_EMBEDDING_INPUT_VERSION,
        )
        .order_by(TrackedVacancy.id)
    )

    return result.all()


def _format_identity(
    company_name: str | None,
    position_title: str,
) -> str:
    return f"{company_name or 'Unknown company'} | {position_title}"


def _print_statistics(label: str, values: list[float]) -> None:
    if not values:
        return

    print(
        f"{label}: "
        f"min={min(values):.6f} "
        f"mean={mean(values):.6f} "
        f"max={max(values):.6f}"
    )


async def _run_evaluation(db: AsyncSession) -> None:
    current_vacancies = await _load_evaluation_vacancies(db)
    result_counts: Counter[int] = Counter()
    rank_similarities: dict[int, list[float]] = {
        rank: [] for rank in range(1, RETRIEVAL_LIMIT + 1)
    }
    top1_top2_gaps: list[float] = []
    top2_top3_gaps: list[float] = []

    for current in current_vacancies:
        matches = await find_similar_historical_applications(
            db=db,
            user_id=current.user_id,
            current_tracked_vacancy_id=current.tracked_vacancy_id,
            limit=RETRIEVAL_LIMIT,
        )
        result_counts[len(matches)] += 1

        print(
            "CURRENT: "
            f"tracked_id={current.tracked_vacancy_id} | "
            f"{_format_identity(current.company_name, current.position_title)}"
        )

        for rank, match in enumerate(matches, start=1):
            rank_similarities[rank].append(match.similarity)
            print(
                f"  {rank}. score={match.similarity:.6f} | "
                f"{_format_identity(match.company_name, match.position_title)} | "
                f"tracked_id={match.tracked_vacancy_id}"
            )

        if len(matches) >= 2:
            top1_top2_gaps.append(
                matches[0].similarity - matches[1].similarity
            )
        if len(matches) >= 3:
            top2_top3_gaps.append(
                matches[1].similarity - matches[2].similarity
            )

    print("Summary:")
    print(f"Evaluated current vacancies: {len(current_vacancies)}")
    for match_count in range(RETRIEVAL_LIMIT + 1):
        print(
            f"Results with {match_count} matches: "
            f"{result_counts[match_count]}"
        )

    for rank in range(1, RETRIEVAL_LIMIT + 1):
        _print_statistics(
            f"Rank {rank} similarity",
            rank_similarities[rank],
        )

    _print_statistics("Top1-Top2 gap", top1_top2_gaps)
    _print_statistics("Top2-Top3 gap", top2_top3_gaps)


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await db.begin()
        try:
            await db.execute(text("SET TRANSACTION READ ONLY"))
            await _run_evaluation(db)
        finally:
            await db.rollback()


if __name__ == "__main__":
    asyncio.run(main())
