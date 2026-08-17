import logging
from decimal import Decimal


logger = logging.getLogger(__name__)


MODEL_PRICING_USD_PER_1M_TOKENS = {
    "gpt-4o-mini": {
        "input": Decimal("0.15"),
        "output": Decimal("0.60"),
    },
    "gpt-4.1-mini": {
        "input": Decimal("0.40"),
        "output": Decimal("1.60"),
    },
    "gpt-5.4-mini": {
        "input": Decimal("0.75"),
        "output": Decimal("4.50"),
    },
    "gpt-5.6-terra": {
        "input": Decimal("2.00"),
        "output": Decimal("12.00"),
    },
    "gpt-5.6-luna": {
        "input": Decimal("0.20"),
        "output": Decimal("1.20"),
    },
}


def calculate_openai_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> dict[str, Decimal | None]:
    """Calculate estimated OpenAI API cost for token usage."""

    pricing = MODEL_PRICING_USD_PER_1M_TOKENS.get(model)

    if pricing is None:
        return {
            "input_cost": None,
            "output_cost": None,
            "total_cost": None,
        }

    input_cost = (Decimal(input_tokens) / Decimal(1_000_000)) * pricing["input"]
    output_cost = (Decimal(output_tokens) / Decimal(1_000_000)) * pricing["output"]
    total_cost = input_cost + output_cost

    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost,
    }


def log_openai_usage(
    model: str,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
) -> None:
    """Log OpenAI token usage and estimated cost."""

    cost = calculate_openai_cost(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    logger.info(
        "OpenAI API usage",
        extra={
            "event": "openai_api_usage",
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "input_cost_usd": (
                str(cost["input_cost"])
                if cost["input_cost"] is not None
                else None
            ),
            "output_cost_usd": (
                str(cost["output_cost"])
                if cost["output_cost"] is not None
                else None
            ),
            "total_cost_usd": (
                str(cost["total_cost"])
                if cost["total_cost"] is not None
                else None
            ),
            "pricing_available": cost["total_cost"] is not None,
        },
    )
