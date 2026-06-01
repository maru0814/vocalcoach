"""
コーチングループのルールエンジン（Phase A〜E の状態機械）。

副作用なし: 入力（session状態 dict + ユーザー入力）→ 出力（コーチメッセージ列 + 新state）。
DB保存・解析実行は endpoint 側が担当し、解析結果はここに渡される。

メッセージは dict: {"role": "coach", "type": "...", "text"?: str, "payload"?: dict}
"""

from __future__ import annotations

import math
import re
from typing import Optional

from app.coaching import feedback_builder, llm
from app.coaching.persona import COACH_NAME
from app.coaching.taxonomy import diagnose_task, get_task, list_weaknesses, projection_point


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
    "pronunciation": {"icon": "🗣", "label": "発音を見る"},
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


PRONUNCIATION_KW = [
    "発音", "はつおん", "滑舌", "かつぜつ", "母音", "子音", "ディクション",
    "歌詞の言い", "歌詞の発音", "口の開き", "言葉がはっき", "言葉の明瞭",
]


def is_pronunciation_request(text: str) -> bool:
    """「発音を見て／原曲と発音を比べて」等の依頼かどうか。"""
    return any(k in text for k in PRONUNCIATION_KW)


def classify_kind(analysis: dict) -> str:
    """録音が「曲」か「基礎練(単純な発声練習)」かを音声特徴から推定する。

    基礎練（ロングトーン/ハミング/リップロール/単音スケール等）は音数が少なく音域も狭い。
    曲はメロディがあり音数・音域が広い。誤検出時の害を抑えるため「曲」寄りにバイアスする
    （曲を基礎練と誤ると「達成おめでとう」誤発火につながるため）。
    """
    pw = analysis.get("timeline", {}).get("per_window", [])
    midis = []
    for w in pw:
        f0 = w.get("f0_mean_hz")
        if f0 and f0 >= 100:
            midis.append(round(69 + 12 * math.log2(f0 / 440.0)))
    if not midis:
        return "song"
    distinct = len(set(midis))
    span = max(midis) - min(midis)
    # 明確に単純（異なる音が3つ以下 かつ 音域が4半音以下）なときだけ基礎練。
    if distinct <= 3 and span <= 4:
        return "practice"
    return "song"


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


def _harmonic_note(a: dict) -> Optional[str]:
    """整数次倍音（声の響き）の所見。声質判定に使う。"""
    hr = a.get("harmonic_ratio")
    if hr is None:
        return None
    if hr >= 0.55:
        return f"声の響き（整数次倍音）は豊かで、クリアに通る声（{hr:.2f}）。"
    if hr >= 0.35:
        return f"声の響き（整数次倍音）は芯と柔らかさのバランス型（{hr:.2f}）。"
    return f"声の響きは息まじりで柔らかめ（整数次倍音 {hr:.2f}）。芯を足すとより通る声になる。"


def _voice_brief(a: dict) -> str:
    """声の状態の短いサマリ（張りどころ・声の響き・ビブラート/揺れ）。

    歌い直し判定など、改善差分だけだと話題が偏る場面で、ビブラートや声の張りにも
    一貫して触れられるようにする。
    """
    parts = []
    proj = _projection_note(a)
    if proj:
        parts.append(proj)
    h = _harmonic_note(a)
    if h:
        parts.append(h)
    parts.append("ビブラート/揺れ: " + feedback_builder.vibrato_label(a.get("vibrato_rate_hz"), a.get("vibrato_depth_cents")))
    return " ".join(parts)


