from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

import app.ai.llm_executor as llm_executor_module
from app.ai.llm_executor import invoke_structured_llm
from app.core.exceptions import AIOutputValidationError


pytestmark = pytest.mark.anyio


class StructuredOutputFixture(BaseModel):
    value: str


class FakeChain:
    def __init__(self, result: dict):
        self.result = result
        self.received_input: dict | None = None

    async def ainvoke(self, input_data: dict) -> dict:
        self.received_input = input_data
        return self.result


class FakePrompt:
    def __init__(self, chain: FakeChain):
        self.chain = chain
        self.received_structured_llm = None

    def __or__(self, structured_llm):
        self.received_structured_llm = structured_llm
        return self.chain


def configure_openai_settings(monkeypatch) -> None:
    monkeypatch.setattr(
        llm_executor_module.settings,
        "openai_api_key",
        "test-api-key",
    )
    monkeypatch.setattr(
        llm_executor_module.settings,
        "openai_model",
        "test-model",
    )


async def test_invoke_structured_llm_returns_parsed_result(
    monkeypatch,
) -> None:
    configure_openai_settings(monkeypatch)

    expected_result = StructuredOutputFixture(value="parsed successfully")

    chain = FakeChain(
        result={
            "parsed": expected_result,
            "raw": SimpleNamespace(usage_metadata=None),
            "parsing_error": None,
        }
    )
    prompt = FakePrompt(chain)

    structured_llm = object()
    llm_mock = MagicMock()
    llm_mock.with_structured_output.return_value = structured_llm

    chat_openai_mock = MagicMock(return_value=llm_mock)
    log_usage_mock = MagicMock()

    monkeypatch.setattr(
        llm_executor_module,
        "ChatOpenAI",
        chat_openai_mock,
    )
    monkeypatch.setattr(
        llm_executor_module,
        "log_openai_usage",
        log_usage_mock,
    )

    result = await invoke_structured_llm(
        prompt=prompt,
        input_data={"text": "test input"},
        output_schema=StructuredOutputFixture,
        temperature=0.2,
    )

    assert result == expected_result
    assert chain.received_input == {"text": "test input"}
    assert prompt.received_structured_llm is structured_llm

    chat_openai_mock.assert_called_once_with(
        model="test-model",
        api_key="test-api-key",
        temperature=0.2,
        timeout=llm_executor_module.settings.openai_timeout,
        max_retries=llm_executor_module.settings.openai_max_retries,
    )
    llm_mock.with_structured_output.assert_called_once_with(
        StructuredOutputFixture,
        include_raw=True,
    )
    log_usage_mock.assert_not_called()


async def test_invoke_structured_llm_raises_when_api_key_is_missing(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        llm_executor_module.settings,
        "openai_api_key",
        None,
    )

    chat_openai_mock = MagicMock()

    monkeypatch.setattr(
        llm_executor_module,
        "ChatOpenAI",
        chat_openai_mock,
    )

    chain = FakeChain(result={})
    prompt = FakePrompt(chain)

    with pytest.raises(
        RuntimeError,
        match="OPENAI_API_KEY is not configured",
    ):
        await invoke_structured_llm(
            prompt=prompt,
            input_data={"text": "test input"},
            output_schema=StructuredOutputFixture,
        )

    chat_openai_mock.assert_not_called()


async def test_invoke_structured_llm_raises_when_parsing_fails(
    monkeypatch,
) -> None:
    configure_openai_settings(monkeypatch)

    original_error = ValueError("Invalid structured output")

    chain = FakeChain(
        result={
            "parsed": None,
            "raw": SimpleNamespace(usage_metadata=None),
            "parsing_error": original_error,
        }
    )
    prompt = FakePrompt(chain)

    llm_mock = MagicMock()
    llm_mock.with_structured_output.return_value = object()

    monkeypatch.setattr(
        llm_executor_module,
        "ChatOpenAI",
        MagicMock(return_value=llm_mock),
    )

    with pytest.raises(
        AIOutputValidationError,
        match="Failed to parse test output",
    ) as exc_info:
        await invoke_structured_llm(
            prompt=prompt,
            input_data={"text": "test input"},
            output_schema=StructuredOutputFixture,
            error_message="Failed to parse test output",
        )

    assert exc_info.value.__cause__ is original_error


async def test_invoke_structured_llm_logs_token_usage(
    monkeypatch,
) -> None:
    configure_openai_settings(monkeypatch)

    expected_result = StructuredOutputFixture(value="parsed successfully")

    raw_response = SimpleNamespace(
        usage_metadata={
            "input_tokens": 120,
            "output_tokens": 30,
            "total_tokens": 150,
        }
    )

    chain = FakeChain(
        result={
            "parsed": expected_result,
            "raw": raw_response,
            "parsing_error": None,
        }
    )
    prompt = FakePrompt(chain)

    llm_mock = MagicMock()
    llm_mock.with_structured_output.return_value = object()

    log_usage_mock = MagicMock()

    monkeypatch.setattr(
        llm_executor_module,
        "ChatOpenAI",
        MagicMock(return_value=llm_mock),
    )
    monkeypatch.setattr(
        llm_executor_module,
        "log_openai_usage",
        log_usage_mock,
    )

    result = await invoke_structured_llm(
        prompt=prompt,
        input_data={"text": "test input"},
        output_schema=StructuredOutputFixture,
    )

    assert result == expected_result

    log_usage_mock.assert_called_once_with(
        model="test-model",
        input_tokens=120,
        output_tokens=30,
        total_tokens=150,
    )
