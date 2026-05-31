"""
コーチングループのルールエンジン（Phase A〜E の状態機械）。

副作用なし: 入力（session状態 dict + ユーザー入力）→ 出力（コーチメッセージ列 + 新state）。
DB保存・解析実行は endpoint 側が担当し、解析結果はここに渡される。

メッセージは dict: {"role": "coach", "type": "...", "text"?: str, "payload"?: dict}
"""

from __future__ import annotations

import re
from typing import Optional

from app.coaching import feedback_builder, llm
from app.coaching.persona import COACH_NAME
from app.coaching.taxonomy import diagnose_task, get_task, projection_point


# フェーズは「行動を縛るゲート」ではなく「現在地を示すソフトラベル」。
#   A      = 初回（弱点さがし前）
#   LESSON = 練習中（診断後。基礎練・歌い直し・質問を自由に行き来）
#   done   = ひと区切り
PHASE_A, PHASE_B, PHASE_C, PHASE_D, PHASE_E, DONE = "A", "B", "C", "D", "E", "done"
LESSON = "practice"

YOUTUBE_RE = re.compile(r"https?://[^\s]*(?:youtube\.com|youtu\.be)[^\s]*")
RANGE_RE = re.compile(r"(\d{1,2}:\d{2}|\d+(?:\.\d+)?)\s*[-–~〜]\s*(\d{1,2}:\d{2}|\d+(?:\.\d+)?)")
FOCUS_KEYWORDS = {
    "throat_tension": ["力み", "詰ま", "喉", "こもる"],
    "long_tone_decay": ["ロングトーン", "伸ば", "息", "支え", "ブレス"],
    "mixed_voice": ["ミックス", "換声", "裏返", "高音"],
    "pitch_wobble": ["音程", "ピッチ", "音痴"],
    "no_vibrato": ["ビブラート", "ゆらし"],
    "rhythm_lag": ["リズム", "走り", "もたり", "拍"],
    "expression_flat": ["表現", "強弱", "抑揚", "平ら", "平坦"],
}

# 「次にやること」チップ（ユーザー主導フロー）
ACTION_DEFS = {
    "more_practice": {"icon": "🎙", "label": "もう一度 基礎練"},
    "recheck_song": {"icon": "🎵", "label": "曲を録り直す"},
    "change_task": {"icon": "🔁", "label": "別の課題に変える"},
    "finish": {"icon": "✅", "label": "今日はここまで"},
}


def _action_chips(*ids: str) -> dict:
    """指定IDのチップ payload を返す。"""
    return {"actions": [{"id": i, **ACTION_DEFS[i]} for i in ids if i in ACTION_DEFS]}


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


def _safe_reason(task: Optional[dict], analysis: Optional[dict]) -> Optional[str]:
    if not task or not analysis:
        return None
    try:
        return task["reason"](analysis, None)
    except Exception:
        return None


