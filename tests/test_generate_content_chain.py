import asyncio

from app.ai.chains import generate_content_chain as chain_module
from app.ai.prompts.content_generation import (
    GENERATED_CONTENT_SYSTEM_PROMPT,
)
from app.schemas.ai_outputs import ParsedGeneratedContent
from app.schemas.cover_letter_strategy import CoverLetterStrategy


def test_generate_content_chain_includes_historical_context_in_prompt(
    monkeypatch,
) -> None:
    historical_context = (
        "=== HISTORICAL APPLICATION 1 ===\n"
        "Company: Historical Company\n"
        "Position: Historical Engineer\n\n"
        "Historical vacancy context:\n"
        "Required skills: Python; PostgreSQL\n\n"
        "Actually sent cover letter:\n"
        "I previously described relevant API development experience."
    )
    strategy = CoverLetterStrategy(
        primary_hiring_focus="Practical software delivery ability.",
        key_hiring_criteria=[
            "Ability to deliver reliable production software.",
            "Experience collaborating on technical requirements.",
        ],
        primary_evidence=(
            "A factual software project demonstrating practical delivery."
        ),
        supporting_evidence=[
            "Professional experience demonstrating responsible execution."
        ],
        positioning_strategy=(
            "Lead with practical delivery and use professional experience "
            "as complementary evidence."
        ),
    )

    async def mock_invoke_structured_llm(
        *,
        prompt,
        input_data,
        output_schema,
        temperature,
        error_message,
    ):
        assert input_data["historical_application_context"] == (
            historical_context
        )

        formatted_messages = prompt.format_messages(**input_data)
        user_message = formatted_messages[-1].content

        assert "Historical Company" in user_message
        assert "Historical Engineer" in user_message
        assert "Required skills: Python; PostgreSQL" in user_message
        assert (
            "I previously described relevant API development experience."
            in user_message
        )

        return ParsedGeneratedContent(
            generated_text="Generated cover letter."
        )

    monkeypatch.setattr(
        chain_module,
        "invoke_structured_llm",
        mock_invoke_structured_llm,
    )

    result = asyncio.run(
        chain_module.generate_content_chain(
            content_type="cover_letter",
            resume_text="Current factual resume.",
            vacancy_text="Current vacancy requirements.",
            strategy=strategy,
            historical_application_context=historical_context,
            language="uk",
            tone="professional",
            extra_instructions="Keep it concise.",
        )
    )

    assert result == ParsedGeneratedContent(
        generated_text="Generated cover letter."
    )


def test_content_generation_prompt_protects_writer_contract() -> None:
    normalized_prompt = " ".join(
        GENERATED_CONTENT_SYSTEM_PROMPT.split()
    )

    assert (
        "Historical examples не змінюють готову CoverLetterStrategy."
        in normalized_prompt
    )
    assert (
        "Не копіюй речення або абзаци з historical letters."
        in normalized_prompt
    )
    assert (
        "Не додавай facts, projects, technologies або professional goals "
        "з historical letters"
        in normalized_prompt
    )
    assert "не підтверджуються current resume" in normalized_prompt
    assert (
        "Не наслідуй мову historical example: пиши мовою, заданою у "
        "параметрі language."
        in normalized_prompt
    )
