"""TikTok自動生成のコンテンツ定義。歌声サンプル不要・Tips型のみで全自動化。

設計方針:
- 歌デモ・画面録画ゼロ。テキスト+TTS(ElevenLabs)+自動字幕だけで動画が完結する。
- フックは煽り強め: 断定・常識否定・限定。1〜2秒で指を止めることを最優先。
  誇大表現は禁止だが、鋭い事実を言い切る形はOK（「プロになれる」NG / 「やり方が間違ってる」OK）。
- 動画の尺・テロップ密度は trends.py が検出したトレンドに寄せる（構造模倣。他者映像の転載なし）。
- リンクは動画内・キャプションに貼れない前提（TikTok仕様）。CTAは「プロフィールから」固定。
"""

APP_URL_DEFAULT = "https://sora-vocal-ai.duckdns.org"

# 8つの声タイプ（診断ページと一致。sns_autopost/themes.py と同期）
VOICE_TYPES = [
    ("Rock",       "🔥", "芯のある地声でまっすぐ前に出るパワフルな声"),
    ("Groovy",     "🎙", "太く温かい、うねるような厚みのある声"),
    ("Pop",        "🌤", "自然体で親しみやすい、軽やかで明るい声"),
    ("Mysterious", "🌒", "翳りのある深い声。浮遊感と余韻をまとう"),
    ("Crystal",    "💎", "高く抜ける裏声に芯がある、きらびやかな声"),
    ("Dramatic",   "🎭", "裏声に情感と伸び。切なく響くドラマチックな声"),
    ("Whisper",    "🍃", "やわらかく透明な裏声。そっと寄り添う声"),
    ("Moody",      "🌙", "息まじりの深い裏声。しっとり包み込む大人の声"),
]

# Tips型ネタ（hook 1行 + body リスト）。
# hook = 大テロップ（1.5秒）。煽り強め: 断定・常識否定・限定。
# body = 1行ずつ均等割りで表示。テンポ最優先、1行15文字前後。
TIPS = [
    # ── 高音 ──
    {"hook": "まだ喉で高音出そうとしてる?",
     "body": ["力むほど声帯が分厚くなって詰まる。",
              "高音は力を抜くほど出やすい。",
              "'ネイ'で低→高にスライドするだけ。",
              "喉を締めず、鼻の奥に引っかける感覚。"]},
    {"hook": "喉を開けば高音出るは嘘",
     "body": ["開きすぎると息が抜けてスカスカになる。",
              "正解は閉じる場所と息の圧のバランス。",
              "試して→'ギ'で裏声サイレン。",
              "このとき力まないのが絶対条件。"]},
    {"hook": "サビで毎回裏返る人、原因はここ",
     "body": ["地声でそのまま上に引っぱってるから。",
              "本来ミックスで運ぶ音域を地声で押してる。",
              "'ネイ'スライドを2週間やるだけで",
              "裏返りが消え始める。"]},

    # ── 音痴・音程 ──
    {"hook": "音痴は才能じゃなくてやり方が間違ってる",
     "body": ["9割は耳がズレを検知できてないだけ。",
              "原曲1フレーズ→ハミングで真似→録音。",
              "あ、ズレたと気づけた時点で半分直ってる。",
              "気づけない間は練習量を増やしても変わらない。"]},
    {"hook": "たくさん歌っても上手くならない理由",
     "body": ["外した音を放置して繰り返すと、ズレごと体に覚えさせる。",
              "直してから反復が鉄則。",
              "1フレーズずつ録音して聴き返す。",
              "これだけで練習の密度が変わる。"]},

    # ── 声の通り・共鳴 ──
    {"hook": "声が通らないのは声量じゃない",
     "body": ["プロが何千人の前でも通る理由は倍音の芯。",
              "2800〜3400Hzの周波数を立てると前に飛ぶ。",
              "喉をやや下げ、声を頬骨に当てる意識。",
              "出すより前に乗せるが正解。"]},
    {"hook": "大きい声で歌うは間違い",
     "body": ["力で押すと喉が締まって声が細くなる。",
              "正解はため息に声を乗せる感覚。",
              "'ハミング→ma'で前に鳴る感覚を探す。",
              "同じ音量でも通り方がまるで変わる。"]},

    # ── ウォームアップ ──
    {"hook": "カラオケ1曲目でバテる人、準備が間違ってる",
     "body": ["声帯は筋肉と粘膜。いきなり高音は傷める。",
              "1. リップロール2分（唇ブルブル）",
              "2. ハミングで低→高スライド",
              "3. 'ニャー'で音域上下。これで後半バテにくくなる。"]},

    # ── ロングトーン・支え ──
    {"hook": "ロングトーンが後半で落ちる人へ",
     "body": ["肺活量の問題じゃない。支えが抜けてるだけ。",
              "息を吸った構えのまま、吐くのをこらえる感覚。",
              "'スー'で細く長く30秒。",
              "お腹の張りを保てると声は最後まで落ちない。"]},

    # ── 録音・自己認識 ──
    {"hook": "録音の自分の声が別人な理由",
     "body": ["骨伝導で聞く声には脳が補正をかけてる。",
              "録音=他人が聞いてる本当の声。",
              "最初に違和感を感じた人ほど伸びが早い。",
              "今日1フレーズ録って聴き返すだけでいい。"]},

    # ── ミックスボイス ──
    {"hook": "ミックスボイス、難しく考えすぎ",
     "body": ["地声と裏声の間を探すだけ。",
              "弱い裏声から、芯を少しずつ足していく。",
              "'ギ'でサイレン（低→高→低）。",
              "繋ぎ目の段差をなくすのがゴール。"]},

    # ── 逆張り系 ──
    {"hook": "ボイトレ動画100本見ても変わらない理由",
     "body": ["知識は増えても自分の今の状態が分からないから。",
              "正しい練習をしてるつもりで、ズレたまま体に入れてる。",
              "1分録音して聴き返す。",
              "これだけで何が足りないかが全部分かる。"]},
    {"hook": "腹式呼吸できれば歌えるは半分嘘",
     "body": ["問題は吸い方じゃなく吐く時に支えを保てるか。",
              "息を吐ききっても腹の張りが残ってる状態が正解。",
              "'ドッグブレス（ハッハッ）'20回で感覚をつかむ。",
              "高音もロングトーンもここが土台。"]},
]

