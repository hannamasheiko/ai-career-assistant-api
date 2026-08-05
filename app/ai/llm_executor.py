from typing import Any, TypeVar

from langchain_core.prompts import BasePromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.services.openai_cost_tracker import log_openai_usage


StructuredOutputT = TypeVar(
    "StructuredOutputT",
    bound=BaseModel,
)


async def invoke_structured_llm(
    *,
    prompt: BasePromptTemplate,
    input_data: dict[str, Any],
    output_schema: type[StructuredOutputT],
    temperature: float = 0,
    error_message: str = "Failed to parse structured AI output",
) -> StructuredOutputT:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=temperature,
    )

    structured_llm = llm.with_structured_output(
        output_schema,
        include_raw=True,
    )

    chain = prompt | structured_llm
    result = await chain.ainvoke(input_data)

    parsed_result = result["parsed"]
    raw_response = result["raw"]

    if parsed_result is None:
        parsing_error = result.get("parsing_error")
        raise RuntimeError(error_message) from parsing_error

    usage_metadata = getattr(raw_response, "usage_metadata", None)

    if usage_metadata:
        log_openai_usage(
            model=settings.openai_model,
            input_tokens=usage_metadata.get("input_tokens", 0),
            output_tokens=usage_metadata.get("output_tokens", 0),
            total_tokens=usage_metadata.get("total_tokens", 0),
        )

    return parsed_result