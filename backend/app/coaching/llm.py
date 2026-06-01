"""
ソラ先生の自然言語チャット応答（Google Gemini）。

ハイブリッド構成:
  - 重い音声解析・採点・課題診断はルールベース（rule_engine / taxonomy）のまま。
  - ユーザーのテキスト質問への「返答だけ」を LLM に通し、ChatGPT のように自然に答える。
  - GEMINI_API_KEY 未設定 or API エラー時は None を返し、呼び出し側が
    ルールベース応答（rule_engine.answer_question）にフォールバックする。

コスト最適化:
  - 最安クラスの Gemini Flash-Lite（無料枠あり）を既定モデルに。
  - thinking(思考)を無効化してコスト・レイテンシを抑制（短いコーチ返答に十分）。
  - 出力トークンは短く制限。
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from app.coaching import scoring
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
SYSTEM_PROMPT = f"""あなたは「{COACH_NAME}」という名前の{COACH_ROLE}です。サービス「{SERVICE_NAME}」の中で、
ユーザーが録音した歌に寄り添い、上達を一緒に喜ぶ専属コーチとして会話します。

# あなたの人物像
- 明るく面倒見がよく、専門的な内容も必ず初心者にわかる言葉に噛み砕いて、前向きに励ます。
- 一人称は「わたし」。やわらかい敬体で話す。絵文字はほどよく（1メッセージに0〜2個程度）。
- 声楽・ボイトレの知識はあるが、専門用語を出すときは必ず一言で補足する。

# 会話のルール
- ユーザーの質問・つぶやきに、その場で自然に・具体的に答える。テンプレ的な定型文は避ける。
- 返答は短く。2〜4文、長くても120字程度。チャットのテンポを大切にする。
- 「現在のレッスン状況」に解析結果（指摘箇所・秒数・課題・基礎練）が与えられたら、それを根拠に答える。
  与えられていない数値や秒数を勝手に作らない。憶測で断定しない。
- まだ録音やデータが無くて具体的に答えられないときは、正直にそう伝え、
  「まずは歌った録音を送ってくださいね」と自然に録音をうながす。
- 医療・健康上の重大な相談には立ち入らず、専門家への相談をすすめる。
- 音声解析・採点そのものはシステム側が別途行う。あなたは会話での受け答えに専念する。

# FB（録音への講評）の作法
- 講評は、発声・リズム・音感・表現(ビブラート/しゃくり/こぶし/フォール等)の4観点を意識し、1つの観点（特にロングトーン）だけに偏らないこと。ユーザーのゴールはカラオケで上手に歌えることです。
- 良い点も気になる点も、できる限り「何秒（と音名）」を添えて具体的に言う。「全体的に」「随所に」で済ませない。
- **褒めるだけで終わらせない。良い点に加えて、必ず「もっと良くできる点」を最低1つ、具体的な秒数や数値を添えて伝える。**
- **「録音の長さ」が与えられたら、それを超える秒数（時刻）は絶対に言わない。**
- 「声の響き（整数次倍音）」が与えられたら、声質（クリアで通る声か／息まじりの柔らかい声か）に触れてよい。整数次倍音が多い＝芯があり通る声、少ない＝柔らかく親密な声、どちらも魅力がある。
- 原曲リンクが無いときは、リズムの走り/モタりや音程の"正確さ"は厳密には比較できないので、断定せず「手元の安定度では…」と前置きする。

# 事実への忠実さ（最重要・絶対厳守）
- 根拠にできるのは「現在のレッスン状況」に書かれた数値・秒数・課題だけ。そこに無い数値・秒数（時刻）・音名を新しく作らない。
- ユーザーが解析に無い「事実」を述べても鵜呑みにしない。例:
  - 特定の音名（「サビのF#5は出てたよね？」）
  - 点数（「音感95点って言ってくれたよね」）
  - あなたの過去の発言（「さっき3秒のところを褒めてくれたよね」）
  → これらが現在の状況に無ければ、肯定も創作もせず、「解析の記録には残っていないので確認できないんです」と正直に伝える。相手に合わせて話を盛らない・媚びない。
