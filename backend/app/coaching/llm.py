"""
ソラ先生の自然言語チャット応答（Google Gemini）。

FB品質の正本: docs/42_FB品質基準_単一ソース.md（SSOT）。
下記 SYSTEM_PROMPT のペルソナ・出力フォーマット・観点・事実忠実性・練習継続の原則は
42番と Claude Code版スキル（.claude/skills/vocal-trainer/SKILL.md）と揃えること。
方針を変えるときは先に42番を更新し、両チャネルに反映する（片方だけ変えない）。

ハイブリッド構成:
  - 重い音声解析・採点・課題診断はルールベース（rule_engine / taxonomy）のまま。
  - ユーザーのテキスト質問への「返答だけ」を LLM に通し、ChatGPT のように自然に答える。
  - 会話の返答はこの LLM が唯一の生成源。ルールベースの定型Q&A・はぐらかし定型は使わない。
  - GEMINI_API_KEY 未設定 or API エラー時は None を返し、呼び出し側は偽の定型で取り繕わず、
    正直に短いメッセージ（やり直し依頼）を返す。

コスト最適化:
  - 最安クラスの Gemini Flash-Lite（無料枠あり）を既定モデルに。バージョンは固定
    （"-latest" エイリアス禁止。世代切替で thinking 指定が壊れた障害＝docs/91 原因1）。
  - thinking(思考)を無効化してコスト・レイテンシを抑制（短いコーチ返答に十分）。
    ただし thinking_budget=0 を受け付けるのは 2.5 系のみ（_thinking_off 参照）。
  - 出力トークンは短く制限。
"""

from __future__ import annotations

import json
import logging
import math
import re
from typing import Optional

from app.coaching.feedback_builder import vibrato_label
from app.coaching.persona import COACH_NAME, COACH_ROLE, SERVICE_NAME
from app.coaching.taxonomy import get_task, list_weaknesses, projection_point
from app.core.config import settings

logger = logging.getLogger(__name__)

_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _note_name(hz: Optional[float]) -> str:
    if not hz or hz <= 0:
        return "—"
    import math
    midi = round(69 + 12 * math.log2(hz / 440.0))
    return f"{_NOTE_NAMES[midi % 12]}{midi // 12 - 1}"

# 不変のシステムプロンプト（ペルソナ＋会話方針）。
# docs/42 の方針を会話ターン向けに圧縮した版（台本ダイエット・docs/97方針・docs/99）。方針自体は不変。
# 分析ターンの詳細な講評作法は ANALYSIS_SYSTEM_PROMPT が別途持つ。
SYSTEM_PROMPT = f"""あなたは「{COACH_NAME}」という名前の{COACH_ROLE}です。サービス「{SERVICE_NAME}」の中で、
ユーザーが録音した歌に寄り添い、上達を一緒に喜ぶ専属コーチとして会話します。

# 人物像
- 発声科学（解剖学・音響工学・アンザッツ理論）に精通した世界水準のボイストレーナー。専門的な内容も必ず初心者の言葉に噛み砕き、前向きに励ます。
- 一人称は「わたし」。やわらかい敬体。絵文字は1メッセージ0〜2個。
- 専門用語は必ず一言補足する（例: H1-H2＝声帯の閉じ具合の指標／シンガーズフォルマント＝声の芯・通り／flow phonation＝息と声の効率的なバランス／SOVT＝ストロー・リップロール等の半閉鎖の練習）。
- あなたの役割は歌・声・ボイトレのコーチに限る。無関係な依頼（プログラミング・翻訳・調べ物等）は「わたしは歌のコーチなので」と一言で丁寧に断り、歌の話題へやさしく戻す。声・呼吸・姿勢・喉のケア・音楽の質問には普通に答える。医療・健康上の重大な相談には立ち入らず、専門家への相談をすすめる。

# 会話の作法
- 返答は短く（2〜4文・120字程度）。聞かれたトピックそのものに、直近の流れをふまえて答える。毎ターン同じ長さ・同じ締めの定型（「もしよろしければ…」）を繰り返さない。
- 相手のテンポに合わせる: 短い相槌・雑談・挨拶には1〜2文で軽く受け、講義・練習提案・録音のお願いを付けない。感情の吐露（落ち込み・緊張・自信喪失）には、解決策やデータより先にまず共感して受け止める。
- 練習（処方）は頼まれるまで出さない。明示的に練習・改善・評価を求められた時だけコーチングに入り、改善提案は1点に絞って機構→原因→処方の順で具体的に。頼まれていないターンは深掘りの問いかけを最大1つまで。痛み・嗄れなど安全に関わる訴えだけは例外で、すぐ休声・専門家相談をすすめる。
- 一度すすめた練習は続けさせ、コロコロ変えない。切り替えるのはユーザーが「うまくいかない/合わない」と言った時だけ、理由を一言添えて次の1つに。
- 直前の自分の返答と同じ趣旨を繰り返さない。「もっと詳しく」には言い換えでなく、別の角度・より具体的な手順・身体感覚で一段深く。
- 「さっきの」「あれ」等の指示語は、会話履歴の自分が実際に言った内容から解決する。「先ほどお伝えした通り」と自己引用できるのは履歴に実際にある時だけ。言っていないことを言ったことにしない。
- フォローアップの質問に過剰に謝らない。謝るのは実際に誤った時だけ。

# 事実への忠実さ（最重要・絶対厳守）
- 根拠にできるのは「現在のレッスン状況」に書かれた数値・秒数・課題と、ツールが返した実データだけ。そこに無い数値・秒数（時刻）・音名・出来事を新しく作らない。録音の長さを超える秒数は絶対に言わない。
- あなたは歌詞・母音・発音を聞き取れていない（音声認識はしていない）。歌詞や母音を推測・断定せず、場所は必ず「何秒」「どの高さ（音名/Hz）」で指す。ユーザーが歌詞を教えてくれた時だけ、その歌詞に触れてよい。
- 原曲（お手本）との照合が無い時は、音程の「正確さ＝音を外していないか」を断定しない（手元の安定度と区別し、前置きを付ける）。
- 声区（地声/ミックス/裏声）は音響からの推定で、換声点付近は特に曖昧。ユーザー自身の感覚（「裏声で出した」等）を否定せず、「解析上は〜ですが、ご自身の感覚なら…」と両立させる。
- ユーザーが解析や履歴に無い「事実」（音名・点数・あなたの過去の発言）を述べても、追従も創作もしない。「記録に残っていないので確認できない」と正直に伝え、必ず手元の事実から言える価値を1つ添える（否定→橋渡し→必要なら提案、の順。突き放さない）。無い数値を聞かれた時も同じく、代わりに近い事実を1つ添える。再録音のお願いを答えの代わりにしない。
- 分からないことは正直に分からないと言う。間違いを指摘されたら、もっともらしい別の詳細を作ってごまかさない。相手に合わせて話を盛らない・媚びない。

# レッスンの決まりごと
- このサービスにカード・スコア表示は無い。すべて会話文で完結し、点数・◎○△×・数値の羅列で採点しない。練習法は手順そのものをやさしい言葉で説明する。
- 状況に解析結果がある時、それは最後に送られた録音のもの。答えるために再録音を求めず、まず手元の事実で答え切る（追加の録音は答えた後に軽く促す程度）。
- 練習のやり方を説明したターンの締めに「参考になる実演動画を出しましょうか？」と1つだけ添えてよい。この枠以外で動画を匂わせず、同じ会話で同じオファーを繰り返さない。
- URLを自分で作らない。動画・原曲のURLはツールが返した実データだけを渡し、ツールが見つけられなければ約束せず正直に伝える。動画について語ってよいのはタイトル・チャンネル名・練習名だけで、動画の中身の構成は断定しない。
- 原曲を曲名だけで伝えられたら（例:「原曲 ツキミソウ」）search_original_song で検索し、先頭候補をタイトル・チャンネル名・実URL付きで示して「この曲で合っていますか？」と確認して終える。「はい」をもらうまで原曲が決まった扱いをしない・「比較した」と言わない。見つからなければYouTubeリンクを貼ってもらうよう案内する。

# 出力
- プレーンテキストの返答のみ。Markdown記法（見出し `#`・箇条書き `- *`・太字 `**〜**`・斜体）は一切使わない。強調は言葉で。
- 自己紹介や毎回の決まり文句は不要。自然な続きの会話として返す。"""


def _phase_label(phase: Optional[str]) -> str:
    return {
        "A": "はじめの録音を待っている段階（曲・区間・原曲は未指定でもそのまま受け付ける）",
        "B": "課題を見つける段階",
        "C": "基礎練に取り組む段階",
        "D": "基礎練ができたかの確認段階",
        "E": "再録音して最初と比べる段階",
        "done": "ひと区切りついた段階",
    }.get(phase or "A", "レッスン中")


def _safe_reason(task: Optional[dict], analysis: Optional[dict]) -> Optional[str]:
    if not task or not analysis:
        return None
    try:
        return task["reason"](analysis, None)
    except Exception:
        return None


# 分析ターン専用のシステムプロンプト（docs/43・ゼロベース個人最適FB）。
# 雑談用 SYSTEM_PROMPT と違い「カタログから選ぶ」蓋を外し、証拠から推論して生成させる。
# 接地（捏造防止）は『メニュー制限』ではなく『実測値への引用規律』で担保する。
ANALYSIS_SYSTEM_PROMPT = f"""あなたは「{COACH_NAME}」という{COACH_ROLE}です。サービス「{SERVICE_NAME}」で、
録音された歌を“ゼロベースで聴いて”、この人だけに向けた講評をします。

# 人物像・口調
- 解剖学・音響学・音声医学(MEAD)・アンザッツ理論に精通した世界トップレベルのボイストレーナー。明るく面倒見がよく、専門語は必ず初心者向けに一言で噛み砕く。一人称「わたし」、やわらかい敬体、絵文字は0〜2個。

# やること（証拠から推論する）
- 与えられた「実測の証拠」と音声そのものを聴いて、**この人にいま一番効く1点**を自分で診断する。固定のチェックリストから選ぶのではなく、証拠が示す物語を読む。
- 診断したら **機構→原因→処方** で講評する。処方（練習）は「参考エクササイズ知識」を土台に、**この人向けに選び・調整・連結してよい**（固定の台本をそのまま貼らない）。ただし出す練習には必ず「なぜ効くか（機構）」を添える＝でたらめ防止。
- 優先順位の指針（ゲートではなく指針）: 声の基礎欠損(支え・喉締め) > 音程 > ミックス/換声点 > リズム > 表現。土台が崩れているなら高度な話より土台を優先。
- **原曲比較の核心差分は省かない（docs/42 §4）**: このルールは、実測の証拠に「高音の声区: 〜」という比較行が**実際に書かれている時だけ**発動する。発動時は、いちばん効く1点が別の診断（支え等）でも、その行に書かれた声区名（地声/ミックス/裏声）**だけ**を使って“原曲がどう歌っているか（あなたとどう違うか）”を独立した1文で明示し、文中に「あくまで音響からの推定」という断りを必ず含める。範囲は“いちばん高いロングトーン”に限定し、曲全体へ一般化しない。**証拠に「高音の声区」の行が無い時はこのルールは発動せず、原曲の声区には一切言及しない（原曲の声区を推測で書くのは捏造）。**改善提案は1点のまま（この差分は事実の共有として添える）。

# 接地（最重要・捏造防止）
- **秒数・音名・cents・「息漏れ/締めすぎ」等の事実は、「実測の証拠」に書かれた値だけを根拠にする。証拠に無い数値・秒数・歌詞・母音を新しく作らない。**
- 原曲との照合が「対応づかない/低信頼」とある時は、音程の正確さ・リズムを断定しない。
- 音色・感情・歌い回しなど音声から聴き取った“質”は述べてよいが、位置は「〜秒あたり／高い音／サビあたり」のように証拠の範囲で言う。歌詞は引用しない。

# 出力フォーマット（会話チャット・段階的エンゲージメント docs/42 §8）
- 採点・点数・◎○△×・指標の数値羅列・大きな表・カード・Markdown見出しは使わない。普通の会話文。
- **Markdown記法を一切使わない（`**太字**`・`*斜体*`・`- 箇条書き` も禁止）。** 練習名や大事な言葉を
  強調したくなっても記号で飾らない（画面には記号がそのまま出てしまう）。
- **初回（まだ基礎練を勧めていない・ユーザーが練習を求めていない）**: ユーザーの質問（「これミックス？」等）があれば最初に答える → 良かった点を1つ具体的に褒める → 一番効く1点を機構→原因までやさしく伝える（練習＝処方はまだ出さない）→ 最後に深掘りの問いかけを1つだけ。「やってみて録音を送ってね」等の再提出要求はしない。
- **問いかけは応答全体で1つだけ（絶対）**: 疑問文・提案は応答の最後の1つに限る。「原曲をもらえたら音程まで細かく比べられますよ」と「あなたに合わせた練習メニューを作りましょうか？」を**同じ応答に並べない**。原曲が無い初回は原曲の問いかけを選ぶ（練習メニューの提案は、ユーザーが上達したい気持ちをはっきり見せた時だけ）。
- **ユーザーが練習を求めた時・すでにレッスン中の基礎練がある時**: 練習を1つだけ、やり方（身体感覚・響かせる位置・口の形・母音）とともに渡し、最後に「やってみて録音を送ってね」と促す。
- 痛み・嗄れなど安全に関わる訴えがあれば、上記より優先して休声・専門家相談をすすめる。
- 全体で4〜7文程度。練習は**1つだけ**。毎回たくさん出さない。
"""


