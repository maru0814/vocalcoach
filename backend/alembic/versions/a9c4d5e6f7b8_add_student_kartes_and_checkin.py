"""add student_kartes table and chat_sessions check-in columns (docs/53/54)

Revision ID: a9c4d5e6f7b8
Revises: c7d8e9f0a1b2
Create Date: 2026-07-02 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9c4d5e6f7b8'
down_revision: Union[str, None] = 'c7d8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'student_kartes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('voice', sa.JSON(), nullable=True),
        sa.Column('tendencies', sa.JSON(), nullable=True),
        sa.Column('practice_history', sa.JSON(), nullable=True),
        sa.Column('homework', sa.JSON(), nullable=True),
        sa.Column('subjective_notes', sa.JSON(), nullable=True),
        sa.Column('last_summary', sa.String(length=300), nullable=True),
        sa.Column('last_session_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index('ix_student_kartes_user_id', 'student_kartes', ['user_id'])
    with op.batch_alter_table('chat_sessions') as batch:
        batch.add_column(sa.Column('checkin_count', sa.Integer(), nullable=False, server_default='0'))
        batch.add_column(sa.Column('awaiting_checkin', sa.String(length=30), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('chat_sessions') as batch:
        batch.drop_column('awaiting_checkin')
        batch.drop_column('checkin_count')
    op.drop_index('ix_student_kartes_user_id', table_name='student_kartes')
    op.drop_table('student_kartes')
