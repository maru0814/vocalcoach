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
from app.services.report_service import GENERATING, generate_report, report_status
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


# --- 詳細添削レポート（有料・docs/31 FR-04） ---

def _get_owned_recording(db: Session, recording_id: int, user_id: int) -> Recording:
    recording = (
        db.query(Recording)
        .filter(Recording.id == recording_id, Recording.user_id == user_id)
        .first()
    )
    if not recording:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="recording not found")
    return recording


def _require_report_access(db: Session, user_id: int) -> None:
    # billing無効＝全機能無料（緊急停止スイッチ）。有効時はpremiumのみ（AC-08）。
    if settings.billing_enabled and not is_premium(db, user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="PREMIUM_REQUIRED")


def _report_job(evaluation_id: int, title: str, note: str | None) -> None:
    db = SessionLocal()
    try:
        generate_report(db, evaluation_id, title, note)
    finally:
        db.close()


@router.post("/{recording_id}/report")
def start_report(
    recording_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict:
    recording = _get_owned_recording(db, recording_id, user.id)
    _require_report_access(db, user.id)
    evaluation = getattr(recording, "evaluation", None)
    if evaluation is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="evaluation not ready")

    st = report_status(evaluation)
    if st in ("ready", "generating"):
        return {"status": st}
    # 二重生成防止のフラグを先に立ててから非同期生成（docs/33 §5）
    evaluation.detailed_report = dict(GENERATING)
    db.add(evaluation)
    db.commit()
    background_tasks.add_task(_report_job, evaluation.id, recording.title, recording.note)
    return {"status": "generating"}


@router.get("/{recording_id}/report")
def get_report(
    recording_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict:
    recording = _get_owned_recording(db, recording_id, user.id)
    _require_report_access(db, user.id)
    evaluation = getattr(recording, "evaluation", None)
    st = report_status(evaluation)
    report = evaluation.detailed_report if (evaluation and st == "ready") else None
    return {"status": st, "report": report}
