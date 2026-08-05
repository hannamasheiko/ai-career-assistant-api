from langchain_core.prompts import ChatPromptTemplate

from app.ai.llm_executor import invoke_structured_llm
from app.ai.prompts.resume_parsing import (
    RESUME_PARSING_SYSTEM_PROMPT,
    RESUME_PARSING_USER_PROMPT,
)
from app.schemas.ai_outputs import ParsedResume


async def parse_resume_chain(raw_text: str) -> ParsedResume:
    """Parse raw resume text into structured resume analysis and resume sections."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", RESUME_PARSING_SYSTEM_PROMPT),
            ("user", RESUME_PARSING_USER_PROMPT),
        ]
    )

    return await invoke_structured_llm(
        prompt=prompt,
        input_data={"resume_text": raw_text},
        output_schema=ParsedResume,
        temperature=0,
        error_message="Failed to parse resume into structured output",
    )
