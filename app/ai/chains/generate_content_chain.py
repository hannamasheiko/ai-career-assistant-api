from langchain_core.prompts import ChatPromptTemplate

from app.ai.llm_executor import invoke_structured_llm
from app.ai.prompts.content_generation import (
    GENERATED_CONTENT_SYSTEM_PROMPT,
    GENERATED_CONTENT_USER_PROMPT,
)
from app.schemas.ai_outputs import ParsedGeneratedContent
from app.schemas.cover_letter_strategy import CoverLetterStrategy


async def generate_content_chain(
    content_type: str,
    resume_text: str,
    vacancy_text: str,
    strategy: CoverLetterStrategy,
    historical_application_context: str,
    language: str,
    tone: str | None,
    extra_instructions: str | None,
) -> ParsedGeneratedContent:
    """Generate AI content for a tracked vacancy."""

    if content_type != "cover_letter":
        raise ValueError(
            f"Unsupported generated content type: {content_type}"
        )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", GENERATED_CONTENT_SYSTEM_PROMPT),
            ("user", GENERATED_CONTENT_USER_PROMPT),
        ]
    )

    return await invoke_structured_llm(
        prompt=prompt,
        input_data={
            "content_type": content_type,
            "resume_text": resume_text,
            "vacancy_text": vacancy_text,
            "primary_hiring_focus": strategy.primary_hiring_focus,
            "key_hiring_criteria": strategy.key_hiring_criteria,
            "primary_evidence": strategy.primary_evidence,
            "supporting_evidence": strategy.supporting_evidence,
            "positioning_strategy": strategy.positioning_strategy,
            "historical_application_context": historical_application_context,
            "language": language,
            "tone": tone or "professional",
            "extra_instructions": (
                extra_instructions
                or "No extra instructions."
            ),
        },
        output_schema=ParsedGeneratedContent,
        temperature=0.3,
        error_message="Failed to generate structured content",
    )
