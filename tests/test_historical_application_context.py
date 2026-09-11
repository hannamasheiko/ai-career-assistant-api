from app.ai.context_builders.historical_application_context import (
    NO_HISTORICAL_APPLICATIONS_CONTEXT,
    build_historical_application_context,
)
from app.services.historical_application_retrieval_service import (
    HistoricalApplicationMatch,
)


def test_build_historical_application_context() -> None:
    matches = [
        HistoricalApplicationMatch(
            interaction_id=10,
            tracked_vacancy_id=20,
            vacancy_id=30,
            company_name="First Company",
            position_title="Python Backend Developer",
            vacancy_embedding_source_text=(
                "Position title: Python Backend Developer\n"
                "Required skills: Python; FastAPI"
            ),
            message_text="First sent cover letter.",
            similarity=0.91,
        ),
        HistoricalApplicationMatch(
            interaction_id=11,
            tracked_vacancy_id=21,
            vacancy_id=31,
            company_name=None,
            position_title="Junior AI Engineer",
            vacancy_embedding_source_text=(
                "Position title: Junior AI Engineer\n"
                "Required skills: Python; RAG"
            ),
            message_text="Second sent cover letter.",
            similarity=0.85,
        ),
    ]

    context = build_historical_application_context(matches)

    assert "=== HISTORICAL APPLICATION 1 ===" in context
    assert "Company: First Company" in context
    assert "Position: Python Backend Developer" in context
    assert "Required skills: Python; FastAPI" in context
    assert "First sent cover letter." in context

    assert "=== HISTORICAL APPLICATION 2 ===" in context
    assert "Company: Unknown company" in context
    assert "Position: Junior AI Engineer" in context
    assert "Required skills: Python; RAG" in context
    assert "Second sent cover letter." in context

    assert context.index(
        "=== HISTORICAL APPLICATION 1 ==="
    ) < context.index(
        "=== HISTORICAL APPLICATION 2 ==="
    )


def test_build_historical_application_context_without_matches() -> None:
    context = build_historical_application_context([])

    assert context == NO_HISTORICAL_APPLICATIONS_CONTEXT
