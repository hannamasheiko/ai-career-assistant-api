from decimal import Decimal

from app.schemas.ai_outputs import ParsedWorkExperiencePeriod
from app.services.experience_calculator import calculate_years_of_experience
from datetime import date


def test_returns_none_when_periods_are_none():
    result = calculate_years_of_experience(None)

    assert result is None


def test_returns_none_when_periods_are_empty():
    result = calculate_years_of_experience([])

    assert result is None


def test_calculates_one_full_year_of_experience():
    periods = [
        ParsedWorkExperiencePeriod(
            start_month=1,
            start_year=2020,
            end_month=12,
            end_year=2020,
            is_current=False,
            is_commercial=True,
        )
    ]

    result = calculate_years_of_experience(periods)

    assert result == Decimal("1.0")

def test_ignores_non_commercial_experience():
    periods = [
        ParsedWorkExperiencePeriod(
            start_month=1,
            start_year=2020,
            end_month=12,
            end_year=2020,
            is_current=False,
            is_commercial=False,
        )
    ]

    result = calculate_years_of_experience(periods)

    assert result is None

def test_sums_multiple_non_overlapping_commercial_periods():
    periods = [
        ParsedWorkExperiencePeriod(
            start_month=1,
            start_year=2020,
            end_month=12,
            end_year=2020,
            is_current=False,
            is_commercial=True,
        ),
        ParsedWorkExperiencePeriod(
            start_month=1,
            start_year=2021,
            end_month=6,
            end_year=2021,
            is_current=False,
            is_commercial=True,
        ),
    ]

    result = calculate_years_of_experience(periods)

    assert result == Decimal("1.5")

def test_merges_overlapping_commercial_periods() -> None:
    periods = [
        ParsedWorkExperiencePeriod(
            start_month=1,
            start_year=2022,
            end_month=12,
            end_year=2023,
            is_current=False,
            is_commercial=True,
        ),
        ParsedWorkExperiencePeriod(
            start_month=6,
            start_year=2022,
            end_month=3,
            end_year=2023,
            is_current=False,
            is_commercial=True,
        ),
    ]

    result = calculate_years_of_experience(periods)

    assert result == Decimal("2.0")

def test_calculates_current_commercial_period_until_as_of_date() -> None:
    periods = [
        ParsedWorkExperiencePeriod(
            start_month=5,
            start_year=2024,
            end_month=None,
            end_year=None,
            is_current=True,
            is_commercial=True,
        ),
    ]

    result = calculate_years_of_experience(
        periods,
        as_of_date=date(2026, 8, 6),
    )

    assert result == Decimal("2.3")