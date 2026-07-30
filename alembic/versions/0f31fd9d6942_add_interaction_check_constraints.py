"""add interaction check constraints

Revision ID: 0f31fd9d6942
Revises: 4876353f99e0
Create Date: 2026-07-30 14:55:41.801068

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0f31fd9d6942'
down_revision: Union[str, Sequence[str], None] = '4876353f99e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_check_constraint(
        "ck_interactions_interaction_type",
        "interactions",
        """
        interaction_type IN (
            'resume_sent',
            'message',
            'call',
            'screening_questions',
            'interview_invitation',
            'hr_interview',
            'technical_interview',
            'final_interview',
            'test_task',
            'feedback',
            'offer_discussion',
            'offer',
            'rejection'
        )
        """,
    )

    op.create_check_constraint(
        "ck_interactions_direction",
        "interactions",
        "direction IN ('incoming', 'outgoing')",
    )
def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "ck_interactions_direction",
        "interactions",
        type_="check",
    )

    op.drop_constraint(
        "ck_interactions_interaction_type",
        "interactions",
        type_="check",
    )
