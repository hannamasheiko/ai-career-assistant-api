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
    key_hiring_criteria: list[str] = Field(
        description=(
            "The 2–4 most important hiring-decision-relevant criteria the "
            "candidate needs to convincingly demonstrate for this specific "
            "vacancy. Each criterion must describe a concrete capability, "
            "experience dimension, or professional evidence that can later "
            "guide evidence selection. They must not be merely a list of "
            "technologies or requirements copied from the vacancy."
        )
    )
    primary_evidence: str = Field(
        description=(
            "The single strongest vacancy-specific evidence from the "
            "candidate's actual resume that best supports the primary hiring "
            "focus and, where relevant, the key hiring criteria. Select it by "
            "hiring importance and relevance, without a fixed preference for "
            "commercial experience, the newest experience, or an exact stack "
            "match. It must be factual and specific enough to guide the writer, "
            "but must not be a ready-made cover letter paragraph."
        )
    )
