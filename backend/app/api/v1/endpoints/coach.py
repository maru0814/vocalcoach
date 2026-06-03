import os
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.audio import analyzer
from app.audio.convert import to_wav
from app.audio.reference import ReferenceFetchError, fetch_reference_wav, fetch_youtube_title
from app.coaching import llm, rule_engine
from app.core.config import settings
from app.core.ratelimit import check_rate_limit
from app.db.session import get_db
from app.deps import get_current_user
from app.models.coaching import ChatMessage, ChatSession, MessageFeedback
from app.schemas.coaching import (
    ActionRequest,
    ChatResponse,
    FeedbackRequest,
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


def _parse_ref_spec(text: str) -> tuple[float | None, float | None]:
    """再診断テキストから原曲側の開始/終了時間を抽出する。

    対応: 「0:45-1:13」「45秒-73秒」(範囲) / 「0:45」「1分20秒」「45秒」「45あたりから」(開始のみ)。
    戻り: (start_sec, end_sec)。見つからなければ (None, None)。
    """
    if not text:
        return None, None
    s, e = _parse_range(text)           # 0:45-1:13 / 45-73 などの範囲
    if s is not None:
        return s, e
    m = re.search(r"(\d{1,2}):(\d{2})", text)               # mm:ss 単体
    if m:
        return int(m.group(1)) * 60 + float(m.group(2)), None
    m = re.search(r"(?:(\d+)\s*分)?\s*(\d+)\s*秒", text)      # 1分20秒 / 45秒
    if m:
        mins = int(m.group(1)) if m.group(1) else 0
        return mins * 60 + float(m.group(2)), None
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:秒)?\s*(?:あたり|くらい|ぐらい|付近|頃)?\s*から", text)  # 45あたりから
    if m:
        return float(m.group(1)), None
    return None, None


def _fmt_time(sec: float | None) -> str:
    if sec is None:
        return ""
    sec = int(round(sec))
    return f"{sec}秒" if sec < 60 else f"{sec // 60}分{sec % 60}秒"


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


def _history_for_llm(s: ChatSession) -> list[dict]:
    """既存メッセージを LLM 用の会話履歴に変換する（古い→新しい）。

    user → "user"、coach → "assistant"。テキスト以外（分析カード等）は短い説明に置き換える。
    """
    card_note = {
        "feedback": "（歌の分析カードを表示しました）",
        "practice": "（基礎練のカードを表示しました）",
        "judge": "（基礎練の達成判定を表示しました）",
        "progress": "（前回との比較カードを表示しました）",
        "audio": "（録音を送りました）",
    }
    hist: list[dict] = []
    for m in s.messages:
        role = "assistant" if m.role == "coach" else "user"
        content = m.text if m.type == "text" and m.text else card_note.get(m.type)
        if content:
            hist.append({"role": role, "content": content})
    return hist[-settings.llm_history_turns:]


def _looks_like_singing(a: dict) -> bool:
    """録音に「歌声」が十分含まれるかの軽い判定（無音・極端に短い・ほぼ無声を弾く）。

    実歌唱: dur>20s, voiced≈0.94, rms≈0.02-0.04。無音: rms≈1e-4, voiced<0.25。
    短尺: dur<1s。これらを安全に分離できるしきい値。
    """
    return (
        (a.get("duration_sec") or 0) >= 1.5
        and (a.get("rms_mean") or 0) >= 0.003
        and (a.get("voiced_ratio") or 0) >= 0.25
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
        "avoid_task": s.avoid_task,
        "baseline_analysis": s.baseline_analysis,
        "last_analysis": s.last_analysis,
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


def _pronunciation_reply(db: Session, s: ChatSession) -> dict:
    """最新の録音を Gemini に聴かせ、発音の講評（原曲があれば比較）を返す。"""
    last_audio = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == s.id, ChatMessage.type == "audio")
        .order_by(ChatMessage.id.desc())
        .first()
    )
    if not last_audio or not last_audio.audio_path or not os.path.exists(last_audio.audio_path):
        return {"type": "text", "text": "発音を見るには、まず歌った録音を送ってくださいね🎤 そのあと「発音を見て」と聞いてください。"}

    wav = last_audio.audio_path + ".wav"
    if not os.path.exists(wav):
        try:
            wav = to_wav(last_audio.audio_path, wav)
        except Exception:
            return {"type": "text", "text": "音声の読み込みがうまくいきませんでした。もう一度録音を送ってみてください。"}
    try:
        user_bytes = open(wav, "rb").read()
    except Exception:
        return {"type": "text", "text": "音声の読み込みに失敗しました。もう一度お試しください。"}

    ref_bytes = None
    if s.song_ref_path and os.path.exists(s.song_ref_path):
        try:
            ref_bytes = open(s.song_ref_path, "rb").read()
        except Exception:
            ref_bytes = None

    reply = llm.analyze_pronunciation(user_bytes, ref_bytes)
    if not reply:
        return {"type": "text", "text": "発音の聞き取りが今うまくできませんでした。少し時間をおいて、もう一度試してくださいね。"}
    if ref_bytes is None:
        reply += "\n\n（原曲＝お手本の音源も用意できれば、原曲と比べた発音アドバイスもできますよ😊）"
    return {"type": "text", "text": reply}