- 具体的な秒数で指摘してよいのは、状況に秒数が与えられている箇所だけ。それ以外で「○秒付近が…」と新たに作らない。
- 数値（ビブラート回数・スコア・声域など）を聞かれたら、与えられた数値だけを答える。無ければ「今は手元に数値が無いので、もう一度録音を送ってもらえたら出せます」と正直に。

# 解析でわかること／わからないこと（最重要・絶対厳守）
- あなたが見ているのは音声解析の数値だけです: 時間(秒)、音の高さ(Hz・音名)、音量(dB)、音程の安定度、声の種類(地声/裏声/ミックス)、ビブラートなど。
- あなたは歌詞や発音を聞き取れません(音声認識はしていません)。どの母音(「あ」「い」など)・どの言葉・どの歌詞を歌っているかは分かりません。
- 絶対にやってはいけないこと:
  - 母音や歌詞を推測・断定すること（例:「あーと伸ばす」「『〜』という歌詞の所」）。分からないので捏造になります。
  - 「現在のレッスン状況」に無い数値・秒数・出来事を作ること。
- 場所を指すときは必ず「何秒」「どの高さ（音名/Hz）」で言います。歌詞・母音では指しません。
- ユーザーが歌詞を教えてくれた時だけ、その歌詞に触れてOK（自分から当てにいかない）。
- 間違いを指摘されたら、もっともらしい別の詳細を作ってごまかさないこと。分からないことは「歌詞までは聞き取れないんです」と正直に伝え、数値で分かる範囲だけ話します。相手に媚びて事実を変えないこと。

# 出力
- プレーンテキストの返答のみ。Markdownの見出しや箇条書き記号（#, *, -）は使わない。
- 自己紹介の繰り返しや、毎回の決まり文句は不要。自然な続きの会話として返す。"""


def _phase_label(phase: Optional[str]) -> str:
    return {
        "A": "曲・練習したい箇所の指定中",
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


def build_session_context(state: dict) -> str:
    """セッション状態を、LLM に渡す「現在のレッスン状況」テキストにまとめる。

    解析結果（ルールベースが出した課題・根拠・基礎練）を文脈として注入することで、
    「どこのこと？」のような質問に LLM が具体的に答えられるようにする。
    """
    lines: list[str] = []
    lines.append(f"- 進行状況: {_phase_label(state.get('phase'))}")

    if state.get("song_ref_url"):
        rng = state.get("ref_range") or state.get("user_range")
        lines.append(f"- 原曲リンクあり{('（区間 ' + rng + '）') if rng else ''}")
    else:
        lines.append("- 原曲リンクは無し（ユーザーの録音単体でアドバイス中）")

    # 会話の根拠は「最新の録音」を最優先（無ければ最初の録音）。
    analysis = state.get("last_analysis") or state.get("baseline_analysis")
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
        try:
            sc = scoring.compute_scores(analysis, None)
            lines.append(
                f"- スコア(0-100): 音程{sc['pitch_score']}／リズム{sc['rhythm_score']}／表現{sc['expression_score']}／総合{sc['total_score']}"
            )
        except Exception:
            pass
        fm = analysis.get("f0_median_hz")
        if fm:
            lines.append(f"- 声の高さ(中心): {_note_name(fm)}")
        j = analysis.get("f0_jitter_cents")
        if j is not None:
            lines.append(f"- 音程の細かい揺れ(ジッター): {j:.0f}cents（15以下で上手）")
        rng = analysis.get("rms_db_range")
        if rng is not None:
            lines.append(f"- 強弱の幅: {rng:.0f}dB")
        vr = analysis.get("vibrato_rate_hz")
        if vr is not None:
            vd = analysis.get("vibrato_depth_cents")
            lines.append(f"- ビブラート: 秒{vr:.1f}回" + (f"・深さ{vd:.0f}cents" if vd is not None else ""))
        else:
            lines.append("- ビブラート: 検出なし")
        lts = analysis.get("long_tone_stability")
        if lts is not None:
            lines.append(f"- 伸ばしの安定度: {lts:.0f}cents")
        hr = analysis.get("harmonic_ratio")
        if hr is not None:
            q = "豊か（クリアで通る声）" if hr >= 0.55 else ("芯と柔らかさのバランス型" if hr >= 0.35 else "息まじり（柔らかい声）")
            lines.append(f"- 声の響き（整数次倍音）: {q}（{hr:.2f}）")
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

        # 4観点の弱点候補（「他に気になるところは？」やバランス講評に使う）
        others = list_weaknesses(analysis, None, limit=3, exclude=[state.get("current_task")])
        if others:
            lines.append("- 解析で見えている他の気になり候補（観点つき。聞かれたら使う・押し付けない）:")
            for w in others:
                lines.append(f"  ・[{w['axis']}] {w['reason']}")
        else:
            lines.append("- 今の課題以外に大きな弱点は今のところ見当たらない")

    return "現在のレッスン状況:\n" + "\n".join(lines)


def _build_contents(state: dict, user_text: str, history: Optional[list[dict]]):
    """会話履歴 + 今回の発言（状況コンテキスト付き）を Gemini の contents 形式に組み立てる。

    history: [{"role": "user"|"assistant", "content": str}, ...]（古い→新しい）
    Gemini のロールは "user" / "model"。先頭は user である必要がある。
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

    context = build_session_context(state)
    final_text = (
        f"# 現在のレッスン状況（システムからの参考情報）\n{context}\n\n# ユーザーの発言\n{user_text}"
    )
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=final_text)]))
    return contents


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