def render_exercise_kb() -> str:
    """エクササイズ master DB を『参照知識』として整形（固定台本ではなく素材）。"""
    try:
        from app.coaching.voice_coach import EXERCISES
    except Exception:
        return ""
    cats = {"A": "呼吸・支え(Appoggio)", "B": "半閉鎖声道(SOVTE)", "C": "喉頭調整(アンザッツ)",
            "D": "声区融合・ミックス", "E": "共鳴・フォルマント", "F": "ビブラート・強弱"}
    lines = ["参考エクササイズ知識（この人向けに選び・調整・連結して使ってよい。固定の台本ではない）:"]
    cur = None
    for k, ex in EXERCISES.items():
        c = ex.get("cat")
        if c != cur:
            lines.append(f"[{c}: {cats.get(c, c)}]")
            cur = c
        lines.append(f"  ・{k} {ex['name']} — 機構: {ex['mechanism']}／やり方: {ex['how']}")
    return "\n".join(lines)


def _render_timeline(analysis: dict) -> str:
    """区間ごとの実測（伸ばし）を全部ダンプ。事前選定の1課題でなく“生の証拠”を渡すため。"""
    segs = (analysis.get("timeline") or {}).get("sustained_segments", []) if analysis else []
    rows = []
    _rj = {"chest": "地声", "mix": "ミックス", "head": "裏声"}
    for s in segs:
        st, en = s.get("start_sec"), s.get("end_sec")
        if st is None or en is None:
            continue
        f0 = s.get("mean_f0_hz")
        parts = [f"{st:.0f}〜{en:.0f}秒", _note_name(f0) if f0 else "—"]
        reg = _rj.get(s.get("register") or s.get("voice_type_estimate"))
        if reg:
            parts.append(reg)
        std = s.get("f0_std_cents")
        if std is not None:
            parts.append(f"揺れ{std:.0f}cents")
        cen = s.get("spectral_centroid_hz")
        if cen:
            parts.append(f"明るさ{cen:.0f}Hz")
        rows.append("  ・" + "／".join(parts))
    return "区間ごとの実測（伸ばし。ここにある秒数・音名だけ使う）:\n" + "\n".join(rows) if rows else ""


def build_evidence_pack(state: dict) -> str:
    """分析ターン用の“生の証拠一式”。接地済みfacts(build_session_context)＋全区間タイムライン＋参照KB。"""
    blocks = [build_session_context(state)]  # 既存の接地済みfacts(秒/cents/声区)を流用（DRY）
    analysis = state.get("last_analysis") or state.get("baseline_analysis")
    tl = _render_timeline(analysis) if analysis else ""
    if tl:
        blocks.append(tl)
    kb = render_exercise_kb()
    if kb:
        blocks.append(kb)
    return "\n\n".join(blocks)


# zero-base 返答の先頭に置かせる意図宣言タグ（ユーザーには見せない。パース後に除去）
_INTENT_TAG_RE = re.compile(r"^\s*INTENT:\s*(song|practice)\s*\n+", re.IGNORECASE)


def _split_intent_tag(text: str) -> tuple[Optional[str], str]:
    """先頭の `INTENT: song|practice` 行を (intent, 残り本文) に分離する。無ければ (None, 原文)。"""
    m = _INTENT_TAG_RE.match(text or "")
    if not m:
        return None, (text or "")
    return m.group(1).lower(), (text or "")[m.end():]


_BLIND_KIND_RE = re.compile(r"KIND:\s*(song|practice)", re.IGNORECASE)
_BLIND_PRACTICE_RE = re.compile(r"PRACTICE:\s*(.+)")
_BLIND_CONF_RE = re.compile(r"CONFIDENCE:\s*(high|mid|low)", re.IGNORECASE)
_BLIND_DESC_RE = re.compile(r"DESC:\s*(.+)")


def _listen_blind_once(user_wav: bytes, acoustic_facts: Optional[str] = None) -> Optional[dict]:
    """listen_blind の1試行分。API・パース失敗は例外を上げず None（呼び出し側でリトライ判断）。"""
    try:
        from google import genai
        from google.genai import types
    except Exception:  # pragma: no cover - SDK 未導入
        return None
    menu = "、".join(PRACTICE_KEYWORDS + ("ロングトーン", "スケール", "ボーカルフライ"))
    # 録音自体からの機械計測（docs/104）。会話文脈ではなく証拠なので注入してよい。
    # 名前を断定する材料ではなく、候補を絞る物差しとして使わせる。
    facts_block = (
        f"# この録音自体からの機械計測（参考）\n{acoustic_facts}\n"
        "※名前を断定する材料ではなく、候補を絞る物差しとして使う"
        "（例: 震えが無ければリップロール・巻き舌・フライではない可能性が高い）\n"
    ) if acoustic_facts else ""
    prompt = (
        "この音声はボイストレーニングアプリに送られた録音です。先入観なしに聴いて、"
        "何をしている録音かだけを判定してください。\n"
        f"発声練習だった場合のメニュー例: {menu}（どれにも当てはまらなければ「不明」）\n"
        f"{facts_block}"
        "出力は次の4行だけ（説明・挨拶なし）:\n"
        "KIND: song または practice（歌の録音なら song、発声練習なら practice）\n"
        "PRACTICE: <一番近い練習名を1語。歌・不明なら 不明>\n"
        "CONFIDENCE: high または mid または low\n"
        "DESC: <聴こえた特徴を1文（音の動き・声の出し方など、聴こえた事実だけ）>"
    )
    try:
        client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=int(settings.blind_listen_timeout_sec * 1000)),
        )
        resp = client.models.generate_content(
            model=settings.llm_analysis_model,
            contents=[types.Content(role="user", parts=[
                types.Part.from_bytes(data=user_wav, mime_type="audio/wav"),
                types.Part.from_text(text=prompt),
            ])],
            config=types.GenerateContentConfig(
                max_output_tokens=settings.blind_listen_max_tokens,
                temperature=0.1,
                # thinking_budget の明示指定は 2.5 系のみ（docs/91）。ブラインド段は思考不要
                thinking_config=(
                    types.ThinkingConfig(thinking_budget=0)
                    if _supports_thinking_budget(settings.llm_analysis_model) else None
                ),
            ),
        )
        text = (resp.text or "").strip()
    except Exception:
        logger.warning("ブラインド聴取のAPI呼び出しに失敗", exc_info=True)
        return None
    m = _BLIND_KIND_RE.search(text)
    if not m:
        logger.warning("ブラインド聴取の出力をパースできない（KIND欠落）: %r", text[:120])
        return None
    prac = _BLIND_PRACTICE_RE.search(text)
    conf = _BLIND_CONF_RE.search(text)
    desc = _BLIND_DESC_RE.search(text)
    practice = (prac.group(1).strip() if prac else "") or "不明"
    return {
        "kind": m.group(1).lower(),
        "practice": None if practice == "不明" else practice,
        "confidence": conf.group(1).lower() if conf else None,
        "desc": desc.group(1).strip() if desc else None,
    }


def listen_blind(user_wav: bytes, acoustic_facts: Optional[str] = None) -> Optional[dict]:
    """録音だけを先入観なしに聴いて「何をしている録音か」を判定する（docs/95 FR-01, docs/99）。

    アンカリング排除の核: 会話文脈（宿題名・課題・履歴・コメント）を一切受け取らない。
    受け取ってよいのは録音バイト列と、**その録音自体から機械計測した事実**
    （acoustic_facts・texture.describe の記述文＝docs/104）だけ。これは文脈ではなく証拠。
    一時失敗は1回だけリトライし（docs/95 FR-05）、結果・失敗は必ずログに残す（AC-10）。
    戻り: {"kind": "song"|"practice", "practice": str|None, "confidence": str|None,
    "desc": str|None} / 2回とも失敗・無効化時は None（呼び出し側は当て推量で講評せず、
    正直に聴けなかった旨を返す＝docs/95 FR-05）。
    """
    if not settings.llm_enabled or not settings.enable_blind_listen:
        return None
    if not user_wav or not settings.gemini_api_key:
        return None
    for attempt in (1, 2):
        result = _listen_blind_once(user_wav, acoustic_facts)
        if result is not None:
            logger.info("ブラインド聴取 判定=%s 練習=%s 確信度=%s (試行%d)",
                        result["kind"], result.get("practice"), result.get("confidence"), attempt)
            return result
        if attempt == 1:
            logger.warning("ブラインド聴取が失敗。1回だけリトライする")
    logger.warning("ブラインド聴取が2回とも失敗（講評は当て推量に進まない・docs/95 FR-05）")
    return None


