"""add auth and resume analysis model refactor

Revision ID: 6607c21f834f
Revises: 8b437a181776
Create Date: 2026-07-07 18:31:03.560479

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "6607c21f834f"
down_revision: Union[str, Sequence[str], None] = "8b437a181776"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "resume_analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resume_document_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("target_role", sa.String(length=255), nullable=True),
        sa.Column("years_of_experience", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column("english_level", sa.String(length=100), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("skills", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("education_level", sa.String(length=100), nullable=True),
        sa.Column("education_summary", sa.Text(), nullable=True),
        sa.Column("languages", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ai_model", sa.String(length=100), nullable=True),
        sa.Column("prompt_version", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["resume_document_id"],
            ["resume_documents.id"],
            name="fk_resume_analyses_resume_document_id_resume_documents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "resume_document_id",
            name="uq_resume_analyses_resume_document_id",
        ),
    )

    op.add_column(
        "candidate_profiles",
        sa.Column("user_id", sa.Integer(), nullable=False),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("email", sa.String(length=255), nullable=False),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("phone", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("github_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("linkedin_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column(
            "preferred_employment_types",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column(
            "preferred_work_formats",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    op.create_unique_constraint(
        "uq_candidate_profiles_user_id",
        "candidate_profiles",
        ["user_id"],
    )
    op.create_foreign_key(
        "fk_candidate_profiles_user_id_users",
        "candidate_profiles",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_column("candidate_profiles", "target_role")
    op.drop_column("candidate_profiles", "years_of_experience")
    op.drop_column("candidate_profiles", "english_level")
    op.drop_column("candidate_profiles", "skills")
    op.drop_column("candidate_profiles", "summary")
    op.drop_column("candidate_profiles", "experience_level")

    op.add_column(
        "tracked_vacancies",
        sa.Column("resume_document_id", sa.Integer(), nullable=False),
    )
    op.drop_constraint(
        op.f("tracked_vacancies_candidate_profile_id_fkey"),
        "tracked_vacancies",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_tracked_vacancies_resume_document_id_resume_documents",
        "tracked_vacancies",
        "resume_documents",
        ["resume_document_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_column("tracked_vacancies", "candidate_profile_id")


def downgrade() -> None:
    """Downgrade schema."""

    op.add_column(
        "tracked_vacancies",
        sa.Column("candidate_profile_id", sa.Integer(), nullable=False),
    )
    op.drop_constraint(
        "fk_tracked_vacancies_resume_document_id_resume_documents",
        "tracked_vacancies",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("tracked_vacancies_candidate_profile_id_fkey"),
        "tracked_vacancies",
        "candidate_profiles",
        ["candidate_profile_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_column("tracked_vacancies", "resume_document_id")

    op.add_column(
        "candidate_profiles",
        sa.Column("experience_level", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("summary", sa.Text(), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("skills", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("english_level", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("years_of_experience", sa.Numeric(precision=4, scale=1), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("target_role", sa.String(length=255), nullable=True),
    )

    op.drop_constraint(
        "fk_candidate_profiles_user_id_users",
        "candidate_profiles",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_candidate_profiles_user_id",
        "candidate_profiles",
        type_="unique",
    )

    op.drop_column("candidate_profiles", "preferred_work_formats")
    op.drop_column("candidate_profiles", "preferred_employment_types")
    op.drop_column("candidate_profiles", "linkedin_url")
    op.drop_column("candidate_profiles", "github_url")
    op.drop_column("candidate_profiles", "phone")
    op.drop_column("candidate_profiles", "email")
    op.drop_column("candidate_profiles", "user_id")

    op.drop_table("resume_analyses")

    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")