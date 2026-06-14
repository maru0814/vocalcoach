"""TikTok自動生成のコンテンツ定義（Tips型＋検証型）。docs/34 のフォーマット研究に準拠。

設計方針（docs/34）:
- 顔出し・歌デモなしで全自動化できる2型に絞る。
  - tip  … Tips型テキスト動画（背景＋テロップ＋ナレーション＋自動字幕）。素材生成ゼロ。
  - demo … 検証型（フック→アプリ画面録画クリップ→結果→CTA）。clipは事前収録プールから選ぶ。
- 動画の「型（フォーマット）」は trends.py が検出したトレンドに寄せる（パクる＝構造の模倣）。
  実際の他者映像・音声は使わない（IP配慮）。寄せるのは尺・フックの言い回し・テロップ密度・トレンド音源ID。
- リンクは動画内・キャプションに貼れない前提（TikTok仕様）。CTAは「プロフィールから」固定。
- 効果を誇張しない（「プロになれる」等NG）。
"""

APP_URL_DEFAULT = "https://sora-vocal-ai.duckdns.org"

# 8つの声タイプ（診断ページと一致。sns_autopost/themes.py と同期）
VOICE_TYPES = [
    ("Rock", "🔥", "芯のある地声でまっすぐ前に出るパワフルな声"),
    ("Groovy", "🎙", "太く温かい、うねるような厚みのある声"),
    ("Pop", "🌤", "自然体で親しみやすい、軽やかで明るい声"),
    ("Mysterious", "🌒", "翳りのある深い声。浮遊感と余韻をまとう"),
    ("Crystal", "💎", "高く抜ける裏声に芯がある、きらびやかな声"),
    ("Dramatic", "🎭", "裏声に情感と伸び。切なく響くドラマチックな声"),
    ("Whisper", "🍃", "やわらかく透明な裏声。そっと寄り添う声"),
    ("Moody", "🌙", "息まじりの深い裏声。しっとり包み込む大人の声"),
]

# Tips型のネタ（フック1行＋本文）。番号付き・断定で“止まる”入りにする。
TIPS = [
    {"hook": "音痴の9割は“喉”じゃなく“耳”",
     "body": ["狙った音と、出した音。", "この2つのズレに気づけてないだけ。",
              "原曲を1フレーズ→ハミングで真似→録音で答え合わせ。", "耳が追いつくと声は後からついてくる。"]},
    {"hook": "高い声が出ないのは“力み”が原因",
     "body": ["高音は“薄い声帯”で出す。", "力むほど声帯が分厚くなって詰まる。",
              "「ネイ」で軽くスライド上昇。", "喉を締めず、鼻の奥に引っかける感覚で。"]},
    {"hook": "ロングトーンが続かない人へ",
     "body": ["肺活量じゃなく“支え”の問題。", "息を吸った構えのまま、吐くのをこらえる。",
              "「スー」で細く長く30秒。", "お腹の張りを保てると、声は最後まで落ちない。"]},
    {"hook": "カラオケ前の“ただ声出し”は逆効果",
     "body": ["声帯は筋肉と粘膜。急な負荷で傷む。", "①リップロール2分", "②ハミングで低→高にスライド",
              "③「ニャー」で音域を上下", "温めてから歌うと後半バテにくい。"]},
    {"hook": "“声が通らない”は声量じゃない",
     "body": ["カギは2800〜3400Hzの倍音（芯）。", "喉をやや下げ、声を鼻の奥・頬骨へ当てる。",
              "「ハミング→ma me mi」で当て感を探す。", "“出す”より“前に乗せる”が正解。"]},
    {"hook": "録音した自分の声が別人に聞こえる理由",
     "body": ["骨伝導で聞く自分の声に脳が補正をかけてる。", "録音＝他人が聞く本当の声。",
              "違和感に気づけた時点で伸びしろ。", "まずは1フレーズ録って聴き返すだけでいい。"]},
    {"hook": "ミックスボイスの掴み方",
     "body": ["地声と裏声の“間”を探す作業。", "弱い裏声から、地声の芯を少しだけ足す。",
              "「ギ」でサイレン（低→高→低）。", "切れ目を段差なくつなぐのがゴール。"]},
]

