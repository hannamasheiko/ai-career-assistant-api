import logging
from decimal import Decimal

from app.services.openai_cost_tracker import (
    calculate_openai_cost,
    log_openai_usage,
)


def test_calculate_chat_completion_cost() -> None:
    cost = calculate_openai_cost(
        model="gpt-5.6-luna",
        input_tokens=2642,
        output_tokens=669,
    )

    assert cost == {
        "input_cost": Decimal("0.0005284"),
        "output_cost": Decimal("0.0008028"),
        "total_cost": Decimal("0.0013312"),
    }


def test_calculate_embedding_cost() -> None:
    cost = calculate_openai_cost(
        model="text-embedding-3-small",
        input_tokens=470,
        output_tokens=0,
    )

    assert cost == {
        "input_cost": Decimal("0.0000094"),
        "output_cost": Decimal("0"),
        "total_cost": Decimal("0.0000094"),
    }


def test_unknown_model_returns_unavailable_cost() -> None:
    cost = calculate_openai_cost(
        model="unknown-model",
        input_tokens=100,
        output_tokens=50,
    )

    assert cost == {
        "input_cost": None,
        "output_cost": None,
        "total_cost": None,
    }


def test_log_openai_usage_includes_visible_values(
    caplog,
) -> None:
    with caplog.at_level(
        logging.INFO,
        logger="app.services.openai_cost_tracker",
    ):
        log_openai_usage(
            model="text-embedding-3-small",
            input_tokens=470,
            output_tokens=0,
            total_tokens=470,
        )

    record = caplog.records[-1]

    assert record.getMessage() == (
        "OpenAI API usage: "
        "model=text-embedding-3-small "
        "input_tokens=470 "
        "output_tokens=0 "
        "total_tokens=470 "
        "total_cost_usd=0.0000094"
    )

    assert record.event == "openai_api_usage"
    assert record.model == "text-embedding-3-small"
    assert record.total_cost_usd == "0.0000094"
    assert record.pricing_available is True
    assert record.pricing_updated_at == "2026-09-10"
