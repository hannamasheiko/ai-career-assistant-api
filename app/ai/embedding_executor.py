import logging

from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    InternalServerError,
    RateLimitError,
)

from app.core.config import settings
from app.core.exceptions import (
    AIOutputValidationError,
    AIRateLimitError,
    AIServiceError,
    AITimeoutError,
)
from app.services.openai_cost_tracker import log_openai_usage


logger = logging.getLogger(__name__)


async def create_embedding(text: str) -> list[float]:
    """Create an embedding vector for non-empty text."""

    normalized_text = text.strip()

    if not normalized_text:
        raise ValueError("Embedding input must not be empty")

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout,
        max_retries=settings.openai_max_retries,
    )

    try:
        response = await client.embeddings.create(
            input=normalized_text,
            model=settings.openai_embedding_model,
            dimensions=settings.openai_embedding_dimensions,
            encoding_format="float",
        )

    except APITimeoutError as exc:
        logger.exception("OpenAI embedding request timed out.")
        raise AITimeoutError(
            "AI embedding request timed out."
        ) from exc

    except RateLimitError as exc:
        logger.exception("OpenAI embedding rate limit exceeded.")
        raise AIRateLimitError(
            "AI embedding rate limit exceeded."
        ) from exc

    except (APIConnectionError, InternalServerError) as exc:
        logger.exception(
            "OpenAI embedding service is temporarily unavailable."
        )
        raise AIServiceError(
            "AI embedding service is temporarily unavailable."
        ) from exc

    if not response.data:
        raise AIOutputValidationError(
            "OpenAI returned no embedding data."
        )

    embedding = response.data[0].embedding

    if len(embedding) != settings.openai_embedding_dimensions:
        raise AIOutputValidationError(
            "OpenAI returned an embedding with an unexpected dimension."
        )
    log_openai_usage(
        model=settings.openai_embedding_model,
        input_tokens=response.usage.prompt_tokens,
        output_tokens=0,
        total_tokens=response.usage.total_tokens,
    )

    return embedding
