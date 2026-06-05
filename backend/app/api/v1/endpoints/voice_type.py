"""声タイプ診断（独立機能）。

コーチングのチャットとは別の入口。録音を1本アップロードすると、その場で
発声指標を解析して8つの「声タイプ」を判定し、シェア用のカードデータを返す。
チャットセッションには一切依存しない（任意のタイミングで何度でも実行可）。
"""
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.v1.endpoints.coach import ALLOWED_EXT, _looks_like_singing
from app.audio import analyzer
from app.audio.convert import to_wav
from app.coaching import scoring, voice_coach
from app.core.config import settings
from app.core.ratelimit import check_rate_limit
from app.db.session import get_db
from app.deps import get_current_user
from app.storage.files import ensure_dir

router = APIRouter(prefix="/api/v1/voice-type", tags=["voice-type"])


@router.post("/analyze")
def analyze_voice_type(
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict:
    """録音1本から声タイプ（8種）を判定して返す。"""
    # --- rate limit（解析はCPU負荷が高いので悪用防止）---
    if not check_rate_limit(
        f"voicetype:{user.id}", settings.rate_limit_max_audio, settings.rate_limit_window_sec
    ):
        raise HTTPException(
            status_code=429,
            detail={"code": "RATE_LIMITED", "message": "少し時間をおいてから、もう一度お試しください。"},
        )

    # --- validate ---
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

    # --- save temp + convert to wav ---
    ensure_dir(settings.coach_audio_dir)
    token = uuid.uuid4().hex
    raw_path = os.path.join(settings.coach_audio_dir, f"vtype_{token}{ext}")
    wav_path = raw_path + ".wav"
    with open(raw_path, "wb") as f:
        f.write(audio_file.file.read())

    try:
        try:
            wav_path = to_wav(raw_path, wav_path)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail={"code": "ANALYSIS_FAILED", "message": f"音声の変換に失敗しました: {e}"},
            )

        try:
            analysis = analyzer.analyze_file(wav_path)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail={"code": "ANALYSIS_FAILED", "message": f"音声の解析に失敗しました: {e}"},
            )

        # 歌声・発声プレゼンスのゲート（無音/極端に短い録音に捏造判定をしない）
        if not _looks_like_singing(analysis):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "NO_VOICE",
                    "message": "声がうまく聞き取れませんでした🎤 静かな場所で、数秒以上ひと続きで歌った録音で試してみてください。",
                },
            )

        vt = voice_coach.classify_voice_type(analysis)
        if not vt:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "NO_VOICE",
                    "message": "声の特徴がうまく取れませんでした🙏 もう少し長め（数秒以上）に歌った録音で試してみてください。",
                },
            )

        scores = scoring.voice_scores(analysis, None)
        return {
            "voice_type": vt,
            "score": scores.get("total_score"),
            "scores": scores,
            "duration_sec": round(float(analysis.get("duration_sec") or 0.0), 1),
        }
    finally:
        for p in (raw_path, wav_path):
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass
