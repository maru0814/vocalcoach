from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Subscription(Base):
    """Stripeサブスクの状態キャッシュ。1ユーザー1行（最新状態のみ）。

    真実の源泉はStripeで、webhook（PR-B）で同期する。プラン判定はこの行のみで行い、
    リクエスト毎にStripeへは問い合わせない（docs/33 §1）。
    """

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class UsageCounter(Base):
    """無料プランの解析回数カウンタ（JST暦月キー）。

    月キー方式なのでリセット処理は不要。解析が「完了」した時点でインクリメントする
    （失敗は数えない＝docs/31 FR-01）。
    """

    __tablename__ = "usage_counters"
    __table_args__ = (UniqueConstraint("user_id", "yyyymm", name="uq_usage_user_month"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    yyyymm: Mapped[str] = mapped_column(String(6), nullable=False)
    analysis_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
