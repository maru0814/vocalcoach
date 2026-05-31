"""
コーチングループのルールエンジン（Phase A〜E の状態機械）。

副作用なし: 入力（session状態 dict + ユーザー入力）→ 出力（コーチメッセージ列 + 新state）。
DB保存・解析実行は endpoint 側が担当し、解析結果はここに渡される。

メッセージは dict: {"role": "coach", "type": "...", "text"?: str, "payload"?: dict}
"""

from __future__ import annotations

import re
from typing import Optional

from app.coaching import feedback_builder
from app.coaching.persona import COACH_NAME
from app.coaching.taxonomy import diagnose_task, get_task


PHASE_A, PHASE_B, PHASE_C, PHASE_D, PHASE_E, DONE = "A", "B", "C", "D", "E", "done"

YOUTUBE_RE = re.compile(r"https?://[^\s]*(?:youtube\.com|youtu\.be)[^\s]*")
RANGE_RE = re.compile(r"(\d{1,2}:\d{2}|\d+(?:\.\d+)?)\s*[-–~〜]\s*(\d{1,2}:\d{2}|\d+(?:\.\d+)?)")
FOCUS_KEYWORDS = {
    "throat_tension": ["力み", "詰ま", "喉", "こもる"],
    "long_tone_decay": ["ロングトーン", "伸ば", "息", "支え", "ブレス"],
    "pitch_wobble": ["音程", "ピッチ", "音痴"],
    "no_vibrato": ["ビブラート", "ゆらし"],
    "expression_flat": ["表現", "強弱", "抑揚", "平ら", "平坦"],
}


def coach_msg(type_: str, text: Optional[str] = None, payload: Optional[dict] = None) -> dict:
    m: dict = {"role": "coach", "type": type_}
    if text is not None:
        m["text"] = text
    if payload is not None:
        m["payload"] = payload
    return m


def initial_messages() -> list[dict]:
    return [
        coach_msg(
            "text",
            f"はじめまして、{COACH_NAME}です😊 あなたの歌、わたしが一緒に磨いていきますね🎤",
        ),
        coach_msg(
            "text",
            "まずは練習したいところを歌って、録音を送ってください。\n"
            "下の🎙ボタンでその場録音、または📎で音源をアップロードできます。\n\n"
            "気になることがあれば先に教えてくれてもOKです"
            "（高音の力み／音程／リズム／表現／ミックスボイス など）。",
        ),
        coach_msg(
            "text",
            "💡 原曲と比べてほしいときは、原曲のYouTube URLと区間（例: 0:48-1:13）も送ってくださいね。"
            "照らし合わせて、より具体的にアドバイスします（任意）。",
        ),
    ]


def parse_phase_a(text: str, state: dict) -> dict:
    """Phase A のテキストから url / range / focus を抽出して state に反映。"""
    updates = {}
    m = YOUTUBE_RE.search(text)
    if m:
        updates["song_ref_url"] = m.group(0)
    all_ranges = [m.group(0).replace(" ", "") for m in RANGE_RE.finditer(text)]
    if len(all_ranges) >= 2:
        # 2つ指定: 1つ目=自分の録音区間、2つ目=原曲区間
        updates["user_range"] = all_ranges[0]
        updates["ref_range"] = all_ranges[1]
    elif len(all_ranges) == 1:
        # 1つだけ=原曲のどこを歌ったか。自分の録音は全体を解析する。
        updates["ref_range"] = all_ranges[0]
        updates["user_range"] = None
    for task_id, kws in FOCUS_KEYWORDS.items():
        if any(k in text for k in kws):
            updates["focus_task"] = task_id
            break
    return updates


def handle_text(state: dict, text: str) -> tuple[list[dict], dict]:
    """テキストメッセージ受信時の応答。state更新を返す。"""
    phase = state.get("phase", PHASE_A)
    out: list[dict] = []
    updates: dict = {}

    if phase == PHASE_A:
        u = parse_phase_a(text, state)
        updates.update(u)
        merged = {**state, **u}
        shown_range = merged.get("ref_range") or merged.get("user_range")
        if merged.get("song_ref_url"):
            # 原曲が指定された → 照合モード
            if shown_range:
                out.append(coach_msg(
                    "text",
                    f"原曲と区間（{shown_range}）を確認しました😊 "
                    f"では、同じところを歌った録音を送ってくださいね🎤（🎙録音 または 📎アップロード）",
                ))
            else:
                out.append(coach_msg(
                    "text",
                    "原曲を確認しました😊 録音を送ってもらえたら、原曲と照らし合わせてアドバイスしますね🎤"
                    "（区間も教えてくれると、より正確に比べられます）",
                ))
        else:
            # 原曲なしでもOK。録音を促す
            out.append(coach_msg(
                "text",
                "了解です🎤 まずは練習したいところを歌って、録音を送ってください"
                "（🎙録音 または 📎アップロード）。聴いて、直すところをお伝えしますね😊",
            ))
        return out, updates

    # Phase B 以降のテキストは補助的な相づち
    out.append(coach_msg(
        "text",
        "うんうん、いいですね。続けて録音を送ってもらえたら、わたしが聴いてみますね🎤",
    ))
    return out, updates


