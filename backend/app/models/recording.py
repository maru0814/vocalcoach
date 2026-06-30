from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Recording(Base):
    __tablename__ = "recordings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    audio_path: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    # coachレッスンからの昇格元（docs/50 T-2）。単発アップロード由来はNULL。
    # source_message_id は冪等キー（同じ録音の二重昇格を防ぐ）。
    # SQLite ALTERの制約上、DB側FKは張らず Integer + index/unique index で表現する。
    source_session_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user = relationship("User", backref="recordings")
    evaluation = relationship("Evaluation", back_populates="recording", uselist=False)