def answer_question(state: dict, text: str) -> Optional[str]:
    """今の課題・解析結果を踏まえて、ユーザーの質問にその場で答える（対話型）。

    ルールベースなので、よくある質問パターンを文脈で埋めて返す。
    該当しなければ None（呼び出し側で一般応答にフォールバック）。
    """
    t = text.strip()
    task = get_task(state.get("current_task")) if state.get("current_task") else None
    baseline = state.get("baseline_analysis")
    reason = _safe_reason(task, baseline)

    def q(*kws: str) -> bool:
        return any(k in t for k in kws)

    # どこ／どの部分（場所を聞いている）
    if q("どこ", "どの部分", "どのへん", "どこら", "場所", "何秒", "どの音", "どこが"):
        if reason:
            return f"はい、{reason} そこを意識して、もう一度歌ってみましょう🎤"
        if task:
            return f"今は「{task['label']}」を見ています。録音をもう一度送ってもらえたら、具体的に何秒のどこか、はっきりお伝えしますね🎤"
        return "まず歌った録音を送ってもらえたら、どこを直すか秒数で具体的にお伝えします🎤"

    # どうやって／やり方／コツ
    if q("どうやって", "どうすれ", "やり方", "方法", "コツ", "どう練習", "練習方法"):
        if task:
            p = task["practices"][0]
            steps = "／".join(p["steps"][:2])
            cp = f"目安は『{p.get('checkpoint','')}』です。" if p.get("checkpoint") else ""
            return f"『{p['name']}』から始めましょう。{steps}…という流れです。{cp}上の基礎練カードに手順とお手本動画があるので、見ながらやってみてくださいね😊"
        return "録音を送ってもらえたら、あなたに合った練習法を具体的にお伝えします🎯"

    # なぜ／理由
    if q("なぜ", "どうして", "理由", "なんで", "なぜか"):
        if task:
            base = reason or f"「{task['label']}」が今いちばん伸ばせるポイントだからです。"
            return f"{base} だからこの基礎練が効くんですよ😊"
        return "気になるところを録音で送ってもらえたら、理由から説明しますね。"

    # わからない／難しい／できない
    if q("わからない", "分からない", "わかんない", "むずかし", "難し", "できない", "苦手"):
        if task:
            p = task["practices"][0]
            return f"大丈夫、ゆっくりいきましょう💪 まずは『{p['name']}』だけでOKです。{p.get('checkpoint','')} を目安にしてみてください。録音を送ってくれたら、できているか一緒に確かめますね🎤"
        return "焦らなくて大丈夫です😊 まずは1フレーズだけ歌って録ってみましょう🎤"

    # スコア／点数
    if q("スコア", "点数", "何点", "評価"):
        return "スコアは音程・リズム・表現の3つをAIで解析して出しています。上の分析カードに内訳が出ていますよ📊 もう一度録ると、前回との変化も比べられます。"

    # 励まし・お礼への返し
    if q("ありがとう", "わかった", "了解", "やってみる", "がんばる", "頑張る"):
        return "その意気です😊 練習できたら録音を送ってくださいね。いつでも待っています🎤"

    return None


def _chat_reply(state: dict, text: str, history: Optional[list[dict]], generic: str) -> str:
    """自由テキストへの返答を決める。

    1) LLM（ソラ先生）で自然言語応答を試みる
    2) ダメなら（APIキー未設定・エラー）ルールベースのテンプレ応答
    3) それも該当しなければ汎用メッセージ
    """
    reply = llm.generate_reply(state, text, history)
    if reply:
        return reply
    reply = answer_question(state, text)
    if reply:
        return reply
    return generic


def handle_text(
    state: dict, text: str, history: Optional[list[dict]] = None
) -> tuple[list[dict], dict]:
    """テキストメッセージ受信時の応答。state更新を返す。

    history: 直近の会話履歴 [{"role": "user"|"assistant", "content": str}]（古い→新しい）。
             LLM に文脈として渡す。None でもルールベースで動作する。
    """
    phase = state.get("phase", PHASE_A)
    out: list[dict] = []
    updates: dict = {}

    # どのフェーズでも、URL/区間/着目点が含まれていれば取り込む
    u = parse_phase_a(text, state)
    updates.update(u)
    merged = {**state, **u}

    if phase == PHASE_A:
        shown_range = merged.get("ref_range") or merged.get("user_range")
        if merged.get("song_ref_url"):
            if shown_range:
                out.append(coach_msg(
                    "text",
                    f"原曲と区間（{shown_range}）を確認しました😊 "
                    f"では、同じところを歌った録音を送ってくださいね🎤（🎙録音 または 📎アップロード）",
                ))
            else:
                out.append(coach_msg(
                    "text",
                    "原曲を確認しました😊 録音を送ってもらえたら、原曲と照らし合わせてアドバイスしますね🎤",
                ))
        else:
            # 質問・つぶやきには自然言語で答える。録音前なら自然に録音をうながす。
            generic = (
                "了解です🎤 まずは練習したいところを歌って、録音を送ってください"
                "（🎙録音 または 📎アップロード）。聴いて、直すところをお伝えしますね😊"
            )
            out.append(coach_msg("text", _chat_reply(merged, text, history, generic)))
        return out, updates

    # Phase B 以降：原曲が新たに付いたら知らせる。質問には答える。
    if u.get("song_ref_url"):
        out.append(coach_msg("text", "原曲を受け取りました😊 次の録音から、照らし合わせてアドバイスしますね🎤"))
        return out, updates

    generic = (
        "なるほど😊 気になることがあれば、なんでも聞いてくださいね。"
        "準備ができたら、下のボタンから録音を送ってください🎤"
    )
    out.append(coach_msg("text", _chat_reply(merged, text, history, generic)))
    return out, updates


