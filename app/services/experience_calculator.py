from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from app.schemas.ai_outputs import ParsedWorkExperiencePeriod


def calculate_years_of_experience(
    periods: list[ParsedWorkExperiencePeriod] | None,
) -> Decimal | None:
    """Calculate total years of experience from parsed work experience periods."""

    if not periods:
        return None

    total_months = 0
    today = date.today()

    for period in periods:
        if not period.is_commercial:
            continue

        if period.start_year is None:
            continue

        start_month = period.start_month or 1
        start_year = period.start_year

        if period.is_current:
            end_year = today.year
            end_month = today.month
        else:
            if period.end_year is None:
                continue

            end_year = period.end_year
            end_month = period.end_month or 12

        start_total_months = start_year * 12 + start_month
        end_total_months = end_year * 12 + end_month

        months = end_total_months - start_total_months + 1

        if months > 0:
            total_months += months

    if total_months == 0:
        return None

    years = Decimal(total_months) / Decimal(12)

    return years.quantize(
        Decimal("0.1"),
        rounding=ROUND_HALF_UP,
    )

