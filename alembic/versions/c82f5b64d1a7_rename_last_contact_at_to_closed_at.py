"""rename last_contact_at to closed_at

Revision ID: c82f5b64d1a7
Revises: 0f31fd9d6942
Create Date: 2026-08-26

"""

from typing import Sequence, Union

from alembic import op


revision: str = "c82f5b64d1a7"
down_revision: Union[str, Sequence[str], None] = "0f31fd9d6942"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename tracked vacancy contact timestamp to closed timestamp."""

    op.alter_column(
        "tracked_vacancies",
        "last_contact_at",
        new_column_name="closed_at",
    )


def downgrade() -> None:
    """Restore the previous tracked vacancy timestamp name."""

    op.alter_column(
        "tracked_vacancies",
        "closed_at",
        new_column_name="last_contact_at",
    )
