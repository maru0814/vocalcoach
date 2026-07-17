#!/usr/bin/env python3
"""リードへの返信下書き生成（docs/58 FR-03改・2026-07-17 方針再転換）。

2026-07-06 に返信提案を廃止した理由は「歌手名等のでっち上げリスク」と
「返信トーンの管理コスト」（docs/58 §1）。本復活版は運用者指示（docs/62 の
人力エンゲージを1日5分に圧縮する）を受け、旧廃止理由をプロンプト任せに
せず**出力側の検証で強制**して潰す:

  - 固有名詞ガード: 下書き中のカタカナ語（3文字以上）は、相手ツイートに
    出てくる語か発声用語ホワイトリストに限る。未知のカタカナ語＝歌手名等の
    でっち上げとみなして棄却。themes.ARTISTS_BY_ID の実名は表記そのまま禁止。
    過剰検出は許容する（棄却＝監修済みテンプレへ、常に安全側）。
  - トーン管理: Gemini 生成が失敗/棄却なら intent 別テンプレへフォールバック。
    テンプレは sns-strategist の監修文面のみを置く（勝手に増やさない）。
  - URL・ハッシュタグ・@・宣伝誘導語の禁止、全角120字上限、
    同日バッチ内の類似連投検出（too_similar）。

writeの自動実行はしない: 下書きはLINEに表示されるだけで、送信は常に
運用者がXアプリで手動（docs/58 §1 の一次原理は不変）。
"""
import difflib
import os
import re
import sys