def handle_audio_phase_b(state: dict, analysis: dict, compare_data: Optional[dict]) -> tuple[list[dict], dict]:
    """Phase B: 課題発見。FB + 課題 + 基礎練を返す。"""
    out: list[dict] = []
    # focus 指定があれば優先、なければ自動診断
    task = None
    focus = state.get("focus_task")
    if focus:
        task = get_task(focus)
        if task and not _safe_diag(task, analysis, compare_data):
            # focus課題が当てはまらなくても、ユーザー希望を尊重しつつ自動診断も考慮
            auto = diagnose_task(analysis, compare_data)
            task = auto or task
    else:
        task = diagnose_task(analysis, compare_data)

    fb_payload = feedback_builder.build_feedback_payload(analysis, compare_data, task)
    out.append(coach_msg("feedback", payload=fb_payload))

    if task:
        out.append(coach_msg(
            "text",
            f"今日のポイントは「{task['label']}」ですね。これに効く基礎練を用意したので、一緒にやってみましょう👇",
        ))
        out.append(coach_msg("practice", payload=feedback_builder.build_practice_payload(task)))
        out.append(coach_msg(
            "text",
            "何日か続けたら、基礎練の録音を送ってくださいね。ちゃんとできているか、わたしがチェックします😊",
        ))
        updates = {"phase": PHASE_C, "current_task": task["id"], "baseline_analysis": analysis}
    else:
        out.append(coach_msg(
            "text",
            "大きな弱点は見当たりませんでした！とてもいい状態ですよ✨ "
            "さらに伸ばすなら、表現の幅づくりに挑戦してみましょう。",
        ))
        updates = {"phase": DONE, "baseline_analysis": analysis}
    return out, updates


def handle_audio_phase_d(state: dict, analysis: dict) -> tuple[list[dict], dict]:
    """Phase D: 基礎練の達成判定。"""
    out: list[dict] = []
    task = get_task(state.get("current_task"))
    if not task:
        out.append(coach_msg("text", "課題情報が見つかりませんでした。最初からやり直しましょう。"))
        return out, {"phase": PHASE_A}

    judge = feedback_builder.build_judge_payload(task, analysis)
    out.append(coach_msg("judge", payload=judge))

    if judge["result"] == "pass":
        out.append(coach_msg(
            "text",
            "クリアです！🎉 よくがんばりましたね。"
            "では、最初の曲の同じ区間をもう一度歌って録音してみましょう。どれくらい良くなったか、一緒に比べてみますね😊",
        ))
        updates = {"phase": PHASE_E, "d_retry_count": 0}
    else:
        retry = state.get("d_retry_count", 0) + 1
        if retry >= 3:
            out.append(coach_msg(
                "text",
                "うーん、この練習だと少し難しいみたいですね。焦らず、別の角度から取り組み直しましょう💪 "
                "もう一度、曲の録音を送ってください。課題を見直しますね。",
            ))
            updates = {"phase": PHASE_B, "d_retry_count": 0}
        else:
            tip = task["practices"][0]
            out.append(coach_msg(
                "text",
                f"あと少しです！『{tip['name']}』のチェックポイント（{tip.get('checkpoint','')}）"
                f"を意識して、もう一度録ってみてください。きっと良くなりますよ😊",
            ))
            updates = {"d_retry_count": retry}
    return out, updates


def handle_audio_phase_e(state: dict, analysis: dict) -> tuple[list[dict], dict]:
    """Phase E: 初回との比較・改善判定。"""
    out: list[dict] = []
    baseline = state.get("baseline_analysis") or {}
    next_task = diagnose_task(analysis, None)
    progress = feedback_builder.build_progress_payload(baseline, analysis, next_task)
    out.append(coach_msg("progress", payload=progress))

    if progress["improved"]:
        if next_task:
            out.append(coach_msg(
                "text",
                f"いい調子ですね😊 次は「{next_task['label']}」に挑戦してみましょう。基礎練を用意しました👇",
            ))
            out.append(coach_msg("practice", payload=feedback_builder.build_practice_payload(next_task)))
            updates = {"phase": PHASE_C, "current_task": next_task["id"], "baseline_analysis": analysis}
        else:
            out.append(coach_msg(
                "text",
                "弱点がかなり減りましたね！素晴らしいです✨ 今日はここまでにして、また別の曲でも一緒にやりましょう🎶",
            ))
            updates = {"phase": DONE}
    else:
        out.append(coach_msg(
            "text",
            "今回はまだ大きな変化は出ていないみたいですね。でも大丈夫、基礎練を少し増やすか、別の課題から取り組み直しましょう💪 "
            "もう一度、課題を見直すために録音を送ってください。",
        ))
        updates = {"phase": PHASE_B}
    return out, updates


def handle_audio(state: dict, analysis: dict, compare_data: Optional[dict], kind: str) -> tuple[list[dict], dict]:
    """音声受信時のディスパッチ。kind: "song" | "practice"。"""
    phase = state.get("phase", PHASE_A)
    if phase in (PHASE_A, PHASE_B):
        return handle_audio_phase_b(state, analysis, compare_data)
    if phase == PHASE_C or kind == "practice":
        return handle_audio_phase_d(state, analysis)
    if phase == PHASE_E:
        return handle_audio_phase_e(state, analysis)
    # フォールバック: 再診断
    return handle_audio_phase_b(state, analysis, compare_data)


def _safe_diag(task: dict, a: dict, c: Optional[dict]) -> bool:
    try:
        return task["diagnose"](a, c)
    except Exception:
        return False
