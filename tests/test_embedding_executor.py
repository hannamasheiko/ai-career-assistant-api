import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from openai import AuthenticationError, BadRequestError

from app.ai.embedding_executor import create_embedding
from app.core.config import settings
from app.core.exceptions import (
    AIConfigurationError,
    AIOutputValidationError,
    AIServiceError,
)


def build_openai_status_error(
    error_class: type[Exception],
    message: str,
    status_code: int,
) -> Exception:
    request = httpx.Request(
        "POST",
        "https://api.openai.com/v1/embeddings",
    )
    response = httpx.Response(status_code=status_code, request=request)

    return error_class(message, response=response, body=None)


def test_create_embedding_returns_vector_and_logs_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "openai_api_key",
        "test-api-key",
    )

    expected_embedding = [0.1] * 1536
    response = SimpleNamespace(
        data=[
            SimpleNamespace(
                embedding=expected_embedding,
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=120,
            total_tokens=120,
        ),
    )

    with (
        patch(
            "app.ai.embedding_executor.AsyncOpenAI"
        ) as openai_client_class,
        patch(
            "app.ai.embedding_executor.log_openai_usage"
        ) as log_usage_mock,
    ):
        client = openai_client_class.return_value
        client.embeddings.create = AsyncMock(
            return_value=response
        )

        result = asyncio.run(
            create_embedding("  vacancy text  ")
        )

    assert result == expected_embedding

    client.embeddings.create.assert_awaited_once_with(
        input="vacancy text",
        model="text-embedding-3-small",
        dimensions=1536,
        encoding_format="float",
    )

    log_usage_mock.assert_called_once_with(
        model="text-embedding-3-small",
        input_tokens=120,
        output_tokens=0,
        total_tokens=120,
    )

def test_create_embedding_rejects_empty_text() -> None:
    with patch(
        "app.ai.embedding_executor.AsyncOpenAI"
    ) as openai_client_class:
        with pytest.raises(
            ValueError,
            match="Embedding input must not be empty",
        ):
            asyncio.run(create_embedding("   "))

    openai_client_class.assert_not_called()


def test_create_embedding_rejects_unexpected_dimension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "openai_api_key",
        "test-api-key",
    )

    response = SimpleNamespace(
        data=[
            SimpleNamespace(
                embedding=[0.1, 0.2],
            )
        ]
    )

    with patch(
        "app.ai.embedding_executor.AsyncOpenAI"
    ) as openai_client_class:
        client = openai_client_class.return_value
        client.embeddings.create = AsyncMock(
            return_value=response
        )

        with pytest.raises(
            AIOutputValidationError,
            match="unexpected dimension",
        ):
            asyncio.run(
                create_embedding("vacancy text")
            )


def test_create_embedding_raises_configuration_error_when_key_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "openai_api_key",
        None,
    )

    with patch(
        "app.ai.embedding_executor.AsyncOpenAI"
    ) as openai_client_class:
        with pytest.raises(
            AIConfigurationError,
            match="OPENAI_API_KEY is not configured",
        ):
            asyncio.run(create_embedding("vacancy text"))

    openai_client_class.assert_not_called()


def test_create_embedding_raises_configuration_error_on_auth_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "openai_api_key",
        "test-api-key",
    )

    original_error = build_openai_status_error(
        AuthenticationError,
        "Invalid API key",
        status_code=401,
    )

    with patch(
        "app.ai.embedding_executor.AsyncOpenAI"
    ) as openai_client_class:
        client = openai_client_class.return_value
        client.embeddings.create = AsyncMock(
            side_effect=original_error
        )

        with pytest.raises(AIConfigurationError) as exc_info:
            asyncio.run(create_embedding("vacancy text"))

    assert exc_info.value.__cause__ is original_error


def test_create_embedding_raises_service_error_on_other_provider_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "openai_api_key",
        "test-api-key",
    )

    original_error = build_openai_status_error(
        BadRequestError,
        "Invalid request",
        status_code=400,
    )

    with patch(
        "app.ai.embedding_executor.AsyncOpenAI"
    ) as openai_client_class:
        client = openai_client_class.return_value
        client.embeddings.create = AsyncMock(
            side_effect=original_error
        )

        with pytest.raises(AIServiceError) as exc_info:
            asyncio.run(create_embedding("vacancy text"))

    assert exc_info.value.__cause__ is original_error
    assert not isinstance(exc_info.value, AIConfigurationError)