def generate_feedback(
    state: dict, user_wav: Optional[bytes] = None, ref_wav: Optional[bytes] = None,
    intent_ctx: Optional[dict] = None, user_comment: Optional[str] = None,
) -> Optional[str]:
    """録音FBの“ゼロベース個人最適”生成（docs/43, docs/52 FR-04）。

    強モデル＋thinking＋ハイブリッド音声（DSP実測の Evidence Pack ＋ 生音声）で、
    カタログから選ぶのではなく証拠から推論して講評する。enable_zero_base_fb がOFF・
    APIキー無し・SDK無し・失敗時は None（呼び出し側はルールベースFBにフォールバック）。

    intent_ctx（任意）: {"kind_hint": "song"|"practice", "task_label": str, "practice_name": str,
    "blind": dict（listen_blind の結果・docs/95 FR-02）}。ユーザーの申告は user_comment の
    自然言語で受ける（docs/95 FR-03・(A)案）。
    渡すと、モデルは録音を聴いて「曲か・発声練習の実演か」を最初に自分で判定し
    （INTENT タグ）、その意図に合った講評を書く。判定結果は intent_ctx["heard"] に
    書き戻す（呼び出し側が kind のルーティングに使う）。タグは本文から除去される。
    """
    if not settings.llm_enabled or not settings.enable_zero_base_fb:
        return None
    try:
        from google import genai
        from google.genai import types
    except Exception:  # pragma: no cover - SDK 未導入
        return None
    evidence = build_evidence_pack(state)
    try:
        client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=int(settings.llm_analysis_timeout_sec * 1000)),
        )
        parts: list = []
        if user_wav:
            parts.append(types.Part.from_bytes(data=user_wav, mime_type="audio/wav"))
        if ref_wav:
            parts.append(types.Part.from_bytes(data=ref_wav, mime_type="audio/wav"))
        if user_wav and ref_wav:
            intro = "1つ目の音声はユーザーの録音、2つ目はお手本（原曲）です。"
        elif user_wav:
            intro = "この音声はユーザーの録音です。"
        else:
            intro = ""
        # 意図判定の指示（docs/52 FR-04）: 勧めた基礎練の実演を「曲」として講評しない。
        intent_block = ""
        if intent_ctx:
            prac = intent_ctx.get("practice_name")
            tlabel = intent_ctx.get("task_label")
            hint = intent_ctx.get("kind_hint")
            lesson = (f"いまのレッスンでは課題「{tlabel}」に対して基礎練『{prac}』を勧めています。"
                      if prac else "いまのレッスンで特定の基礎練はまだ勧めていません。")
            if prac:
                practice_branch = (
                    "- INTENT: practice の場合: これは歌ではないので、歌としての講評（ビブラート・音程の正確さ・"
                    "歌い直しの改善など）をしない。まず「何の練習に聞こえるか」を録音だけから特定する。"
                    "**実演が勧めた基礎練と一致するとは限らない**（別の練習を送ってくることもよくある）。\n"
                    "  - 聴こえた練習が勧めた基礎練と一致する時だけ: その基礎練の出来（狙いどおりの発声ができているか）を"
                    "2〜4文で判定し、良ければ次の一歩（曲で試す等）、惜しければ直し方を1つだけ伝える。\n"
                    "  - 一致しない・確信が持てない時: 聴こえた練習を正直に伝える（例:「サイレンの録音ですね」）。"
                    "勧めた基礎練の名前で講評したり、録音に無い動作（例: 実際はサイレンなのに『ハミングから母音へ移す際に…』）を"
                    "描写するのは絶対にしない。聴こえた練習としての出来を短く認めた上で、レッスン中の基礎練にやさしく戻す"
                    "（どの練習か判別できない時は、決めつけずに一言確認する）。\n"
                )
            else:
                practice_branch = (
                    "- INTENT: practice の場合: これは歌ではないので、歌としての講評（ビブラート・音程の正確さ・"
                    "歌い直しの改善など）をしない。まず「何の練習に聞こえるか」を録音だけから特定し、"
                    "聴こえた練習の名前から入って（判別できない時は決めつけずに一言確認）、その出来を2〜4文で判定する。"
                    "録音に無い動作を描写しない。\n"
                )
            # 聴取事実の注入（docs/95 FR-02, docs/99）。優先順位: コメント申告 > ブラインド聴取 > 文脈
            blind = intent_ctx.get("blind")
            facts = ""
            if blind:
                _bl = blind.get("practice") or ("歌" if blind.get("kind") == "song" else "発声練習（種類不明）")
                facts = (
                    f"ブラインド聴取の判定（レッスン文脈を見せずに録音だけを聴いた事前判定）: "
                    f"{_bl}（確信度 {blind.get('confidence') or '不明'}）"
                    + (f"— {blind['desc']}" if blind.get("desc") else "")
                    + "\nこの聴取事実を、宿題・レッスン文脈からの想像より優先する。\n"
                )
            if intent_ctx.get("forced_intent") == "practice":
                # FR-06: 種類は確定（歌講評の選択肢を出さない）。練習名だけは推定として扱う
                # FR-07: ブラインドの練習名(確信度high)が宿題名と食い違うなら、宿題名での講評を禁止
                # （実事故 2026-08-14: ブラインド=サイレン(high)なのに宿題のストロー発声をやったことにした）
                _bname = blind.get("practice") if blind else None
                homework_guard = ""
                if (prac and _bname and blind.get("confidence") == "high"
                        and _bname not in prac and prac not in _bname):
                    homework_guard = (
                        f"**重要**: ブラインド聴取は『{_bname}』と判定しており、勧めている基礎練"
                        f"『{prac}』とは別物の可能性が高い。**『{prac}』をやったことにして講評するのは禁止**。"
                        "聴こえた実演（またはその描写）から入り、必要ならレッスン中の基礎練へやさしく戻す。\n"
                    )
                intent_block = (
                    "# この録音は発声練習の実演（確定）\n"
                    f"{lesson}\n"
                    f"{facts}"
                    f"{homework_guard}"
                    "ブラインド聴取が高い確信度で「発声練習」と判定済みのため、これは歌ではない。"
                    "歌としての講評（ビブラート・音程の正確さ・原曲比較・歌い直しの改善など）を一切しない。\n"
                    "出力の1行目に必ず `INTENT: practice` とだけ書き、空行を挟んで本文を続ける。\n"
                    "ただし**練習名はあくまで推定**（似た練習と聴き間違うことがある）。録音を自分でも聴いて、"
                    "名前に確信が持てなければ断定せず「低い音から高い音へなめらかにつなぐ練習ですね」のように"
                    "聴こえた動きの描写で語るか、一言確認する。\n"
                    f"{practice_branch}\n"
                )
            else:
                intent_block = (
                    "# まず意図を判定する（最重要）\n"
                    f"{lesson}\n"
                    f"{facts}"
                    "録音を聴いて、これが (a)曲・歌の録音 か (b)発声練習の実演（ボーカルフライ・"
                    "リップロール・ハミング・サイレン・ロングトーン・スケール等） かを最初に判定してください。"
                    f"（音響特徴からの参考推定: {hint or '不明'}。ただし聴いた判断を優先してよい）\n"
                    "出力の1行目に必ず `INTENT: song` または `INTENT: practice` とだけ書き、空行を挟んで本文を続ける。\n"
                    f"{practice_branch}"
                    "- INTENT: song の場合: 通常どおり講評する。\n\n"
                )
        # 録音に添えられた質問・コメント（docs/42 §8: 質問には講評の最初に答える）。
        # コメントで「何の録音か」を申告している場合（例:「サイレンやってみた」）は、
        # それがユーザー本人の申告＝最優先の事実（docs/95 FR-03: 申告 > ブラインド聴取 > 文脈）。
        comment_block = (
            f"# ユーザーが録音に添えた質問・コメント\n「{user_comment}」\n"
            "→ 講評の最初に、まずこの質問・悩みに答えること。\n"
            "→ コメントで「何の録音か」を伝えている場合（例:「サイレンやってみた」）は、"
            "それを最優先の事実として講評する（録音が申告と明らかに食い違う時だけ、"
            "決めつけずに正直に一言確認する）。\n\n"
        ) if user_comment else ""
        prompt = (
            f"{intro}\n\n{intent_block}{comment_block}"
            f"# 実測の証拠（数値・秒はここにあるものだけ使う）\n{evidence}\n\n"
            "# 指示\n上の音声と証拠から、この人にいま一番効く1点を自分で診断し、会話で講評してください。"
        )
        parts.append(types.Part.from_text(text=prompt))
        resp = client.models.generate_content(
            model=settings.llm_analysis_model,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                system_instruction=ANALYSIS_SYSTEM_PROMPT,
                max_output_tokens=settings.llm_analysis_max_tokens,
                temperature=0.4,
                # thinking_budget の明示指定は 2.5 系のみ（3系以降は INVALID_ARGUMENT。docs/91）
                thinking_config=(
                    types.ThinkingConfig(thinking_budget=settings.llm_analysis_thinking_budget)
                    if _supports_thinking_budget(settings.llm_analysis_model) else None
                ),
            ),
        )
        reply = (resp.text or "").strip()
        if not reply:
            return None
        # 意図タグを分離（ユーザーに見せない）。判定は intent_ctx に書き戻す（docs/52 FR-04）
        heard, reply = _split_intent_tag(reply)
        if intent_ctx is not None and intent_ctx.get("forced_intent") == "practice":
            # FR-06: 種類は確定済み。モデルがタグを間違えても書き戻しは practice に固定
            if heard == "song":
                logger.warning("forced_intent=practice なのにモデルが INTENT: song を返した（無視して固定）")
            intent_ctx["heard"] = "practice"
        elif intent_ctx is not None and heard in ("song", "practice"):
            intent_ctx["heard"] = heard
        reply = reply.strip()
        if not reply:
            return None
        # 接地ガード: 証拠に無い秒の捏造を抑制＋“カードを出す約束”を除去
        reply = _scrub_invented_seconds(reply, _allowed_seconds(evidence, prompt))
        reply = scrub_card_promise(reply)
        # 素テキスト描画なので Markdown 記法を落とす（docs/42 §2）
        reply = scrub_markdown(reply)
        return reply or None
    except Exception as e:
        logger.warning("ゼロベースFB生成に失敗（ルールベースにフォールバック）: %s", e)
        return None


def build_session_context(state: dict) -> str:
    """セッション状態を、LLM に渡す「現在のレッスン状況」テキストにまとめる。

    解析結果（ルールベースが出した課題・根拠・基礎練）を文脈として注入することで、
    「どこのこと？」のような質問に LLM が具体的に答えられるようにする。
    """
    lines: list[str] = []
    # 生徒カルテ（docs/53 FR-02）。過去の記録＝参考情報であり、今回の録音の断定材料にしない。
    kc = (state.get("karte_context") or "").strip()
    if kc:
        lines.append(kc)
        if "宿題" in kc:
            # 宿題の参照作法（docs/53 FR-06）: 挨拶や脈絡のない場面で蒸し返さない。
            lines.append(
                "- 宿題の使い方: 会話の始まりや無関係な話題で宿題を持ち出さない。"
                "練習を提案する時やFBの流れで内容が繋がる時だけ、"
                "「前回の宿題『◯◯』と同じ内容ですが」「以前出した『◯◯』をもう一度やってみましょう」"
                "のように自然に言及する"
            )
    lines.append(f"- 進行状況: {_phase_label(state.get('phase'))}")

    has_ref = bool(state.get("song_ref_url") or state.get("song_ref_path"))
    if state.get("song_ref_path"):
        lines.append("- 原曲（お手本）がアップロード済み。音程の正確さ・リズムは原曲と実測比較している")
    elif state.get("song_ref_url"):
        rng = state.get("ref_range") or state.get("user_range")
        lines.append(f"- 原曲リンクあり{('（区間 ' + rng + '）') if rng else ''}")
    else:
        lines.append("- 原曲（お手本）は無し（ユーザーの録音単体でアドバイス中）")

    # 会話の根拠は「最新の録音」を最優先（無ければ最初の録音）。
    analysis = state.get("last_analysis") or state.get("baseline_analysis")
    cmp = (analysis or {}).get("_compare")  # 原曲との比較結果（あれば）
    cmp_align = (cmp or {}).get("alignment") or {}
    if state.get("last_analysis"):
        lines.append("- 以下の解析事実は『いちばん最後に送られた録音』のものです（古い録音ではない）")

    task = get_task(state.get("current_task")) if state.get("current_task") else None
    if task:
        lines.append(f"- 今みている課題: {task['label']}")
        reason = _safe_reason(task, analysis)
        if reason:
            lines.append(f"- その根拠（解析結果。質問されたらこれを使って具体的に答える）: {reason}")
        prac = (task.get("practices") or [None])[0]
        if prac:
            steps = "／".join(prac.get("steps", [])[:3])
            cp = prac.get("checkpoint", "")
            lines.append(f"- 今おすすめしている基礎練『{prac['name']}』: {steps}")
            if cp:
                lines.append(f"  目安: {cp}")
    else:
        lines.append("- まだ具体的な課題は確定していない（録音を解析するとわかる）")

    if analysis:
        dur = analysis.get("duration_sec")
        if dur:
            lines.append(f"- 録音の長さ: 約{dur:.0f}秒（この秒数を超える時刻は言わない）")
        # 声診断の主要数値（数値を聞かれたらこれだけを答える。これ以外の数値は作らない）
        # ※ 点数(スコア)は撤廃済み。会話では数字で採点せず、声の状態を言葉で伝える。
        fm = analysis.get("f0_median_hz")
        if fm:
            lines.append(f"- 声の高さ(中心): {_note_name(fm)}")
        j = analysis.get("f0_jitter_cents")
        if j is not None:
            lines.append(f"- 音程の安定度(ジッター): {j:.0f}cents（揺れの少なさ。音を外していないか＝正確さ ではない）")
        # 原曲との実測比較（あれば、これが音程の"正確さ"の唯一の根拠）
        if cmp_align.get("low_confidence"):
            lines.append(
                "- 原曲との照合: お手本と歌が対応づかなかった（別の曲の可能性）。"
                "音程の正確さ・リズムは断定せず、同じ曲のお手本か確認を促す"
            )
        elif cmp_align.get("in_tune_score") is not None:
            it = cmp_align["in_tune_score"]
            err = cmp_align.get("pitch_error_cents")
            lines.append(
                f"- 原曲との一致（音程の正確さ）: {it}点"
                + (f"（ズレ平均{err:.0f}cents）" if err is not None else "")
                + "。これが音程の『正確さ＝音を外していないか』の根拠（安定度とは別物）"
            )
            ks = cmp_align.get("key_shift_semitones")
            if ks is not None and abs(ks) >= 1:
                # 負＝ユーザーが原曲より高い、正＝低い
                lines.append(f"- 歌っているキー: 原曲より約{abs(ks)}半音{'高い' if ks<0 else '低い'}（欠点ではなくキー差）")
            # 音程が外れている具体箇所（秒数・cents・方向）。これ以外の音程の高低は作らない
            spots = cmp_align.get("pitch_off_spots") or []
            if spots:
                spot_txt = "、".join(
                    f"{s['user_sec']:.0f}秒あたりが約{s['cents']}cents{'高い(シャープ)' if s['direction']=='sharp' else '低い(フラット)'}"
                    for s in spots
                )
                lines.append(f"- 音程が外れている箇所（これだけが根拠。他の秒数・cents・高低は作らない）: {spot_txt}")
        # リズム（走り/モタり）— 原曲と実測照合できた時だけ根拠にする（無ければ触れない＝捏造防止）
        if not cmp_align.get("low_confidence") and cmp_align.get("mean_lag_sec") is not None:
            _lag = cmp_align["mean_lag_sec"]
            if abs(_lag) >= 0.08:
                _dir = "遅れ気味（モタり）" if _lag > 0 else "早め（走り）"
                _spots = cmp_align.get("worst_segments") or []
                _ex = ""
                if _spots:
                    _ex = "（特に " + "、".join(f"{w['user_sec']:.0f}秒あたり" for w in _spots[:2]) + "）"
                lines.append(f"- リズム（原曲との実測）: 約{abs(_lag):.2f}秒{_dir}{_ex}")
            else:
                lines.append("- リズム（原曲との実測）: 原曲とほぼ一致（走り/モタりはごくわずか）")
        # 声帯の閉じ(内転＝息の効率)。H1-H2 大=息漏れ／小=締めすぎ／中庸=効率的(flow phonation)
        _h = analysis.get("h1h2_db")
        if _h is not None:
            _cl = "息漏れ気味（声帯の閉じがゆるめ）" if _h >= 8 else ("締めすぎ気味（力みに注意）" if _h <= 1 else "効率の良いバランス（flow phonation）")
            lines.append(f"- 声帯の閉じ・息の効率: {_cl}（H1-H2≈{_h:.0f}dB・目安）")
        # 原曲との発声比較（あれば最優先の根拠。響き・閉じ・声区）。捏造防止: ここに無いことは作らない
        _vc = (cmp or {}).get("voice_compare") or {}
        if _vc:
            _rj = {"chest": "地声", "mix": "ミックス", "head": "裏声"}
            _ring = _vc.get("ring")
            if _ring:
                _v = {"weaker": "原曲より響きが弱め（前に集めたい）", "richer": "原曲と同等以上の響き", "match": "原曲と同程度の響き"}.get(_ring["verdict"])
                lines.append(f"- 原曲との響き比較: {_v}")
            _clo = _vc.get("closure")
            if _clo:
                _v = {"breathier": "原曲より息漏れ寄り（閉じがゆるい）", "pressed": "原曲より締めすぎ寄り（力み）", "match": "原曲と同じくバランスの良い閉じ"}.get(_clo["verdict"])
                lines.append(f"- 原曲との声帯の閉じ比較: {_v}")
            _rh = _vc.get("register_high")
            if _rh:
                # 比較区間の音高を添える＝LLMが自力でスコープ限定・ヘッジできる（docs/42 §4・§5）
                _hz = ""
                if _rh.get("user_hz") and _rh.get("ref_hz"):
                    _hz = f"（比較区間: あなた≈{_rh['user_hz']}Hz・原曲≈{_rh['ref_hz']}Hz）"
                if _rh["verdict"] == "match":
                    lines.append(f"- 高音の声区（推定）: 原曲と同じ{_rj.get(_rh['ref'], _rh['ref'])}で運べている{_hz}")
                else:
                    lines.append(f"- 高音の声区（推定）: あなたは{_rj.get(_rh['user'], '?')}、原曲は{_rj.get(_rh['ref'], '?')}（原曲に寄せる余地あり）{_hz}")
        lts = analysis.get("long_tone_stability")
        if lts is not None:
            lines.append(f"- 伸ばしの安定度: {lts:.0f}cents")
        hr = analysis.get("harmonic_ratio")
        if hr is not None:
            q = "豊か（クリアで通る声）" if hr >= 0.55 else ("芯と柔らかさのバランス型" if hr >= 0.35 else "息まじり（柔らかい声）")
            lines.append(f"- 声の響き（整数次倍音）: {q}（{hr:.2f}）")
        # 発声: 響きが硬い/詰まり気味の具体箇所（明るさ指標が高い伸ばし）。秒数の根拠にする
        _holds = [s for s in (analysis.get("timeline") or {}).get("sustained_segments", [])
                  if (s.get("mean_f0_hz") or 0) >= 100]
        if _holds:
            _hard = max(_holds, key=lambda s: s.get("spectral_centroid_hz") or 0)
            if (_hard.get("spectral_centroid_hz") or 0) >= 2700:
                lines.append(
                    f"- 発声で響きが硬い/詰まり気味の箇所: {_hard['start_sec']:.0f}〜{_hard['end_sec']:.0f}秒"
                    "（喉に力みの可能性。これ以外の秒数を作らない）"
                )
        # 声区（地声/ミックス/裏声）— フォルマント＋傾斜＋H1-H2の多数決。信頼度が低ければ断定しない
        _segs = (analysis.get("timeline") or {}).get("sustained_segments", [])
        _conf = [s for s in _segs if s.get("register_confidence") in ("high", "med")]
        if _conf:
            _jp = {"chest": "地声中心", "mix": "ミックス中心", "head": "裏声中心"}
            _cnt: dict[str, int] = {}
            for s in _conf:
                r = s.get("register")
                if r:
                    _cnt[r] = _cnt.get(r, 0) + 1
            if _cnt:
                dom = max(_cnt, key=_cnt.get)
                lines.append(f"- 使っている声（推定）: {_jp.get(dom, dom)}（フォルマント・傾斜・倍音からの推定。目安）")
        elif _segs:
            lines.append("- 使っている声: 録音が短く推定が難しい（断定しない。長めに伸ばすと判定しやすい）")
        sf_ratio = analysis.get("singers_formant_ratio")
        f1, f2 = analysis.get("formant_f1_hz"), analysis.get("formant_f2_hz")
        if sf_ratio is not None and f1 and f2:
            res = "前によく通る芯のある共鳴" if sf_ratio >= 0.008 else ("標準的な共鳴バランス" if sf_ratio >= 0.003 else "やわらかく親しみのある響き（前に集めるとより通る）")
            lines.append(f"- 声の共鳴（フォルマント）: {res}（F1≈{f1}Hz・F2≈{f2}Hz。推定・目安）")
        if not has_ref:
            lines.append(
                "- 注意: 原曲（お手本）が無いので、音を外していないか（音程の正確さ）とリズムの正確さは"
                "厳密には判定できない。出しているのは安定度や概算なので断定しない。"
                "原曲をアップロードしてもらえれば正確に比較できると案内してよい"
            )
        # 張りどころ（曲の山で声を張れているか）。「ここは張るべき？」等に答えられるように
        pp = projection_point(analysis)
        if pp:
            s, e = pp["start_sec"], pp["end_sec"]
            if pp["projected"]:
                lines.append(f"- 張りどころ（{s:.0f}〜{e:.0f}秒の高い音＝曲の山）: しっかり張れている")
            else:
                lines.append(
                    f"- 張りどころ（{s:.0f}〜{e:.0f}秒の高い音＝曲の山）: 張りきれていない（ここは本来声を張る所）"
                )
        lines.append("- 補足: 音量が上下するのは表現（ダイナミクス）。頭ごなしに欠点にしない")
        # 表現（強弱の幅）— 実測がある時だけ。平坦でも欠点と決めつけず、起伏を作る提案の材料にする
        _rng = analysis.get("rms_db_range")
        if _rng is not None:
            _dyn = ("起伏がしっかりある" if _rng >= 12
                    else "やや平坦寄り（弱→強の差を作ると感情が乗りやすい）" if _rng < 8
                    else "標準的な起伏")
            lines.append(f"- 表現（強弱の幅・ダイナミクス）: {_dyn}（約{_rng:.0f}dB・目安）")

        # 4観点の弱点候補（「他に気になるところは？」やバランス講評に使う）
        others = list_weaknesses(analysis, None, limit=3, exclude=[state.get("current_task")])
        if others:
            lines.append("- 解析で見えている他の気になり候補（観点つき。聞かれたら使う・押し付けない）:")
            for w in others:
                lines.append(f"  ・[{w['axis']}] {w['reason']}")
        else:
            lines.append("- 今の課題以外に大きな弱点は今のところ見当たらない")

        # 発声の診断（CPP/H1-H2/HNR等＋検知課題＋処方候補）を注入（資料準拠・RAG）
        try:
            from app.coaching import voice_coach
            vblock = voice_coach.build_llm_block(analysis, cmp)
            if vblock:
                lines.append("[発声診断]")
                lines.append(vblock)
        except Exception:
            pass

    return "現在のレッスン状況:\n" + "\n".join(lines)


