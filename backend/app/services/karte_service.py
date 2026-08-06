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
_REOPEN_DAYS = 30   # 引き継ぎ挨拶をやめて「久しぶり」挨拶に切り替える空白日数（FR-06）

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


def practice_mentioned(texts: list[str], practice_name: str | None) -> bool:
    """コーチが実際に表示した文章に、その練習が登場したかを判定する。

    完全一致の包含に加え、既知の練習語彙（llm.PRACTICE_KEYWORDS）のうち
    練習名に含まれる語（例: 『ハミング → 母音（マスクに集める）』の「ハミング」）が
    本文にあれば言及ありとみなす（LLMが練習名を言い換えるケースの取りこぼし防止）。
    """
    if not practice_name:
        return False
    joined = "\n".join(t for t in texts if t)
    if not joined:
        return False
    if practice_name in joined:
        return True
    from app.coaching.llm import PRACTICE_KEYWORDS
    return any(k in practice_name and k in joined for k in PRACTICE_KEYWORDS)


def record_prescription(db: Session, user_id: int, *, task_id: str | None,
                        practice_name: str) -> None:
    """会話で実際に提示した基礎練を宿題としてカルテに記録する（FR-06）。

    呼び出し側は practice_mentioned() で「表示テキストに練習名が登場した」ことを
    確認してから呼ぶこと。会話に無い練習を宿題にすると、次回の開始挨拶が
    「さっき『◯◯』のお話をしましたね」と存在しない会話を引用してしまう。
    """
    k = _get_or_create(db, user_id)
    k.homework = {"task_id": task_id, "practice_name": practice_name,
                  "assigned_at": datetime.utcnow().isoformat()}


def drop_unmentioned_homework(db: Session, user_id: int) -> None:
    """会話に一度も登場していない宿題をカルテから破棄する（自己修復・FR-06）。

    過去に「診断＝即・カタログ練習名を宿題記録」していた時期の汚染データが残っていると、
    開始挨拶が実在しない会話を引用し続ける。照合対象は「ユーザー発言より後のコーチ発言」
    だけにする（開始挨拶自身が練習名を口にするため、それを根拠に自己正当化しない）。
    """
    k = get_or_none(db, user_id)
    name = ((k.homework or {}) if k else {}).get("practice_name")
    if not name:
        return
    from sqlalchemy import func

    from app.models.coaching import ChatMessage, ChatSession

    first_user = (
        db.query(ChatMessage.session_id.label("sid"),
                 func.min(ChatMessage.id).label("first_user_id"))
        .filter(ChatMessage.role == "user")
        .group_by(ChatMessage.session_id)
        .subquery()
    )
    rows = (
        db.query(ChatMessage.text)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .join(first_user, first_user.c.sid == ChatMessage.session_id)
        .filter(
            ChatSession.user_id == user_id,
            ChatMessage.role == "coach",
            ChatMessage.id > first_user.c.first_user_id,
            ChatMessage.text.isnot(None),
        )
        .order_by(ChatMessage.id.desc())
        .limit(300)
        .all()
    )
    if not practice_mentioned([r[0] for r in rows], name):
        k.homework = None


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
        # 内部ID（breathy_closure 等）をそのまま挨拶に露出させない。ラベルに翻訳する
        from app.coaching.taxonomy import get_task
        _label = ((get_task(diagnosed_task) or {}).get("label")) or diagnosed_task
        summary_bits.append(f"課題は「{_label}」")
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
    """セッション開始時の引き継ぎ情報（FR-06）。無ければ None＝現行挨拶。

    開始挨拶は宿題・練習名に言及しない（新しいテーマで始まるかもしれない場に
    前回の宿題を蒸し返すのは不自然、という実ユーザーFB 2026-08-06。
    2026-07-08 の「数分前の提案を宿題扱いして聞く」事故も同根）。
    宿題はカルテに残り、FB・練習提案の文脈でだけ参照される（render_context 経由）。
    """
    if karte is None or karte.last_session_at is None:
        return None
    days = (datetime.utcnow() - karte.last_session_at).days
    if days >= _REOPEN_DAYS:
        return {"mode": "reopen", "days": days}
    if days == 0:
        # 同日の再訪: 直前の会話の要約を読み上げるのも不自然なので、短い出迎えだけ
        return {"mode": "continue_recent"}
    if karte.last_summary:
        return {"mode": "continue", "last_summary": karte.last_summary}
    return None