def _llm_or(text_fallback: str, facts: str, instruction: str, history: Optional[list[dict]]) -> str:
    """LLM で自然文コメントを生成。失敗時はテンプレ文へフォールバック。"""
    reply = llm.generate_coach_comment(facts, instruction, history)
    return reply or text_fallback


def _projection_note(analysis: dict) -> Optional[str]:
    """張りどころ（曲の山）で声を張れているかを、コメント用の事実文にする。"""
    pp = projection_point(analysis)
    if not pp:
        return None
    s, e = pp["start_sec"], pp["end_sec"]
    if pp["projected"]:
        return f"張りどころ（{s:.0f}〜{e:.0f}秒の高い音＝曲の山）では、しっかり声を張れている（ここは褒める）。"
    esc = {"head": "裏声に逃げ気味", "chest": "地声で力んで", "mix": "やや不安定で"}.get(pp.get("voice_type"), "引き気味で")
    return (
        f"張りどころ（{s:.0f}〜{e:.0f}秒の高い音＝曲の山）で、声が{esc}張りきれていない。"
        f"ここは本来しっかり張る所だと伝えてよい（音量変化そのものは表現なので頭ごなしに否定しない）。"
    )


def _audio_diagnose(
    state: dict, analysis: dict, compare_data: Optional[dict], history: Optional[list[dict]]
) -> tuple[list[dict], dict]:
    """弱点診断（初回 or 課題未確定）。FBカード + 自然文 + 基礎練カード + 任意チップ。"""
    out: list[dict] = []
    avoid = state.get("avoid_task")
    exclude = [avoid] if avoid else []
    # focus 指定があれば優先（ただし除外対象なら無視）、なければ自動診断
    task = None
    focus = state.get("focus_task")
    if focus and focus not in exclude:
        task = get_task(focus)
        if task and not _safe_diag(task, analysis, compare_data):
            auto = diagnose_task(analysis, compare_data, exclude=exclude)
            task = auto or task
    else:
        task = diagnose_task(analysis, compare_data, exclude=exclude)

    fb_payload = feedback_builder.build_feedback_payload(analysis, compare_data, task)
    out.append(coach_msg("feedback", payload=fb_payload))

    if task:
        prac = task["practices"][0]
        reason = (fb_payload.get("today_task") or {}).get("reason", "")
        goods = "／".join(fb_payload.get("good_points", [])[:2])
        proj = _projection_note(analysis)
        facts = (
            f"歌を解析した。今いちばん伸ばせる弱点は「{task['label']}」。根拠: {reason}\n"
            f"良かった点: {goods}\n"
            + (f"張りどころの状況: {proj}\n" if proj else "")
            + f"おすすめの基礎練: 『{prac['name']}』（目安: {prac.get('checkpoint','')}）。詳しい手順カードはこの後に表示される。"
        )
        instr = (
            "解析の結果としてこの弱点をやさしく具体的に伝え、続けてこの基礎練を一緒にやってみようと前向きに促してください。"
            "良かった点や張りどころにも一言触れて構いません。"
            "音量が上下すること自体は表現（ダイナミクス）なので欠点扱いせず、"
            "支え不足や張りどころで張れていない場合のみ具体的に指摘してください。"
        )
        fallback = (
            f"今日のポイントは「{task['label']}」ですね。これに効く基礎練を用意したので、一緒にやってみましょう👇"
        )
        out.append(coach_msg("text", _llm_or(fallback, facts, instr, history)))
        out.append(coach_msg("practice", payload=feedback_builder.build_practice_payload(task)))
        out.append(coach_msg(
            "text",
            "やってみたら基礎練の録音を、もう同じ箇所を歌い直して確かめたいなら曲の録音を送ってください。"
            "下のボタンからも選べます😊",
            payload=_action_chips("more_practice", "recheck_song", "change_task", "finish"),
        ))
        updates = {"phase": LESSON, "current_task": task["id"], "baseline_analysis": analysis, "avoid_task": None}
    else:
        proj = _projection_note(analysis)
        facts = "歌を解析したが、大きな弱点は見当たらなかった。とても良い状態。" + (f"\n{proj}" if proj else "")
        instr = (
            "大きな弱点が無いことを一緒に喜び、張りどころに触れつつ、さらに伸ばすなら表現の幅づくりに挑戦してみようと前向きに促してください。"
        )
        fallback = "大きな弱点は見当たりませんでした！とてもいい状態ですよ✨ さらに伸ばすなら、表現の幅づくりに挑戦してみましょう。"
        out.append(coach_msg("text", _llm_or(fallback, facts, instr, history),
                             payload=_action_chips("recheck_song", "finish")))
        updates = {"phase": DONE, "baseline_analysis": analysis, "avoid_task": None}
    return out, updates


