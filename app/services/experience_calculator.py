from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from app.schemas.ai_outputs import ParsedWorkExperiencePeriod


def calculate_years_of_experience(
    periods: list[ParsedWorkExperiencePeriod] | None,
    *,
    as_of_date: date | None = None,
) -> Decimal | None:
    """Calculate unique commercial experience without double-counting overlaps."""

    if not periods:
        return None

    calculation_date = as_of_date or date.today()
    intervals: list[tuple[int, int]] = []

    for period in periods:
        if not period.is_commercial:
            continue

        if period.start_year is None:
            continue

        start_year = period.start_year
        start_month = period.start_month or 1

        if period.is_current:
            end_year = calculation_date.year
            end_month = calculation_date.month
        else:
            if period.end_year is None:
                continue

            end_year = period.end_year
            end_month = period.end_month or 12

        start_total_months = start_year * 12 + start_month
        end_total_months = end_year * 12 + end_month

        if end_total_months < start_total_months:
            continue

        intervals.append(
            (
                start_total_months,
                end_total_months,
            )
        )

    if not intervals:
        return None

    intervals.sort(key=lambda interval: interval[0])

    merged_intervals: list[list[int]] = []

    for start_month, end_month in intervals:
        if not merged_intervals:
            merged_intervals.append(
                [
                    start_month,
                    end_month,
                ]
            )
            continue

        previous_interval = merged_intervals[-1]
        previous_end_month = previous_interval[1]

        if start_month <= previous_end_month + 1:
            previous_interval[1] = max(
                previous_end_month,
                end_month,
            )
        else:
            merged_intervals.append(
                [
                    start_month,
                    end_month,
                ]
            )

    total_months = sum(
        end_month - start_month + 1
        for start_month, end_month in merged_intervals
    )

    if total_months == 0:
        return None

    years = Decimal(total_months) / Decimal(12)

    return years.quantize(
        Decimal("0.1"),
        rounding=ROUND_HALF_UP,
    )