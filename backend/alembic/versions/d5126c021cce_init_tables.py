"""init tables

Revision ID: d5126c021cce
Revises: 
Create Date: 2026-05-27 23:15:36.004669

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5126c021cce'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "recordings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.Column("audio_path", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_recordings_user_id", "recordings", ["user_id"], unique=False)
    op.create_index("ix_recordings_status", "recordings", ["status"], unique=False)

    op.create_table(
        "evaluations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "recording_id",
            sa.Integer(),
            sa.ForeignKey("recordings.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("pitch_score", sa.Integer(), nullable=False),
        sa.Column("rhythm_score", sa.Integer(), nullable=False),
        sa.Column("expression_score", sa.Integer(), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("feedback_text", sa.String(length=4000), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_evaluations_recording_id", "evaluations", ["recording_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_evaluations_recording_id", table_name="evaluations")
    op.drop_table("evaluations")
    op.drop_index("ix_recordings_status", table_name="recordings")
    op.drop_index("ix_recordings_user_id", table_name="recordings")
    op.drop_table("recordings")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
