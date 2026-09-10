import argparse
import asyncio
from collections import Counter

from sqlalchemy import select

from app import models  # noqa: F401
from app.ai.context_builders.vacancy_embedding_input import (
    VACANCY_EMBEDDING_INPUT_VERSION,
    build_vacancy_embedding_input,
)
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.vacancy import Vacancy, VacancyAnalysis
from app.models.vacancy_embedding import VacancyEmbedding
from app.services.vacancy_embedding_service import (
    create_or_update_vacancy_embedding,
)
from app.core.logging import configure_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill embeddings for all analyzed vacancies. "
            "Runs in dry-run mode unless --apply is provided."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Generate and persist missing or stale embeddings.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most this many vacancies.",
    )

    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be greater than zero")

    return args


def get_embedding_action(
    vacancy_embedding: VacancyEmbedding | None,
    vacancy_analysis: VacancyAnalysis,
    source_text: str,
) -> str:
    if vacancy_embedding is None:
        return "create"

    representation_is_current = (
        vacancy_embedding.source_text == source_text
        and vacancy_embedding.embedding_model
        == settings.openai_embedding_model
        and vacancy_embedding.embedding_input_version
        == VACANCY_EMBEDDING_INPUT_VERSION
    )

    if not representation_is_current:
        return "refresh"

    if (
        vacancy_embedding.vacancy_analysis_id
        != vacancy_analysis.id
    ):
        return "update_metadata"

    return "skip"


async def load_vacancies_for_backfill() -> list[
    tuple[
        Vacancy,
        VacancyAnalysis,
        VacancyEmbedding | None,
    ]
]:
    latest_analysis_id = (
        select(VacancyAnalysis.id)
        .where(
            VacancyAnalysis.vacancy_id == Vacancy.id,
        )
        .order_by(
            VacancyAnalysis.created_at.desc(),
            VacancyAnalysis.id.desc(),
        )
        .limit(1)
        .correlate(Vacancy)
        .scalar_subquery()
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(
                Vacancy,
                VacancyAnalysis,
                VacancyEmbedding,
            )
            .join(
                VacancyAnalysis,
                VacancyAnalysis.id == latest_analysis_id,
            )
            .outerjoin(
                VacancyEmbedding,
                VacancyEmbedding.vacancy_id == Vacancy.id,
            )
            .order_by(Vacancy.id)
        )

        return list(result.all())


async def run_backfill(
    *,
    apply: bool,
    limit: int | None,
) -> None:
    rows = await load_vacancies_for_backfill()

    if limit is not None:
        rows = rows[:limit]

    mode = "APPLY" if apply else "DRY RUN"
    action_counts: Counter[str] = Counter()

    print(f"Mode: {mode}")
    print(f"Selected vacancies: {len(rows)}")

    async with AsyncSessionLocal() as db:
        for vacancy, vacancy_analysis, vacancy_embedding in rows:
            source_text = build_vacancy_embedding_input(
                vacancy=vacancy,
                vacancy_analysis=vacancy_analysis,
            )

            action = get_embedding_action(
                vacancy_embedding=vacancy_embedding,
                vacancy_analysis=vacancy_analysis,
                source_text=source_text,
            )
            action_counts[action] += 1

            print(
                f"vacancy_id={vacancy.id} "
                f"analysis_id={vacancy_analysis.id} "
                f"action={action}"
            )

            if not apply or action == "skip":
                continue

            await create_or_update_vacancy_embedding(
                db=db,
                vacancy=vacancy,
                vacancy_analysis=vacancy_analysis,
            )

    print("Summary:")
    print(f"  create: {action_counts['create']}")
    print(f"  refresh: {action_counts['refresh']}")
    print(
        "  update_metadata: "
        f"{action_counts['update_metadata']}"
    )
    print(f"  skip: {action_counts['skip']}")


def main() -> None:
    configure_logging()
    args = parse_args()

    asyncio.run(
        run_backfill(
            apply=args.apply,
            limit=args.limit,
        )
    )


if __name__ == "__main__":
    main()
