import random
import time

from sqlalchemy.orm import Session

from app.models.evaluation import Evaluation
from app.models.recording import Recording
from app.services.billing_service import increment_analysis_count


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


def evaluate_recording(db: Session, recording_id: int) -> None:
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

