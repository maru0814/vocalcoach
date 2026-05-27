from datetime import datetime

from pydantic import BaseModel


class StatusResponse(BaseModel):
    recording_id: int
    status: str


class RecordingListItem(BaseModel):
    id: int
    title: str
    total_score: int | None = None
    created_at: datetime


class RecordingDetailEvaluation(BaseModel):
    pitch_score: int
    rhythm_score: int
    expression_score: int
    total_score: int
    feedback_text: str
    created_at: datetime


class RecordingDetail(BaseModel):
    id: int
    title: str
    note: str | None
    status: str
    created_at: datetime
    evaluation: RecordingDetailEvaluation | None = None

