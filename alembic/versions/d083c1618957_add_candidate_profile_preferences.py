"""add candidate profile preferences

Revision ID: d083c1618957
Revises: e626b56b02d1
Create Date: 2026-07-14 12:58:59.969791
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d083c1618957"
down_revision: Union[str, Sequence[str], None] = "e626b56b02d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "candidate_profiles",
        sa.Column(
            "preferred_locations",
            postgresql.ARRAY(sa.String()),
            nullable=True,
        ),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column(
            "desired_roles",
            postgresql.ARRAY(sa.String()),
            nullable=True,
        ),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column(
            "desired_salary_currency",
            sa.String(length=3),
            nullable=True,
        ),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column(
            "willing_to_relocate",
            sa.Boolean(),
            nullable=True,
        ),
    )

    op.add_column(
        "candidate_profiles",
        sa.Column(
            "preferred_employment_types_new",
            postgresql.ARRAY(sa.String()),
            nullable=True,
        ),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column(
            "preferred_work_formats_new",
            postgresql.ARRAY(sa.String()),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE candidate_profiles
        SET preferred_employment_types_new =
            CASE
                WHEN preferred_employment_types IS NULL THEN NULL
                ELSE ARRAY(
                    SELECT jsonb_array_elements_text(
                        preferred_employment_types
                    )
                )
            END
        """
    )

    op.execute(
        """
        UPDATE candidate_profiles
        SET preferred_work_formats_new =
            CASE
                WHEN preferred_work_formats IS NULL THEN NULL
                ELSE ARRAY(
                    SELECT jsonb_array_elements_text(
                        preferred_work_formats
                    )
                )
            END
        """
    )

    op.drop_column(
        "candidate_profiles",
        "preferred_employment_types",
    )
    op.drop_column(
        "candidate_profiles",
        "preferred_work_formats",
    )

    op.alter_column(
        "candidate_profiles",
        "preferred_employment_types_new",
        new_column_name="preferred_employment_types",
    )
    op.alter_column(
        "candidate_profiles",
        "preferred_work_formats_new",
        new_column_name="preferred_work_formats",
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.add_column(
        "candidate_profiles",
        sa.Column(
            "preferred_employment_types_old",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column(
            "preferred_work_formats_old",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE candidate_profiles
        SET preferred_employment_types_old =
            CASE
                WHEN preferred_employment_types IS NULL THEN NULL
                ELSE to_jsonb(preferred_employment_types)
            END
        """
    )

    op.execute(
        """
        UPDATE candidate_profiles
        SET preferred_work_formats_old =
            CASE
                WHEN preferred_work_formats IS NULL THEN NULL
                ELSE to_jsonb(preferred_work_formats)
            END
        """
    )

    op.drop_column(
        "candidate_profiles",
        "preferred_employment_types",
    )
    op.drop_column(
        "candidate_profiles",
        "preferred_work_formats",
    )

    op.alter_column(
        "candidate_profiles",
        "preferred_employment_types_old",
        new_column_name="preferred_employment_types",
    )
    op.alter_column(
        "candidate_profiles",
        "preferred_work_formats_old",
        new_column_name="preferred_work_formats",
    )

    op.drop_column(
        "candidate_profiles",
        "willing_to_relocate",
    )
    op.drop_column(
        "candidate_profiles",
        "desired_salary_currency",
    )
    op.drop_column(
        "candidate_profiles",
        "desired_roles",
    )
    op.drop_column(
        "candidate_profiles",
        "preferred_locations",
    )