def _rediagnose_reply(db: Session, s: ChatSession, text: str, history: list[dict]) -> list[dict]:
    """「今の録音で、原曲の◯秒あたりから重ねて再度診断して」に応える特別経路。

    直前の録音を、テキストで指定された原曲側の区間と重ね直して解析し、採点カードを返す。
    """
    last_audio = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == s.id, ChatMessage.type == "audio")
        .order_by(ChatMessage.id.desc())
        .first()
    )
    if not last_audio or not last_audio.audio_path or not os.path.exists(last_audio.audio_path):
        return [{"type": "text", "text": "まず歌った録音を送ってくださいね🎤 そのあと「原曲の45秒あたりから重ねて診断して」のように言ってもらえれば、その区間と重ねて見ます。"}]

    wav = last_audio.audio_path + ".wav"
    if not os.path.exists(wav):
        try:
            wav = to_wav(last_audio.audio_path, wav)
        except Exception:
            return [{"type": "text", "text": "録音の読み込みがうまくいきませんでした。もう一度録音を送ってみてください。"}]

    # 原曲（お手本）を確保（アップ済み or YouTube から取得）
    ref_wav = s.song_ref_path
    if not ref_wav and s.song_ref_url and settings.enable_youtube_reference:
        try:
            ref_wav = fetch_reference_wav(s.song_ref_url, settings.reference_cache_dir, name=f"session_{s.id}")
            s.song_ref_path = ref_wav
        except ReferenceFetchError:
            ref_wav = None
    if not ref_wav:
        return [{"type": "text", "text": "重ねる原曲が見つかりませんでした🙏 先に原曲のYouTube URLを貼ってから、もう一度お願いします🎼"}]

    # 原曲側の区間（指定が無ければ既存の ref_range を使う）
    r_start, r_end = _parse_ref_spec(text)
    if r_start is not None:
        r_end_eff = r_end if r_end is not None else r_start + 30.0
        s.ref_range = f"{r_start:.0f}-{r_end_eff:.0f}"
    else:
        r_start, r_end = _parse_range(s.ref_range or "")
    u_start, u_end = _parse_range(s.user_range)

    try:
        paired = analyzer.analyze_pair(wav, ref_wav, user_range=(u_start, u_end), ref_range=(r_start, r_end))
    except Exception:
        return [{"type": "text", "text": "重ね合わせの解析がうまくいきませんでした🙏 少し時間をおいて、もう一度お試しください。"}]

    user_analysis = paired["user"]
    compare_data = paired["compare"]
    alignment = paired.get("alignment")
    if alignment is not None:
        compare_data = {**(compare_data or {}), "alignment": alignment}
    if analyzer.is_same_source(user_analysis, paired["reference"]):
        return [{"type": "text", "text": "いただいた録音が原曲と同じ音源みたいです🎤 あなた自身が歌った録音で試してくださいね😊"}]

    s.last_analysis = {**user_analysis, "_compare": compare_data} if compare_data else user_analysis
    # 再診断は常に「採点カード（弱点診断）」を出す（前回比較カードにしない）
    msgs, updates = rule_engine._audio_diagnose(_session_state(s), user_analysis, compare_data, history)
    _apply_updates(s, updates)

    ht = _fmt_time(r_start)
    head = {
        "type": "text",
        "text": (f"了解です！原曲の{ht}あたりから重ねて、もう一度見てみますね🎧" if ht
                 else "原曲と重ねて、もう一度見てみますね🎧"),
    }
    return [head] + msgs


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
        has_reference=bool(s.song_ref_path),
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

    # 新規ユーザー発言を追加する前に、これまでの会話履歴を LLM 用に取得
    history = _history_for_llm(s)

    user_msg = ChatMessage(session_id=s.id, role="user", type="text", text=body.text)
    db.add(user_msg)

    # 「今の録音で、原曲の◯秒から重ねて再度診断して」→ 直前録音を指定区間で再解析（特別経路）
    if rule_engine.is_rediagnose_request(body.text):
        if not check_rate_limit(f"audio:{user.id}", settings.rate_limit_max_audio, settings.rate_limit_window_sec):
            raise HTTPException(status_code=429, detail={"code": "RATE_LIMITED", "message": "少し間隔をあけてからお願いします🙏"})
        db.flush()
        msgs = _rediagnose_reply(db, s, body.text, history)
        rows = _persist_coach_messages(db, s.id, msgs)
        db.commit()
        for r in rows:
            db.refresh(r)
        return ChatResponse(phase=s.phase, current_task=s.current_task, messages=[_msg_out(r) for r in rows])

    # 発音アドバイスの依頼は、最新の録音音声を Gemini に聴かせて講評する（特別経路）
    if rule_engine.is_pronunciation_request(body.text):
        db.flush()
        pron = _pronunciation_reply(db, s)
        rows = _persist_coach_messages(db, s.id, [pron])
        db.commit()
        for r in rows:
            db.refresh(r)
        return ChatResponse(phase=s.phase, current_task=s.current_task, messages=[_msg_out(r) for r in rows])

    # 「動画ある？／見本が欲しい」等は、話題に合う実際の練習カード（動画つき）を確定的に返す。
    # LLM任せだと「動画カードを用意しました」と言うだけでカードが出ない事故が起きるため。
    if rule_engine.is_video_request(body.text):
        msgs = rule_engine.handle_video_request(_session_state(s), body.text, history=history)
        rows = _persist_coach_messages(db, s.id, msgs)
        db.commit()
        for r in rows:
            db.refresh(r)
        return ChatResponse(phase=s.phase, current_task=s.current_task, messages=[_msg_out(r) for r in rows])

    prev_url = s.song_ref_url
    prev_ref_path = s.song_ref_path
    msgs, updates = rule_engine.handle_text(_session_state(s), body.text, history=history)
    _apply_updates(s, updates)

    # 原曲URLが変わったら、前にYouTubeから取得した原曲キャッシュ(session_*)は無効化する。
    # （古い曲のwavと比較してしまう事故を防ぐ。アップロードされたお手本(ref_*)は保持する）
    new_url = updates.get("song_ref_url")
    if (
        new_url
        and new_url != prev_url
        and prev_ref_path
        and os.path.basename(prev_ref_path).startswith(f"session_{s.id}")
    ):
        try:
            os.remove(prev_ref_path)
        except OSError:
            pass
        s.song_ref_path = None

    # 原曲URLが新たに付いたら、YouTubeタイトルを自動でレッスン名にする（未設定時のみ）
    if updates.get("song_ref_url") and not s.song_title:
        title = fetch_youtube_title(updates["song_ref_url"])
        if title:
            s.song_title = title

    # 原曲URLが新しく付いたら、この時点で先に原曲を取得しておく（先読み）。
    # 録音時にダウンロードを待たずに済み、最初の聴き比べも10秒以内に収めやすくなる。
    if (
        new_url
        and new_url != prev_url
        and settings.enable_youtube_reference
        and not s.song_ref_path
    ):
        try:
            ref_wav = fetch_reference_wav(
                new_url, settings.reference_cache_dir, name=f"session_{s.id}"
            )
            s.song_ref_path = ref_wav
        except ReferenceFetchError:
            pass  # 失敗しても録音時に再試行・フォールバックする

    rows = _persist_coach_messages(db, s.id, msgs)
    db.commit()
    for r in rows:
        db.refresh(r)
    return ChatResponse(phase=s.phase, current_task=s.current_task, messages=[_msg_out(r) for r in rows])


