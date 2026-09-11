import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context_builders.vacancy_embedding_input import (
    VACANCY_EMBEDDING_INPUT_VERSION,
)
from app.core.config import settings
from app.core.exceptions import AIPrerequisiteError
from app.models.candidate_profile import CandidateProfile
from app.models.interaction import Interaction
from app.models.resume import ResumeDocument
from app.models.tracked_vacancy import TrackedVacancy
from app.models.user import User
from app.models.vacancy import Vacancy, VacancyAnalysis
from app.models.vacancy_embedding import VacancyEmbedding
from app.schemas.interaction_enums import (
    InteractionDirection,
    InteractionType,
)
from app.services.historical_application_retrieval_service import (
    find_similar_historical_applications,
)


EMBEDDING_DIMENSIONS = 1536


def _vector(first: float, second: float = 0.0) -> list[float]:
    return [first, second, *([0.0] * (EMBEDDING_DIMENSIONS - 2))]


async def _create_user_context(
    db: AsyncSession,
    suffix: str,
) -> tuple[User, ResumeDocument]:
    user = User(
        username=f"user-{suffix}",
        email=f"user-{suffix}@example.com",
        hashed_password="test-hash",
    )
    db.add(user)
    await db.flush()

    profile = CandidateProfile(
        user_id=user.id,
        full_name=f"Test User {suffix}",
        email=f"candidate-{suffix}@example.com",
    )
    db.add(profile)
    await db.flush()

    resume = ResumeDocument(
        candidate_profile_id=profile.id,
        raw_text="Test resume",
    )
    db.add(resume)
    await db.flush()
    return user, resume


async def _create_vacancy_with_embedding(
    db: AsyncSession,
    suffix: str,
    embedding: list[float] | None,
    *,
    embedding_model: str | None = None,
    embedding_input_version: str | None = None,
) -> Vacancy:
    vacancy = Vacancy(
        company_name=f"Company {suffix}",
        position_title=f"Position {suffix}",
        raw_text=f"Vacancy {suffix}",
    )
    db.add(vacancy)
    await db.flush()

    analysis = VacancyAnalysis(
        vacancy_id=vacancy.id,
        required_skills=["Python"],
    )
    db.add(analysis)
    await db.flush()

    if embedding is not None:
        db.add(
            VacancyEmbedding(
                vacancy_id=vacancy.id,
                vacancy_analysis_id=analysis.id,
                source_text=f"Embedding input {suffix}",
                embedding=embedding,
                embedding_model=(
                    embedding_model or settings.openai_embedding_model
                ),
                embedding_input_version=(
                    embedding_input_version
                    or VACANCY_EMBEDDING_INPUT_VERSION
                ),
            )
        )
        await db.flush()

    return vacancy


async def _create_tracked_vacancy(
    db: AsyncSession,
    resume: ResumeDocument,
    vacancy: Vacancy,
) -> TrackedVacancy:
    tracked_vacancy = TrackedVacancy(
        resume_document_id=resume.id,
        vacancy_id=vacancy.id,
    )
    db.add(tracked_vacancy)
    await db.flush()
    return tracked_vacancy


async def _create_interaction(
    db: AsyncSession,
    tracked_vacancy: TrackedVacancy,
    message_text: str | None,
    *,
    interaction_type: InteractionType = InteractionType.RESUME_SENT,
    direction: InteractionDirection = InteractionDirection.OUTGOING,
) -> Interaction:
    interaction = Interaction(
        tracked_vacancy_id=tracked_vacancy.id,
        interaction_type=interaction_type,
        direction=direction,
        message_text=message_text,
    )
    db.add(interaction)
    await db.flush()
    return interaction


