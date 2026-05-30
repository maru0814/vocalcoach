from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    song_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    song_ref_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    song_ref_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    user_range: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ref_range: Mapped[str | None] = mapped_column(String(50), nullable=True)

    phase: Mapped[str] = mapped_column(String(10), nullable=False, default="A")
    current_task: Mapped[str | None] = mapped_column(String(50), nullable=True)
    focus_task: Mapped[str | None] = mapped_column(String(50), nullable=True)
    baseline_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    d_retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user = relationship("User", backref="chat_sessions")
    messages = relationship(
        "ChatMessage", back_populates="session", order_by="ChatMessage.id", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id"), index=True, nullable=False
    )

    role: Mapped[str] = mapped_column(String(10), nullable=False)   # coach | user
    type: Mapped[str] = mapped_column(String(20), nullable=False)   # text|audio|feedback|practice|judge|progress
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")
