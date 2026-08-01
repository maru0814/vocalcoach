"""add login_events and diagnosis identity columns

KPI日次スプレッドシート自動記録（docs/84）のための計測強化。
- login_events 新設: ログインUUの真値を取れるようにする
- voice_type_diagnoses に user_id / visitor_hash 追加: 診断UUを取れるようにする
  （生IPは保存しない。ソルト付き一方向ハッシュのみ）

Revision ID: d1e2f3a4b5c6
Revises: b7e2c1a4f9d0
Create Date: 2026-08-01 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'b7e2c1a4f9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'login_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_login_events_user_id', 'login_events', ['user_id'])
    op.create_index('ix_login_events_created_at', 'login_events', ['created_at'])

    # SQLiteでも通る nullable カラム追加（FKは張らない）
    op.add_column('voice_type_diagnoses', sa.Column('user_id', sa.Integer(), nullable=True))
    op.add_column('voice_type_diagnoses', sa.Column('visitor_hash', sa.String(length=64), nullable=True))
    op.create_index('ix_voice_type_diagnoses_user_id', 'voice_type_diagnoses', ['user_id'])
    op.create_index('ix_voice_type_diagnoses_visitor_hash', 'voice_type_diagnoses', ['visitor_hash'])


def downgrade() -> None:
    op.drop_index('ix_voice_type_diagnoses_visitor_hash', table_name='voice_type_diagnoses')
    op.drop_index('ix_voice_type_diagnoses_user_id', table_name='voice_type_diagnoses')
    op.drop_column('voice_type_diagnoses', 'visitor_hash')
    op.drop_column('voice_type_diagnoses', 'user_id')
    op.drop_index('ix_login_events_created_at', table_name='login_events')
    op.drop_index('ix_login_events_user_id', table_name='login_events')
    op.drop_table('login_events')
