#!/usr/bin/env python3
"""リードへの返信下書き生成（docs/55 FR-03、docs/56）。

相手ツイートの文脈に合わせ、ソラ先生トーンの返信を1件作る。
Gemini があれば文脈生成、無ければ intent 別テンプレ（キー無しでも動く）。

制約（sns-strategist ゲートと同じ思想）:
- URLを絶対に入れない（reach減・課金回避。誘導はプロフィール固定前提）
- リプ乞い・媚び・誇大・医療的断定をしない
- 歌手名は出さない（正本 themes.ARTISTS_BY_ID 外の名前をでっち上げるリスクを断つ）
- 「ほぼ同じ返信文の連投」はそれ自体がスパムシグナル → too_similar() で検出
"""
import difflib
import os
import re
import sys

# intent 別テンプレ（Gemini無し/失敗時のフォールバック）。具体的な一手＋今日試せる形。
TEMPLATES = {
    "highnote": ("高音、張り上げるより「息を細く・当てる位置をおでこ側へ」で届きやすくなりますよ。"
                 "まず今の8割の声量で試してみてください🎤"),
    "flip": ("裏返るのは切り替え場所で急に息が増えるサインです。裏返る音の少し手前から"
             "「弱めの声量のまま」通過する練習が効きますよ。"),
    "mix": ("ミックスは特別な声というより地声と裏声のブレンド調整です。"
            "「ん〜」のハミングで低→高をつなぐ練習から始めるのがおすすめです。"),
    "onchi": ("音程は才能より「聴く→合わせる」の反復で伸びます。"
              "1音をピアノアプリと交互に出して合わせる練習、地味ですが確実ですよ。"),
    "pitch": ("ピッチのぶれ、実は息の支えの揺れが原因のことが多いです。"
              "ロングトーンをまっすぐ10秒、を毎日やると安定してきますよ。"),
    "karaoke": ("採点、ビブラートや抑揚の項目で伸ばせる余地があるかもしれません。"
                "音程バーが合ってるのに点が伸びない時は表現系の配点を見てみてください。"),
    "falsetto": ("裏声はいきなり歌で出すより「ホー」とフクロウの真似で出すのが近道です。"
                 "小さくてOK、まず毎日10回だけ試してみてください。"),
    "throat": ("喉が締まる時は「あくびの入り口」の形を先に作ると楽になりますよ。"
               "痛みが続くようなら無理せず休ませてあげてくださいね。"),
    "longtone": ("息が続かないのは吸いすぎのことも多いです。吐き切ってから自然に入る分だけで"
                 "歌うと、むしろ伸びますよ。"),
    "utattemita": ("歌ってみた、録って聴き返すだけでも立派な練習です。"
                   "1曲通しより「サビだけ10回」の方が伸びが早いですよ。"),
    "mention": ("聴いてくださってありがとうございます🎤 気になる悩みがあれば、"
                "できる範囲でアドバイスしますね。"),
}
_GENERIC = ("歌の悩みは原因が分かると一気に楽になります。焦らず1つずつで大丈夫ですよ🎤")

_URL_RE = re.compile(r"https?://\S+|www\.\S+")


def strip_urls(text: str) -> str:
    """保険: 生成物からURLを除去する（本文にURLを入れない方針の最終ガード）。"""
    return _URL_RE.sub("", text or "").strip()


def too_similar(text: str, recent_texts: list[str], threshold: float = 0.8) -> bool:
    """直近の返信文と酷似していないか（同文連投＝スパムシグナルの検出）。"""
    t = (text or "").strip()
    for prev in recent_texts:
        if difflib.SequenceMatcher(None, t, (prev or "").strip()).ratio() >= threshold:
            return True
    return False


def _gemini_draft(source_text: str, intent: str) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        model = os.getenv("SNS_LLM_MODEL", "gemini-flash-lite-latest")
        prompt = (
            "あなたは歌のAIコーチ「ソラ先生」。明るく面倒見のよい専門家、やわらかい敬体。\n"
            "X(Twitter)で下の投稿をした人に、そのまま送れる返信を1件だけ書いてください。\n\n"
            f"【相手の投稿】\n{source_text}\n\n【相手の悩みの種類】{intent}\n\n"
            "# 厳守\n"
            "- 1〜2文・全角100字以内。相手の文面の言葉を拾い、具体的な一手を1つだけ渡す\n"
            "- URL・ハッシュタグ・宣伝・「フォローして」等の誘導は書かない\n"
            "- 歌手名・アーティスト名は出さない\n"
            "- 医療的断定（〜症です等）をしない。喉の痛みには無理しない声かけまで\n"
            "- 上から目線・媚び・絵文字の多用をしない（絵文字は最大1つ）\n"
            "返信文だけを出力してください（前置き・引用符なし）。"
        )
        resp = client.models.generate_content(model=model, contents=prompt)
        text = strip_urls((resp.text or "").strip())
        if 10 <= len(text) <= 140 and "#" not in text:
            return text
        return None
    except Exception as e:
        print(f"[warn] Gemini返信生成に失敗 → テンプレ使用: {e}", file=sys.stderr)
        return None


def draft(source_text: str, query_id: str) -> tuple[str, bool]:
    """返信下書きを1件返す。returns (text, generated) — generated=False はテンプレ使用。"""
    import leads
    intent = (leads.QUERY_BY_ID.get(query_id) or {}).get("intent", "歌の悩み")
    text = _gemini_draft(source_text, intent)
    if text:
        return text, True
    return TEMPLATES.get(query_id, _GENERIC), False
