from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class MessageOut(BaseModel):
    id: int
    role: str
    type: str
    text: Optional[str] = None
    audio_url: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
    created_at: datetime


class SessionSummary(BaseModel):
    id: int
    song_title: Optional[str] = None
    phase: str
    current_task: Optional[str] = None
    updated_at: datetime


class SessionDetail(BaseModel):
    id: int
    song_title: Optional[str] = None
    song_ref_url: Optional[str] = None
    user_range: Optional[str] = None
    phase: str
    current_task: Optional[str] = None
    messages: list[MessageOut]


class SendTextRequest(BaseModel):
    text: str


class UpdateSessionRequest(BaseModel):
    song_title: str


class ActionRequest(BaseModel):
    action: str  # more_practice | recheck_song | change_task | finish


class ChatResponse(BaseModel):
    phase: str
    current_task: Optional[str] = None
    messages: list[MessageOut]  # newly added messages only
