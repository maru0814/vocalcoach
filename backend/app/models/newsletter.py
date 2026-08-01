from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NewsletterSend(Base):
    """お知らせメールの送信台帳（docs/89 §2）。

    1行 = 1会員 × 1キャンペーンの送信成功。UNIQUE(user_id, campaign_key) が
    冪等性の根拠で、バッチ再実行時の二重送信を防ぐ。失敗時は記録しない＝再送対象。
    """
    __tablename__ = "newsletter_sends"
    __table_args__ = (UniqueConstraint("user_id", "campaign_key", name="uq_newsletter_user_campaign"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    campaign_key: Mapped[str] = mapped_column(String(100), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
