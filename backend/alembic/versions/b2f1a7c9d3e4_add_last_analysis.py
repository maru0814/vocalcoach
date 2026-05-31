"""add last_analysis to chat_sessions

Revision ID: b2f1a7c9d3e4
Revises: cf80942ccfcf
Create Date: 2026-05-31 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2f1a7c9d3e4'
down_revision: Union[str, None] = 'cf80942ccfcf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chat_sessions', sa.Column('last_analysis', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('chat_sessions', 'last_analysis')
