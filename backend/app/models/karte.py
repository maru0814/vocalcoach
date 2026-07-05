from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudentKarte(Base):
    """生徒カルテ（docs/53/54）。1ユーザー1行。セッションを跨ぐ「生徒の記憶」。

    項目はスキーマ進化前提でJSON中心。更新はすべてシステム（karte_service）が行い、
    手動編集UIは無い。アカウント削除と連鎖して消える（個人データ）。
    """

    __tablename__ = "student_kartes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )

    # 声の特徴: {"f0_min_hz", "f0_max_hz", "voice_type"}
    voice: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 持ち癖: {task_id: 診断回数}
    tendencies: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 練習履歴: [{"task_id", "practice", "result", "at"}] 直近10件
    practice_history: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # 宿題: {"task_id", "practice_name", "assigned_at"}
    homework: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 主観メモ（問診回答）: [{"at", "note", "red_flag"}] 直近5件
    subjective_notes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # 前回サマリ（ルール生成1〜2行）
    last_summary: Mapped[str | None] = mapped_column(String(300), nullable=True)
    last_session_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
