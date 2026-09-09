from app.models.vacancy import Vacancy, VacancyAnalysis


VACANCY_EMBEDDING_INPUT_VERSION = "vacancy_embedding_v1"


def build_vacancy_embedding_input(
    vacancy: Vacancy,
    vacancy_analysis: VacancyAnalysis,
) -> str:
    """Build deterministic text used to generate a vacancy embedding."""

    sections = [
        ("Position title", vacancy.position_title),
        ("Experience level", vacancy_analysis.experience_level),
        (
            "Required skills",
            _format_list(vacancy_analysis.required_skills),
        ),
        (
            "Optional skills",
            _format_list(vacancy_analysis.optional_skills),
        ),
        (
            "Responsibilities",
            _format_list(vacancy_analysis.responsibilities),
        ),
    ]

    return "\n".join(
        f"{label}: {value.strip()}"
        for label, value in sections
        if value and value.strip()
    )


def _format_list(values: list[str] | None) -> str | None:
    if not values:
        return None

    normalized_values = [
        value.strip()
        for value in values
        if value and value.strip()
    ]

    if not normalized_values:
        return None

    return "; ".join(normalized_values)
