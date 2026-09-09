from app.ai.context_builders.vacancy_embedding_input import (
    VACANCY_EMBEDDING_INPUT_VERSION,
    build_vacancy_embedding_input,
)
from app.models.vacancy import Vacancy, VacancyAnalysis


def test_build_vacancy_embedding_input() -> None:
    vacancy = Vacancy(
        position_title="Python Backend Developer",
        raw_text="Vacancy text",
    )
    vacancy_analysis = VacancyAnalysis(
        experience_level="Junior",
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        optional_skills=["Docker", "AWS"],
        responsibilities=[
            "Develop APIs",
            "Write automated tests",
        ],
    )

    result = build_vacancy_embedding_input(
        vacancy,
        vacancy_analysis,
    )

    assert result == (
        "Position title: Python Backend Developer\n"
        "Experience level: Junior\n"
        "Required skills: Python; FastAPI; PostgreSQL\n"
        "Optional skills: Docker; AWS\n"
        "Responsibilities: Develop APIs; Write automated tests"
    )


def test_build_vacancy_embedding_input_omits_empty_values() -> None:
    vacancy = Vacancy(
        position_title="  AI Engineer  ",
        raw_text="Vacancy text",
    )
    vacancy_analysis = VacancyAnalysis(
        experience_level=None,
        required_skills=[" Python ", "", "  LLM  "],
        optional_skills=[],
        responsibilities=None,
    )

    result = build_vacancy_embedding_input(
        vacancy,
        vacancy_analysis,
    )

    assert result == (
        "Position title: AI Engineer\n"
        "Required skills: Python; LLM"
    )


def test_vacancy_embedding_input_version() -> None:
    assert VACANCY_EMBEDDING_INPUT_VERSION == "vacancy_embedding_v1"