def _audio_practice_check(
    state: dict, analysis: dict, history: Optional[list[dict]]
) -> tuple[list[dict], dict]:
    """基礎練の達成判定（出来を見てほしい人向け）。judgeカード + 自然文 + 任意チップ。"""
    out: list[dict] = []
    task = get_task(state.get("current_task"))
    if not task:
        return _audio_diagnose(state, analysis, None, history)

    judge = feedback_builder.build_judge_payload(task, analysis)
    out.append(coach_msg("judge", payload=judge))
    prac = task["practices"][0]

    if judge["result"] == "pass":
        facts = f"基礎練『{task['label']}』の達成判定: 達成（基準「{task['achieve_label']}」をクリア）。"
        instr = (
            "基礎練ができていることを一緒に喜んでください。そのうえで、同じ箇所を歌い直して治ったか確かめるか、"
            "別のことをするか、ユーザーが選べるよう自然に促してください。"
        )
        fallback = "クリアです！🎉 よくがんばりましたね。同じ箇所を歌い直して確かめてもいいですよ😊"
        out.append(coach_msg("text", _llm_or(fallback, facts, instr, history),
                             payload=_action_chips("recheck_song", "more_practice", "change_task", "finish")))
    else:
        facts = (
            f"基礎練『{task['label']}』の達成判定: まだ達成していない。"
            f"基準「{task['achieve_label']}」。チェックポイント: {prac.get('checkpoint','')}。"
        )
        instr = "あと少しであることを前向きに伝え、チェックポイントを意識してもう一度試してみようと優しく励ましてください。"
        fallback = (
            f"あと少しです！『{prac['name']}』のチェックポイント（{prac.get('checkpoint','')}）"
            f"を意識して、もう一度録ってみてください😊"
        )
        out.append(coach_msg("text", _llm_or(fallback, facts, instr, history),
                             payload=_action_chips("more_practice", "recheck_song", "change_task")))
    return out, {"phase": LESSON}