@router.post("/sessions/{session_id}/action", response_model=ChatResponse)
def send_action(
    session_id: int,
    body: ActionRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> ChatResponse:
    """「次にやること」チップ押下を処理（ユーザー主導フロー）。"""
    s = _get_owned_session(db, session_id, user)

    # 「発音を見る」チップは、最新録音を Gemini に聴かせる特別経路
    if body.action == "pronunciation":
        rows = _persist_coach_messages(db, s.id, [_pronunciation_reply(db, s)])
        db.commit()
        for r in rows:
            db.refresh(r)
        return ChatResponse(phase=s.phase, current_task=s.current_task, messages=[_msg_out(r) for r in rows])

    msgs, updates = rule_engine.handle_action(_session_state(s), body.action)
    _apply_updates(s, updates)
    rows = _persist_coach_messages(db, s.id, msgs)
    db.commit()
    for r in rows:
        db.refresh(r)
    return ChatResponse(phase=s.phase, current_task=s.current_task, messages=[_msg_out(r) for r in rows])


def _analysis_summary(a: dict | None) -> dict | None:
    """フィードバックに添える解析サマリ（後でレビューしやすい主要値だけ）。"""
    if not a:
        return None
    cmp = (a.get("_compare") or {}).get("alignment") or {}
    keys = [
        "duration_sec", "f0_median_hz", "f0_jitter_cents", "estimated_key",
        "vibrato_rate_hz", "rms_db_range", "harmonic_ratio",
        "formant_f1_hz", "formant_f2_hz", "spectral_tilt_db_oct",
    ]
    out = {k: a.get(k) for k in keys if a.get(k) is not None}
    if cmp.get("in_tune_score") is not None:
        out["in_tune_score"] = cmp.get("in_tune_score")
        out["pitch_error_cents"] = cmp.get("pitch_error_cents")
    segs = (a.get("timeline") or {}).get("sustained_segments", [])
    regs = [s.get("register") for s in segs if s.get("register")]
    if regs:
        out["registers"] = regs
    return out


@router.post("/sessions/{session_id}/messages/{message_id}/feedback")
def submit_feedback(
    session_id: int,
    message_id: int,
    body: FeedbackRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict:
    """コーチ返信への👍/👎＋任意コメント。間違い指摘を蓄積して改善ループに使う。

    1ユーザー×1メッセージにつき1件（再送は上書き）。対象は coach のメッセージのみ。
    """
    s = _get_owned_session(db, session_id, user)

    if body.rating not in ("up", "down"):
        raise HTTPException(
            status_code=400,
            detail={"code": "BAD_REQUEST", "message": "rating は up または down です"},
        )
    msg = (
        db.query(ChatMessage)
        .filter(ChatMessage.id == message_id, ChatMessage.session_id == s.id)
        .first()
    )
    if not msg or msg.role != "coach":
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "対象のコーチ返信が見つかりません"},
        )

    context = {
        "message_excerpt": (msg.text or "")[:500],
        "message_type": msg.type,
        "analysis": _analysis_summary(s.last_analysis),
    }

    fb = (
        db.query(MessageFeedback)
        .filter(MessageFeedback.message_id == message_id, MessageFeedback.user_id == user.id)
        .first()
    )
    if fb is None:
        fb = MessageFeedback(
            message_id=message_id, session_id=s.id, user_id=user.id, rating=body.rating
        )
        db.add(fb)
    fb.rating = body.rating
    fb.reason = (body.reason or None)
    fb.comment = (body.comment or None)
    fb.context = context
    db.commit()
    return {"ok": True, "rating": fb.rating}


