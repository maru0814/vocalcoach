"""add billing tables (subscriptions, usage_counters) and evaluation report columns

Revision ID: f3a9b1c2d7e8
Revises: e7a1c2b3d4f5
Create Date: 2026-06-12 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a9b1c2d7e8'
down_revision: Union[str, None] = 'e7a1c2b3d4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('stripe_customer_id', sa.String(length=64), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='none'),
        sa.Column('current_period_end', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
        sa.UniqueConstraint('stripe_customer_id'),
        sa.UniqueConstraint('stripe_subscription_id'),
    )
    op.create_table(
        'usage_counters',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('yyyymm', sa.String(length=6), nullable=False),
        sa.Column('analysis_count', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'yyyymm', name='uq_usage_user_month'),
    )
    # 詳細添削レポート（PR-Cで使用）。先にスキーマだけ用意。
    op.add_column('evaluations', sa.Column('detailed_report', sa.JSON(), nullable=True))
    op.add_column('evaluations', sa.Column('report_generated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('evaluations', 'report_generated_at')
    op.drop_column('evaluations', 'detailed_report')
    op.drop_table('usage_counters')
    op.drop_table('subscriptions')