def _audio_recheck(
    state: dict, analysis: dict, history: Optional[list[dict]]
) -> tuple[list[dict], dict]:
    """同じ箇所の歌い直し → 初回との改善判定（基礎練確認を飛ばしたい人向け）。"""
    out: list[dict] = []
    baseline = state.get("baseline_analysis") or {}
    next_task = diagnose_task(analysis, None, exclude=[state.get("current_task")])
    progress = feedback_builder.build_progress_payload(baseline, analysis, next_task)
    out.append(coach_msg("progress", payload=progress))

    if progress["improved"]:
        praise = progress.get("praise") or "最初より良くなっています。"
        if next_task:
            facts = (
                f"歌い直しの結果、最初の録音より改善した。{praise}\n"
                f"次に伸ばせそうな弱点: 「{next_task['label']}」（根拠: {next_task['reason'](analysis, None)}）。"
            )
            instr = (
                "良くなった点を具体的に伝えて一緒に喜び、次のおすすめ課題をやんわり提案してください。"
                "続けるか別のことをするかはユーザーが選べる雰囲気で。"
            )
            fallback = f"いい調子ですね😊 次は「{next_task['label']}」がおすすめです。続けますか？それとも別のことをしますか？"
            out.append(coach_msg("text", _llm_or(fallback, facts, instr, history)))
            out.append(coach_msg("practice", payload=feedback_builder.build_practice_payload(next_task)))
            out.append(coach_msg("text", "下のボタンからも選べます👇",
                                 payload=_action_chips("more_practice", "recheck_song", "change_task", "finish")))
            updates = {"phase": LESSON, "current_task": next_task["id"], "baseline_analysis": analysis}
        else:
            facts = f"歌い直しの結果、最初より改善し、大きな弱点はほぼ無くなった。{praise}"
            instr = "改善を大いに喜び、今日はここまででも別の曲でも続けられると前向きに伝えてください。"
            fallback = "弱点がかなり減りましたね！素晴らしいです✨ 今日はここまででも、別の曲でも続けられますよ🎶"
            out.append(coach_msg("text", _llm_or(fallback, facts, instr, history),
                                 payload=_action_chips("recheck_song", "finish")))
            updates = {"phase": DONE}
    else:
        facts = "歌い直したが、初回と比べて大きな改善はまだ出ていない。"
        instr = "落ち込ませないよう励まし、もう少し基礎練を続けるか、別の課題に変えるかを優しく提案してください。"
        fallback = "今回はまだ大きな変化は出ていないみたいですね。でも大丈夫、もう少し基礎練するか、別の課題に変えてみましょう💪"
        out.append(coach_msg("text", _llm_or(fallback, facts, instr, history),
                             payload=_action_chips("more_practice", "change_task", "recheck_song", "finish")))
        updates = {"phase": LESSON}
    return out, updates


def handle_audio(
    state: dict, analysis: dict, compare_data: Optional[dict], kind: str,
    history: Optional[list[dict]] = None,
) -> tuple[list[dict], dict]:
    """音声受信時のディスパッチ（意図駆動・フェーズ非依存）。

    kind は frontend が明示送信（"song" | "practice"）。流れは縛らない:
    - 基礎練 + 課題あり    → 達成判定（出来を見たい人）
    - 曲 + 課題&基準あり   → 改善判定（歌い直して治ったか見たい人。基礎練確認を飛ばしてOK）
    - それ以外（初回など） → 弱点診断
    """
    has_task = bool(state.get("current_task"))
    has_baseline = bool(state.get("baseline_analysis"))

    if kind == "practice" and has_task:
        return _audio_practice_check(state, analysis, history)
    if kind == "song" and has_task and has_baseline:
        return _audio_recheck(state, analysis, history)
    return _audio_diagnose(state, analysis, compare_data, history)


def handle_action(state: dict, action_id: str) -> tuple[list[dict], dict]:
    """「次にやること」チップ押下の処理。"""
    if action_id == "more_practice":
        task = get_task(state.get("current_task"))
        if not task:
            return ([coach_msg("text", "まずは曲を歌った録音を送ってくださいね🎵")], {"phase": PHASE_A})
        return (
            [coach_msg(
                "text",
                f"いいですね！『{task['label']}』の基礎練を、もう一度録音して送ってください🎙",
            )],
            {"phase": LESSON},
        )
    if action_id == "recheck_song":
        return (
            [coach_msg(
                "text",
                "では、曲の同じところをもう一度歌って録音してください🎵 最初とどれくらい変わったか比べてみますね😊",
            )],
            {"phase": LESSON},
        )
    if action_id == "change_task":
        avoid = state.get("current_task")
        # current_task をクリア → 次の曲の録音で別の弱点を診断（前の課題は除外）
        return (
            [coach_msg(
                "text",
                "わかりました！別のポイントを探しますね。もう一度、曲を歌った録音を送ってください🎵",
            )],
            {"phase": LESSON, "avoid_task": avoid, "current_task": None, "focus_task": None},
        )
    if action_id == "finish":
        return (
            [coach_msg(
                "text",
                f"おつかれさまでした！今日もよくがんばりましたね😊 また歌いたくなったら、いつでも{COACH_NAME}を呼んでください🎶",
            )],
            {"phase": DONE},
        )
    return ([coach_msg("text", "もう一度お試しください。")], {})


def _safe_diag(task: dict, a: dict, c: Optional[dict]) -> bool:
    try:
        return task["diagnose"](a, c)
    except Exception:
        return False
