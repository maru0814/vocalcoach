import os
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.audio import analyzer
from app.audio.convert import to_wav
from app.audio.reference import ReferenceFetchError, fetch_reference_wav, fetch_youtube_title
from app.coaching import rule_engine
from app.core.config import settings
from app.db.session import get_db
from app.deps import get_current_user
from app.models.coaching import ChatMessage, ChatSession
from app.schemas.coaching import (
    ChatResponse,
    MessageOut,
    SendTextRequest,
    SessionDetail,
    SessionSummary,
    UpdateSessionRequest,
)
from app.storage.files import ensure_dir

router = APIRouter(prefix="/api/v1/coach", tags=["coach"])

RANGE_RE = re.compile(r"(\d{1,2}:\d{2}|\d+(?:\.\d+)?)\s*[-–~〜]\s*(\d{1,2}:\d{2}|\d+(?:\.\d+)?)")
ALLOWED_EXT = {".wav", ".mp3", ".m4a", ".webm", ".ogg", ".aac", ".mp4"}


def _parse_time(token: str) -> float:
    if ":" in token:
        m, s = token.split(":")
        return int(m) * 60 + float(s)
    return float(token)


def _parse_range(rng: str | None) -> tuple[float | None, float | None]:
    if not rng:
        return None, None
    m = RANGE_RE.search(rng)
    if not m:
        return None, None
    return _parse_time(m.group(1)), _parse_time(m.group(2))


def _msg_out(m: ChatMessage) -> MessageOut:
    return MessageOut(
        id=m.id,
        role=m.role,
        type=m.type,
        text=m.text,
        audio_url=f"/api/v1/coach/audio/{m.id}" if m.audio_path else None,
        payload=m.payload,
        created_at=m.created_at,
    )


def _session_state(s: ChatSession) -> dict:
    return {
        "phase": s.phase,
        "song_ref_url": s.song_ref_url,
        "song_ref_path": s.song_ref_path,
        "user_range": s.user_range,
        "ref_range": s.ref_range,
        "current_task": s.current_task,
        "focus_task": s.focus_task,
        "baseline_analysis": s.baseline_analysis,
        "d_retry_count": s.d_retry_count,
    }


def _apply_updates(s: ChatSession, updates: dict) -> None:
    for k, v in updates.items():
        if hasattr(s, k):
            setattr(s, k, v)


def _persist_coach_messages(db: Session, session_id: int, msgs: list[dict]) -> list[ChatMessage]:
    rows = []
    for m in msgs:
        row = ChatMessage(
            session_id=session_id,
            role="coach",
            type=m["type"],
            text=m.get("text"),
            payload=m.get("payload"),
        )
        db.add(row)
        rows.append(row)
    db.flush()
    return rows


def _get_owned_session(db: Session, session_id: int, user) -> ChatSession:
    s = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    return s


@router.post("/sessions", response_model=ChatResponse)
def create_session(db: Session = Depends(get_db), user=Depends(get_current_user)) -> ChatResponse:
    s = ChatSession(user_id=user.id, phase="A")
    db.add(s)
    db.flush()
    rows = _persist_coach_messages(db, s.id, rule_engine.initial_messages())
    db.commit()
    for r in rows:
        db.refresh(r)
    return ChatResponse(phase=s.phase, current_task=s.current_task, messages=[_msg_out(r) for r in rows])


@router.get("/sessions", response_model=list[SessionSummary])
def list_sessions(db: Session = Depends(get_db), user=Depends(get_current_user)) -> list[SessionSummary]:
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return [
        SessionSummary(
            id=s.id, song_title=s.song_title, phase=s.phase,
            current_task=s.current_task, updated_at=s.updated_at,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=SessionDetail)
def get_session(session_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)) -> SessionDetail:
    s = _get_owned_session(db, session_id, user)
    return SessionDetail(
        id=s.id, song_title=s.song_title, song_ref_url=s.song_ref_url,
        user_range=s.user_range, phase=s.phase, current_task=s.current_task,
        messages=[_msg_out(m) for m in s.messages],
    )


