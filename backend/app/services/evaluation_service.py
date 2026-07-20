import random
import time

from sqlalchemy.orm import Session

from app.models.coaching import ChatMessage, ChatSession
from app.models.evaluation import Evaluation
from app.models.recording import Recording
from app.services.billing_service import analysis_allowed, increment_analysis_count


class NoCoachAudioError(Exception):
    """昇格対象の音声メッセージがレッスンに無い（409 NO_AUDIO）。"""


class AnalysisLimitReachedError(Exception):
    """無料プランの月次解析上限に達している（402 LIMIT_REACHED）。"""


def compute_scores_deterministically(recording_id: int) -> dict[str, int]:
    # NOTE: MVPでは音声解析の代わりに決定論的なスコアを返す。
    # 後続で実解析（pitch/rhythm/expression）に差し替える前提。
    rng = random.Random(recording_id)
    pitch = rng.randint(40, 100)
    rhythm = rng.randint(30, 100)
    expression = rng.randint(35, 100)
    total = int(round((pitch + rhythm + expression) / 3))
    return {
        "pitch_score": pitch,
        "rhythm_score": rhythm,
        "expression_score": expression,
        "total_score": total,
    }


def generate_feedback_text(total_score: int) -> str:
    if total_score >= 85:
        return "安定しています。さらに表現（感情の起伏）を意識すると伸びます。"
    if total_score >= 70:
        return "全体のバランスは良いです。音程とリズムを部分練習で強化しましょう。"
    if total_score >= 55:
        return "改善ポイントが明確です。まずは基礎（音程・呼吸）を丁寧に整えましょう。"
    return "現在の録音は大きく伸びる余地があります。短いフレーズで反復し、徐々にテンポを上げてください。"


def evaluate_recording(db: Session, recording_id: int, count_usage: bool = True) -> None:
    """録音を評価する。count_usage=False は coach 昇格用（送信時にカウント済みの
    同一音声の再評価のため、月次カウントを増やさない＝docs/31 v3 AC-12）。"""
    recording = db.query(Recording).filter(Recording.id == recording_id).first()
    if recording is None:
        return

    # 解析開始
    recording.status = "analyzing"
    db.add(recording)
    db.commit()
    db.refresh(recording)

    # 設計書の方針に合わせて最大3回まで再試行する。
    # 1回目失敗後 5秒, 2回目失敗後 15秒 待機して再試行。
    retry_delays = [5, 15]

    for attempt in range(3):
        try:
            scores = compute_scores_deterministically(recording_id)
            feedback = generate_feedback_text(scores["total_score"])

            existing = db.query(Evaluation).filter(Evaluation.recording_id == recording_id).first()
            if existing:
                existing.pitch_score = scores["pitch_score"]
                existing.rhythm_score = scores["rhythm_score"]
                existing.expression_score = scores["expression_score"]
                existing.total_score = scores["total_score"]
                existing.feedback_text = feedback
                db.add(existing)
            else:
                evaluation = Evaluation(
                    recording_id=recording_id,
                    pitch_score=scores["pitch_score"],
                    rhythm_score=scores["rhythm_score"],
                    expression_score=scores["expression_score"],
                    total_score=scores["total_score"],
                    feedback_text=feedback,
                )
                db.add(evaluation)

            recording.status = "completed"
            db.add(recording)
            db.commit()
            # 解析が完了した時だけカウント（失敗は数えない＝docs/31 FR-01）
            if count_usage:
                increment_analysis_count(db, recording.user_id)
            return
        except Exception:
            db.rollback()
            if attempt < len(retry_delays):
                time.sleep(retry_delays[attempt])
                continue

    recording.status = "failed"
    db.add(recording)
    db.commit()


def promote_coach_recording(db: Session, session: ChatSession, user_id: int) -> Recording:
    """coachレッスンの最新録音を Recording に昇格し、評価まで作る（docs/50 T-2）。

    既存の評価→詳細添削レポートのパイプラインに乗せるための橋渡し。
    冪等: 同じ音声メッセージ由来の Recording があればそれを返す（二重作成・上限二重消費を防ぐ）。
    """
    last_audio = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.session_id == session.id,
            ChatMessage.type == "audio",
            ChatMessage.audio_path.isnot(None),
        )
        .order_by(ChatMessage.id.desc())
        .first()
    )
    if last_audio is None or not last_audio.audio_path:
        raise NoCoachAudioError()

    # 冪等: 既に昇格済みならそのまま返す。
    existing = (
        db.query(Recording).filter(Recording.source_message_id == last_audio.id).first()
    )
    if existing is not None:
        return existing

    # 新規昇格は1解析としてカウント対象（上限ゲート）。
    if not analysis_allowed(db, user_id):
        raise AnalysisLimitReachedError()

    recording = Recording(
        user_id=user_id,
        title=session.song_title or f"レッスン #{session.id} の録音",
        note=None,
        audio_path=last_audio.audio_path,
        status="uploaded",
        source_session_id=session.id,
        source_message_id=last_audio.id,
    )
    db.add(recording)
    db.commit()
    db.refresh(recording)

    # 決定論的評価（既存パイプライン再利用）。coach送信時にカウント済みのため
    # 昇格ではカウントしない（docs/31 v3 AC-12・docs/50）。
    evaluate_recording(db, recording.id, count_usage=False)
    db.refresh(recording)
    return recording