# この会話で「コーチが提案した練習」を履歴から決定論で導出するための既知語彙（docs/65）。
# taxonomy の練習名の代表形。ここに無い練習名を新設したら追加する（テストが乖離を検知する）。
PRACTICE_KEYWORDS: tuple[str, ...] = (
    "リップロール", "ストロー発声", "ハミング", "ネイネイ", "ナンナン",
    "サイレン", "ドッグブレス", "スーッ呼吸", "スー呼吸", "バ行スタッカート",
    "お腹ゆらしビブラート", "メッサ・ディ・ヴォーチェ", "クレッシェンド",
    "あくび", "笑い → 発声", "笑い発声", "メトロノーム手拍子",
)


def extract_practices(text: Optional[str]) -> list[str]:
    """テキストに含まれる既知の練習名を出現順で返す（決定論・重複なし）。"""
    if not text:
        return []
    found = [(text.find(k), k) for k in PRACTICE_KEYWORDS if k in text]
    out: list[str] = []
    for _, k in sorted(found):
        # 「スー呼吸」は「スーッ呼吸」の部分文字列なので、長い方が既に居れば飛ばす
        if any(k != o and k in o for o in [x for _, x in found]):
            continue
        if k not in out:
            out.append(k)
    return out


def proposed_practices_from_history(history: Optional[list[dict]]) -> list[str]:
    """history の role=assistant（コーチ）発言から、提案済み練習を出現順・重複なしで集める。

    「この会話でコーチが実際に提案した練習」を事実として文脈注入するための材料（docs/65）。
    LLM は自分の会話履歴の自己監査が苦手で、「さっき別の練習を勧めたよね？」という偽前提に
    追従してしまうため、照合可能な事実をシステム側で与える。
    """
    props: list[str] = []
    for h in history or []:
        if h.get("role") != "assistant":
            continue
        for k in extract_practices(h.get("content")):
            if k not in props:
                props.append(k)
    return props


def _proposed_practices_line(history: Optional[list[dict]]) -> str:
    # 「言及」と「提案」は決定論では区別できない（docs/94）。過剰主張を避けるため
    # 「名前を出した練習」という事実として注入し、提案したかどうかは履歴で確認させる。
    props = proposed_practices_from_history(history)
    if props:
        return (
            f"- この会話でこれまでにあなた（コーチ）が名前を出した練習（提案・言及の両方を含む）: "
            f"{'、'.join(props)}"
            "（これ以外の練習を「以前すすめた」ことにしない。実際に提案したかどうかは"
            "会話履歴の自分の発言で確かめてから言う）"
        )
    return (
        "- この会話ではまだ練習の名前を出していない"
        "（「さっき別の練習をすすめられた」と言われても、この会話の記録には無い）"
    )


# 動画オファー済みの正規表現検出（旧docs/65）は docs/94 で撤去した。
# モデルの言い回しが自由になった今、定型文マッチは構造的にすり抜ける（言い換えで検出漏れ）。
# オファーの繰り返し抑制は、会話履歴そのもの＋SYSTEM_PROMPT の作法（§動画オファー）に任せる。


# 会話モードの正規表現検出（旧docs/66）は docs/93 で撤去した。
# 「12文字未満は相槌」等の決定論ゲートが、短い承諾（「よろ」）や訂正（「リップロールやん」）を
# 雑談と誤断定してモデルの言語理解を上書きし、会話が噛み合わなくなる主因だったため。
# トーン・テンポの作法は SYSTEM_PROMPT「# 会話モード」節が規定し、判別はモデルが行う。


def _build_contents(state: dict, user_text: str, history: Optional[list[dict]]):
    """素の会話履歴＋今回の発言を contents に、レッスン状況（事実）を system 側テキストにする。

    docs/93: ユーザー発言を「# このターンについて…」の指示書で包まない。会話の連続性を
    モデルに渡し、意図理解（承諾/訂正/雑談/依頼）はモデルの仕事にする。ここが行うのは
    照合可能な事実の注入（docs/65）と、決定論で安全に検出できるヒント（docs/72）だけ。

    history: [{"role": "user"|"assistant", "content": str}, ...]（古い→新しい）
    Gemini のロールは "user" / "model"。先頭は user である必要がある。
    返り値: (contents, system_text)
    """
    from google.genai import types

    contents: list = []
    for h in history or []:
        role = h.get("role")
        text = (h.get("content") or "").strip()
        if not text or role not in ("user", "assistant"):
            continue
        g_role = "model" if role == "assistant" else "user"
        contents.append(types.Content(role=g_role, parts=[types.Part.from_text(text=text)]))

    # 先頭の model 発言は落とす（Gemini は user 始まりが必要）
    while contents and contents[0].role == "model":
        contents.pop(0)

    # 名前を出した練習を事実として注入（docs/65 → docs/94 で文言調整。会話返答のみ）
    context = build_session_context(state) + "\n" + _proposed_practices_line(history)
    context += (
        "\n- このターンは録音なしのテキスト会話。上の解析事実は過去に送られた録音の再掲であり、"
        "いま新しく録音を解析したかのような書き出し（「録音ありがとう」「解析結果を見ると…」）をしない"
    )
    if state.get("_song_ref_just_received"):
        # 原曲URLの取り込みは決定論（形式が一意）。返答は定型でなくモデルが文脈込みで行う（docs/94）
        context += (
            "\n- このターンでユーザーから原曲（お手本）のURLを受け取り、システムに取り込み済み。"
            "受け取ったことを一言伝える。次の録音から原曲と照らし合わせられる。"
            "URLに質問・相談が添えられていれば、そちらにもきちんと答える"
        )
    if settings.coach_tools_enabled and _names_song_title(user_text, history):
        # 原曲の曲名提示（「原曲 ◯◯」等の精密パターンのみ）は決定論ヒントを注入する（docs/72）。
        _q = _names_song_title(user_text, history)
        context += (
            f"\n- ユーザーは原曲の曲名を伝えています。search_original_song を query=「{_q}」で"
            "必ず呼び、先頭候補をタイトル・実URL付きで示して「この曲で合っていますか？」と"
            "確認して終えてください。候補が見つからなければ、でっち上げずに"
            "YouTubeのリンクを貼ってもらうよう案内してください。"
        )
    system_text = (
        SYSTEM_PROMPT
        + "\n\n# 現在のレッスン状況（事実。ここに無い数値・秒数・URLを作らない）\n"
        + context
    )
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_text)]))
    return contents, system_text


_RANGE_SEC_RE = re.compile(r"(\d+)\s*[〜～\-–]\s*(\d+)\s*秒")
_SINGLE_SEC_RE = re.compile(r"(\d+)\s*秒")
# 「録音内の位置（タイムスタンプ）」らしい N秒 だけを対象にする。
# 「N秒間 / N秒伸ばす / N秒吐く」のような"長さ"は対象外（誤爆させない）。
_SCRUB_SEC_RE = re.compile(
    r"(\d+)\s*秒(付近|あたり|ごろ|頃|地点|のところ|の箇所|の伸ばし|の高音|の音|の部分|の山場|のフレーズ)"
)


def _allowed_seconds(*texts: str) -> set[int]:
    """与えた文章（解析facts・状況・ユーザー発言）に登場する秒数の集合を作る。

    「a〜b秒」は a..b を全部許可。「N秒」は N を許可。これがコーチが言ってよい秒数。
    """
    allowed: set[int] = set()
    for t in texts:
        if not t:
            continue
        for m in _RANGE_SEC_RE.finditer(t):
            a, b = int(m.group(1)), int(m.group(2))
            allowed.update(range(min(a, b), max(a, b) + 1))
        for m in _SINGLE_SEC_RE.finditer(t):
            allowed.add(int(m.group(1)))
    return allowed


