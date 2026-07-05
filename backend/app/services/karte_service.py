"""生徒カルテと主観問診（docs/53/54）。

セッションを跨ぐ「生徒の記憶」の読み書きと、録音FB後の1問問診のロジック。
すべてルールベース（追加LLM呼び出しゼロ）。カルテ更新の失敗はFBを止めない
（呼び出し側で try/except、ここでは例外を素通しにする）。
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.karte import StudentKarte

logger = logging.getLogger(__name__)

_HISTORY_MAX = 10   # 練習履歴の保持件数
_NOTES_MAX = 5      # 主観メモの保持件数
_NOTE_LEN = 120     # 主観メモの要旨長（生ログを溜めない）
_CONTEXT_LEN = 500  # プロンプト注入の上限（docs/53 FR-02）
_REOPEN_DAYS = 30   # 宿題確認をやめて「久しぶり」挨拶に切り替える空白日数（FR-06）

# レッドフラグ（FR-05）: 医療診断はしない。検知したら安全側（休声・受診目安の案内）。
RED_FLAG_RE = re.compile(
    r"痛い|痛く|痛み|ヒリヒリ|ひりひり|イガイガ|枯れ|かすれ|嗄れ|ガラガラ声が続|"
    r"血|声が出ない|声が出なく|出なくなっ|飲み込みにく|しこり"
)

# 問診の種類 → 質問文（1問だけ・短く）
CHECKIN_QUESTIONS = {
    "first_audio": "ところで、いま歌ってみて、喉や息はラクでしたか？感じたままで大丈夫ですよ😊",
    "strain": "高いところ、喉はラクでしたか？力んだ感じがあったら教えてくださいね。",
    "after_practice": "やってみて、どこか力む感じはありましたか？",
}


def get_or_none(db: Session, user_id: int) -> StudentKarte | None:
    return db.query(StudentKarte).filter(StudentKarte.user_id == user_id).first()


def _get_or_create(db: Session, user_id: int) -> StudentKarte:
    k = get_or_none(db, user_id)
    if k is None:
        k = StudentKarte(user_id=user_id)
        db.add(k)
        db.flush()
    return k


def render_context(karte: StudentKarte | None) -> str:
    """カルテを「この生徒について」ブロック（≤500字）にする。未作成なら空文字。

    docs/53 FR-02: 過去の傾向は参考情報。今回の録音の断定材料にしない旨を明記する。
    """
    if karte is None:
        return ""
    lines: list[str] = ["この生徒について（カルテ。過去の記録＝参考情報。今回の録音の断定には使わない）:"]
    v = karte.voice or {}
    if v.get("f0_min_hz") and v.get("f0_max_hz"):
        lines.append(f"- これまでの声域: 約{v['f0_min_hz']:.0f}〜{v['f0_max_hz']:.0f}Hz")
    if v.get("voice_type"):
        lines.append(f"- 声タイプ: {v['voice_type']}")
    t = karte.tendencies or {}
    if t:
        top = sorted(t.items(), key=lambda x: -x[1])[:3]
        lines.append("- 持ち癖（診断頻度の高い課題）: " + "、".join(f"{k}×{c}" for k, c in top))
    hw = karte.homework or {}
    if hw.get("practice_name"):
        lines.append(f"- 宿題: 『{hw['practice_name']}』（{hw.get('assigned_at', '')[:10]}に出した）")
    for n in (karte.subjective_notes or [])[:2]:
        flag = "⚠️" if n.get("red_flag") else ""
        lines.append(f"- 本人の感覚{flag}（{n.get('at', '')[:10]}）: {n.get('note', '')}")
    if karte.last_summary:
        lines.append(f"- 前回: {karte.last_summary}")
    out = "\n".join(lines)
    return out[:_CONTEXT_LEN] if len(lines) > 1 else ""


def update_from_audio(
    db: Session, user_id: int, *,
    diagnosed_task: str | None = None,
    achieved: bool | None = None,
    song_title: str | None = None,
    analysis: dict | None = None,
    practice_name: str | None = None,
) -> None:
    """録音FB確定後のカルテ更新（FR-01）。呼び出し側で try/except すること。"""
    k = _get_or_create(db, user_id)
    now = datetime.utcnow().isoformat()

    if analysis:
        v = dict(k.voice or {})
        fm = analysis.get("f0_median_hz")
        if fm:
            v["f0_min_hz"] = min(v.get("f0_min_hz") or fm, fm)
            v["f0_max_hz"] = max(v.get("f0_max_hz") or fm, fm)
        k.voice = v

    if diagnosed_task:
        t = dict(k.tendencies or {})
        t[diagnosed_task] = int(t.get(diagnosed_task, 0)) + 1
        k.tendencies = t
        if practice_name:
            k.homework = {"task_id": diagnosed_task, "practice_name": practice_name, "assigned_at": now}

    if achieved is not None and (diagnosed_task or k.homework):
        task_id = diagnosed_task or (k.homework or {}).get("task_id")
        hist = list(k.practice_history or [])
        hist.append({
            "task_id": task_id,
            "practice": practice_name or (k.homework or {}).get("practice_name"),
            "result": "pass" if achieved else "retry",
            "at": now,
        })
        k.practice_history = hist[-_HISTORY_MAX:]
        if achieved:
            k.homework = None  # 達成した宿題は消す

    summary_bits = []
    if song_title:
        summary_bits.append(f"『{song_title}』を練習")
    if diagnosed_task:
        summary_bits.append(f"課題は{diagnosed_task}")
    if achieved:
        summary_bits.append("基礎練は達成")
    if summary_bits:
        k.last_summary = "。".join(summary_bits)[:300]
    k.last_session_at = datetime.utcnow()


def record_subjective(db: Session, user_id: int, text: str) -> dict:
    """問診回答をカルテに記録し、レッドフラグ判定を返す（FR-03/05）。"""
    note = (text or "").strip().replace("\n", " ")[:_NOTE_LEN]
    red = bool(RED_FLAG_RE.search(note))
    k = _get_or_create(db, user_id)
    notes = [{"at": datetime.utcnow().isoformat(), "note": note, "red_flag": red}]
    notes += list(k.subjective_notes or [])
    k.subjective_notes = notes[:_NOTES_MAX]
    return {"red_flag": red}


def should_ask_checkin(session, *, first_audio_in_session: bool,
                       diagnosed_task: str | None, after_practice_check: bool) -> str | None:
    """問診を出すか（FR-03）。出すなら種類を返す。上限2回/セッション・連続禁止は呼び出し側の
    awaiting_checkin クリア後にのみ呼ばれる前提（回答待ち中は録音FB側で発火しない）。
    """
    if (session.checkin_count or 0) >= 2:
        return None
    if session.awaiting_checkin:
        return None
    if diagnosed_task in ("throat_tension", "mixed_voice"):
        return "strain"
    if after_practice_check:
        return "after_practice"
    if first_audio_in_session:
        return "first_audio"
    return None


RED_FLAG_REPLY = (
    "教えてくれてありがとうございます。喉に痛みや違和感があるときは、無理をしないのがいちばん大切です🙏 "
    "今日は歌の練習をお休みして、水分をとって声を休ませてあげてください。"
    "声のかすれや痛みが2週間以上続くようなら、耳鼻咽喉科（できれば音声外来）で診てもらうと安心です。"
    "落ち着いたら、また一緒にゆっくり再開しましょうね。"
)


def session_opener_context(karte: StudentKarte | None) -> dict | None:
    """セッション開始時の引き継ぎ情報（FR-06）。無ければ None＝現行挨拶。"""
    if karte is None or karte.last_session_at is None:
        return None
    days = (datetime.utcnow() - karte.last_session_at).days
    hw = karte.homework or {}
    if days >= _REOPEN_DAYS:
        return {"mode": "reopen", "days": days}
    if hw.get("practice_name"):
        return {"mode": "homework", "practice_name": hw["practice_name"],
                "task_id": hw.get("task_id"), "last_summary": karte.last_summary}
    if karte.last_summary:
        return {"mode": "continue", "last_summary": karte.last_summary}
    return None
