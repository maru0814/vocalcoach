from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LoginEvent(Base):
    """ログイン成功イベント（KPI「ログインUU」の算出用。docs/84）。

    1ログイン成功=1行。ログインUU = その日の distinct user_id。
    記録は best-effort（失敗してもログイン自体は成功させる）。
    """
    __tablename__ = "login_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