# intent 別テンプレ（Gemini無し/棄却時のフォールバック）。1つの具体的な一手＋今日試せる形。
# 文面は週次レポートの返信下書き（sns-strategist 監修）から採録。勝手な追加・改変はしない。
TEMPLATES = {
    "sing_better": ("上手くなりたい気持ちが一番の才能ですよ。まず1曲通しより「サビだけ録音して"
                    "聴き返す」を10回。自分の声を客観で聴けた人から伸びていきます🎤"),
    "mixvoice_want": ("ミックスの前に、裏声そのものは安定していますか？弱い裏声に芯を足すより、"
                      "まず“揺れない裏声”を育てるのが最短のことが多いです。小さな「フー」の"
                      "ロングトーンから試してみてください😌"),
    "karaoke_up": ("カラオケ上達は選曲が半分です。今のキーで楽に歌える曲で「語尾を丁寧に処理する」"
                   "だけでも聴こえ方が変わりますよ。背伸びキーはその後で🎤"),
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
_GENERIC = "歌の悩みは原因が分かると一気に楽になります。焦らず1つずつで大丈夫ですよ🎤"

_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_KATA_RE = re.compile(r"[ァ-ヶー]{3,}")

# 下書きに出てよいカタカナ語（発声・練習の一般用語のみ）。歌手名は絶対に入れない。
VOCAL_TERMS = frozenset({
    "ミックスボイス", "ファルセット", "ハミング", "リップロール", "リップトリル",
    "ロングトーン", "ビブラート", "カラオケ", "ピアノ", "ピッチ", "ブレス",
    "ウォーミングアップ", "ウォームアップ", "トレーニング", "レッスン", "メロディ",
    "フレーズ", "リズム", "テンポ", "バランス", "イメージ", "ポイント", "コントロール",
    "アプリ", "マイク", "スマホ", "ストロー", "ペース", "スタート", "アドバイス",
    "ブレンド", "フクロウ", "サイン", "コツコツ", "オッケー",
})

# 宣伝・誘導・自己言及の禁止語（返信は価値提供のみ。誘導はプロフィール固定に任せる）
_BANNED_WORDS = ("フォロー", "プロフ", "リンク", "登録", "診断できます", "ソラ先生")

# 医療的断定の禁止語（voice-health 方針: 診断はしない。休む・受診を促すまで）
_MEDICAL_WORDS = ("結節", "ポリープ", "炎症です", "症です")


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


def _artist_names() -> tuple[str, ...]:
    """themes.ARTISTS_BY_ID の実名一覧（表記そのまま禁止。括弧付き表記は中身も見る）。"""
    try:
        import themes
        names = []
        for pair in themes.ARTISTS_BY_ID.values():
            for lst in pair.values():
                names.extend(lst)
        return tuple(names)
    except Exception:
        return ()


def validate(text: str, source_text: str) -> tuple[bool, str]:
    """下書き1件の検証。returns (ok, reason)。プロンプト任せにしない最終ゲート。"""
    t = (text or "").strip()
    if not (10 <= len(t) <= 120):
        return False, f"長さ{len(t)}が範囲外(10〜120)"
    if _URL_RE.search(t):
        return False, "URLを含む"
    if "#" in t or "@" in t:
        return False, "ハッシュタグ/メンションを含む"
    for w in _BANNED_WORDS:
        if w in t:
            return False, f"宣伝・誘導語（{w}）"
    for w in _MEDICAL_WORDS:
        if w in t:
            return False, f"医療的断定（{w}）"
    for name in _artist_names():
        if name and name in t:
            return False, f"歌手名（{name}）"
    # 固有名詞ガード: 相手の文にもホワイトリストにも無いカタカナ語は棄却（安全側）
    allowed = set(_KATA_RE.findall(source_text or "")) | set(VOCAL_TERMS)
    unknown = [k for k in _KATA_RE.findall(t) if not _covered(k, allowed)]
    if unknown:
        return False, f"未知のカタカナ語（{unknown[0]}）"
    return True, "ok"


def _covered(token: str, allowed: set[str]) -> bool:
    """カタカナ語 token が許可語だけで説明できるか。
    完全一致／許可語の部分列（例:「ミックス」⊂「ミックスボイス」）／
    許可語の連結（例:「ピアノアプリ」＝ピアノ+アプリ）を許す。
    「ヨルシカアプリ」のように許可語を除いても残りが出るものは不許可。"""
    if token in allowed or any(token in v for v in allowed):
        return True
    rest = token
    for v in sorted(allowed, key=len, reverse=True):
        if v and v in rest:
            rest = rest.replace(v, "")
    return not rest.strip("ー・")


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
            "- 歌手名・アーティスト名・商品名は出さない\n"
            "- 医療的断定（〜症です等）をしない。喉の痛みには無理しない声かけまで\n"
            "- 上から目線・媚び・絵文字の多用をしない（絵文字は最大1つ）\n"
            "返信文だけを出力してください（前置き・引用符なし）。"
        )
        resp = client.models.generate_content(model=model, contents=prompt)
        return strip_urls((resp.text or "").strip()) or None
    except Exception as e:
        print(f"[warn] Gemini返信生成に失敗 → テンプレ使用: {e}", file=sys.stderr)
        return None


def draft(source_text: str, query_id: str) -> tuple[str, str]:
    """返信下書きを1件返す。returns (text, origin) — origin は "gemini" | "template"。

    Gemini生成 → validate() 棄却ならテンプレへ。テンプレも validate() を通し、
    万一落ちたら汎用文（_GENERIC）を返す（無音にはしない）。"""
    import leads
    intent = (leads.QUERY_BY_ID.get(query_id) or {}).get("intent", "歌の悩み")
    text = _gemini_draft(source_text, intent)
    if text:
        ok, reason = validate(text, source_text)
        if ok:
            return text, "gemini"
        print(f"[info] Gemini下書きを棄却（{reason}）→ テンプレ使用", file=sys.stderr)
    tpl = TEMPLATES.get(query_id, _GENERIC)
    ok, reason = validate(tpl, source_text)
    if not ok:
        print(f"[warn] テンプレが検証に落ちました（{reason}/{query_id}）。汎用文を使用",
              file=sys.stderr)
        return _GENERIC, "template"
    return tpl, "template"
