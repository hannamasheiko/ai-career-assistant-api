from langchain_core.prompts import ChatPromptTemplate

from app.ai.llm_executor import invoke_structured_llm
from app.ai.prompts.vacancy_parsing import (
    VACANCY_PARSING_SYSTEM_PROMPT,
    VACANCY_PARSING_USER_PROMPT,
)
from app.schemas.ai_outputs import ParsedVacancyDetails


async def parse_vacancy_chain(raw_text: str) -> ParsedVacancyDetails:
    """Parse copied vacancy page text into structured vacancy details."""

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", VACANCY_PARSING_SYSTEM_PROMPT),
            ("user", VACANCY_PARSING_USER_PROMPT),
        ]
    )

    return await invoke_structured_llm(
        prompt=prompt,
        input_data={"vacancy_text": raw_text},
        output_schema=ParsedVacancyDetails,
        temperature=0,
        error_message="Failed to parse vacancy into structured output",
    )