# 検証型のネタ。アプリ操作の画面録画（demo_clips）に被せるフック＋結果テロップ。
DEMO_SCENARIOS = [
    {"hook": "AIに自分の歌を診断させたら辛口だった", "tag": "diagnose",
     "result": ["声タイプと似た声質の歌手", "今日直す1か所", "まで15秒で返ってきた"]},
    {"hook": "地声と裏声、AIは聞き分けられるのか", "tag": "register",
     "result": ["地声→ミックス→裏声", "声区の切り替わりを", "AIがちゃんと検出した"]},
    {"hook": "わざと音を外したらAIにバレるのか", "tag": "pitch",
     "result": ["外した区間を秒単位で指摘", "“どっちにズレたか”まで", "可視化された"]},
    {"hook": "15秒歌うだけで似てる歌手が分かる", "tag": "similar",
     "result": ["声質を8タイプで分類", "近い声の歌手を提示", "結果はそのままシェアできる"]},
]

# 投稿の柱（曜日 → 型）。docs/34 §3 のカレンダーに準拠（週4本想定でも毎日回せる配列）。
# demo（検証型）を看板に厚め配置。tip はテキストのみで量産が効くので谷を埋める。
PILLARS = [
    "demo",  # 月: 検証型（看板）
    "tip",   # 火: Tips型
    "demo",  # 水: 検証型
    "tip",   # 木: Tips型
    "demo",  # 金: 検証型
    "tip",   # 土: Tips型
    "demo",  # 日: 検証型（ビジュアル枠）
]

HASHTAGS_BASE = ["#ボイトレ", "#歌ってみた", "#カラオケ"]
HASHTAGS_BY_PILLAR = {
    "tip": ["#ボイトレ初心者", "#歌が上手くなる方法"],
    "demo": ["#声診断", "#AI"],
}


def pillar_for(weekday: int) -> str:
    """曜日(0=月)から投稿の型を返す。"""
    return PILLARS[weekday % 7]


def hashtags_for(pillar: str, scenario_tag: str | None = None) -> list[str]:
    tags = list(HASHTAGS_BASE) + HASHTAGS_BY_PILLAR.get(pillar, [])
    if scenario_tag == "diagnose" or scenario_tag == "similar":
        tags.append("#声タイプ診断")
    # 重複除去（順序保持）。TikTokは3〜5個が目安（docs/34 §4）。
    seen, out = set(), []
    for t in tags:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:5]


def storyboard(pillar: str, day_index: int, trend: dict) -> dict:
    """1本ぶんの絵コンテ（storyboard）を返す。video_assembler が消費する共通フォーマット。

    trend: trends.py が返す型プロファイル。尺・テロップ密度・トレンド音源を反映（パクる＝構造模倣）。
    """
    target_sec = int(trend.get("target_duration_sec", 22))
    bgm = trend.get("trending_sound")  # 公式APIで許諾された音源ID or ローカルBGMパス or None

    if pillar == "tip":
        return _tip_storyboard(day_index, target_sec, bgm)
    return _demo_storyboard(day_index, target_sec, bgm)


