from typing import Annotated, Any

import pycountry
from pydantic import BeforeValidator


def normalize_and_validate_currency_code(value: Any) -> Any:
    """Normalize and validate an ISO 4217 currency code."""

    if value is None:
        return None

    if not isinstance(value, str):
        return value

    normalized_value = value.strip().upper()

    currency = pycountry.currencies.get(
        alpha_3=normalized_value,
    )

    if currency is None:
        raise ValueError(
            "desired_salary_currency must be a valid ISO 4217 currency code"
        )

    return normalized_value


CurrencyCode = Annotated[
    str,
    BeforeValidator(normalize_and_validate_currency_code),
]