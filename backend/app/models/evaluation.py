from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    recording_id: Mapped[int] = mapped_column(
        ForeignKey("recordings.id"), unique=True, nullable=False, index=True
    )

    pitch_score: Mapped[int] = mapped_column(Integer, nullable=False)
    rhythm_score: Mapped[int] = mapped_column(Integer, nullable=False)
    expression_score: Mapped[int] = mapped_column(Integer, nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)

    feedback_text: Mapped[str] = mapped_column(String(4000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    recording = relationship("Recording", back_populates="evaluation")