@router.post("/sessions/{session_id}/reference", response_model=ChatResponse)
def upload_reference(
    session_id: int,
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> ChatResponse:
    """原曲（お手本）の音源をアップロードして、このセッションの比較基準にする。

    以降この曲の録音を送ると、原曲とDTWで整列し「音程の正確さ(in-tune)」と
    「リズムの走り/モタり」を実測してフィードバックする（精度向上の主経路）。
    """
    s = _get_owned_session(db, session_id, user)

    _, ext = os.path.splitext(audio_file.filename or "")
    ext = ext.lower() or ".mp3"
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

    ensure_dir(settings.reference_cache_dir)
    raw_path = os.path.join(settings.reference_cache_dir, f"ref_{s.id}{ext}")
    with open(raw_path, "wb") as f:
        f.write(audio_file.file.read())
    try:
        wav_path = to_wav(raw_path, raw_path + ".wav")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "ANALYSIS_FAILED", "message": f"お手本音源の変換に失敗しました: {e}"},
        )

    s.song_ref_path = wav_path
    msg = {
        "role": "coach", "type": "text",
        "text": "🎼 お手本（原曲）を受け取りました！\n"
                "このあと同じ曲を歌って録音を送ってくれたら、原曲と聴き比べて"
                "「音を外していないか（音程の正確さ）」と「リズムの走り／モタり」を"
                "具体的に見ていきますね😊",
    }
    rows = _persist_coach_messages(db, s.id, [msg])
    db.commit()
    for r in rows:
        db.refresh(r)
    return ChatResponse(phase=s.phase, current_task=s.current_task,
                        messages=[_msg_out(r) for r in rows])


