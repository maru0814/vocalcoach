"""add newsletter opt-in fields and sends ledger

Revision ID: a8b9c0d1e2f3
Revises: d1e2f3a4b5c6
Create Date: 2026-08-01 15:00:00.000000

docs/88（要件）/ docs/89 §4（設計）。既存会員は opt_in=false 初期化（勝手に同意しない）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8b9c0d1e2f3'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('newsletter_opt_in', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column('users', sa.Column('unsubscribe_token', sa.String(length=64), nullable=True))
    op.create_index('ix_users_unsubscribe_token', 'users', ['unsubscribe_token'], unique=True)
    op.create_table(
        'newsletter_sends',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('campaign_key', sa.String(length=100), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id', 'campaign_key', name='uq_newsletter_user_campaign'),
    )
    op.create_index('ix_newsletter_sends_user_id', 'newsletter_sends', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_newsletter_sends_user_id', table_name='newsletter_sends')
    op.drop_table('newsletter_sends')
    op.drop_index('ix_users_unsubscribe_token', table_name='users')
    op.drop_column('users', 'unsubscribe_token')
    op.drop_column('users', 'newsletter_opt_in')
