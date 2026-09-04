from pydantic import BaseModel, Field


class CoverLetterStrategy(BaseModel):
    """Structured strategy for generating a vacancy-specific cover letter."""

    primary_hiring_focus: str = Field(
        description=(
            "The single most important hiring criterion the employer needs to "
            "see or verify in a candidate for this specific vacancy. Determine "
            "it from the role responsibilities, experience expectations, "
            "seniority, key requirements, and emphasis in the vacancy text. "
            "It must not be merely a role title, a broad role category, a list "
            "of technologies, or a description of the candidate."
        )
    )
