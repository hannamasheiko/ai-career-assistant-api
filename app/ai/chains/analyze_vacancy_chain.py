from langchain_core.prompts import ChatPromptTemplate

from app.ai.llm_executor import invoke_structured_llm
from app.ai.prompts.vacancy_analysis import (
    VACANCY_ANALYSIS_SYSTEM_PROMPT,
    VACANCY_ANALYSIS_USER_PROMPT,
)
from app.schemas.ai_outputs import ParsedVacancyAnalysis


async def analyze_vacancy_chain(
    vacancy_text: str,
) -> ParsedVacancyAnalysis:
    """Analyze vacancy text into structured AI-generated vacancy analysis."""

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", VACANCY_ANALYSIS_SYSTEM_PROMPT),
            ("user", VACANCY_ANALYSIS_USER_PROMPT),
        ]
    )

    return await invoke_structured_llm(
        prompt=prompt,
        input_data={"vacancy_text": vacancy_text},
        output_schema=ParsedVacancyAnalysis,
        temperature=0,
        error_message="Failed to analyze vacancy into structured output",
    )
