"""Rules that link interactions to tracked vacancy statuses.

Everything a new interaction may or may not do to a tracked vacancy status
lives in the tables below, so the whole behaviour can be read in one place.
"""

from dataclasses import dataclass

from app.schemas.interaction_enums import (
    InteractionDirection,
    InteractionType,
)
from app.schemas.tracked_vacancy_enums import TrackedVacancyStatus

Direction = InteractionDirection
Status = TrackedVacancyStatus
Type = InteractionType


@dataclass(frozen=True)
class DirectionRule:
    """Directions an interaction type may be created with."""

    interaction_type: InteractionType
    allowed_directions: frozenset[InteractionDirection]
    error_message: str


@dataclass(frozen=True)
class StatusRule:
    """Tracked vacancy statuses an interaction type may be created from."""

    interaction_type: InteractionType
    allowed_statuses: frozenset[TrackedVacancyStatus]
    error_message: str


@dataclass(frozen=True)
class TransitionRule:
    """Status change caused by an interaction.

    directions=None means the direction does not matter.
    """

    interaction_types: frozenset[InteractionType]
    directions: frozenset[InteractionDirection] | None
    from_statuses: frozenset[TrackedVacancyStatus]
    to_status: TrackedVacancyStatus


DIRECTION_RULES: tuple[DirectionRule, ...] = (
    DirectionRule(
        interaction_type=Type.RESUME_SENT,
        allowed_directions=frozenset({Direction.OUTGOING}),
        error_message="A resume_sent interaction must have outgoing direction.",
    ),
    DirectionRule(
        interaction_type=Type.REJECTION,
        allowed_directions=frozenset({Direction.INCOMING, Direction.OUTGOING}),
        error_message="A rejection interaction must have a direction.",
    ),
    DirectionRule(
        interaction_type=Type.OFFER,
        allowed_directions=frozenset({Direction.INCOMING}),
        error_message="An offer interaction must have incoming direction.",
    ),
)


STATUS_RULES: tuple[StatusRule, ...] = (
    StatusRule(
        interaction_type=Type.REJECTION,
        allowed_statuses=frozenset(
            {
                Status.RESUME_SENT,
                Status.RECRUITER_CONTACT,
                Status.SCREENING,
                Status.INTERVIEW,
                Status.TEST_TASK,
                Status.OFFER,
            }
        ),
        error_message=(
            "A rejection interaction cannot be created for a tracked "
            "vacancy with status {status}."
        ),
    ),
    StatusRule(
        interaction_type=Type.OFFER,
        allowed_statuses=frozenset(Status)
        - {Status.REJECTED, Status.DISCARDED, Status.CLOSED},
        error_message=(
            "An offer interaction cannot be created for a tracked "
            "vacancy with status {status}."
        ),
    ),
)


TRANSITION_RULES: tuple[TransitionRule, ...] = (
    TransitionRule(
        interaction_types=frozenset({Type.RESUME_SENT}),
        directions=None,
        from_statuses=frozenset({Status.SAVED, Status.ANALYZED}),
        to_status=Status.RESUME_SENT,
    ),
    TransitionRule(
        interaction_types=frozenset({Type.MESSAGE, Type.CALL}),
        directions=frozenset({Direction.INCOMING}),
        from_statuses=frozenset(
            {Status.SAVED, Status.ANALYZED, Status.RESUME_SENT}
        ),
        to_status=Status.RECRUITER_CONTACT,
    ),
    TransitionRule(
        interaction_types=frozenset({Type.SCREENING_QUESTIONS}),
        directions=frozenset({Direction.INCOMING}),
        from_statuses=frozenset({Status.RESUME_SENT, Status.RECRUITER_CONTACT}),
        to_status=Status.SCREENING,
    ),
    TransitionRule(
        interaction_types=frozenset(
            {
                Type.HR_INTERVIEW,
                Type.TECHNICAL_INTERVIEW,
                Type.FINAL_INTERVIEW,
            }
        ),
        directions=None,
        from_statuses=frozenset(
            {
                Status.RESUME_SENT,
                Status.RECRUITER_CONTACT,
                Status.SCREENING,
                Status.TEST_TASK,
            }
        ),
        to_status=Status.INTERVIEW,
    ),
    TransitionRule(
        interaction_types=frozenset({Type.TEST_TASK}),
        directions=frozenset({Direction.INCOMING}),
        from_statuses=frozenset(
            {
                Status.RESUME_SENT,
                Status.RECRUITER_CONTACT,
                Status.SCREENING,
                Status.INTERVIEW,
            }
        ),
        to_status=Status.TEST_TASK,
    ),
    TransitionRule(
        interaction_types=frozenset({Type.OFFER}),
        directions=None,
        from_statuses=frozenset(
            {
                Status.RESUME_SENT,
                Status.RECRUITER_CONTACT,
                Status.SCREENING,
                Status.INTERVIEW,
                Status.TEST_TASK,
                Status.OFFER,
            }
        ),
        to_status=Status.OFFER,
    ),
    TransitionRule(
        interaction_types=frozenset({Type.REJECTION}),
        directions=None,
        from_statuses=frozenset(
            {
                Status.RESUME_SENT,
                Status.RECRUITER_CONTACT,
                Status.SCREENING,
                Status.INTERVIEW,
                Status.TEST_TASK,
                Status.OFFER,
            }
        ),
        to_status=Status.REJECTED,
    ),
)


def find_direction_violation(
    interaction_type: InteractionType,
    direction: InteractionDirection | None,
) -> str | None:
    """Return an error message if the direction is not allowed, else None."""

    for rule in DIRECTION_RULES:
        if rule.interaction_type == interaction_type:
            if direction not in rule.allowed_directions:
                return rule.error_message

    return None


def find_status_violation(
    interaction_type: InteractionType,
    status: TrackedVacancyStatus,
) -> str | None:
    """Return an error message if the status does not allow this interaction."""

    for rule in STATUS_RULES:
        if rule.interaction_type == interaction_type:
            if status not in rule.allowed_statuses:
                return rule.error_message.format(status=status)

    return None


def next_status(
    status: TrackedVacancyStatus,
    interaction_type: InteractionType,
    direction: InteractionDirection | None,
) -> TrackedVacancyStatus:
    """Return the status after the interaction; unchanged if no rule applies."""

    for rule in TRANSITION_RULES:
        if (
            interaction_type in rule.interaction_types
            and (rule.directions is None or direction in rule.directions)
            and status in rule.from_statuses
        ):
            return rule.to_status

    return status
