import asyncio
from unittest.mock import AsyncMock

from sqlalchemy import func, select

from app.models.vacancy import Vacancy, VacancyAnalysis
from app.models.vacancy_embedding import VacancyEmbedding
from app.services import vacancy_embedding_service
import pytest
from app.core.exceptions import AIServiceError



def test_create_and_reuse_vacancy_embedding(
    client,
    testing_session_factory,
    monkeypatch,
) -> None:
    expected_embedding = [0.1] * 1536
    create_embedding_mock = AsyncMock(
        return_value=expected_embedding
    )

    monkeypatch.setattr(
        vacancy_embedding_service,
        "create_embedding",
        create_embedding_mock,
    )

    async def run_scenario() -> tuple[int, int, int]:
        async with testing_session_factory() as db:
            vacancy = Vacancy(
                position_title="Python Backend Developer",
                raw_text="Vacancy text",
            )
            db.add(vacancy)
            await db.flush()

            vacancy_analysis = VacancyAnalysis(
                vacancy_id=vacancy.id,
                experience_level="Junior",
                required_skills=["Python", "FastAPI"],
                optional_skills=["Docker"],
                responsibilities=["Develop APIs"],
            )
            db.add(vacancy_analysis)
            await db.commit()
            await db.refresh(vacancy)
            await db.refresh(vacancy_analysis)

            created = (
                await vacancy_embedding_service
                .create_or_update_vacancy_embedding(
                    db=db,
                    vacancy=vacancy,
                    vacancy_analysis=vacancy_analysis,
                )
            )

            reused = (
                await vacancy_embedding_service
                .create_or_update_vacancy_embedding(
                    db=db,
                    vacancy=vacancy,
                    vacancy_analysis=vacancy_analysis,
                )
            )

            count_result = await db.execute(
                select(func.count())
                .select_from(VacancyEmbedding)
            )
            embedding_count = count_result.scalar_one()

            return (
                created.id,
                reused.id,
                embedding_count,
            )

    created_id, reused_id, embedding_count = asyncio.run(
        run_scenario()
    )

    assert created_id == reused_id
    assert embedding_count == 1
    create_embedding_mock.assert_awaited_once()

def test_update_vacancy_embedding_when_source_changes(
    client,
    testing_session_factory,
    monkeypatch,
) -> None:
    first_embedding = [0.1] * 1536
    updated_embedding = [0.2] * 1536

    create_embedding_mock = AsyncMock(
        side_effect=[
            first_embedding,
            updated_embedding,
        ]
    )

    monkeypatch.setattr(
        vacancy_embedding_service,
        "create_embedding",
        create_embedding_mock,
    )

    async def run_scenario() -> tuple[
        int,
        int,
        int,
        str,
        float,
    ]:
        async with testing_session_factory() as db:
            vacancy = Vacancy(
                position_title="Python Backend Developer",
                raw_text="Vacancy text",
            )
            db.add(vacancy)
            await db.flush()

            first_analysis = VacancyAnalysis(
                vacancy_id=vacancy.id,
                experience_level="Junior",
                required_skills=["Python"],
                responsibilities=["Develop APIs"],
            )
            db.add(first_analysis)
            await db.commit()
            await db.refresh(vacancy)
            await db.refresh(first_analysis)

            created = (
                await vacancy_embedding_service
                .create_or_update_vacancy_embedding(
                    db=db,
                    vacancy=vacancy,
                    vacancy_analysis=first_analysis,
                )
            )
            created_id = created.id

            updated_analysis = VacancyAnalysis(
                vacancy_id=vacancy.id,
                experience_level="Junior",
                required_skills=["Python", "FastAPI"],
                responsibilities=[
                    "Develop and maintain APIs",
                ],
            )
            db.add(updated_analysis)
            await db.commit()
            await db.refresh(updated_analysis)

            updated = (
                await vacancy_embedding_service
                .create_or_update_vacancy_embedding(
                    db=db,
                    vacancy=vacancy,
                    vacancy_analysis=updated_analysis,
                )
            )

            count_result = await db.execute(
                select(func.count())
                .select_from(VacancyEmbedding)
            )

            return (
                created_id,
                updated.id,
                count_result.scalar_one(),
                updated.source_text,
                float(updated.embedding[0]),
            )

    (
        created_id,
        updated_id,
        embedding_count,
        source_text,
        first_vector_value,
    ) = asyncio.run(run_scenario())

    assert updated_id == created_id
    assert embedding_count == 1
    assert "Required skills: Python; FastAPI" in source_text
    assert first_vector_value == pytest.approx(0.2)
    assert create_embedding_mock.await_count == 2

