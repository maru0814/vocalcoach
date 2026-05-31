"""
ソラ先生の自然言語チャット応答（Anthropic Claude）。

ハイブリッド構成:
  - 重い音声解析・採点・課題診断はルールベース（rule_engine / taxonomy）のまま。
  - ユーザーのテキスト質問への「返答だけ」を LLM に通し、ChatGPT のように自然に答える。
  - ANTHROPIC_API_KEY 未設定 or API エラー時は None を返し、呼び出し側が
    ルールベース応答（rule_engine.answer_question）にフォールバックする。

コスト最適化:
  - 安価なモデル（既定 Haiku 4.5）。
  - 不変のシステムプロンプト（ペルソナ＋方針）に prompt caching を効かせる。
  - 出力トークンは短く制限（コーチの一言返答想定）。
"""

from __future__ import annotations

import logging
from typing import Optional

from app.coaching.persona import COACH_NAME, COACH_ROLE, SERVICE_NAME
from app.coaching.taxonomy import get_task
from app.core.config import settings

logger = logging.getLogger(__name__)

# 不変のシステムプロンプト（プレフィックス＝prompt cache 対象）。
# ここを書き換えるとキャッシュが無効化されるので、揮発的な情報は入れない。
SYSTEM_PROMPT = f"""あなたは「{COACH_NAME}」という名前の{COACH_ROLE}です。サービス「{SERVICE_NAME}」の中で、
ユーザーが録音した歌に寄り添い、上達を一緒に喜ぶ専属コーチとして会話します。

# あなたの人物像
- 明るく面倒見がよく、専門的な内容も必ず初心者にわかる言葉に噛み砕いて、前向きに励ます。
- 一人称は「わたし」。やわらかい敬体で話す。絵文字はほどよく（1メッセージに0〜2個程度）。
- 声楽・ボイトレの知識はあるが、専門用語を出すときは必ず一言で補足する。

# 会話のルール
- ユーザーの質問・つぶやきに、その場で自然に・具体的に答える。テンプレ的な定型文は避ける。
- 返答は短く。2〜4文、長くても120字程度。チャットのテンポを大切にする。
- 「# 現在のレッスン状況」に解析結果（指摘箇所・秒数・課題・基礎練）が与えられたら、それを根拠に答える。
  与えられていない数値や秒数を勝手に作らない。憶測で断定しない。
- まだ録音やデータが無くて具体的に答えられないときは、正直にそう伝え、
  「まずは歌った録音を送ってくださいね」と自然に録音をうながす。
- 医療・健康上の重大な相談には立ち入らず、専門家への相談をすすめる。
- 音声解析・採点そのものはシステム側が別途行う。あなたは会話での受け答えに専念する。

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

    task = get_task(state.get("current_task")) if state.get("current_task") else None
    if task:
        lines.append(f"- 今みている課題: {task['label']}")
        reason = _safe_reason(task, state.get("baseline_analysis"))
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

    return "現在のレッスン状況:\n" + "\n".join(lines)


def _build_messages(state: dict, user_text: str, history: Optional[list[dict]]) -> list[dict]:
    """会話履歴 + 今回の発言（状況コンテキスト付き）を Messages 形式に組み立てる。

    history: [{"role": "user"|"assistant", "content": str}, ...]（古い→新しい）
    """
    msgs: list[dict] = []
    for h in history or []:
        role = h.get("role")
        content = (h.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            msgs.append({"role": role, "content": content})

    # API は先頭が user である必要があるため、先頭の assistant を落とす
    while msgs and msgs[0]["role"] == "assistant":
        msgs.pop(0)

    context = build_session_context(state)
    msgs.append(
        {
            "role": "user",
            "content": f"# 現在のレッスン状況（システムからの参考情報）\n{context}\n\n# ユーザーの発言\n{user_text}",
        }
    )
    return msgs


def generate_reply(
    state: dict, user_text: str, history: Optional[list[dict]] = None
) -> Optional[str]:
    """ユーザーのテキストに対するソラ先生の自然言語返答を生成する。

    APIキー未設定・SDK未導入・API エラー時は None を返す（呼び出し側でフォールバック）。
    """
    if not settings.llm_enabled:
        return None

    try:
        import anthropic
    except Exception:  # pragma: no cover - SDK 未導入環境
        logger.warning("anthropic SDK が見つかりません。ルールベース応答にフォールバックします。")
        return None

    try:
        client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key,
            timeout=settings.llm_timeout_sec,
            max_retries=1,
        )
        resp = client.messages.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    # 不変プレフィックスをキャッシュ（繰り返し会話でコスト削減）
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=_build_messages(state, user_text, history),
        )
        parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
        text = "".join(parts).strip()
        return text or None
    except Exception as e:  # API エラー・ネットワーク・レート制限など
        logger.warning("LLM 応答生成に失敗（フォールバックします）: %s", e)
        return None
