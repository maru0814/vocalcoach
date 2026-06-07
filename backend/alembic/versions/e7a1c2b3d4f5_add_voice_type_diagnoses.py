"""add voice_type_diagnoses

Revision ID: e7a1c2b3d4f5
Revises: a1b2c3d4e5f6
Create Date: 2026-06-06 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7a1c2b3d4f5'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'voice_type_diagnoses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type_id', sa.String(length=20), nullable=False),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_voice_type_diagnoses_type_id', 'voice_type_diagnoses', ['type_id'])
    op.create_index('ix_voice_type_diagnoses_created_at', 'voice_type_diagnoses', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_voice_type_diagnoses_created_at', table_name='voice_type_diagnoses')
    op.drop_index('ix_voice_type_diagnoses_type_id', table_name='voice_type_diagnoses')
    op.drop_table('voice_type_diagnoses')