@router.patch("/sessions/{session_id}", response_model=SessionSummary)
def update_session(
    session_id: int,
    body: UpdateSessionRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> SessionSummary:
    s = _get_owned_session(db, session_id, user)
    title = body.song_title.strip()
    if not title:
        raise HTTPException(
            status_code=400,
            detail={"code": "BAD_REQUEST", "message": "レッスン名を入力してください"},
        )
    s.song_title = title[:200]
    db.commit()
    db.refresh(s)
    return SessionSummary(
        id=s.id, song_title=s.song_title, phase=s.phase,
        current_task=s.current_task, updated_at=s.updated_at,
    )


@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
def send_message(
    session_id: int,
    body: SendTextRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> ChatResponse:
    s = _get_owned_session(db, session_id, user)

    user_msg = ChatMessage(session_id=s.id, role="user", type="text", text=body.text)
    db.add(user_msg)

    msgs, updates = rule_engine.handle_text(_session_state(s), body.text)
    _apply_updates(s, updates)

    # 原曲URLが新たに付いたら、YouTubeタイトルを自動でレッスン名にする（未設定時のみ）
    if updates.get("song_ref_url") and not s.song_title:
        title = fetch_youtube_title(updates["song_ref_url"])
        if title:
            s.song_title = title

    rows = _persist_coach_messages(db, s.id, msgs)
    db.commit()
    for r in rows:
        db.refresh(r)
    return ChatResponse(phase=s.phase, current_task=s.current_task, messages=[_msg_out(r) for r in rows])


@router.post("/sessions/{session_id}/audio", response_model=ChatResponse)
def send_audio(
    session_id: int,
    audio_file: UploadFile = File(...),
    kind: str = Form("song"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> ChatResponse:
    s = _get_owned_session(db, session_id, user)

    # --- validate + save raw upload ---
    _, ext = os.path.splitext(audio_file.filename or "")
    ext = ext.lower() or ".webm"
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=400,
            detail={"code": "BAD_REQUEST", "message": f"対応していない形式です: {ext}"},
        )
    audio_file.file.seek(0, os.SEEK_END)
    size = audio_file.file.tell()
    audio_file.file.seek(0)
    if size > settings.max_audio_mb * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail={"code": "BAD_REQUEST", "message": f"ファイルが大きすぎます（{settings.max_audio_mb}MBまで）"},
        )

    ensure_dir(settings.coach_audio_dir)
    user_msg = ChatMessage(session_id=s.id, role="user", type="audio")
    db.add(user_msg)
    db.flush()
    raw_path = os.path.join(settings.coach_audio_dir, f"{s.id}_{user_msg.id}{ext}")
    with open(raw_path, "wb") as f:
        f.write(audio_file.file.read())
    user_msg.audio_path = raw_path

    # --- convert to wav ---
    try:
        wav_path = to_wav(raw_path, raw_path + ".wav")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "ANALYSIS_FAILED", "message": f"音声の変換に失敗しました: {e}"},
        )

    u_start, u_end = _parse_range(s.user_range)
    phase = s.phase
    compare_data = None
    alignment = None
    needs_ref = phase in ("A", "B") and kind == "song"

    ref_wav = None
    if needs_ref:
        ref_wav = s.song_ref_path
        if not ref_wav and s.song_ref_url:
            try:
                ref_wav = fetch_reference_wav(
                    s.song_ref_url, settings.reference_cache_dir, name=f"session_{s.id}"
                )
                s.song_ref_path = ref_wav
            except ReferenceFetchError as e:
                raise HTTPException(
                    status_code=502,
                    detail={"code": "REFERENCE_FETCH_FAILED", "message": str(e)},
                )

    try:
        if needs_ref and ref_wav:
            # 原曲は声分離（軽量）して解析 + DTWアライメント
            r_start, r_end = _parse_range(s.ref_range or s.user_range)
            paired = analyzer.analyze_pair(
                wav_path, ref_wav, user_range=(u_start, u_end), ref_range=(r_start, r_end)
            )
            user_analysis = paired["user"]
            ref_analysis = paired["reference"]
            compare_data = paired["compare"]
            alignment = paired.get("alignment")
            if analyzer.is_same_source(user_analysis, ref_analysis):
                same_msg = {
                    "role": "coach", "type": "text",
                    "text": "ご提出いただいた録音が原曲と同じ音源のようです🎤 "
                            "あなたが歌った録音を送ってくださいね。",
                }
                rows = _persist_coach_messages(db, s.id, [same_msg])
                db.commit()
                for r in rows:
                    db.refresh(r)
                return ChatResponse(phase=s.phase, current_task=s.current_task,
                                    messages=[_msg_out(r) for r in rows])
        else:
            user_analysis = analyzer.analyze_file(wav_path, u_start, u_end)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "ANALYSIS_FAILED", "message": f"音声の解析に失敗しました: {e}"},
        )

    if alignment is not None:
        compare_data = {**(compare_data or {}), "alignment": alignment}

    msgs, updates = rule_engine.handle_audio(_session_state(s), user_analysis, compare_data, kind)
    _apply_updates(s, updates)
    rows = _persist_coach_messages(db, s.id, msgs)
    db.commit()
    db.refresh(user_msg)
    for r in rows:
        db.refresh(r)
    out = [_msg_out(user_msg)] + [_msg_out(r) for r in rows]
    return ChatResponse(phase=s.phase, current_task=s.current_task, messages=out)


@router.get("/audio/{message_id}")
def get_audio(message_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    m = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    if not m or not m.audio_path or not os.path.exists(m.audio_path):
        raise HTTPException(status_code=404, detail="audio not found")
    owner = (
        db.query(ChatSession)
        .filter(ChatSession.id == m.session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not owner:
        raise HTTPException(status_code=403, detail="forbidden")
    return FileResponse(m.audio_path)
