"""add source_session_id/source_message_id to recordings (coach昇格・docs/50 T-2)

Revision ID: c7d8e9f0a1b2
Revises: f3a9b1c2d7e8
Create Date: 2026-06-30 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, None] = 'f3a9b1c2d7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # coachレッスン由来の録音をトレースする2列（既存行はNULL）。
    # SQLite は ALTER で FK/UNIQUE 列を直接追加できないため、列は素の Integer で足し、
    # 一意制約は unique index で別途張る（MySQL でも同等に動く）。
    op.add_column("recordings", sa.Column("source_session_id", sa.Integer(), nullable=True))
    op.add_column("recordings", sa.Column("source_message_id", sa.Integer(), nullable=True))
    op.create_index(
        "ix_recordings_source_session_id", "recordings", ["source_session_id"], unique=False
    )
    op.create_index(
        "uq_recordings_source_message_id", "recordings", ["source_message_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("uq_recordings_source_message_id", table_name="recordings")
    op.drop_index("ix_recordings_source_session_id", table_name="recordings")
    op.drop_column("recordings", "source_message_id")
    op.drop_column("recordings", "source_session_id")
