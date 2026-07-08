from decimal import Decimal


MODEL_PRICING_USD_PER_1M_TOKENS = {
    "gpt-4o-mini": {
        "input": Decimal("0.15"),
        "output": Decimal("0.60"),
    },
    "gpt-4.1-mini": {
        "input": Decimal("0.40"),
        "output": Decimal("1.60"),
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


def print_openai_usage(
    model: str,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
) -> None:
    """Print OpenAI token usage and estimated cost."""

    cost = calculate_openai_cost(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    print("========== OPENAI TOKEN USAGE ==========")
    print(f"Model: {model}")
    print(f"Input tokens: {input_tokens}")
    print(f"Output tokens: {output_tokens}")
    print(f"Total tokens: {total_tokens}")

    if cost["total_cost"] is None:
        print("Estimated cost: unknown pricing for this model")
    else:
        print(f"Estimated input cost: ${cost['input_cost']:.6f}")
        print(f"Estimated output cost: ${cost['output_cost']:.6f}")
        print(f"Estimated total cost: ${cost['total_cost']:.6f}")

    print("========================================")