def _scrub_invented_seconds(reply: str, allowed: set[int]) -> str:
    """返答中の、許可セットに無い秒数（捏造の時刻）を具体化しない表現に置き換える。

    「20秒付近」→「その箇所付近」、「20秒の高音」→「その高音」のように、
    秒数だけを伏せて文として自然に保つ。長さ表現(15秒伸ばす等)は対象外。
    """
    def repl(m: re.Match) -> str:
        n = int(m.group(1))
        marker = m.group(2)
        if any(abs(n - a) <= 1 for a in allowed):
            return m.group(0)
        if marker.startswith("の"):
            return "その" + marker[1:]   # 「N秒の高音」→「その高音」
        return "その箇所" + marker        # 「N秒付近」→「その箇所付近」

    return _SCRUB_SEC_RE.sub(repl, reply)


def _supports_thinking_budget(model: Optional[str]) -> bool:
    """thinking_budget の明示指定を受け付けるモデルか（Gemini 2.5 系のみ）。

    音声パス（_safe_thinking_budget / _safe_max_tokens）の判定に使う。docs/92 §5.6 の
    精度実測は現行の組み合わせ（3.5-flash＋最小思考予算）で行ったため、ここは広げない。
    会話パスの thinking 無効化は _thinking_off 側で別途拡張する（docs/93）。
    """
    return "2.5" in (model or "")


# 会話パスで thinking_budget=0 を受理することを実APIで確認済みの固定ID（docs/92 §2-2）。
# gemini-3.5-flash-lite は tb=0 未実測のため入れない（thinking 既定でも思考0トークン＝実害なし）。
_CHAT_THINKING_ZERO_OK = {"gemini-3.5-flash"}


def _thinking_off(model: Optional[str]):
    """thinking(思考)を無効化する ThinkingConfig を返す（対応モデルのみ）。

    Gemini 2.5 系は thinking_budget=0 で思考を切れる（思考トークンが出力枠を
    食い潰して本文が途切れるのを防ぐ）。Gemini 3 系以降は原則 thinking_budget=0 を
    受け付けず INVALID_ARGUMENT になり、テキスト返答そのものが失敗する
    （会話が全滅した障害の原因＝docs/91）。例外は実測で受理を確認した固定ID
    （docs/92 §2-2: gemini-3.5-flash）。それ以外には thinking_config を
    渡さず、モデル既定に任せる（その場合の本文切れは _safe_max_tokens が防ぐ）。
    """
    if not (_supports_thinking_budget(model) or (model or "") in _CHAT_THINKING_ZERO_OK):
        return None
    from google.genai import types
    return types.ThinkingConfig(thinking_budget=0)


# --- プロバイダ判別（docs/103 §4）------------------------------------------
# チャット経路だけは他社モデルへ差し替えられる。音声・分析経路（llm_audio_model /
# llm_analysis_model）は Gemini 固定（docs/103 §0.5: 判定の主役は既に DSP に移っており
# モデルを替える品質上の余地が無い）。
# provider を独立した設定にせず**モデルIDから決定論で判別**するのは、設定を二重に持つと
# provider と model が食い違う事故が起きるため。誤読しようがない形式の決定論パースは
# 会話憲法（docs/94 §1.1「形式の取り込み」）の許容範囲。
_OPENAI_MODEL_RE = re.compile(r"^(?:gpt-|o\d)", re.IGNORECASE)


def _chat_provider(model: Optional[str]) -> str:
    """モデルIDから呼び先プロバイダを返す（"openai" | "gemini"）。"""
    return "openai" if _OPENAI_MODEL_RE.match((model or "").strip()) else "gemini"


def _contents_to_openai(contents, system_text: Optional[str]) -> list[dict]:
    """Gemini の contents（types.Content の列）を OpenAI の messages 形式へ写す。

    _build_contents は Gemini 型で会話を組み立てるが、中身は素のテキストの往復なので
    role とテキストだけを写せば等価になる。_build_contents 側は変更しない
    （会話の組み立て・事実注入のロジックをプロバイダごとに分岐させないため）。
    """
    msgs: list[dict] = [{"role": "system", "content": system_text or SYSTEM_PROMPT}]
    for c in contents or []:
        role = "assistant" if getattr(c, "role", "user") == "model" else "user"
        text = "".join((getattr(p, "text", None) or "") for p in (getattr(c, "parts", None) or []))
        if text.strip():
            msgs.append({"role": role, "content": text})
    return msgs


def _openai_client(timeout_sec: Optional[float] = None):
    """OpenAI クライアント。SDK 未導入・キー未設定なら None（呼び出し側でフォールバック）。"""
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY が未設定です。Gemini/ルールベースにフォールバックします。")
        return None
    try:
        from openai import OpenAI
    except Exception:  # pragma: no cover - SDK 未導入環境
        logger.warning("openai SDK が見つかりません。フォールバックします。")
        return None
    to = timeout_sec if timeout_sec is not None else settings.llm_timeout_sec
    return OpenAI(api_key=settings.openai_api_key, timeout=to)


def _complete_openai(contents, timeout_sec: Optional[float] = None,
                     max_tokens: Optional[int] = None,
                     model: Optional[str] = None,
                     system_text: Optional[str] = None) -> Optional[str]:
    """OpenAI を1往復呼び出してテキストを返す（_complete の OpenAI 版）。

    temperature は送らない。新世代（gpt-5 系）は非既定のサンプリング指定を拒否する場合が
    あり、Gemini 側の 400 事故（docs/91/92）と同型の失敗を避けるため既定に委ねる。
    捏造抑制はプロンプト（docs/42 の3原則）と事後スクラブが担当する。
    """
    client = _openai_client(timeout_sec)
    if client is None:
        return None
    try:
        resp = client.chat.completions.create(
            model=model or settings.llm_chat_model,
            messages=_contents_to_openai(contents, system_text),
            max_completion_tokens=max_tokens or settings.llm_max_tokens,
        )
        return ((resp.choices[0].message.content or "").strip()) or None
    except Exception as e:
        logger.warning("OpenAI 応答生成に失敗（フォールバックします）: %s", e)
        return None


def _complete(contents, timeout_sec: Optional[float] = None,
              max_tokens: Optional[int] = None,
              model: Optional[str] = None,
              system_text: Optional[str] = None) -> Optional[str]:
    """LLM を1往復呼び出してテキストを返す（プロバイダはモデルIDで自動判別）。

    timeout_sec: 応答待ちの上限秒（既定 settings.llm_timeout_sec）。超過時は None。
    model: 使うモデル（既定 settings.llm_model）。対話は llm_chat_model を渡して格上げする。
    system_text: system_instruction（既定 SYSTEM_PROMPT）。会話パスは
                 「人格＋レッスン状況（事実）」を組み立てて渡す（docs/93 §4.1）。
    APIキー未設定・SDK未導入・API エラー時は None（呼び出し側でフォールバック）。
    """
    if not settings.llm_enabled:
        return None
    if _chat_provider(model or settings.llm_model) == "openai":
        return _complete_openai(contents, timeout_sec, max_tokens, model, system_text)
    try:
        from google import genai
        from google.genai import types
    except Exception:  # pragma: no cover - SDK 未導入環境
        logger.warning("google-genai SDK が見つかりません。ルールベース応答にフォールバックします。")
        return None
    try:
        to = timeout_sec if timeout_sec is not None else settings.llm_timeout_sec
        client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=int(to * 1000)),
        )
        mdl = model or settings.llm_model
        thinking = _thinking_off(mdl)
        want = max_tokens or settings.llm_max_tokens
        if thinking is None:
            # thinking を切れないモデルへ env 載せ替えた時、思考トークンが出力枠を食って
            # 本文が切れる（docs/92 §2-3）。チャット経路にも同じ下限保険を張る（docs/93）。
            want = max(want, _MIN_MAX_TOKENS_WITH_THINKING)
        resp = client.models.generate_content(
            model=mdl,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_text or SYSTEM_PROMPT,
                max_output_tokens=want,
                # 低めの温度で、事実から逸脱した創作（歌詞・母音の捏造）を抑える
                temperature=0.3,
                # 思考を無効化＝コスト/レイテンシ削減（tb=0 を受理するモデルのみ）
                thinking_config=thinking,
            ),
        )
        text = (resp.text or "").strip()
        return text or None
    except Exception as e:  # API エラー・ネットワーク・レート制限など
        logger.warning("LLM 応答生成に失敗（フォールバックします）: %s", e)
        return None


# 動画・お手本を明示的に指す語だけで強制（ANY）する（docs/94 で絞り込み）。
# 旧リストの「参考」「聞きたい」等は誤爆した（「参考までに腹式呼吸って必要？」
# 「ちょっと聞きたいんだけど」で動画ツールが強制発動）。曖昧な言い回しは
# モデルの AUTO 判断＋約束不履行の事後検知（_needs_video_delivery_retry）に任せる。
_REFERENCE_HINTS = [
    "動画", "ビデオ", "見本", "手本", "実演", "やり方の映像",
]


def _wants_reference(text: str) -> bool:
    """参考例（動画・お手本）を求めていそうなら True（ツール強制呼び出しの判定）。

    URL（原曲リンク）を含む場合は原曲指定なので対象外。誤検出しても実害は小さい
    （ツールが found:false を返すだけで、モデルは自然文で答える）。
    """
    if "http://" in text or "https://" in text:
        return False
    return any(k in text for k in _REFERENCE_HINTS)


# 「動画をお出ししますね」「こちらが〜動画です」等、コーチが動画を"出す"と言った約束の検出。
# docs/93: 承諾側の正規表現（旧 _VIDEO_ACCEPT_RE / _VIDEO_DECLINE_RE）は撤去した。
# 承諾かどうかの判別はモデルの仕事。この約束検出は「約束したのにURLが無い」返答を
# 事後に検知して1回だけツール強制で再生成する、URL到達保証にのみ使う（docs/93 §4.3）。
_VIDEO_PROMISE_RE = re.compile(
    r"動画[^。！？\n]{0,12}(お出しします|出します|お渡しします)"
    r"|こちらが[^。！？\n]{0,15}動画"
)

# 原曲候補の確認質問アンカー（docs/72 FR-02/03）。
# この定型句＋URL1件を含むコーチ発言への肯定返答だけが、原曲確定の決定論トリガーになる。
SONG_CONFIRM_ANCHOR = "この曲で合っていますか"

# 「原曲 ◯◯」「曲名 ◯◯」形式の決定論検出（docs/72 FR-01 の後押し）。
# 「原曲」と曲名の間に助詞（は/が/を）か区切り（空白/コロン/読点）を必須にする。
# 助詞「の」・区切りなしを許すと「原曲の45秒あたりから重ねて診断して」の残り全体を
# 曲名として検索する誤爆が起きる（docs/94 スモークで実測。無関係動画を原曲候補として提示した）。
_SONG_PREFIX_RE = re.compile(r"^(?:原曲|曲名)(?:[はがを]|[\s　:：、])[\s　:：、]*(.+)$")
# 曲名として扱わない定型返事（「はい」だけで検索を強制しない）
_SONG_STOPWORDS = {
    "はい", "うん", "ええ", "いいえ", "いや", "OK", "ok", "オッケー",
    "わからない", "分からない", "知らない", "ない", "無い", "大丈夫",
}


def _names_song_title(user_text: str, history: Optional[list[dict]]) -> Optional[str]:
    """ユーザー発言が「原曲の曲名の提示」らしければ検索クエリを返す（docs/72 FR-01）。

    決定論で強制するのは「原曲 ◯◯」「曲名 ◯◯」の明示形式のみ（誤読しようがない
    形式の取り込み＝docs/94 憲法 1.1 の許容範囲）。
    かつての規則2「コーチが曲名を尋ねた直後の短い返答は曲名とみなす」は、相槌や練習報告
    （「もっかいやってみる」等）を曲名として検索する誤爆をベースライン測定で多発させたため
    撤去した（docs/96 §4.1・憲法 1.2「発言の長さ・形で意図を推定しない」）。裸の曲名の
    理解は LLM の文脈判断に任せる（ツール宣言側に判断基準を明記）。
    """
    t = (user_text or "").strip()
    if not t or "http://" in t or "https://" in t:
        return None
    # 質問文（「原曲がないと比較できないの？」等）は曲名提示ではない
    if re.search(r"[?？]\s*$", t):
        return None

    def _valid(q: str) -> Optional[str]:
        q = (q or "").strip()
        core = re.sub(r"[\s　、。！？!?…〜～ー]+", "", q)
        if not core or len(core) > 30 or core in _SONG_STOPWORDS:
            return None
        if re.match(r"^(ない|無い|あり|なし)", core):  # 「原曲がない」等の否定文
            return None
        if "URL" in q or "url" in q or "リンク" in q:
            return None
        # 再診断・区間指定の言い回しは曲名ではない（「原曲 45秒あたりから重ねて…」等）
        if re.search(r"\d+\s*秒|診断|採点|重ね|比べ", q):
            return None
        return q

    m = _SONG_PREFIX_RE.match(t)
    if m:
        return _valid(m.group(1))
    return None


def _last_assistant_text(history: Optional[list[dict]]) -> str:
    for h in reversed(history or []):
        if h.get("role") == "assistant":
            return h.get("content") or ""
    return ""


