from langchain_core.prompts import ChatPromptTemplate

from app.ai.llm_executor import invoke_structured_llm
from app.ai.prompts.cover_letter_strategy import (
    COVER_LETTER_STRATEGY_SYSTEM_PROMPT,
    COVER_LETTER_STRATEGY_USER_PROMPT,
)
from app.schemas.cover_letter_strategy import CoverLetterStrategy


async def generate_cover_letter_strategy(
    resume_text: str,
    vacancy_text: str,
    match_analysis_text: str,
) -> CoverLetterStrategy:
    """Generate a structured cover letter strategy from raw input texts."""

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", COVER_LETTER_STRATEGY_SYSTEM_PROMPT),
            ("user", COVER_LETTER_STRATEGY_USER_PROMPT),
        ]
    )

    return await invoke_structured_llm(
        prompt=prompt,
        input_data={
            "resume_text": resume_text,
            "vacancy_text": vacancy_text,
            "match_analysis_text": match_analysis_text,
        },
        output_schema=CoverLetterStrategy,
        temperature=0,
        error_message="Failed to generate structured cover letter strategy",
    )
