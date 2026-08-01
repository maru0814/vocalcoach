from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VoiceTypeDiagnosis(Base):
    """声タイプ診断の実行イベント（社会的証明＝累計件数・タイプ分布の集計用）。

    1診断=1行。生のPIIは持たない（メール・生IPは保存しない）。
    KPI「診断UU」算出のため、ログイン時は user_id、未ログイン時は
    visitor_hash（ソルト付きIPの一方向ハッシュ＝仮名化識別子）を持つ（docs/84）。
    """
    __tablename__ = "voice_type_diagnoses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # FKは張らない（匿名診断が主で、users との結合は集計時のみ）
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    visitor_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