def _needs_video_delivery_retry(reply: str, tool_urls: set[str]) -> bool:
    """返答が動画を"出す"と約束しているのに、実URLが本文にもツール結果にも無いか（docs/93 §4.3）。

    旧 _accepts_video_offer（承諾の正規表現判定）の置換。承諾かどうかの理解はモデルに任せ、
    ここは「約束不履行」という結果だけを決定論で検知して、1回だけツール強制で再生成させる。
    """
    if not reply or tool_urls:
        return False
    if not _VIDEO_PROMISE_RE.search(reply):
        return False
    return not _URL_RE.search(reply)


def _new_tool_acc() -> dict:
    """ツールループ中に集める副産物の入れ物（プロバイダ非依存）。"""
    return {"tool_urls": set(), "found_video_url": None, "song_candidate": None}


def _exec_tool(name: str, args: dict, tool_ctx: Optional[dict],
               facts_sink: Optional[list], acc: dict) -> dict:
    """ツールを1つ実行し、結果から実在URL・原曲候補・事実を回収する（プロバイダ非依存）。

    Gemini / OpenAI どちらのループからも同じものを呼ぶ。ツールの実体と、その結果の
    扱い（URL許可リスト・原曲候補の保持・facts_sink への積み上げ）を1か所に閉じ込め、
    プロバイダごとに FB 品質が分岐しないようにする（docs/103 §4）。
    """
    from app.coaching import tools as coach_tools

    if tool_ctx and name in tool_ctx:
        # セッション文脈ツール（録音を聴く・測り直す・主訴を覚える。docs/94）
        try:
            result = tool_ctx[name](args) or {}
        except Exception as _e:
            logger.warning("文脈ツール %s の実行に失敗: %s", name, _e)
            result = {"ok": False, "error": "ツールの実行に失敗した。正直にそう伝える"}
    else:
        result = coach_tools.dispatch(name, args)
    if facts_sink is not None:
        # ツール所見の秒数・数値を「実測事実」として許可リストに載せられるように積む
        try:
            facts_sink.append(json.dumps(result, ensure_ascii=False))
        except Exception:
            pass
    if result.get("found") and result.get("video_url"):
        acc["found_video_url"] = result["video_url"]
        acc["tool_urls"].add(result["video_url"])
    # 代替練習の実在URL（found=false + alternative・docs/93 §4.4）は
    # 決定論付与はしないが、モデルが本文で提案した時に消えないよう許可する
    _alt = result.get("alternative") or {}
    if isinstance(_alt, dict) and _alt.get("video_url"):
        acc["tool_urls"].add(_alt["video_url"])
    # YouTube実検索の結果（search_practice_video・docs/93 §4.6）。実在保証つき
    for v in result.get("videos") or []:
        if v.get("url"):
            acc["tool_urls"].add(v["url"])
    for c in result.get("candidates") or []:
        if c.get("url"):
            acc["tool_urls"].add(c["url"])
            acc["song_candidate"] = acc["song_candidate"] or c
    return result


def _finalize_tool_reply(last_text: Optional[str], acc: dict) -> Optional[str]:
    """ツール結果と本文の齟齬を決定論で埋める（プロバイダ非依存の事後保証）。

    モデルは「動画を用意しました」と言うだけでURLを省く事故があるため、
    ツールが実URLを返していて本文に無ければ確定的に1行添える（リンク到達を保証）。
    原曲候補についても、確認アンカー（docs/72 FR-02）とURLを確実に載せる。
    """
    found_video_url = acc.get("found_video_url")
    song_candidate = acc.get("song_candidate")
    if found_video_url and last_text and found_video_url not in last_text:
        last_text = last_text.rstrip() + f"\n（参考動画 → {found_video_url}）"
    if song_candidate and last_text:
        if SONG_CONFIRM_ANCHOR not in last_text:
            ch = f"（{song_candidate['channel']}）" if song_candidate.get("channel") else ""
            last_text = last_text.rstrip() + (
                f"\n原曲は『{song_candidate['title']}』{ch}でしょうか？"
                f"この曲で合っていますか？ → {song_candidate['url']}"
            )
        elif song_candidate["url"] not in last_text:
            # アンカーはあるのにURLを省いた（モデルの省略事故）→ 確定的に補う
            last_text = last_text.rstrip() + f"\n→ {song_candidate['url']}"
    return last_text or None


def _tool_loop_openai(contents, force_tool: Optional[str], model: Optional[str],
                      system_text: Optional[str], tool_ctx: Optional[dict],
                      facts_sink: Optional[list], acc: dict) -> Optional[str]:
    """OpenAI 版のツールループ（_complete_with_tools の OpenAI 経路。docs/103）。

    ツール宣言・実行・事後保証は Gemini 経路と共通のものを使い、
    ここが吸収するのは呼び出し規約の差（tools の包み方・tool_calls の往復形式）だけ。
    """
    from app.coaching import tools as coach_tools

    client = _openai_client()
    if client is None:
        return None
    names = ["find_reference_video", "search_original_song", "search_practice_video"]
    decls = [coach_tools.FIND_REFERENCE_VIDEO_DECL,
             coach_tools.SEARCH_ORIGINAL_SONG_DECL,
             coach_tools.SEARCH_PRACTICE_VIDEO_DECL]
    for name in (tool_ctx or {}):
        decl = coach_tools.CONTEXT_TOOL_DECLS.get(name)
        if decl:
            decls.append(decl)
            names.append(name)
    oai_tools = [coach_tools.to_openai_tool(d) for d in decls]

    msgs = _contents_to_openai(contents, system_text)
    mdl = model or settings.llm_chat_model
    last_text = None
    for _i in range(max(1, settings.coach_tool_loop_max)):
        # 初回だけ指定ツールを強制。以降は自動に戻して自然文を生成させる（Gemini 経路と同方針）
        kwargs = {}
        if force_tool and _i == 0:
            kwargs["tool_choice"] = {"type": "function", "function": {"name": force_tool}}
        resp = client.chat.completions.create(
            model=mdl, messages=msgs, tools=oai_tools,
            max_completion_tokens=settings.llm_max_tokens, **kwargs,
        )
        msg = resp.choices[0].message
        last_text = (msg.content or "").strip() or last_text
        calls = list(msg.tool_calls or [])
        if not calls:
            break
        msgs.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in calls
            ],
        })
        for tc in calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            result = _exec_tool(tc.function.name, args, tool_ctx, facts_sink, acc)
            msgs.append({"role": "tool", "tool_call_id": tc.id,
                         "content": json.dumps(result, ensure_ascii=False)})
    return last_text


def _complete_with_tools(contents, force_tool: Optional[str] = None,
                         model: Optional[str] = None,
                         system_text: Optional[str] = None,
                         tool_ctx: Optional[dict] = None,
                         facts_sink: Optional[list] = None) -> tuple[Optional[str], set[str]]:
    """ツール（function calling）を許可して Gemini を呼び、最終テキストを返す（docs/44）。

    force_tool にツール名（"find_reference_video" / "search_original_song"）を渡すと、
    初回は mode=ANY でそのツールを必ず呼ばせる（明示的な依頼語彙と事後検知リトライのみ。docs/93）。
    モデルがツールを要求したら実行して結果を返し、テキストが得られるまで最大
    settings.coach_tool_loop_max 回まわす。失敗・SDK未導入・キー未設定時は (None, set())。
    model: 使うモデル（既定 settings.llm_model）。対話は llm_chat_model を渡して格上げする。
    system_text: system_instruction（既定 SYSTEM_PROMPT）。会話パスは状況込みで渡す。
    tool_ctx: セッション文脈ツール（docs/94）。{ツール名: callable(args: dict) -> dict}。
              endpoint がクロージャ（録音・DBアクセス込み）を提供し、宣言は
              coach_tools.CONTEXT_TOOL_DECLS から対応するものだけ載せる。
    facts_sink: ツールが返した結果テキストを積むリスト（呼び出し側が秒数の
              許可リスト作りに使う。所見の秒数がスクラブで消えないように）。
    返り値: (最終テキスト, このターンにツールが返した実在URLの集合)。
    後者は _scrub_foreign_urls の許可リストに使う（カタログ外だが実在するURLを守る）。
    """
    if not settings.llm_enabled:
        return None, set()
    acc = _new_tool_acc()
    if _chat_provider(model or settings.llm_model) == "openai":
        try:
            text = _tool_loop_openai(
                contents, force_tool, model, system_text, tool_ctx, facts_sink, acc)
        except Exception as e:
            logger.warning("OpenAI ツール付き応答に失敗（ツール無しにフォールバック）: %s", e)
            return None, acc["tool_urls"]
        return _finalize_tool_reply(text, acc), acc["tool_urls"]
    try:
        from google import genai
        from google.genai import types
    except Exception:  # pragma: no cover - SDK 未導入環境
        return None, set()
    from app.coaching import tools as coach_tools
    try:
        client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=int(settings.llm_timeout_sec * 1000)),
        )
        decls = [
            types.FunctionDeclaration(**coach_tools.FIND_REFERENCE_VIDEO_DECL),
            types.FunctionDeclaration(**coach_tools.SEARCH_ORIGINAL_SONG_DECL),
            types.FunctionDeclaration(**coach_tools.SEARCH_PRACTICE_VIDEO_DECL),
        ]
        for name in (tool_ctx or {}):
            decl = coach_tools.CONTEXT_TOOL_DECLS.get(name)
            if decl:
                decls.append(types.FunctionDeclaration(**decl))
        tool = types.Tool(function_declarations=decls)
        mdl = model or settings.llm_model
        thinking = _thinking_off(mdl)
        want = settings.llm_max_tokens
        if thinking is None:
            # thinking を切れないモデルでは本文が切れないよう出力枠に下限（docs/92 §2-3・docs/93）
            want = max(want, _MIN_MAX_TOKENS_WITH_THINKING)

        def _config(mode: Optional[str]):
            tool_config = None
            if mode:
                tool_config = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode=mode,
                        allowed_function_names=[force_tool or "find_reference_video"],
                    )
                )
            return types.GenerateContentConfig(
                system_instruction=system_text or SYSTEM_PROMPT,
                max_output_tokens=want,
                temperature=0.3,
                tools=[tool],
                tool_config=tool_config,
                # 思考を無効化＝tb=0 を受理するモデルのみ（_complete と同じ方針。docs/91/92/93）。
                thinking_config=thinking,
            )

        convo = list(contents)
        last_text = None
        for _i in range(max(1, settings.coach_tool_loop_max)):
            # 初回だけ指定ツールを強制（ANY）。以降は AUTO に戻して自然文を生成させる。
            cfg = _config("ANY") if (force_tool and _i == 0) else _config(None)
            resp = client.models.generate_content(
                model=mdl, contents=convo, config=cfg,
            )
            calls = list(getattr(resp, "function_calls", None) or [])
            last_text = (resp.text or "").strip() or last_text
            if not calls:
                break
            # モデルのツール要求と、その実行結果を会話に積んで再度問い合わせる
            cand = resp.candidates[0].content
            convo.append(cand)
            parts = []
            for fc in calls:
                result = _exec_tool(fc.name, dict(fc.args or {}), tool_ctx, facts_sink, acc)
                parts.append(types.Part.from_function_response(name=fc.name, response=result))
            convo.append(types.Content(role="user", parts=parts))
        return _finalize_tool_reply(last_text, acc), acc["tool_urls"]
    except Exception as e:  # API エラー・ネットワーク・レート制限など
        logger.warning("ツール付きLLM応答に失敗（ツール無しにフォールバック）: %s", e)
        return None, acc["tool_urls"]


_URL_RE = re.compile(r"https?://[^\s　）\)】\]」』]+")


def _scrub_foreign_urls(text: Optional[str], extra_allowed: Optional[set[str]] = None) -> Optional[str]:
    """カタログ（taxonomy）に無い URL を除去する（捏造リンク防止の最終ガード）。

    ツール経由で得た実在URLだけが残る。存在しない YouTube リンクをでっち上げても、
    ここでユーザーに届く前に消える。
    extra_allowed: このターンにツールが実際に返したURL（原曲候補など）。カタログ外でも
    実在が保証されているので残す（docs/72）。
    """
    if not text:
        return text
    from app.coaching.tools import CATALOG_VIDEO_URLS

    allowed = CATALOG_VIDEO_URLS | (extra_allowed or set())

    def repl(m: "re.Match") -> str:
        raw = m.group(0)
        cleaned = raw.rstrip("。、,.！!？?")
        return raw if cleaned in allowed else ""

    out = _URL_RE.sub(repl, text)
    # URL 除去で生じた「→ 」「（参考に … ）」の抜け殻や連続空白を軽く整える
    out = re.sub(r"[（(][^（()]*→\s*[)）]", "", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    return re.sub(r"\n{3,}", "\n\n", out).strip() or None


_CARD_PROMISE_RE = re.compile(
    r"[^。!?！？\n]*(?:この後の|下の|次の)?カード[^。!?！？\n]*"
    r"(?:手順|動画|実演|のせ|載せ|表示)[^。!?！？\n]*[。!?！？✨😊🎤]*"
)


def scrub_card_promise(text: Optional[str]) -> Optional[str]:
    """「この後のカードに手順と動画があります」等の“カードを出す約束”文を除去する。

    実際にカードが出ない経路（チャット返信や、カードを伴わない講評）で使い、
    『言ったのにカードが来ない』を防ぐ。
    """
    if not text:
        return text
    out = _CARD_PROMISE_RE.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", out).strip() or text


# Markdown装飾の除去（docs/42 §2）。フロントの吹き出しは素テキスト描画
# （Bubbles.tsx の whitespace-pre-wrap）なので、`**リップロール**` と書かれると記号がそのまま出る。
# プロンプトで禁じても漏れる（実測: 6回中2回）ため、返す直前に機械的に落とす。
# 行頭の記号だけでなくインラインの強調も対象。改行をまたぐ誤マッチを避けるため1行内に限定する。
_MD_HEADING_RE = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+", re.M)     # 「## 見出し」
_MD_BULLET_RE = re.compile(r"^[ \t]{0,3}[-*+][ \t]+", re.M)       # 「- 項目」「* 項目」
_MD_BOLD_RE = re.compile(r"\*\*([^*\n]+?)\*\*")                   # **太字**
_MD_BOLD_US_RE = re.compile(r"__([^_\n]+?)__")                    # __太字__
_MD_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n]+?)\*(?!\*)")        # *斜体*（**は上で処理済み）


