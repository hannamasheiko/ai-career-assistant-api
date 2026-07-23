"""add constraints to tracked vacancy fields

Revision ID: 4876353f99e0
Revises: d083c1618957
Create Date: 2026-07-23 15:09:54.679896

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4876353f99e0'
down_revision: Union[str, Sequence[str], None] = 'd083c1618957'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.alter_column(
        "tracked_vacancies",
        "priority",
        existing_type=sa.VARCHAR(length=100),
        nullable=False,
        server_default="low",
    )

    op.alter_column(
        "tracked_vacancies",
        "decision",
        existing_type=sa.VARCHAR(length=100),
        nullable=False,
        server_default="interested",
    )

    op.create_check_constraint(
        "ck_tracked_vacancies_status",
        "tracked_vacancies",
        """
        status IN (
            'saved',
            'analyzed',
            'resume_sent',
            'recruiter_contact',
            'screening',
            'interview',
            'test_task',
            'offer',
            'rejected',
            'discarded',
            'closed'
        )
        """,
    )

    op.create_check_constraint(
        "ck_tracked_vacancies_priority",
        "tracked_vacancies",
        "priority IN ('low', 'medium', 'high')",
    )

    op.create_check_constraint(
        "ck_tracked_vacancies_decision",
        "tracked_vacancies",
        """
        decision IN (
            'interested',
            'consider_later',
            'not_interested'
        )
        """,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_constraint(
        "ck_tracked_vacancies_decision",
        "tracked_vacancies",
        type_="check",
    )

    op.drop_constraint(
        "ck_tracked_vacancies_priority",
        "tracked_vacancies",
        type_="check",
    )

    op.drop_constraint(
        "ck_tracked_vacancies_status",
        "tracked_vacancies",
        type_="check",
    )

    op.alter_column(
        "tracked_vacancies",
        "decision",
        existing_type=sa.VARCHAR(length=100),
        nullable=True,
        server_default=None,
    )

    op.alter_column(
        "tracked_vacancies",
        "priority",
        existing_type=sa.VARCHAR(length=100),
        nullable=True,
        server_default=None,
    )
