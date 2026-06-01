"""add message_feedback table

Revision ID: a1b2c3d4e5f6
Revises: b2f1a7c9d3e4
Create Date: 2026-06-01 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'b2f1a7c9d3e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'message_feedback',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('rating', sa.String(length=8), nullable=False),
        sa.Column('reason', sa.String(length=32), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('context', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id']),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_message_feedback_message_id', 'message_feedback', ['message_id'])
    op.create_index('ix_message_feedback_session_id', 'message_feedback', ['session_id'])
    op.create_index('ix_message_feedback_user_id', 'message_feedback', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_message_feedback_user_id', table_name='message_feedback')
    op.drop_index('ix_message_feedback_session_id', table_name='message_feedback')
    op.drop_index('ix_message_feedback_message_id', table_name='message_feedback')
    op.drop_table('message_feedback')