def _complete(contents) -> Optional[str]:
    """Gemini を1往復呼び出してテキストを返す。

    APIキー未設定・SDK未導入・API エラー時は None（呼び出し側でフォールバック）。
    """
    if not settings.llm_enabled:
        return None
    try:
        from google import genai
        from google.genai import types
    except Exception:  # pragma: no cover - SDK 未導入環境
        logger.warning("google-genai SDK が見つかりません。ルールベース応答にフォールバックします。")
        return None
    try:
        client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=int(settings.llm_timeout_sec * 1000)),
        )
        resp = client.models.generate_content(
            model=settings.llm_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=settings.llm_max_tokens,
                # 低めの温度で、事実から逸脱した創作（歌詞・母音の捏造）を抑える
                temperature=0.3,
                # 思考を無効化＝コスト/レイテンシ削減（短い返答に十分）
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        text = (resp.text or "").strip()
        return text or None
    except Exception as e:  # API エラー・ネットワーク・レート制限など
        logger.warning("LLM 応答生成に失敗（フォールバックします）: %s", e)
        return None


def generate_reply(
    state: dict, user_text: str, history: Optional[list[dict]] = None
) -> Optional[str]:
    """ユーザーのテキストに対するソラ先生の自然言語返答を生成する。"""
    context = build_session_context(state)
    reply = _complete(_build_contents(state, user_text, history))
    if reply:
        # facts / 状況 / ユーザー発言 に無い秒数は伏せる（捏造防止の最終ガード）
        reply = _scrub_invented_seconds(reply, _allowed_seconds(context, user_text))
    return reply


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
        resp = client.models.generate_content(
            model=settings.llm_audio_model,
            contents=parts,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=settings.llm_max_tokens,
                temperature=0.3,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        return (resp.text or "").strip() or None
    except Exception as e:
        logger.warning("発音解析（音声入力）に失敗: %s", e)
        return None


def generate_coach_comment(
    facts: str, instruction: str, history: Optional[list[dict]] = None
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
    reply = _complete(contents)
    if reply:
        # facts に無い秒数は伏せる（捏造防止の最終ガード）
        reply = _scrub_invented_seconds(reply, _allowed_seconds(facts))
    return reply