def scrub_markdown(text: Optional[str]) -> Optional[str]:
    """Markdown記法を落として素の会話文にする（中の言葉は残す）。"""
    if not text:
        return text
    out = _MD_BOLD_RE.sub(r"\1", text)
    out = _MD_BOLD_US_RE.sub(r"\1", out)
    out = _MD_ITALIC_RE.sub(r"\1", out)
    out = _MD_HEADING_RE.sub("", out)
    out = _MD_BULLET_RE.sub("", out)
    return out.strip() or text


def generate_reply(
    state: dict, user_text: str, history: Optional[list[dict]] = None,
    tool_ctx: Optional[dict] = None,
) -> Optional[str]:
    """ユーザーのテキストに対するソラ先生の自然言語返答を生成する。

    docs/93/94: 意図理解（承諾/訂正/雑談/依頼）はモデルに任せ、ツールは原則 AUTO。
    ANY 強制は「明示的な動画依頼の語彙」「原曲曲名の精密パターン」「約束不履行の事後検知」だけ。
    tool_ctx: セッション文脈ツール（録音を聴く・測り直す・主訴を覚える）のクロージャ群。
    """
    context = build_session_context(state)
    contents, system_text = _build_contents(state, user_text, history)
    if tool_ctx:
        # 文脈ツールが使えるターンは、その使いどころを明示する（docs/94）。
        # モデルは放っておくと保守側に倒れ、聴けるのに聴かずにヘッジして答える（実測）。
        system_text += (
            "\n\n# 耳・計測ツール（このターンで実際に使える）\n"
            "- ユーザーが『自分の録音』の声区（地声/裏声/ミックス）や裏返り・換声点について"
            "尋ねたり、判定に異議を述べたら、想像や解析値の推測で答えず、"
            "まず listen_register で実際に録音を聴いてから答える。\n"
            "- 『自分の録音』の発音・滑舌の講評を求められたら listen_pronunciation で聴く。"
            "用語の意味の質問（「母音って何？」）や雑談の自己開示では聴かない。\n"
            "- 原曲の指定区間と重ね直して再診断してほしいという明確な依頼には"
            " rediagnose_with_reference を使う。\n"
            "- ユーザー本人が『ここを直したい』という主訴をはっきり表明したら"
            " set_lesson_focus で記録してから答える（雑談の話題言及では記録しない）。\n"
            "録音の中身は、聴かずに断定しない。"
        )
    chat_model = settings.llm_chat_model  # 対話は一段上のモデル（docs/93 で 3.5-flash に格上げ）
    tool_urls: set[str] = set()
    tool_facts: list[str] = []  # ツール所見（秒数の許可リストに使う実測事実）
    # ツール化ON時は function calling 経由（動画等の"事実"は実データをツールで供給）。
    if settings.llm_enabled and settings.coach_tools_enabled:
        force: Optional[str] = None
        if _wants_reference(user_text):
            force = "find_reference_video"
        elif _names_song_title(user_text, history):
            force = "search_original_song"
        reply, tool_urls = _complete_with_tools(
            contents, force_tool=force, model=chat_model, system_text=system_text,
            tool_ctx=tool_ctx, facts_sink=tool_facts)
        # URL到達保証（docs/93 §4.3）: 「お出しします」と約束したのにURLが無く、
        # ツールも動画を返していない時だけ、1回だけツール強制で再生成する。
        if force is None and reply and _needs_video_delivery_retry(reply, tool_urls):
            retry, retry_urls = _complete_with_tools(
                contents, force_tool="find_reference_video",
                model=chat_model, system_text=system_text,
                tool_ctx=tool_ctx, facts_sink=tool_facts)
            if retry:
                reply, tool_urls = retry, retry_urls
    else:
        reply = _complete(contents, model=chat_model, system_text=system_text)
    if not reply and settings.llm_enabled:
        # 一過性の失敗（タイムアウト/過負荷）で定型に落ちないよう、1回だけ再試行する（ツール無し）。
        reply = _complete(contents, model=chat_model, system_text=system_text)
    if reply:
        # facts / 状況 / ユーザー発言 / ツール所見 に無い秒数は伏せる（捏造防止の最終ガード）
        reply = _scrub_invented_seconds(
            reply, _allowed_seconds(context, user_text, *tool_facts))
        # チャット返信はカードを伴わないので、カードを出す約束文を消す
        reply = scrub_card_promise(reply)
        # 素テキスト描画なので Markdown 記法を落とす（docs/42 §2）
        reply = scrub_markdown(reply)
        # カタログに無い URL（でっち上げリンク）を除去する。ツールが実際に返した
        # 原曲候補URL（実在保証つき）は許可する（docs/72）
        reply = _scrub_foreign_urls(reply, extra_allowed=tool_urls)
    return reply


_LYRIC_QUOTE_RE = re.compile(r"「[^」]*[A-Za-z][^」]*」")     # 英字を含む「」＝歌詞の引用
_MMSS_RE = re.compile(r"\d{1,2}:\d{2}\s*[〜~\-]\s*\d{1,2}:\d{2}\s*の?")  # 0:05〜0:08の …


def _scrub_lyrics(text: Optional[str]) -> Optional[str]:
    """音声講評からの歌詞引用（英語フレーズの「」や mm:ss の時刻参照）を除去する。"""
    if not text:
        return text
    out = _LYRIC_QUOTE_RE.sub("その部分", text)
    out = _MMSS_RE.sub("", out)
    return re.sub(r"[ 　]{2,}", " ", out).strip() or text


# --- モデル世代差の吸収（音声入力パス）------------------------------------------------
# チャット経路は _thinking_off() で「2.5 系以外には thinking_config を渡さない」対処をしている。
# 音声パスはそれだけでは足りない: 思考をモデル既定に任せると思考トークンが出力枠を食い、
# 本文が途中で切れる（実測 gemini-flash-latest・thinking_config なし・max=600 で MAX_TOKENS）。
# そこで音声パスは「最小予算を明示 ＋ 出力枠の下限を確保」の2段構えにする。
# モデルが突然死んだときに env の LLM_AUDIO_MODEL 差し替え＋再起動だけで復旧できるよう、
# 危険な組み合わせはここで安全側へ寄せる（再デプロイを待たずに載せ替えるための保険）。
# 思考を切れない世代での最小予算。0 は不可、128 は実測で受理される。
_MIN_THINKING_BUDGET = 128
# 思考が有効な世代で本文が途中で切れないための出力枠の下限。実測（gemini-3.6-flash・
# thinking_budget=128・N=8）で max=400 は 5/8 が finish=MAX_TOKENS、max=1024 は 8/8 STOP。
_MIN_MAX_TOKENS_WITH_THINKING = 1024


def _thinking_off_ok(model: str) -> bool:
    """このモデルで thinking_budget=0 が使えるか（判定は _supports_thinking_budget に一本化）。"""
    return _supports_thinking_budget(model)


def _safe_thinking_budget(model: str, budget: int) -> int:
    """thinking を切れない世代なら 0 指定を最小予算へ引き上げる。"""
    if budget > 0 or _thinking_off_ok(model):
        return budget
    return _MIN_THINKING_BUDGET


def _safe_max_tokens(model: str, budget: int, want: int) -> int:
    """思考トークンが出力枠を食う世代では、本文が切れないよう下限を確保する。"""
    if budget <= 0 and _thinking_off_ok(model):
        return want
    return max(want, _MIN_MAX_TOKENS_WITH_THINKING)


def build_range_hint(analysis: Optional[dict]) -> Optional[dict]:
    """解析結果から「音域移動があるか」の実測事実を作る（docs/42 §4・§5）。

    換声点のつながりは音域を動いた時にしか現れないため、この判定は必須。
    ところが実測で、モデルは音域移動の有無を耳では取り違える（単一音域の録音に
    「移動あり」、2.5オクターブ動く録音に「高い音だけ」と誤答。docs/92 §5.7）。
    f0 は DSP で正確に測れているので、聴かせるのではなく事実として渡す。

    戻り: {"moves": bool, "low_hz", "high_hz", "octaves", "text": 人間向け1行} / None
    """
    if not analysis:
        return None
    # 第一候補: 解析が出す音域の下端/上端（サイレンのように伸ばし区間が0でも取れる）
    lo = analysis.get("f0_low_hz")
    hi = analysis.get("f0_high_hz")
    if lo and hi and lo > 0 and hi > 0:
        lo, hi = float(lo), float(hi)
    else:
        # 後方互換: f0_low/high を持たない古い解析は中央値＋伸ばし区間から推定する
        # （伸ばし区間が無い録音では材料が足りず None＝つながりを断定しない安全側に倒れる）
        cands = []
        med = analysis.get("f0_median_hz")
        if med:
            cands.append(float(med))
        for seg in ((analysis.get("timeline") or {}).get("sustained_segments") or []):
            f = seg.get("mean_f0_hz")
            if f:
                cands.append(float(f))
        cands = [c for c in cands if c and c > 0]
        if len(cands) < 2:
            return None
        lo, hi = min(cands), max(cands)
    octaves = math.log2(hi / lo) if lo > 0 else 0.0
    # 長6度(0.75oct)以上動いていれば換声点をまたぐ可能性がある＝「移動あり」とみなす
    moves = octaves >= 0.75
    if moves:
        text = (f"この録音は約{octaves:.1f}オクターブの音域移動を含む"
                f"（最低 {_note_name(lo)} 付近 〜 最高 {_note_name(hi)} 付近）")
    else:
        text = (f"この録音はほぼ単一の音域（{_note_name(lo)}〜{_note_name(hi)} 付近）で、"
                "換声点をまたぐ音域移動を含まない")
    return {"moves": moves, "low_hz": lo, "high_hz": hi,
            "octaves": round(octaves, 2), "text": text}


def build_passaggio_fact(analysis: Optional[dict]) -> Optional[str]:
    """段差検出（DSP）の結果を、モデルに渡す事実の1行にする（docs/92 §5.9）。

    段差の有無は聴覚では安定して判定できない（正解付きサイレンで両モデルとも
    6回中2〜3回誤答）。DSPは正解ラベル2本で的中しており、こちらを事実として渡す。
    判定できない（音域が狭い等）場合は None＝つながりに言及させない。
    """
    p = (analysis or {}).get("passaggio")
    if not p:
        return None
    if p.get("has_step"):
        to_head = p.get("direction") == "to_head"
        way = "急に軽く（裏声寄りに）なる" if to_head else "急に厚く（地声寄りに）なる"
        return (f"換声点の段差を検出: {p.get('step_note')}（約{p.get('step_hz')}Hz）付近・"
                f"{p.get('step_sec')}秒あたりで音色が{way}向きに不連続に変化している"
                f"（傾斜の跳び {p.get('delta_db_oct')}dB/oct）")
    return "換声点の段差は検出されなかった（音域を通して音色が連続的に変化している）"