def test_provider_failure_preserves_existing_embedding(
    client,
    testing_session_factory,
    monkeypatch,
) -> None:
    original_embedding = [0.1] * 1536

    create_embedding_mock = AsyncMock(
        side_effect=[
            original_embedding,
            AIServiceError("Embedding provider failed"),
        ]
    )

    monkeypatch.setattr(
        vacancy_embedding_service,
        "create_embedding",
        create_embedding_mock,
    )

    async def run_scenario() -> tuple[
        int,
        int,
        str,
        str,
        float,
    ]:
        async with testing_session_factory() as db:
            vacancy = Vacancy(
                position_title="Python Backend Developer",
                raw_text="Vacancy text",
            )
            db.add(vacancy)
            await db.flush()

            first_analysis = VacancyAnalysis(
                vacancy_id=vacancy.id,
                experience_level="Junior",
                required_skills=["Python"],
            )
            db.add(first_analysis)
            await db.commit()
            await db.refresh(vacancy)
            await db.refresh(first_analysis)

            existing = await vacancy_embedding_service.create_or_update_vacancy_embedding(
                db=db,
                vacancy=vacancy,
                vacancy_analysis=first_analysis,
            )

            original_analysis_id = (
                existing.vacancy_analysis_id
            )
            original_source_text = existing.source_text

            updated_analysis = VacancyAnalysis(
                vacancy_id=vacancy.id,
                experience_level="Junior",
                required_skills=["Python", "FastAPI"],
            )
            db.add(updated_analysis)
            await db.commit()
            await db.refresh(updated_analysis)

            with pytest.raises(
                AIServiceError,
                match="Embedding provider failed",
            ):
                await vacancy_embedding_service.create_or_update_vacancy_embedding(
                    db=db,
                    vacancy=vacancy,
                    vacancy_analysis=updated_analysis,
                )

            await db.refresh(existing)

            return (
                original_analysis_id,
                existing.vacancy_analysis_id,
                original_source_text,
                existing.source_text,
                float(existing.embedding[0]),
            )

    (
        original_analysis_id,
        stored_analysis_id,
        original_source_text,
        stored_source_text,
        stored_vector_value,
    ) = asyncio.run(run_scenario())

    assert stored_analysis_id == original_analysis_id
    assert stored_source_text == original_source_text
    assert stored_vector_value == pytest.approx(0.1)
    assert create_embedding_mock.await_count == 2

def test_reuse_embedding_for_identical_new_analysis(
    client,
    testing_session_factory,
    monkeypatch,
) -> None:
    create_embedding_mock = AsyncMock(
        return_value=[0.1] * 1536
    )

    monkeypatch.setattr(
        vacancy_embedding_service,
        "create_embedding",
        create_embedding_mock,
    )

    async def run_scenario() -> tuple[int, int, int, int]:
        async with testing_session_factory() as db:
            vacancy = Vacancy(
                position_title="Python Backend Developer",
                raw_text="Vacancy text",
            )
            db.add(vacancy)
            await db.flush()

            first_analysis = VacancyAnalysis(
                vacancy_id=vacancy.id,
                experience_level="Junior",
                required_skills=["Python", "FastAPI"],
            )
            db.add(first_analysis)
            await db.commit()
            await db.refresh(vacancy)
            await db.refresh(first_analysis)

            created = await vacancy_embedding_service.create_or_update_vacancy_embedding(
                db=db,
                vacancy=vacancy,
                vacancy_analysis=first_analysis,
            )
            created_id = created.id

            identical_analysis = VacancyAnalysis(
                vacancy_id=vacancy.id,
                experience_level="Junior",
                required_skills=["Python", "FastAPI"],
            )
            db.add(identical_analysis)
            await db.commit()
            await db.refresh(identical_analysis)

            reused = await vacancy_embedding_service.create_or_update_vacancy_embedding(
                db=db,
                vacancy=vacancy,
                vacancy_analysis=identical_analysis,
            )

            return (
                created_id,
                reused.id,
                reused.vacancy_analysis_id,
                identical_analysis.id,
            )

    (
        created_id,
        reused_id,
        stored_analysis_id,
        identical_analysis_id,
    ) = asyncio.run(run_scenario())

    assert reused_id == created_id
    assert stored_analysis_id == identical_analysis_id
    assert create_embedding_mock.await_count == 1
