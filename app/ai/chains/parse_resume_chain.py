from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.schemas.ai_outputs import ParsedResume

from app.services.openai_cost_tracker import log_openai_usage

from app.ai.prompts.resume_parsing import (
    RESUME_PARSING_SYSTEM_PROMPT,
    RESUME_PARSING_USER_PROMPT,
)


async def parse_resume_chain(raw_text: str) -> ParsedResume:
    """Parse raw resume text into structured resume analysis and resume sections."""

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system", RESUME_PARSING_SYSTEM_PROMPT
            ),
            (
                "user", RESUME_PARSING_USER_PROMPT
            ),
        ]
    )

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )

    structured_llm = llm.with_structured_output(
        ParsedResume,
        include_raw=True,
    )

    chain = prompt | structured_llm

    result = await chain.ainvoke(
        {
            "resume_text": raw_text,
        }
    )

    parsed_resume = result["parsed"]
    raw_response = result["raw"]

    if parsed_resume is None:
        raise RuntimeError("Failed to parse resume into structured output")

    usage_metadata = getattr(raw_response, "usage_metadata", None)

    if usage_metadata:
        input_tokens = usage_metadata.get("input_tokens", 0)
        output_tokens = usage_metadata.get("output_tokens", 0)
        total_tokens = usage_metadata.get("total_tokens", 0)

        log_openai_usage(
            model=settings.openai_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

    return parsed_resume