def test_ranks_limits_and_excludes_current_vacancy(
    client,
    testing_session_factory,
) -> None:
    async def run_scenario():
        async with testing_session_factory() as db:
            user, resume = await _create_user_context(db, "ranking")

            current_vacancy = await _create_vacancy_with_embedding(
                db, "current", _vector(1.0)
            )
            current_tracked = await _create_tracked_vacancy(
                db, resume, current_vacancy
            )
            await _create_interaction(
                db, current_tracked, "Current vacancy message"
            )

            historical = []
            for suffix, vector, message in (
                ("nearest", _vector(1.0), "Nearest message"),
                ("second", _vector(0.8, 0.6), "Second message"),
                ("third", _vector(0.0, 1.0), "Third message"),
            ):
                vacancy = await _create_vacancy_with_embedding(
                    db, suffix, vector
                )
                tracked = await _create_tracked_vacancy(db, resume, vacancy)
                interaction = await _create_interaction(db, tracked, message)
                historical.append((vacancy, tracked, interaction))

            await db.commit()
            results = await find_similar_historical_applications(
                db=db,
                user_id=user.id,
                current_tracked_vacancy_id=current_tracked.id,
                limit=2,
            )
            return current_vacancy.id, historical, results

    current_vacancy_id, historical, results = asyncio.run(run_scenario())

    assert len(results) == 2
    assert [result.vacancy_id for result in results] == [
        historical[0][0].id,
        historical[1][0].id,
    ]
    assert results[0].similarity == pytest.approx(1.0)
    assert results[1].similarity == pytest.approx(0.8)
    assert current_vacancy_id not in {result.vacancy_id for result in results}

    nearest_vacancy, nearest_tracked, nearest_interaction = historical[0]
    assert results[0].interaction_id == nearest_interaction.id
    assert results[0].tracked_vacancy_id == nearest_tracked.id
    assert results[0].vacancy_id == nearest_vacancy.id
    assert results[0].company_name == "Company nearest"
    assert results[0].position_title == "Position nearest"
    assert results[0].vacancy_embedding_source_text == "Embedding input nearest"
    assert results[0].message_text == "Nearest message"


def test_filters_ineligible_historical_applications(
    client,
    testing_session_factory,
) -> None:
    async def run_scenario():
        async with testing_session_factory() as db:
            user, resume = await _create_user_context(db, "owner")
            _, other_resume = await _create_user_context(db, "other")
            current_vacancy = await _create_vacancy_with_embedding(
                db, "filter-current", _vector(1.0)
            )
            current_tracked = await _create_tracked_vacancy(
                db, resume, current_vacancy
            )

            cases = (
                (
                    "valid",
                    resume,
                    InteractionType.RESUME_SENT,
                    InteractionDirection.OUTGOING,
                    "Valid message",
                ),
                (
                    "wrong-type",
                    resume,
                    InteractionType.MESSAGE,
                    InteractionDirection.OUTGOING,
                    "Message",
                ),
                (
                    "incoming",
                    resume,
                    InteractionType.RESUME_SENT,
                    InteractionDirection.INCOMING,
                    "Incoming",
                ),
                (
                    "null",
                    resume,
                    InteractionType.RESUME_SENT,
                    InteractionDirection.OUTGOING,
                    None,
                ),
                (
                    "blank",
                    resume,
                    InteractionType.RESUME_SENT,
                    InteractionDirection.OUTGOING,
                    "   \n",
                ),
                (
                    "other-user",
                    other_resume,
                    InteractionType.RESUME_SENT,
                    InteractionDirection.OUTGOING,
                    "Other user",
                ),
            )
            valid_interaction = None
            for index, case in enumerate(cases):
                suffix, case_resume, kind, direction, text = case
                vacancy = await _create_vacancy_with_embedding(
                    db, suffix, _vector(1.0, index / 10)
                )
                tracked = await _create_tracked_vacancy(db, case_resume, vacancy)
                interaction = await _create_interaction(
                    db,
                    tracked,
                    text,
                    interaction_type=kind,
                    direction=direction,
                )
                if suffix == "valid":
                    valid_interaction = interaction

            await db.commit()
            results = await find_similar_historical_applications(
                db, user.id, current_tracked.id, limit=10
            )
            return valid_interaction.id, results

    valid_interaction_id, results = asyncio.run(run_scenario())

    assert len(results) == 1
    assert results[0].interaction_id == valid_interaction_id
    assert results[0].message_text == "Valid message"