# Tips型オンリー（歌声サンプル・画面録画ゼロ）。
PILLARS = ["tip"] * 7

HASHTAGS_BASE = ["#ボイトレ", "#カラオケ", "#歌ってみた"]
HASHTAGS_TIPS = ["#高音の出し方", "#ボイトレ初心者", "#歌が上手くなる方法",
                 "#ミックスボイス", "#音痴を直したい"]


def pillar_for(weekday: int) -> str:
    return PILLARS[weekday % 7]


def hashtags_for(tip_index: int) -> list[str]:
    """日替わりで HASHTAGS_TIPS から1〜2個足す（マンネリ防止）。計5個以内。"""
    extra = [HASHTAGS_TIPS[tip_index % len(HASHTAGS_TIPS)]]
    nxt = HASHTAGS_TIPS[(tip_index + 3) % len(HASHTAGS_TIPS)]
    if nxt not in extra:
        extra.append(nxt)
    seen, out = set(), []
    for t in HASHTAGS_BASE + extra:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:5]


def storyboard(pillar: str, day_index: int, trend: dict) -> dict:
    """1本ぶんの絵コンテを返す（Tips型固定）。video_assembler が消費する共通フォーマット。"""
    target_sec = int(trend.get("target_duration_sec", 22))
    bgm = trend.get("trending_sound")
    return _tip_storyboard(day_index, target_sec, bgm)


def _tip_storyboard(day_index: int, target_sec: int, bgm) -> dict:
    tip = TIPS[day_index % len(TIPS)]
    body = tip["body"]
    # フック1.5秒（煽りは速攻で刺す）+ 本文均等割り + CTA2.5秒
    hook_sec, cta_sec = 1.5, 2.5
    body_total = max(target_sec - hook_sec - cta_sec, len(body) * 2)
    per = body_total / len(body)
    scenes = [{"t0": 0, "t1": hook_sec, "kind": "hook", "text": tip["hook"], "style": "big"}]
    t = hook_sec
    for line in body:
        scenes.append({"t0": round(t, 2), "t1": round(t + per, 2), "kind": "body", "text": line})
        t += per
    scenes.append({"t0": round(t, 2), "t1": round(t + cta_sec, 2), "kind": "cta",
                   "text": "自分の声を診断したい人→\nプロフィールから無料🎤"})
    narration = tip["hook"] + "。" + "。".join(body)
    return {
        "pillar": "tip", "scenario_tag": None,
        "duration": round(t + cta_sec, 2),
        "bg": {"type": "gradient", "colors": ["#1a0a2e", "#0d0d1a"]},
        "bgm": bgm, "scenes": scenes, "narration": narration,
        "hashtags": hashtags_for(day_index),
        "caption": tip["hook"],
    }


def claude_prompt(storyboard_in: dict) -> str:
    """Claudeに渡す口語リライト指示。テロップ・ナレーションをTikTok向けに磨く。"""
    import json
    return (
        "あなたはAIボイストレーナー『ソラ先生』のTikTok担当です。"
        "以下の絵コンテ(JSON)のテロップ(scenes[].text)とナレーション(narration)を、"
        "短尺TikTok向けに、より自然で指を止める口語にリライトしてください。\n"
        "条件:\n"
        "- 1枚目(kind=hook)は1.5秒で読み切れる強いフック（断定/数字/常識否定）。煽り強めはOK。\n"
        "- テロップは各5〜20文字、改行は最小。テンポ重視。\n"
        "- 効果を誇張しない（'プロになれる'等NG）。鋭い事実はOK。\n"
        "- 各sceneのt0/t1/kindは変更しない。textだけ書き換える。\n"
        "- narrationは全体を読み上げる1〜2文。\n"
        "出力は絵コンテと同じスキーマのJSONのみ（説明文なし）。\n"
        "絵コンテ:\n" + json.dumps(storyboard_in, ensure_ascii=False)
    )