def _compare_brief(compare_data: Optional[dict]) -> str:
    """原曲アップロードがある場合、音程の正確さ(in-tune)とリズムの実測値を文章化する。

    キー差（移調）は除いて、原曲メロディからのズレを実測しているのがポイント。
    原曲が無い/対応が取れない場合は、その旨を返す（断定させないため）。
    """
    if not compare_data:
        return ""
    al = compare_data.get("alignment") or {}
    parts: list[str] = []
    it = al.get("in_tune_score")
    err = al.get("pitch_error_cents")
    if it is not None and err is not None:
        parts.append(
            f"音程の正確さ（原曲メロディとの一致）{it}点／ズレ平均{err:.0f}cents"
            "（全体のキーずれは除いて算出）"
        )
    lag = al.get("mean_lag_sec")
    if lag is not None:
        if abs(lag) < 0.05:
            parts.append("リズムは原曲とほぼ一致（走り/モタりはごくわずか）")
        elif lag > 0:
            parts.append(f"リズムは原曲よりややモタり気味（平均{lag:.2f}秒遅れ）")
        else:
            parts.append(f"リズムは原曲よりやや走り気味（平均{abs(lag):.2f}秒先行）")
        worst = al.get("worst_segments") or []
        if worst:
            w = worst[0]
            d = "モタり" if w["lag_sec"] > 0 else "走り"
            parts.append(f"特にずれが大きいのは{w['user_sec']:.0f}秒付近（{d}{abs(w['lag_sec']):.1f}秒）")
    if not parts:
        return "原曲と照合したが、うまく対応が取れず音程・リズムの実測値は出せなかった（断定しない）。"
    tail = ""
    if it is not None and it < 65:
        tail = "（※音程の正確さが低め＝原曲から音が外れている箇所が目立つので、最優先で具体的に触れること）"
    return "【原曲との照合（実測）】" + "／".join(parts) + "。" + tail


