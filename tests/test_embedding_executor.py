import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.embedding_executor import create_embedding
from app.core.config import settings
from app.core.exceptions import AIOutputValidationError


def test_create_embedding_returns_vector(
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
        ]
    )

    with patch(
        "app.ai.embedding_executor.AsyncOpenAI"
    ) as openai_client_class:
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