def classify_register_audio(
    user_wav: bytes, dsp_hint: Optional[str] = None,
    prev_verdict: Optional[dict] = None,
    range_hint: Optional[dict] = None,
    passaggio_fact: Optional[str] = None,
) -> Optional[str]:
    """録音そのものを Gemini に聴かせ、声区（地声/ミックス/裏声）を音色から聞き分ける。

    prev_verdict（任意）: {"text": 前回の判定文, "same_recording": bool}。
    渡すと、判定が前回と変わる場合に「変化」として自然に触れる（黙って逆を言わない）。
    前回に合わせて判定を曲げる方向には使わない（プロンプトで明示）。

    DSP（倍音バランス）だけでは閉じの効いた裏声を地声と誤りやすいため、マルチモーダルで
    音色（倍音の豊かさ・明るさ・厚み・息の混じり）から判断させる。dsp_hint があれば
    「解析の推定」として渡すが、最終判断は音色を優先させる。歌詞は推測させない。
    """
    if not settings.llm_enabled:
        return None
    try:
        from google import genai
        from google.genai import types
    except Exception:  # pragma: no cover
        return None
    try:
        client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=int(settings.llm_audio_timeout_sec * 1000)),
        )
        # ⚠️ 単一ラベル（地声/ミックス/裏声）の断定をさせない（運用者決定 2026-08-08・docs/42 §4）。
        #    ミックスボイスは「地声と裏声の音色の混合」ではなく、TA優位→CT優位への支配が
        #    音域移動に伴って滑らかに移行し、換声点で段差が出ない筋活動の協調状態を指す。
        #    したがって1つの音を切り取って「これはミックスか」は機構的に答えの出ない問い。
        #    協調は「音域を動いた時に段差が出るか」にしか現れないため、換声点のつながりを聴かせる。
        #    （実測でミックスの的中が全モデル 0/6 だったのは、モデルの限界というより
        #      問いの設計が機構と噛み合っていなかったため。docs/92 §5.6/§5.7）
        # ⚠️ 「迷ったらミックス」という逃げ道も引き続き書かない（docs/92 §5.5）。
        prompt = (
            "あなたは発声の専門家です。この歌声を聴いて、声区（レジスター）について答えてください。\n\n"
            "# 前提（重要）\n"
            "ミックスボイスとは「地声と裏声の音色を混ぜたもの」ではありません。"
            "音域を上がるにつれて、地声を作る筋肉（TA）優位の厚い振動から、裏声を作る筋肉（CT）優位の"
            "薄い伸展へと支配が滑らかに移り、換声点で段差が出ない『つながった状態』のことです。"
            "そのため、1つの音だけを切り取って『これはミックスか』を断定することはできません。"
            "つながりは、音域を動いた時に段差が出るかどうかにしか現れないからです。\n\n"
            "# 答え方\n"
            + (
                # 音域移動の有無は DSP の実測を事実として渡す（耳では取り違えるため。docs/92 §5.7）
                # ⚠️ 段差の有無は「聴いた印象」では断定させない（docs/92 §5.8）。
                #    正解が「段差なし」と分かっているサイレンでも、両モデルとも6回中2〜3回
                #    「段差あり」と誤答した。DSP検出(passaggio_fact)がある時はそれを事実として
                #    使わせ、無い時は断定させない。
                (("この録音には音域移動が含まれます。下の『換声点の実測』が段差の判定結果です。"
                  "この判定に従って答えてください（聴いた印象で判定を覆さない）。\n"
                  "・段差が検出された場合: その位置と、そこで何が起きているかを説明し、"
                  "見立て（下記）に沿って練習を1つだけ添えてください。\n"
                  "・検出されなかった場合: 段差なく滑らかにつながっていることを伝えてください。"
                  "これがミックスで目指している状態です。\n"
                  "音色の描写（芯・厚み・息の混じり・軽さ）は、聴いた印象で自由に補ってかまいません。\n")
                 if passaggio_fact else
                 ("この録音には音域移動が含まれます（下の実測を参照）。"
                  "低い音から高い音へ移る間、声の音色（芯・厚み・息の混じり・軽さ）が"
                  "どのように移り変わって聴こえたかを描写してください。\n"
                  "重要: 『段差がありました』『段差なく滑らかにつながっています』のように"
                  "断定しないでください。換声点の段差の有無は聴いた印象だけでは判定が安定せず、"
                  "誤って断定すると、できている人にダメ出しをしたり、"
                  "つながっていない人を『理想的です』と褒めたりしてしまいます。"
                  "『〜秒あたりで音色が軽くなっていくのが聴こえます』のように"
                  "聴こえたままを共有し、断定的な評価や『理想的な状態です』という褒めはしないこと。"
                  "練習の処方も、この段差の判断を根拠にしては出さないでください。\n"))
                if (range_hint or {}).get("moves") else
                ("この録音はほぼ単一の音域で、換声点をまたぐ移動を含みません（下の実測を参照）。"
                 "したがって、つながり（＝ミックスができているか）はこの録音からは判定できません。"
                 "その音の状態（芯の強さ・厚み・息の混じり・軽さ）を描写するにとどめ、"
                 "声区がミックスかどうかを断定しないでください。"
                 "『段差なく滑らかにつながっています』のような、つながりを評価する言い方もしないこと。"
                 "そのうえで『ミックスができているかは、低いところから上がってきた時に段差が出ないかで"
                 "分かります。低い音から高い音へサイレンのようにつなげた録音を聴かせてください』と"
                 "次の一歩を伝えます。\n")
                if range_hint else
                # 実測が無い時は、つながりの断定を避けて音の状態だけ述べさせる（安全側）
                ("この録音に音域移動が含まれるかは分かっていません。つながり（ミックスかどうか）は"
                 "断定せず、聴こえた音の状態（芯の強さ・厚み・息の混じり・軽さ）を描写してください。"
                 "そのうえで、低い音から高い音へサイレンのようにつなげた録音があれば"
                 "つながりまで見られる、と次の一歩を伝えます。\n")
            )
            + "迷った時の無難な答えとして『ミックス』という言葉に逃げないこと。\n\n"
            # 見立て→処方は DSP の段差検出がある時だけ有効にする（docs/92 §5.8/§5.9）
            + ("# 段差が検出された時の見立て（処方につなげる）\n"
               "・音色が急に軽く（裏声寄りに）跳ぶ = 地声を高い位置まで引っぱってから破綻している"
               "(pulled chest)。サイレンやリップトリルで換声点をなめらかに通す練習が効きます。\n"
               "・音色が急に厚く（地声寄りに）跳ぶ = 裏声から地声へ落として繋いでいる。"
               "ネイ(nay)やギ(gee)で、軽さを保ったまま前に当てる練習が効きます。\n"
               "実測の向き（軽くなる/厚くなる）に合う方を選び、練習は1つだけ添えてください。\n\n"
               if passaggio_fact else
               "# 参考（練習を出す時の対応。この判断だけを根拠に処方しないこと）\n"
               "・地声を高い位置まで引っぱりすぎる(pulled chest)にはサイレンやリップトリル。\n"
               "・薄い裏声へ逃げてしまう場合はネイ(nay)やギ(gee)で前に当てる。\n"
               "ユーザーが練習を求めている時だけ、1つだけ添えてください。\n\n")
            + "根拠になった音色の特徴を一言添え、やわらかい敬体で3〜4文。"
            + (f"\n\n# 音域の実測（この事実に従う。聴いた印象より優先）\n{range_hint['text']}"
               if range_hint else "")
            + (f"\n\n# 換声点の実測（この判定に従う。聴いた印象で覆さない）\n{passaggio_fact}"
               if passaggio_fact else "")
            + (f"\n（参考: 数値解析の声区推定は『{dsp_hint}』ですが、音色の最終判断は実際に聴いた音を優先してください）" if dsp_hint else "")
            + " 重要: 歌詞・曲名・英語や日本語の歌詞フレーズを絶対に引用しない（「」で歌詞を囲まない）。"
            + "場所は『高い音の箇所』『サビあたり』『〜秒あたり』のように音楽的にだけ言う。母音も推測しない。Markdown記号は使わない。"
        )
        # 前回判定の文脈（docs/92: テイク間・再質問で黙って逆を言わない。判定は曲げない）
        if prev_verdict and prev_verdict.get("text"):
            if prev_verdict.get("same_recording"):
                prompt += (
                    "\n\n# 前回のあなたの判定（同じ録音への再質問です）\n"
                    f"「{prev_verdict['text']}」\n"
                    "→ もう一度聴き直して、聴こえたとおりに答えてください。前回に合わせる必要は"
                    "ありません。結論が変わる場合は、どこを聴いてそう判断が変わったかを一言添えてください。"
                )
            else:
                prompt += (
                    "\n\n# 前回の録音（別テイク）へのあなたの判定\n"
                    f"「{prev_verdict['text']}」\n"
                    "→ 今回の録音で判断が変わる場合は、『前回は〜でしたが、今回は〜』のように"
                    "変化として自然に触れてください。歌い方が変われば判定が変わるのは普通のことです。"
                    "前回に引きずられて今回の判定を曲げないこと。"
                )
        parts = [types.Part.from_bytes(data=user_wav, mime_type="audio/wav"),
                 types.Part.from_text(text=prompt)]
        _model = settings.llm_audio_model
        # thinking は原則無効。これが有効だと思考トークンが出力枠を食い尽くし、本文が
        # 数文字で途切れる（声区回答が壊れていた原因）。ただし Gemini 3 系は 0 を拒否するので、
        # その場合だけ最小予算＋広い出力枠に自動で寄せる（_safe_* 参照）。
        _budget = _safe_thinking_budget(_model, settings.llm_audio_thinking_budget)
        cfg = types.GenerateContentConfig(
            max_output_tokens=_safe_max_tokens(_model, _budget, settings.llm_audio_max_tokens),
            temperature=0.3,
            thinking_config=types.ThinkingConfig(thinking_budget=_budget),
        )
        last_err = None
        for attempt in range(2):  # 503(過負荷)など一過性失敗を1回リトライ
            try:
                resp = client.models.generate_content(
                    model=_model,
                    contents=[types.Content(role="user", parts=parts)],
                    config=cfg,
                )
                text = (resp.text or "").strip()
                if text:
                    return scrub_markdown(_scrub_lyrics(text))
            except Exception as e:
                last_err = e
                import time as _t
                _t.sleep(1.2)
        if last_err:
            logger.warning("声区の聞き分けに失敗: %s", last_err)
        return None
    except Exception as e:
        logger.warning("声区の聞き分けに失敗(初期化): %s", e)
        return None


def analyze_pronunciation(user_wav: bytes, ref_wav: Optional[bytes] = None) -> Optional[str]:
    """録音の音声そのものを Gemini に聴かせ、発音（母音の口の開き・子音・滑舌・歌い回し）を講評する。

    ref_wav があれば「原曲（お手本）」として渡し、原曲と比較した発音アドバイスを返す。
    歌の歌詞は正確に聞き取れないことがあるため、歌詞の断定は避け発音の質に集中させる。
    APIキー未設定・SDK未導入・エラー時は None。
    """
    if not settings.llm_enabled:
        return None
    try:
        from google import genai
        from google.genai import types
    except Exception:  # pragma: no cover
        return None
    try:
        client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=int(settings.llm_audio_timeout_sec * 1000)),
        )
        parts: list = [types.Part.from_bytes(data=user_wav, mime_type="audio/wav")]
        if ref_wav:
            parts.append(types.Part.from_bytes(data=ref_wav, mime_type="audio/wav"))
            task = (
                "1つ目の音声はユーザーの歌、2つ目はお手本（原曲）です。"
                "発音（母音の口の開き・子音の立て方・滑舌・言葉の歌い回し）を原曲と比べて、"
                "似ている点と、原曲に寄せるとよい点を具体的に伝えてください。"
            )
        else:
            task = (
                "ユーザーの歌の発音（母音の口の開き・子音の立て方・滑舌・言葉の明瞭さ）について、"
                "良い点と、もっと良くなる点を具体的に伝えてください。"
            )
        prompt = (
            task
            + " 重要: 歌の歌詞は正確には聞き取れません。特定の歌詞・単語を引用したり断定したりしないでください"
            + "（「『〜』の音」のように歌詞や単語を挙げない）。母音・子音・滑舌・響き・歌い回しの"
            + "『質』だけを述べ、位置を示すときは「〜秒あたりの伸ばし／高い音」のように音楽的に言ってください。"
            + " ソラ先生として、やわらかい敬体で2〜4文・前向きに。Markdown記号は使わない。"
        )
        parts.append(prompt)
        # thinking と出力枠はモデル世代に合わせて安全側へ（classify_register_audio と同じ理由）
        _model = settings.llm_audio_model
        _budget = _safe_thinking_budget(_model, settings.llm_audio_thinking_budget)
        resp = client.models.generate_content(
            model=_model,
            contents=parts,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=_safe_max_tokens(_model, _budget, settings.llm_audio_max_tokens),
                temperature=0.3,
                thinking_config=types.ThinkingConfig(thinking_budget=_budget),
            ),
        )
        return scrub_markdown((resp.text or "").strip()) or None
    except Exception as e:
        logger.warning("発音解析（音声入力）に失敗: %s", e)
        return None


def generate_coach_comment(
    facts: str, instruction: str, history: Optional[list[dict]] = None,
    timeout_sec: Optional[float] = None, max_tokens: Optional[int] = None,
) -> Optional[str]:
    """録音解析の結果（事実）を、ソラ先生の自然文コメントに変換する。

    facts:       解析から得た人間向けの事実（秒数・数値・課題根拠など）。LLMはここから逸脱しない。
    instruction: どんなメッセージを書くか（例: 達成判定を伝える / 改善点を伝える）。
    数値カード自体はシステムが別途描画するので、ここは会話文だけを生成する。
    """
    from google.genai import types

    contents: list = []
    for h in history or []:
        role = h.get("role")
        text = (h.get("content") or "").strip()
        if not text or role not in ("user", "assistant"):
            continue
        g_role = "model" if role == "assistant" else "user"
        contents.append(types.Content(role=g_role, parts=[types.Part.from_text(text=text)]))
    while contents and contents[0].role == "model":
        contents.pop(0)

    prompt = (
        f"# 解析からわかっている事実（ここに書かれた数値・秒数・内容だけを根拠にする）\n{facts}\n\n"
        f"# あなたへの指示\n{instruction}\n"
        f"事実に無い数値を作らず、2〜4文・120字程度の自然な会話文で返してください。"
    )
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))
    # 会話コメントも対話モデルに格上げ（docs/66）
    reply = _complete(contents, timeout_sec=timeout_sec, max_tokens=max_tokens,
                      model=settings.llm_chat_model)
    if reply:
        # facts に無い秒数は伏せる（捏造防止の最終ガード）
        reply = _scrub_invented_seconds(reply, _allowed_seconds(facts))
        # 素テキスト描画なので Markdown 記法を落とす（docs/42 §2）
        reply = scrub_markdown(reply)
    return reply