@router.post("/sessions/{session_id}/audio", response_model=ChatResponse)
def send_audio(
    session_id: int,
    audio_file: UploadFile = File(...),
    kind: str = Form("song"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> ChatResponse:
    s = _get_owned_session(db, session_id, user)

    # 録音を追加する前に、これまでの会話履歴を LLM 用に取得（コメント生成の文脈に使う）
    history = _history_for_llm(s)

    # --- rate limit（CPU負荷の高い解析の悪用防止）---
    if not check_rate_limit(
        f"audio:{user.id}", settings.rate_limit_max_audio, settings.rate_limit_window_sec
    ):
        raise HTTPException(
            status_code=429,
            detail={"code": "RATE_LIMITED", "message": "少し時間をおいてから、もう一度お試しください。"},
        )

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
    # 原曲（お手本）がある曲の録音は、フェーズに関係なく常に原曲と比較する（主経路）
    needs_ref = kind != "practice" and bool(s.song_ref_path or s.song_ref_url)

    ref_wav = None
    ref_fetch_failed = False
    if needs_ref:
        ref_wav = s.song_ref_path
        # 原曲取得が有効なときだけ YouTube からダウンロード（本番は既定で無効＝録音単体FB）
        if not ref_wav and s.song_ref_url and settings.enable_youtube_reference:
            try:
                ref_wav = fetch_reference_wav(
                    s.song_ref_url, settings.reference_cache_dir, name=f"session_{s.id}"
                )
                s.song_ref_path = ref_wav
            except ReferenceFetchError:
                ref_wav = None  # 取得失敗時は単体解析にフォールバック
                ref_fetch_failed = True

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
                    "text": "あれ、いただいた録音が原曲と同じ音源みたいです🎤 "
                            "あなた自身が歌った録音を送ってもらえますか？そこからが本番ですよ😊",
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

    # 歌声プレゼンスのゲート: 無音・極端に短い・ほぼ無声 の録音には
    # FBを捏造せず録り直しを促す（無音や非歌唱に講評をつけるハルシネーション防止）。
    if not _looks_like_singing(user_analysis):
        msg = {
            "role": "coach", "type": "text",
            "text": "うまく歌声を聞き取れませんでした🙏 "
                    "もう少し長め（数秒以上）に、はっきり歌った録音を送ってください。"
                    "マイクが声を拾えているかもご確認くださいね🎤",
        }
        rows = _persist_coach_messages(db, s.id, [msg])
        db.commit()
        for r in rows:
            db.refresh(r)
        return ChatResponse(phase=s.phase, current_task=s.current_task,
                            messages=[_msg_out(r) for r in rows])

    # 種類が明示されていなければ（"auto"）、音声から曲/基礎練を自動判定する
    if kind not in ("song", "practice"):
        kind = rule_engine.classify_kind(user_analysis)
    # 最新の録音の解析を保持（会話の文脈は常に最新録音を参照する）。
    # 原曲との比較結果(in-tune/リズム)も埋め込み、後続のチャットがカードと矛盾しないようにする。
    if compare_data:
        s.last_analysis = {**user_analysis, "_compare": compare_data}
    else:
        s.last_analysis = user_analysis

    msgs, updates = rule_engine.handle_audio(
        _session_state(s), user_analysis, compare_data, kind, history=history
    )
    _apply_updates(s, updates)
    # 原曲URLを貼ってくれたのに取得できなかった時は、黙って単体FBにせず一言ことわる
    # （URLを貼った＝聴き比べを期待しているので、比較できなかった事実を隠さない）。
    if ref_fetch_failed and not compare_data:
        msgs = [
            {
                "role": "coach", "type": "text",
                "text": "🙏 原曲をうまく取り込めませんでした。今回はあなたの録音だけで講評しますね。"
                        "（YouTube側の仕様で取得できない動画もあります。別のリンクなら聴き比べできることもあります）",
            }
        ] + msgs
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
