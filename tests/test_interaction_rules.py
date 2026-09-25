from itertools import product

import pytest

from app.schemas.interaction_enums import InteractionDirection, InteractionType
from app.schemas.tracked_vacancy_enums import TrackedVacancyStatus
from app.services.interaction_rules import (
    TRANSITION_RULES,
    find_direction_violation,
    find_status_violation,
    next_status,
)

Direction = InteractionDirection
Status = TrackedVacancyStatus
Type = InteractionType

DIRECTIONS = [None, Direction.INCOMING, Direction.OUTGOING]


@pytest.mark.parametrize(
    ("status", "interaction_type", "direction", "expected"),
    [
        (Status.SAVED, Type.RESUME_SENT, Direction.OUTGOING, Status.RESUME_SENT),
        (Status.ANALYZED, Type.RESUME_SENT, Direction.OUTGOING, Status.RESUME_SENT),
        (Status.RECRUITER_CONTACT, Type.RESUME_SENT, Direction.OUTGOING, Status.RECRUITER_CONTACT),
        (Status.SAVED, Type.MESSAGE, Direction.INCOMING, Status.RECRUITER_CONTACT),
        (Status.RESUME_SENT, Type.CALL, Direction.INCOMING, Status.RECRUITER_CONTACT),
        (Status.SAVED, Type.MESSAGE, Direction.OUTGOING, Status.SAVED),
        (Status.RESUME_SENT, Type.SCREENING_QUESTIONS, Direction.INCOMING, Status.SCREENING),
        (Status.RESUME_SENT, Type.SCREENING_QUESTIONS, Direction.OUTGOING, Status.RESUME_SENT),
        (Status.RECRUITER_CONTACT, Type.HR_INTERVIEW, None, Status.INTERVIEW),
        (Status.TEST_TASK, Type.TECHNICAL_INTERVIEW, Direction.OUTGOING, Status.INTERVIEW),
        (Status.SCREENING, Type.FINAL_INTERVIEW, Direction.INCOMING, Status.INTERVIEW),
        (Status.INTERVIEW, Type.TEST_TASK, Direction.INCOMING, Status.TEST_TASK),
        (Status.INTERVIEW, Type.TEST_TASK, Direction.OUTGOING, Status.INTERVIEW),
        (Status.INTERVIEW, Type.OFFER, Direction.INCOMING, Status.OFFER),
        (Status.OFFER, Type.OFFER, Direction.INCOMING, Status.OFFER),
        (Status.SCREENING, Type.REJECTION, Direction.INCOMING, Status.REJECTED),
        (Status.OFFER, Type.REJECTION, Direction.OUTGOING, Status.REJECTED),
        (Status.INTERVIEW, Type.FEEDBACK, Direction.INCOMING, Status.INTERVIEW),
        (Status.CLOSED, Type.MESSAGE, Direction.INCOMING, Status.CLOSED),
    ],
)
def test_next_status(status, interaction_type, direction, expected):
    assert next_status(status, interaction_type, direction) == expected


def test_no_two_transition_rules_match_the_same_input():
    """Rule order must never matter: at most one rule fits any event."""

    for status, interaction_type, direction in product(
        Status, Type, DIRECTIONS
    ):
        matching_rules = [
            rule
            for rule in TRANSITION_RULES
            if interaction_type in rule.interaction_types
            and (rule.directions is None or direction in rule.directions)
            and status in rule.from_statuses
        ]

        assert len(matching_rules) <= 1, (status, interaction_type, direction)


@pytest.mark.parametrize(
    ("interaction_type", "direction", "has_violation"),
    [
        (Type.RESUME_SENT, Direction.OUTGOING, False),
        (Type.RESUME_SENT, Direction.INCOMING, True),
        (Type.RESUME_SENT, None, True),
        (Type.OFFER, Direction.INCOMING, False),
        (Type.OFFER, Direction.OUTGOING, True),
        (Type.OFFER, None, True),
        (Type.REJECTION, Direction.INCOMING, False),
        (Type.REJECTION, Direction.OUTGOING, False),
        (Type.REJECTION, None, True),
        (Type.MESSAGE, None, False),
        (Type.FEEDBACK, None, False),
    ],
)
def test_find_direction_violation(interaction_type, direction, has_violation):
    violation = find_direction_violation(interaction_type, direction)

    assert (violation is not None) == has_violation


@pytest.mark.parametrize(
    ("interaction_type", "status", "has_violation"),
    [
        (Type.REJECTION, Status.SAVED, True),
        (Type.REJECTION, Status.ANALYZED, True),
        (Type.REJECTION, Status.RESUME_SENT, False),
        (Type.REJECTION, Status.OFFER, False),
        (Type.REJECTION, Status.REJECTED, True),
        (Type.OFFER, Status.SAVED, False),
        (Type.OFFER, Status.INTERVIEW, False),
        (Type.OFFER, Status.REJECTED, True),
        (Type.OFFER, Status.DISCARDED, True),
        (Type.OFFER, Status.CLOSED, True),
        (Type.MESSAGE, Status.CLOSED, False),
    ],
)
def test_find_status_violation(interaction_type, status, has_violation):
    violation = find_status_violation(interaction_type, status)

    assert (violation is not None) == has_violation


def test_status_violation_message_names_the_current_status():
    violation = find_status_violation(Type.REJECTION, Status.SAVED)

    assert violation == (
        "A rejection interaction cannot be created for a tracked "
        "vacancy with status saved."
    )