def _stretch_target(a: dict) -> tuple[str, Optional[str]]:
    """弱点が無い録音でも提示する「もっと良くできる点」: (説明文, 対応課題ID)。

    課題IDがあれば、その基礎練カード（手順＋実演動画）を一緒に出して"方法"まで示す。
    ビブラートと"揺れ(wobble)"を区別し、大きくゆっくりの揺れは「整える」でなく
    「まず一定に伸ばす」へ誘導する（声の張りとは無関係）。
    """
    vr = a.get("vibrato_rate_hz")
    depth = a.get("vibrato_depth_cents") or 0
    rng = a.get("rms_db_range")
    j = a.get("f0_jitter_cents")
    hr = a.get("harmonic_ratio")
    if vr is None:
        return ("伸ばす音に軽くビブラート（秒4〜7回の規則的なゆれ）を足すと、表現の幅が広がります。", "no_vibrato")
    if vr < 4.0 or depth > 80:
        return (
            f"伸ばした音が大きくゆっくり揺れています（秒{vr:.1f}回・幅{depth:.0f}cents）。"
            f"整ったビブラートというより不安定な揺れなので、まずは一定にまっすぐ伸ばす練習から整えましょう。",
            "pitch_wobble",
        )
    if vr > 7.5:
        return (f"ビブラートが秒{vr:.1f}回と速めなので、秒4〜7回に落ち着けると聴きやすくなります。", "no_vibrato")
    if rng is not None and rng < 15:
        return (f"強弱の幅が約{rng:.0f}dBなので、サビと静かな所の音量差を広げると物語が出ます（15dB目安）。", "expression_flat")
    if j is not None and j > 5:
        return (f"音程の細かい揺れが{j:.0f}centsなので、5cents以下を目指すとさらに安定します。", "pitch_wobble")
    if hr is not None and hr < 0.4:
        return ("声に芯（整数次倍音）を足すと、もっと前に通る声になります。ハミングで鼻に響かせる練習がおすすめ。", "throat_tension")
    return ("今の安定感を保ちつつ、もう一段高い音域や、別の曲にも挑戦すると伸びます。", None)


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
    # Voick風の声診断カード（音域・声区・ロングトーン・ビブラート・音程精度）
    out.append(coach_msg("diagnosis", payload=feedback_builder.build_voice_diagnosis_payload(analysis)))

    if task:
        prac = task["practices"][0]
        scores = fb_payload.get("scores", {})
        goods = "／".join(fb_payload.get("good_points", [])[:2])
        proj = _projection_note(analysis)
        issues = list_weaknesses(analysis, compare_data, limit=3, exclude=[avoid] if avoid else [])
        issue_lines = "\n".join(f"  ・[{w['axis']}] {w['reason']}" for w in issues) or "  ・大きな弱点は少ない"
        harm = _harmonic_note(analysis)
        cmp_brief = _compare_brief(compare_data)
        ref_note = cmp_brief if cmp_brief else (
            "原曲（お手本）が無いので、リズムの走り/モタりや音程の正確さは厳密には比較できない"
            "（手元の安定度・声の質で判断している）。原曲の音源を送ってもらえれば実測できる。"
        )
        facts = (
            "歌を解析した。\n"
            f"録音の長さ: 約{analysis.get('duration_sec', 0):.0f}秒（この秒数を超える時刻は言わない）\n"
            f"スコア(0-100): 音程{scores.get('pitch_score')} / リズム{scores.get('rhythm_score')} / 表現{scores.get('expression_score')} / 総合{scores.get('total_score')}\n"
            f"良かった点: {goods}\n"
            + (f"{harm}\n" if harm else "")
            + (f"張りどころ: {proj}\n" if proj else "")
            + f"気になる点（観点つき・優先度順）:\n{issue_lines}\n"
            + (f"{ref_note}\n" if ref_note else "")
            + f"今日の最優先課題: 「{task['label']}」。おすすめ基礎練『{prac['name']}』（目安: {prac.get('checkpoint','')}）。手順カードはこの後に表示される。"
        )
        instr = (
            "録音の講評を、発声・リズム・音感・表現(ビブラート/しゃくり等)の4観点を意識してバランスよく伝えてください。"
            "良い点と気になる点は、できるだけ具体的な秒数（と音名）を添えて話します。録音の長さを超える秒数は言わないこと。"
            "ロングトーンなど1つの観点だけに偏らないこと。音量の上下そのものは表現なので欠点にしません。"
            "『原曲との照合（実測）』がある場合は、音程の正確さ(in-tune)とリズムの走り/モタりは"
            "その実測値だけを根拠に話してください（推測で音名や正確さを断定しない）。"
            "このとき音程の話は『正確さ(原曲との一致)』を主軸にし、『安定度(揺れ)』が小さくても"
            "原曲と外れていれば『音程は完璧』とは言わないこと（安定度＝揺れの少なさ と 正確さ＝音を外していないか は別物）。"
            "実測が無い場合は『原曲を送ってもらえれば音程・リズムを正確に見られる』と一言案内すること。"
            "張りどころで声を張りきれていない場合は、どうすれば張れるか（息の支え・喉を開く）も最初に一言添えてください。"
            "最後に、今日の最優先課題の基礎練を1つだけ前向きに勧めてください。"
        )
        fallback = (
            f"今日のポイントは「{task['label']}」ですね。これに効く基礎練を用意したので、一緒にやってみましょう👇"
        )
        out.append(coach_msg("text", _llm_or(fallback, facts, instr, history)))
        out.append(coach_msg("practice", payload=feedback_builder.build_practice_payload(task)))
        out.append(coach_msg(
            "text",
            "やってみたら基礎練の録音を、もう同じ箇所を歌い直して確かめたいなら曲の録音を送ってください。"
            "発音を詳しく見たいときは「🗣 発音を見る」もどうぞ😊",
            payload=_action_chips("more_practice", "recheck_song", "pronunciation", "change_task", "finish"),
        ))
        updates = {"phase": LESSON, "current_task": task["id"], "baseline_analysis": analysis, "avoid_task": None}
    else:
        scores = fb_payload.get("scores", {})
        goods = "／".join(fb_payload.get("good_points", [])[:3])
        proj = _projection_note(analysis)
        harm = _harmonic_note(analysis)
        stretch, stretch_id = _stretch_target(analysis)
        stretch_task = get_task(stretch_id) if stretch_id else None
        cmp_brief = _compare_brief(compare_data)
        ref_note = (cmp_brief + "\n") if cmp_brief else "原曲（お手本）が無いのでリズム/音程の正確さは厳密には比較できない。\n"
        prac_line = ""
        if stretch_task:
            p0 = stretch_task["practices"][0]
            prac_line = f"次の一歩の基礎練『{p0['name']}』（手順と実演動画はこの後のカードに出る）\n"
        facts = (
            "歌を解析したが、大きな弱点は見当たらなかった。とても良い状態。\n"
            f"録音の長さ: 約{analysis.get('duration_sec', 0):.0f}秒（この秒数を超える時刻は言わない）\n"
            f"スコア(0-100): 音程{scores.get('pitch_score')} / リズム{scores.get('rhythm_score')} / 表現{scores.get('expression_score')} / 総合{scores.get('total_score')}\n"
            f"良かった点: {goods}\n"
            + (f"{harm}\n" if harm else "")
            + (f"張りどころ: {proj}\n" if proj else "")
            + f"もっと良くできる点（必ず1つ伝える）: {stretch}\n"
            + prac_line
            + ref_note
        )
        instr = (
            "発声・リズム・音感・表現の4観点に軽く触れて、良い状態であることを一緒に喜んでください。"
            "良い点は秒数（と音名）を添えて具体的に。録音の長さを超える秒数は言わないこと。"
            "必ず最後に『もっと良くできる点』を1つ、具体的な数値を添えて伝え、褒めて終わらせないこと。"
            "改善提案は1つの技術に絞り、無関係な技術（声の張りとビブラート等）を結びつけないこと。"
            + ("基礎練を勧めるときは『この後のカードに手順と動画があります』と一言添える。" if stretch_task else "")
        )
        fallback = "大きな弱点は見当たりませんでした！とてもいい状態ですよ✨ さらに伸ばすなら、下の基礎練に挑戦してみましょう。"
        text_msg = coach_msg("text", _llm_or(fallback, facts, instr, history))
        if stretch_task:
            out.append(text_msg)
            out.append(coach_msg("practice", payload=feedback_builder.build_practice_payload(stretch_task)))
            out.append(coach_msg(
                "text", "やってみたら基礎練の録音を送ってください。発音を見たいときは「🗣 発音を見る」もどうぞ😊",
                payload=_action_chips("more_practice", "recheck_song", "pronunciation", "finish"),
            ))
            updates = {"phase": LESSON, "current_task": stretch_task["id"], "baseline_analysis": analysis, "avoid_task": None}
        else:
            text_msg["payload"] = _action_chips("recheck_song", "finish")
            out.append(text_msg)
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
    state: dict, analysis: dict, history: Optional[list[dict]],
    compare_data: Optional[dict] = None,
) -> tuple[list[dict], dict]:
    """同じ箇所の歌い直し → 初回との改善判定（基礎練確認を飛ばしたい人向け）。"""
    out: list[dict] = []
    baseline = state.get("baseline_analysis") or {}
    next_task = diagnose_task(analysis, None, exclude=[state.get("current_task")])
    progress = feedback_builder.build_progress_payload(baseline, analysis, next_task)
    out.append(coach_msg("progress", payload=progress))
    brief = _voice_brief(analysis)
    cmp_brief = _compare_brief(compare_data)
    if cmp_brief:
        brief = brief + " " + cmp_brief

    if progress["improved"]:
        praise = progress.get("praise") or "最初より良くなっています。"
        if next_task:
            facts = (
                f"歌い直しの結果、最初の録音より改善した。{praise}\n"
                f"今回の声の状態: {brief}\n"
                f"次に伸ばせそうな弱点: 「{next_task['label']}」（根拠: {next_task['reason'](analysis, None)}）。"
            )
            instr = (
                "良くなった点を具体的に伝えて一緒に喜び、次のおすすめ課題をやんわり提案してください。"
                "ビブラートや声の張り（張りどころ）にも、状態に応じて自然に触れてよい。"
                "続けるか別のことをするかはユーザーが選べる雰囲気で。"
            )
            fallback = f"いい調子ですね😊 次は「{next_task['label']}」がおすすめです。続けますか？それとも別のことをしますか？"
            out.append(coach_msg("text", _llm_or(fallback, facts, instr, history)))
            out.append(coach_msg("practice", payload=feedback_builder.build_practice_payload(next_task)))
            out.append(coach_msg("text", "下のボタンからも選べます👇",
                                 payload=_action_chips("more_practice", "recheck_song", "change_task", "finish")))
            updates = {"phase": LESSON, "current_task": next_task["id"], "baseline_analysis": analysis}
        else:
            facts = f"歌い直しの結果、最初より改善し、大きな弱点はほぼ無くなった。{praise}\n今回の声の状態: {brief}"
            instr = "改善を大いに喜び、ビブラートや声の張りの状態にも一言触れつつ、今日はここまででも別の曲でも続けられると前向きに伝えてください。"
            fallback = "弱点がかなり減りましたね！素晴らしいです✨ 今日はここまででも、別の曲でも続けられますよ🎶"
            out.append(coach_msg("text", _llm_or(fallback, facts, instr, history),
                                 payload=_action_chips("recheck_song", "finish")))
            updates = {"phase": DONE}
    else:
        facts = f"歌い直したが、初回と比べて大きな改善はまだ出ていない。\n今回の声の状態: {brief}"
        instr = "落ち込ませないよう励まし、ビブラートや声の張りの状態にも一言触れつつ、もう少し基礎練を続けるか別の課題に変えるかを優しく提案してください。"
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
        return _audio_recheck(state, analysis, history, compare_data)
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
