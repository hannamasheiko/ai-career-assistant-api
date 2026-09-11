from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.historical_application_retrieval_service import (
        HistoricalApplicationMatch,
    )


NO_HISTORICAL_APPLICATIONS_CONTEXT = (
    "No historical application examples are available."
)


def build_historical_application_context(
    matches: Sequence["HistoricalApplicationMatch"],
) -> str:
    """Build prompt context from historical applications."""

    if not matches:
        return NO_HISTORICAL_APPLICATIONS_CONTEXT

    examples: list[str] = []

    for index, match in enumerate(matches, start=1):
        company_name = match.company_name or "Unknown company"

        examples.append(
            "\n".join(
                [
                    f"=== HISTORICAL APPLICATION {index} ===",
                    f"Company: {company_name}",
                    f"Position: {match.position_title}",
                    "",
                    "Historical vacancy context:",
                    match.vacancy_embedding_source_text,
                    "",
                    "Actually sent cover letter:",
                    match.message_text,
                ]
            )
        )

    return "\n\n".join(examples)
