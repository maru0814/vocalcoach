import os

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.deps import get_current_user
from app.models.recording import Recording
from app.schemas.recordings import (
    RecordingDetail,
    RecordingDetailEvaluation,
    RecordingListItem,
    StatusResponse,
)
from app.services.billing_service import analysis_allowed, is_premium
from app.services.evaluation_service import evaluate_recording
from app.storage.files import save_upload_file


router = APIRouter(prefix="/api/v1/recordings", tags=["recordings"])


def _evaluate_job(recording_id: int) -> None:
    # BackgroundTasksはrequestスコープのDBセッションを共有しにくいので新規作成。
    db = SessionLocal()
    try:
        evaluate_recording(db, recording_id)
    finally:
        db.close()


@router.post("", response_model=StatusResponse)
def upload_recording(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    note: str | None = Form(None),
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> StatusResponse:
    if not title.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="title is required")

    # 無料プランの月次上限ゲート（docs/31 FR-01）。402はフロントでアップグレード導線を開く合図。
    if not analysis_allowed(db, user.id):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="LIMIT_REACHED",
        )

    # MVP制約: 10MB以内
    audio_file.file.seek(0, os.SEEK_END)
    size = audio_file.file.tell()
    audio_file.file.seek(0)
    if size > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="audio file too large (10MB max)")

    recording = Recording(
        user_id=user.id,
        title=title,
        note=note,
        status="uploaded",
        audio_path="",
    )
    db.add(recording)
    db.commit()
    db.refresh(recording)

    # 保存パスを確定（idが必要）
    audio_path = save_upload_file(settings.uploads_dir, recording.id, audio_file)
    recording.audio_path = audio_path
    recording.status = "analyzing"
    db.add(recording)
    db.commit()
    db.refresh(recording)

    background_tasks.add_task(_evaluate_job, recording.id)

    return StatusResponse(recording_id=recording.id, status=recording.status)


@router.get("", response_model=list[RecordingListItem])
def list_recordings(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> list[RecordingListItem]:
    query = (
        db.query(Recording)
        .filter(Recording.user_id == user.id)
        .order_by(Recording.created_at.desc())
    )
    # 無料プランは直近N件のみ表示（削除はしない。加入で全件復活＝docs/31 FR-01）。
    if settings.billing_enabled and not is_premium(db, user.id):
        query = query.limit(settings.free_history_limit)
    recordings = query.all()

    items: list[RecordingListItem] = []
    for r in recordings:
        # evaluationsは 1録音=1評価（uselist=False想定）
        total_score = None
        if getattr(r, "evaluation", None):
            total_score = r.evaluation.total_score
        items.append(
            RecordingListItem(
                id=r.id,
                title=r.title,
                total_score=total_score,
                created_at=r.created_at,
            )
        )
    return items


@router.get("/{recording_id}", response_model=RecordingDetail)
def get_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> RecordingDetail:
    recording = (
        db.query(Recording)
        .filter(Recording.id == recording_id, Recording.user_id == user.id)
        .first()
    )
    if not recording:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="recording not found")

    evaluation = getattr(recording, "evaluation", None)
    evaluation_schema = None
    if evaluation:
        evaluation_schema = RecordingDetailEvaluation(
            pitch_score=evaluation.pitch_score,
            rhythm_score=evaluation.rhythm_score,
            expression_score=evaluation.expression_score,
            total_score=evaluation.total_score,
            feedback_text=evaluation.feedback_text,
            created_at=evaluation.created_at,
        )

    return RecordingDetail(
        id=recording.id,
        title=recording.title,
        note=recording.note,
        status=recording.status,
        created_at=recording.created_at,
        evaluation=evaluation_schema,
    )

