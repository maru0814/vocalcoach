"""
コーチングループのルールエンジン（Phase A〜E の状態機械）。

副作用なし: 入力（session状態 dict + ユーザー入力）→ 出力（コーチメッセージ列 + 新state）。
DB保存・解析実行は endpoint 側が担当し、解析結果はここに渡される。

メッセージは dict: {"role": "coach", "type": "...", "text"?: str, "payload"?: dict}
"""

from __future__ import annotations

import math
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Optional

from app.core.config import settings

from app.coaching import feedback_builder, llm
from app.coaching.persona import COACH_NAME
from app.coaching.taxonomy import (
    _ref_has_vibrato,
    diagnose_task,
    get_task,
    list_weaknesses,
    projection_point,
)


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
            "まずは【①どの曲の・②どこ（区間）】を練習したいか教えてください。\n"
            "原曲のYouTube URLと区間（例: 0:48-1:13 や「サビ」）を送ってもらえると、"
            "原曲と照らし合わせて具体的にアドバイスできます😊\n"
            "（曲を決めずに、まず歌って相談だけでもOKです）",
        ),
        coach_msg(
            "text",
            "曲と箇所が決まったら、その同じところを歌って録音を送ってください🎤\n"
            "下の🎙ボタンでその場録音、または📎で音源をアップロードできます。\n\n"
            "気になることを先に教えてくれてもOKです（高音の力み／音程／リズム／表現 など）。",
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


_LLM_POOL = ThreadPoolExecutor(max_workers=4)


def _llm_or(text_fallback: str, facts: str, instruction: str, history: Optional[list[dict]]) -> str:
    """LLM で自然文コメントを生成。失敗/タイムアウト時はテンプレ文へフォールバック。

    録音FBに添えるコメントは「解析＋コメント」合計10秒以内に収めたい。Gemini の
    クライアント期限は最低10秒だが、ここでは別スレッドで投げて実時間 llm_coach_wait_sec
    だけ待ち、間に合わなければルールベース文を返す（遅い時に会話を止めない）。
    """
    fut = _LLM_POOL.submit(
        llm.generate_coach_comment, facts, instruction, history,
        settings.llm_coach_timeout_sec, settings.llm_coach_max_tokens,
    )
    try:
        reply = fut.result(timeout=settings.llm_coach_wait_sec)
    except FuturesTimeout:
        reply = None  # 間に合わない → フォールバック（裏のリクエストは捨てる）
    except Exception:
        reply = None
    return reply or text_fallback


PRONUNCIATION_KW = [
    "発音", "はつおん", "滑舌", "かつぜつ", "母音", "子音", "ディクション",
    "歌詞の言い", "歌詞の発音", "口の開き", "言葉がはっき", "言葉の明瞭",
]


def is_pronunciation_request(text: str) -> bool:
    """「発音を見て／原曲と発音を比べて」等の依頼かどうか。"""
    return any(k in text for k in PRONUNCIATION_KW)


_REGISTER_TERMS = ["地声", "じごえ", "裏声", "うらごえ", "ミックス", "声区", "チェスト",
                   "ファルセット", "ヘッドボイス", "ヘッド", "ミドル", "ミックスボイス"]
_REGISTER_Q = ["どっち", "どちら", "判断", "聞き分け", "聴き分け", "なのに", "違う", "ちがう",
               "じゃない", "ですか", "ますか", "？", "?", "出してる", "出した", "合ってる", "正しい"]


_REGISTER_DEFN = ["とは", "なんですか", "なんでしょう", "何ですか", "ってなに", "って何",
                  "教えて", "違いは", "どう違う", "意味", "やり方", "出し方", "コツ", "練習",
                  # 「〜を強くするには」「鍛えたい」等の技術・上達系も一般会話で答える（録音判定に飛ばさない）
                  "強く", "鍛え", "習得", "上達", "どうすれ", "どうやって", "するには",
                  "出すには", "できるよう", "伸ばすには"]


def _register_both_terms(t: str) -> bool:
    """地声と裏声を並べて『どっち?』と聞いている（この録音の声区判定の強い信号）。"""
    chest = ("地声" in t or "チェスト" in t)
    head = ("裏声" in t or "ファルセット" in t or "ヘッドボイス" in t)
    return chest and head


def is_register_question(text: str) -> bool:
    """「ここは地声？裏声？」「裏声なのに地声と判断されてる」等、自分の録音の声区の聞き分け依頼/異議か。

    「ミックスボイスとは？」「裏声の出し方は？」のような一般的な質問は除外する（通常チャットへ）。
    """
    t = text or ""
    if any(k in t for k in _REGISTER_DEFN):   # 一般的な定義/方法/上達の質問は対象外（通常チャットへ）
        return False
    if _register_both_terms(t):               # 地声と裏声を並べて「どっち?」＝この録音の声区判定
        return True
    if not any(k in t for k in _REGISTER_TERMS):
        return False
    return any(k in t for k in _REGISTER_Q)


# 「直前の録音を、原曲と（指定区間で）重ねて もう一度 診断/採点して」という再診断の依頼。
REDIAGNOSE_KW = [
    "再度診断", "もう一度診断", "もう一回診断", "再診断", "診断し直", "診断しなおし",
    "再採点", "採点し直", "採点しなおし", "もう一度採点", "もう一回採点",
    "比べ直", "比較し直", "もう一度比べ", "もう一回比べ", "重ねて診断", "重ねて採点",
]


def is_rediagnose_request(text: str) -> bool:
    """「今の録音で、原曲の◯秒あたりから重ねて再度診断して」等の再診断依頼か。"""
    t = text or ""
    if any(k in t for k in REDIAGNOSE_KW):
        return True
    # 「重ねて」+ 診断系の動詞、または「もう一度/もう一回」+ 診断系
    diag_words = ("診断", "採点", "見て", "比べ", "評価", "判定")
    if ("重ね" in t or "もう一度" in t or "もう一回" in t or "再度" in t) and any(d in t for d in diag_words):
        return True
    return False


# 「（練習の）動画/見本が欲しい」依頼の検出。
# 注: 原曲URL（YouTubeリンク）はお手本の指定なので動画リクエストではない → "youtube"等は入れない。
VIDEO_KW = ["動画", "ビデオ", "見本", "手本", "やり方の映像", "実演"]
# 話題キーワード → 課題ID（複数一致時は先頭の語が出た順で判定）
TOPIC_KEYWORDS: list[tuple[str, str]] = [
    ("ミックスボイス", "mixed_voice"), ("ミックス", "mixed_voice"), ("ミドルボイス", "mixed_voice"),
    ("高音", "mixed_voice"), ("高い声", "mixed_voice"), ("裏声", "mixed_voice"),
    ("ビブラート", "no_vibrato"), ("ゆらし", "no_vibrato"), ("揺らし", "no_vibrato"),
    ("リズム", "rhythm_lag"), ("テンポ", "rhythm_lag"), ("走り", "rhythm_lag"), ("モタ", "rhythm_lag"),
    ("音程", "pitch_wobble"), ("ピッチ", "pitch_wobble"), ("音を外", "pitch_wobble"),
    ("ロングトーン", "long_tone_decay"), ("伸ば", "long_tone_decay"), ("息の支え", "long_tone_decay"),
    ("喉", "throat_tension"), ("力み", "throat_tension"), ("詰ま", "throat_tension"), ("張り", "throat_tension"),
    ("強弱", "expression_flat"), ("ダイナミ", "expression_flat"), ("表現", "expression_flat"),
]


def is_video_request(text: str) -> bool:
    """「（その練習の）動画ない？／見本が欲しい」等、参考動画カードを求める依頼か。

    URL（原曲リンク）を含む場合は、お手本の指定なので動画リクエストではない。
    """
    if "http://" in text or "https://" in text:
        return False
    return any(k in text for k in VIDEO_KW)


def detect_topic_task(text: str, history: Optional[list[dict]] = None,
                      fallback: Optional[str] = None) -> Optional[str]:
    """メッセージ→直近履歴の順に話題キーワードを探し、対応する課題IDを返す。

    「動画で何かない？」のように話題語が無いときは、直近の会話（ユーザー/コーチ）を
    新しい順に見て話題を引き継ぐ。それでも無ければ fallback（current_task）。
    """
    def scan(t: str) -> Optional[str]:
        for kw, task_id in TOPIC_KEYWORDS:
            if kw in t:
                return task_id
        return None

    hit = scan(text)
    if hit:
        return hit
    # 履歴は「ユーザー自身の発言」だけを新しい順に見る。
    # コーチの挨拶や例示（「ミックスボイス等の練習が…」）を話題と誤検出しないため。
    for msg in reversed(history or []):
        if (msg.get("role") or "") != "user":
            continue
        hit = scan(msg.get("content") or msg.get("text") or "")
        if hit:
            return hit
    return fallback


def handle_video_request(state: dict, text: str,
                         history: Optional[list[dict]] = None) -> list[dict]:
    """「動画ある？」等に、話題に合う実際の練習カード（手順＋実演動画）を確定的に返す。

    LLMに任せると「動画カードを用意しました」と言うだけでカードが出ない/別話題の動画に
    なる事故が起きるため、ここで話題判定→該当課題の練習カードを必ず一緒に出す。
    """
    task_id = detect_topic_task(text, history, fallback=state.get("current_task"))
    task = get_task(task_id) if task_id else None
    if not task:
        return [coach_msg(
            "text",
            "どの練習の動画がいいですか？😊 たとえば『ミックスボイス』『ビブラート』"
            "『リズム』『ロングトーン』『強弱』など、気になるテーマを教えてください。",
        )]
    prac = task["practices"][0]
    intro = (
        f"「{task['label']}」の参考動画ですね！下のカードに手順と実演動画をのせました。"
        f"まずは『{prac['name']}』を動画に合わせて真似してみてください😊"
    )
    return [
        coach_msg("text", intro),
        coach_msg("practice", payload=feedback_builder.build_practice_payload(task)),
    ]


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


def _resonance_note(a: dict) -> Optional[str]:
    """発声（響き）の具体箇所: どの秒数の響きが良い／硬い・弱いかを伸ばし区間から出す。"""
    holds = [s for s in (a.get("timeline") or {}).get("sustained_segments", [])
             if (s.get("mean_f0_hz") or 0) >= 100]
    if not holds:
        return None
    parts = []
    # 良い響き: 張りどころで張れていれば最優先、なければ最も長い安定した伸ばし
    pp = projection_point(a)
    if pp and pp.get("projected"):
        parts.append(f"{pp['start_sec']:.0f}〜{pp['end_sec']:.0f}秒は声が前に通って響きが良い")
    else:
        longest = max(holds, key=lambda s: s.get("duration_sec", 0))
        parts.append(f"{longest['start_sec']:.0f}〜{longest['end_sec']:.0f}秒（{feedback_builder._note_name(longest['mean_f0_hz'])}）の伸ばしは響きが安定")
    # 硬い/詰まり: 明るさ(スペクトル重心)が高い伸ばし
    hard = max(holds, key=lambda s: s.get("spectral_centroid_hz") or 0)
    if (hard.get("spectral_centroid_hz") or 0) >= 2700:
        parts.append(f"{hard['start_sec']:.0f}〜{hard['end_sec']:.0f}秒あたりは音色が硬め＝喉に力みの可能性（響きを落とさず喉を開く余地）")
    return "発声（響き）の具体箇所: " + "／".join(parts) + "。"


def _ornament_note(a: dict) -> Optional[str]:
    """表現の装飾（ビブラート/しゃくり/フォール）の検出状況を文章化する。

    表現＝強弱だけでなく、歌い回しの技法にも触れられるようにする。
    """
    orn = a.get("expression_ornaments") or {}
    vr = a.get("vibrato_rate_hz")
    parts = []
    parts.append("ビブラート: " + feedback_builder.vibrato_label(vr, a.get("vibrato_depth_cents")))
    sc, fl = orn.get("scoop_count", 0), orn.get("fall_count", 0)
    if sc:
        ex = "、".join(f"{t:.0f}秒" for t in (orn.get("scoops") or [])[:3])
        parts.append(f"しゃくり（下から当てる）を約{sc}回検出（例: {ex}）")
    else:
        parts.append("しゃくりはほぼ無し")
    if fl:
        ex = "、".join(f"{t:.0f}秒" for t in (orn.get("falls") or [])[:3])
        parts.append(f"フォール（語尾を落とす）を約{fl}回検出（例: {ex}）")
    return "表現（歌い回し）: " + "／".join(parts) + "。こぶしは自動検出していない（必要なら一般論で説明可）。"


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
    # ③ 同じ曲として照合できなかった（誤った原曲/無関係な音源など）→ 数値を断定しない
    if al.get("low_confidence"):
        return (
            "【原曲との照合】アップロードされたお手本と、歌った録音がうまく対応づきませんでした"
            "（別の曲・無関係な音源の可能性）。音程の正確さ・リズムは断定できないので、"
            "同じ曲のお手本かどうか確認を促すこと。"
        )
    parts: list[str] = []
    # ② キー差（別キーで歌っている）を検出したら共有する
    ks = al.get("key_shift_semitones")
    if ks is not None and abs(ks) >= 1:
        # key_shift はユーザーのクロマを原曲へ合わせる回転量。負＝ユーザーが高い、正＝低い。
        direction = "高い" if ks < 0 else "低い"
        parts.append(f"原曲より約{abs(ks)}半音{direction}キーで歌っている（音程の正確さはキー差を除いて評価）")
    it = al.get("in_tune_score")
    err = al.get("pitch_error_cents")
    if it is not None and err is not None:
        parts.append(
            f"音程の正確さ（原曲メロディとの一致）{it}点／ズレ平均{err:.0f}cents"
            "（全体のキーずれは除いて算出）"
        )
    # ④ 音程が外れている具体的な箇所（どこが高い/低いか）
    spots = al.get("pitch_off_spots") or []
    if spots:
        spot_txt = "、".join(
            f"{s['user_sec']:.0f}秒あたりが約{s['cents']}cents{'高い(シャープ)' if s['direction']=='sharp' else '低い(フラット)'}"
            for s in spots
        )
        parts.append(f"特に音程が外れている箇所: {spot_txt}")
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


def _stretch_target(a: dict, compare_data: Optional[dict] = None) -> tuple[str, Optional[str]]:
    """弱点が無い録音でも提示する「もっと良くできる点」: (説明文, 対応課題ID)。

    優先順位は 発声 → 音程 → 強弱(表現) → ビブラート。
    ビブラートは「多ければ良い」ものではないので、原曲(お手本)にビブラートがあって
    ユーザーが再現できていない時だけ最後に提案する（原曲が無ければ提案しない）。
    """
    vc = (compare_data or {}).get("voice_compare") or {}
    h = a.get("h1h2_db")
    sf = a.get("singers_formant_ratio")
    j = a.get("f0_jitter_cents")
    lts = a.get("long_tone_stability")
    # 1) 声帯の閉じ（息漏れ/締めすぎ）— 原曲比較を優先
    clo = vc.get("closure")
    if (clo and clo.get("verdict") == "breathier") or (h is not None and h >= 10):
        return ("声に少し息が混じり気味なので、ストロー発声で声帯の閉じを揃えると、同じ息でもっと前に鳴ります。", "breathy_closure")
    if (clo and clo.get("verdict") == "pressed") or (h is not None and h <= -1):
        return ("やや締めすぎ気味なので、リップロールで力を抜くと、楽に響く声に近づきます。", "throat_tension")
    # 2) 響き（前に集める）
    ring = vc.get("ring")
    if (ring and ring.get("verdict") == "weaker") or (sf is not None and sf < 0.004):
        return ("響きをもう少し前（鼻〜前歯）に集めると、芯が出てさらに前に通る声になります。ハミング→母音の練習がおすすめ。", "weak_resonance")
    # 3) 高音の声区（原曲はミックスなのに地声で押し上げ）
    rh = vc.get("register_high")
    if rh and rh.get("verdict") == "differ" and rh.get("user") == "chest" and rh.get("ref") in ("mix", "head"):
        return ("高音を原曲はミックスで運んでいます。地声で押し上げず軽く前に当てると、もっと楽に届きます。", "mixed_voice")
    # 4) 支え（伸ばしの安定）
    if lts is not None and lts > 30:
        return (f"伸ばした音が後半で少し動きます（{lts:.0f}cents）。息の支えを一定にするとまっすぐ保てます。", "long_tone_decay")
    # 5) 音程の細かい揺れ
    if j is not None and j > 10:
        return (f"音程の細かい揺れが{j:.0f}centsなので、まっすぐ保つともっと安定して聞こえます（15cents以下が目安）。", "pitch_wobble")
    return ("今の発声バランスを保ちつつ、もう一段高い音域や別の曲にも挑戦すると伸びます。", None)


_REG_JP = {"chest": "地声", "mix": "ミックス", "head": "裏声"}


def _voice_facts(analysis: dict, c: Optional[dict]) -> str:
    """録音FBコーチ文用の『発声の事実』。声帯の閉じ・響き・声区・音程（原曲比較込み・docs/21）。"""
    lines: list[str] = []
    h = analysis.get("h1h2_db")
    if h is not None:
        cl = "息漏れ気味（声帯の閉じがゆるめ）" if h >= 8 else ("締めすぎ気味（力みに注意）" if h <= 1 else "効率の良いバランス(flow phonation)")
        lines.append(f"声帯の閉じ・息の効率: {cl}（H1-H2≈{h:.0f}dB・目安）")
    sf = analysis.get("singers_formant_ratio")
    if sf is not None:
        r = "前に通る芯のある響き" if sf >= 0.008 else ("標準的な響き" if sf >= 0.003 else "やわらかい響き（前に集めると通る）")
        lines.append(f"響き(シンガーズフォルマント=声の芯・通り): {r}")
    vc = (c or {}).get("voice_compare") or {}
    if vc.get("ring"):
        v = {"weaker": "原曲より響きが弱め（前に集めたい）", "richer": "原曲と同等以上の響き", "match": "原曲と同程度の響き"}.get(vc["ring"]["verdict"])
        lines.append(f"原曲との響き比較: {v}")
    if vc.get("closure"):
        v = {"breathier": "原曲より息漏れ寄り（閉じがゆるい）", "pressed": "原曲より締めすぎ寄り（力み）", "match": "原曲と同じくバランスの良い閉じ"}.get(vc["closure"]["verdict"])
        lines.append(f"原曲との声帯の閉じ比較: {v}")
    rh = vc.get("register_high")
    if rh:
        if rh["verdict"] == "match":
            lines.append(f"高音の声区: 原曲と同じ{_REG_JP.get(rh['ref'], rh['ref'])}で運べている")
        else:
            lines.append(f"高音の声区: あなたは{_REG_JP.get(rh['user'], '?')}、原曲は{_REG_JP.get(rh['ref'], '?')}（原曲に寄せる余地）")
    al = (c or {}).get("alignment") or {}
    if al.get("in_tune_score") is not None:
        lines.append(f"原曲との音程の一致: {al['in_tune_score']}点（音を外していないかの実測。安定度とは別物）")
    lts = analysis.get("long_tone_stability")
    if lts is not None:
        lines.append(f"伸ばしの安定（息の支え）: {lts:.0f}cents（小さいほど安定）")
    return "\n".join(lines)


def _voice_dx_block(analysis: dict, compare_data: Optional[dict]) -> str:
    """発声の検知課題＋処方候補(RAG)を facts に注入する（資料準拠）。失敗時は空。"""
    try:
        from app.coaching import voice_coach
        return voice_coach.build_llm_block(analysis, compare_data)
    except Exception:
        return ""


_VOICE_INSTR = (
    "あなたは世界最高峰のボイストレーナーです。発声だけに絞って講評してください（リズム・抑揚・しゃくり/こぶし等の表現技法は扱わない）。"
    "これは録音への“詳しい”講評なので、チャットの短さ制限は外し、5〜8文でしっかり解説してよい（ただし冗長や繰り返しは避け、1文1メッセージで明快に）。"
    "次の流れで書く: "
    "(1)【良い点】具体的に1つ褒める（数値や音域・秒数を添えて）。"
    "(2)【今の声の状態＝客観診断】与えられた発声指標を“噛み砕いて”説明する。例:『声の芯(CPP)が◯dBで〜』『声帯の閉じ(H1-H2)が◯dBで息が少し漏れ気味』『声のクリアさ(HNR)が◯dB』。数値は与えられたものだけを使い、各指標に必ず一言の補足を付ける。"
    "(3)【根本原因】表面の力み/息漏れで止めず、息の支え(アッポッジョ)・喉頭懸垂機構(アンザッツ)・共鳴(フォルマント)の観点で“なぜそうなるか”を一言で。"
    "(4)【処方＝具体的な打ち手】処方候補(★推奨)から1つ選び、『なぜ効くか(メカニズム)』と『どうやるか(身体の感覚・響かせる位置・口の形・母音)』をていねいに。"
    "原曲比較の事実があれば必ず根拠に使う。音程を外した箇所が事実にあれば『何秒が何centひくい/高い』と具体的に（録音の長さを超える秒は言わない）。"
    "声区は音響からの推定であり、ユーザーが裏声等の感覚を述べたら断定せず尊重する。事実に無い数値・秒数・声区・処方は作らない。"
    "練習は一度すすめたら基本そのまま続けるよう導き、毎回別の練習名に変えない。"
    "最後に基礎練を1つだけ前向きに勧める（基礎練カードが一緒に出る時だけ『この後のカードに手順と動画があります』と添える）。"
)


# 発声診断(voice_coach)の課題 → 対応する基礎練タスク（動画つき）
_ISSUE_TASK = {
    "pulled_chest": "mixed_voice",
    "breathy": "breathy_closure",
    "lack_resonance": "weak_resonance",
    "unstable_support": "long_tone_decay",
    "mix_incoordination": "mixed_voice",
    "artificial_vibrato": "pitch_wobble",
}


def _voice_issue_task(analysis: dict, compare_data: Optional[dict], exclude: list):
    """発声診断(資料ベース)の主課題を、対応する基礎練タスクに対応づける。"""
    try:
        from app.coaching import voice_coach
        for iss in voice_coach.diagnose(analysis, compare_data):
            tid = _ISSUE_TASK.get(iss["id"])
            if tid and tid not in (exclude or []):
                t = get_task(tid)
                if t:
                    return t
    except Exception:
        pass
    return None


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

    # 録音できている限り、必ず「課題＋基礎練（動画つき）」を1つ提示する（ユーザー要望）。
    # 弱点が検知されなくても、発声診断の主課題→次の磨きどころ→既定ドリル の順で必ず確定させる。
    if task is None:
        task = _voice_issue_task(analysis, compare_data, exclude)
    if task is None:
        _, _sid = _stretch_target(analysis, compare_data)
        task = get_task(_sid) if _sid else None
    if task is None:
        for _tid in ("weak_resonance", "long_tone_decay", "mixed_voice"):
            if _tid not in exclude:
                task = get_task(_tid)
                if task:
                    break

    # 採点カード1枚に集約（声の特徴も payload.voice_profile に同居。別の声診断カードは出さない）
    ref_attempted = bool(state.get("song_ref_url") or state.get("song_ref_path"))
    fb_payload = feedback_builder.build_feedback_payload(
        analysis, compare_data, task, ref_attempted=ref_attempted
    )
    out.append(coach_msg("feedback", payload=fb_payload))

    if task:
        prac = task["practices"][0]
        goods = "／".join(fb_payload.get("good_points", [])[:2])
        headline = fb_payload.get("headline", "")
        facts = (
            "歌を発声の観点で解析した。\n"
            f"録音の長さ: 約{analysis.get('duration_sec', 0):.0f}秒（この秒数を超える時刻は言わない）\n"
            f"発声の一言総評: {headline}\n"
            f"良かった点: {goods}\n"
            + _voice_facts(analysis, compare_data) + "\n"
            + _voice_dx_block(analysis, compare_data) + "\n"
            + f"今日の最優先課題: 「{task['label']}」。おすすめ基礎練『{prac['name']}』（目安: {prac.get('checkpoint', '')}）。手順カードはこの後に表示される。"
        )
        instr = _VOICE_INSTR
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
        goods = "／".join(fb_payload.get("good_points", [])[:3])
        headline = fb_payload.get("headline", "")
        stretch, stretch_id = _stretch_target(analysis, compare_data)
        stretch_task = get_task(stretch_id) if stretch_id else None
        prac_line = ""
        if stretch_task:
            p0 = stretch_task["practices"][0]
            prac_line = f"次の一歩の基礎練『{p0['name']}』（手順と実演動画はこの後のカードに出る）\n"
        facts = (
            "歌を発声の観点で解析した。大きな弱点は少なく、とても良い状態。\n"
            f"録音の長さ: 約{analysis.get('duration_sec', 0):.0f}秒（この秒数を超える時刻は言わない）\n"
            f"発声の一言総評: {headline}\n"
            f"良かった点: {goods}\n"
            + _voice_facts(analysis, compare_data) + "\n"
            + _voice_dx_block(analysis, compare_data) + "\n"
            + f"もっと良くできる発声の点（必ず1つ伝える）: {stretch}\n"
            + prac_line
        )
        instr = (
            _VOICE_INSTR
            + "今回は大きな弱点が少ない良い状態なので、まず一緒に喜びつつ、それでも『もっと良くできる発声の点』を必ず1つ具体的に伝える。"
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
            # 基礎練カードを出さないので、テキストの「カードに手順があります」約束は消す
            text_msg["text"] = llm.scrub_card_promise(text_msg.get("text"))
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