def test_filters_incompatible_historical_embeddings(
    client,
    testing_session_factory,
) -> None:
    async def run_scenario():
        async with testing_session_factory() as db:
            user, resume = await _create_user_context(db, "compatibility")
            current = await _create_vacancy_with_embedding(
                db, "compat-current", _vector(1.0)
            )
            current_tracked = await _create_tracked_vacancy(db, resume, current)

            candidates = (
                ("compatible", None, None),
                ("old-model", "obsolete-embedding-model", None),
                ("old-version", None, "vacancy_embedding_v0"),
            )
            compatible_interaction_id = None
            for suffix, model, version in candidates:
                vacancy = await _create_vacancy_with_embedding(
                    db,
                    suffix,
                    _vector(1.0),
                    embedding_model=model,
                    embedding_input_version=version,
                )
                tracked = await _create_tracked_vacancy(db, resume, vacancy)
                interaction = await _create_interaction(
                    db, tracked, f"Message {suffix}"
                )
                if suffix == "compatible":
                    compatible_interaction_id = interaction.id

            await db.commit()
            results = await find_similar_historical_applications(
                db, user.id, current_tracked.id, limit=10
            )
            return compatible_interaction_id, results

    compatible_interaction_id, results = asyncio.run(run_scenario())

    assert [result.interaction_id for result in results] == [
        compatible_interaction_id
    ]


def test_missing_current_embedding_raises_prerequisite_error(
    client,
    testing_session_factory,
) -> None:
    async def run_scenario():
        async with testing_session_factory() as db:
            user, resume = await _create_user_context(db, "missing")
            vacancy = await _create_vacancy_with_embedding(
                db, "missing-current", None
            )
            tracked = await _create_tracked_vacancy(db, resume, vacancy)
            await db.commit()

            with pytest.raises(
                AIPrerequisiteError,
                match="Vacancy embedding is required for retrieval",
            ):
                await find_similar_historical_applications(
                    db, user.id, tracked.id
                )

    asyncio.run(run_scenario())


def test_outdated_current_embedding_raises_prerequisite_error(
    client,
    testing_session_factory,
) -> None:
    async def run_scenario():
        async with testing_session_factory() as db:
            user, resume = await _create_user_context(db, "outdated")
            vacancy = await _create_vacancy_with_embedding(
                db,
                "outdated-current",
                _vector(1.0),
                embedding_model="obsolete-embedding-model",
            )
            tracked = await _create_tracked_vacancy(db, resume, vacancy)
            await db.commit()

            with pytest.raises(
                AIPrerequisiteError,
                match="Current vacancy embedding is outdated",
            ):
                await find_similar_historical_applications(
                    db, user.id, tracked.id
                )

    asyncio.run(run_scenario())


@pytest.mark.parametrize("limit", [0, -1])
def test_rejects_non_positive_limit(
    client,
    testing_session_factory,
    limit: int,
) -> None:
    async def run_scenario():
        async with testing_session_factory() as db:
            with pytest.raises(
                ValueError,
                match="Retrieval limit must be greater than zero",
            ):
                await find_similar_historical_applications(
                    db, user_id=1, current_tracked_vacancy_id=1, limit=limit
                )

    asyncio.run(run_scenario())


def test_returns_empty_list_when_no_candidates_are_available(
    client,
    testing_session_factory,
) -> None:
    async def run_scenario():
        async with testing_session_factory() as db:
            user, resume = await _create_user_context(db, "empty")
            vacancy = await _create_vacancy_with_embedding(
                db, "empty-current", _vector(1.0)
            )
            tracked = await _create_tracked_vacancy(db, resume, vacancy)
            await db.commit()
            return await find_similar_historical_applications(
                db, user.id, tracked.id
            )

    assert asyncio.run(run_scenario()) == []
