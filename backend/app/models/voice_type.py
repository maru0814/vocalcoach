from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VoiceTypeDiagnosis(Base):
    """声タイプ診断の実行イベント（社会的証明＝累計件数・タイプ分布の集計用）。

    1診断=1行。PIIは持たない（type_id と score と時刻のみ）。
    """
    __tablename__ = "voice_type_diagnoses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