def _tip_storyboard(day_index: int, target_sec: int, bgm) -> dict:
    tip = TIPS[day_index % len(TIPS)]
    body = tip["body"]
    # フック2秒 + 本文を均等割り + CTA3秒
    cta_sec = 3
    hook_sec = 2
    body_total = max(target_sec - hook_sec - cta_sec, len(body) * 2)
    per = body_total / len(body)
    scenes = [{"t0": 0, "t1": hook_sec, "kind": "hook", "text": tip["hook"], "style": "big"}]
    t = hook_sec
    for line in body:
        scenes.append({"t0": round(t, 2), "t1": round(t + per, 2), "kind": "body", "text": line})
        t += per
    scenes.append({"t0": round(t, 2), "t1": round(t + cta_sec, 2), "kind": "cta",
                   "text": "録音を送るとAIが添削🎤\nプロフィールから無料で"})
    narration = tip["hook"] + "。" + "".join(body)
    return {
        "pillar": "tip", "scenario_tag": None,
        "duration": round(t + cta_sec, 2),
        "bg": {"type": "gradient", "colors": ["#1b2a4a", "#0d1424"]},
        "bgm": bgm, "scenes": scenes, "narration": narration,
        "hashtags": hashtags_for("tip"),
        "caption": f"{tip['hook']}🎤 #ソラ先生",
    }


def _demo_storyboard(day_index: int, target_sec: int, bgm) -> dict:
    sc = DEMO_SCENARIOS[day_index % len(DEMO_SCENARIOS)]
    hook_sec, result_sec, cta_sec = 2.5, 6.0, 3.0
    clip_sec = max(target_sec - hook_sec - result_sec - cta_sec, 6.0)
    t = 0.0
    scenes = [{"t0": 0, "t1": hook_sec, "kind": "hook", "text": sc["hook"], "style": "big"}]
    t = hook_sec
    # 検証型のキモ＝アプリ操作の画面録画。プールから tag 一致を選ぶ（無ければ assembler が代替背景）。
    scenes.append({"t0": round(t, 2), "t1": round(t + clip_sec, 2), "kind": "clip",
                   "clip_tag": sc["tag"], "text": ""})
    t += clip_sec
    for i, line in enumerate(sc["result"]):
        seg = result_sec / len(sc["result"])
        scenes.append({"t0": round(t, 2), "t1": round(t + seg, 2), "kind": "result", "text": line})
        t += seg
    scenes.append({"t0": round(t, 2), "t1": round(t + cta_sec, 2), "kind": "cta",
                   "text": "あなたの声は何タイプ？\nプロフィールから無料診断🎤"})
    narration = sc["hook"] + "。" + "。".join(sc["result"])
    return {
        "pillar": "demo", "scenario_tag": sc["tag"],
        "duration": round(t + cta_sec, 2),
        "bg": {"type": "gradient", "colors": ["#2a1b4a", "#0d1424"]},
        "bgm": bgm, "scenes": scenes, "narration": narration,
        "hashtags": hashtags_for("demo", sc["tag"]),
        "caption": f"{sc['hook']}🎤 結果は…👀 #ソラ先生",
    }


def claude_prompt(storyboard_in: dict) -> str:
    """Claudeに渡す“絵コンテのリライト指示”。テロップとナレーションを自然な口語へ。

    返ってきたJSONで scenes[*].text と narration を差し替える（失敗時は元の絵コンテのまま）。
    """
    import json
    return (
        "あなたはAIボイストレーナー『ソラ先生』のTikTok担当です。"
        "以下の絵コンテ(JSON)のテロップ(scenes[].text)とナレーション(narration)を、"
        "短尺TikTok向けに、より自然で“スクロールを止める”口語にリライトしてください。\n"
        "条件:\n"
        "- 1枚目(kind=hook)は1〜2秒で読み切れる強いフック（断定/数字/共感）。\n"
        "- テロップは各5〜18文字、改行は最小。テンポ重視。\n"
        "- 効果を誇張しない（『プロになれる』等NG）。専門語は最小限。\n"
        "- kind=clip の text は空のまま（画面録画に被せる字幕は付けない）。\n"
        "- 各sceneのt0/t1/kind/clip_tagは変更しない。textだけ書き換える。\n"
        "- narrationは全体を読み上げる1〜3文。\n"
        "出力は絵コンテと同じスキーマのJSONのみ（説明文なし）。\n"
        "絵コンテ:\n" + json.dumps(storyboard_in, ensure_ascii=False)
    )
