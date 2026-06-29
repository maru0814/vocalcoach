#!/usr/bin/env python3
"""投稿に添付するブランド画像の生成（縦4:5 / 1080x1350）。

方針（main: SNSマーケ判断 / 「キーが無くても動く」を踏襲）:
  背景 = Gemini(Imagen)でブランド背景を生成。失敗・未設定なら Pillow の
         グラデーション背景に自動フォールバック（=画像は必ず出る）。
  文字 = 日本語見出しは AI に焼かせず、必ず Pillow で後から描く
         （画像モデルは日本語を崩すため。事実忠実性・誇張禁止の観点でも安全）。

公開関数:
  build_headline(pillar, text, reply) -> str   … 焼き込む短い見出しを本文から作る
  generate_image(pillar, headline, out_path) -> str | None
                                               … PNGを出力しパスを返す。作れなければ None

環境変数:
  SNS_IMAGE=1            … 画像添付の総スイッチ（既定ON。0で従来どおり画像なし）
  SNS_IMAGE_AI=1         … AI背景を試す（既定ON。0でPillowグラデ固定。キー無しでも自動でグラデ）
  SNS_IMAGE_MODEL=imagen-3.0-generate-002   … Geminiの画像モデル
  SNS_FONT_PATH=/path/to/font.ttf|otf|ttc   … 日本語フォント（丸ゴシック推奨）
  GEMINI_API_KEY=...     … AI背景生成にだけ使用（無ければグラデ）
"""
import os
import re
import sys

# 4:5 縦（Xのフィードで縦長が映える）
WIDTH, HEIGHT = 1080, 1350

# ブランドのグラデ（紫→ピンク）。globals.css / tailwind.config と一致。
C_VIOLET = (124, 58, 237)   # #7c3aed
C_PURPLE = (139, 92, 246)   # #8b5cf6
C_PINK = (236, 72, 153)     # #ec4899

# 見出しの“眉ラベル”（型ごとの小見出し）。
_EYEBROW = {
    "tip": "今日のボイトレ",
    "contrarian": "ボイトレの誤解",
    "voice_type": "声タイプ図鑑",
    "self_type": "声タイプ診断",
    "visual": "声タイプ診断",
}
_SIGNATURE = "ソラ先生 ・ Vocal Coach"

# 日本語フォント候補（先頭から最初に存在したものを使う）。
_FONT_CANDIDATES = [
    "/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc",          # macOS（丸ゴ＝ブランドに最も近い）
    "/System/Library/Fonts/Hiragino Sans GB.ttc",             # macOS（保険）
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.otf",    # Debian/Ubuntu fonts-noto-cjk
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]


def _truthy(v: str | None, default: bool) -> bool:
    s = str(v).strip().lower() if v is not None else ""
    if s == "":
        return default
    return s in ("1", "true", "yes", "on")


def _font_path() -> str | None:
    env = os.getenv("SNS_FONT_PATH")
    if env and os.path.exists(env):
        return env
    # 同梱フォント（assets/fonts/ に置けば最優先で拾う）
    assets = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")
    if os.path.isdir(assets):
        for fn in sorted(os.listdir(assets)):
            if fn.lower().endswith((".ttf", ".otf", ".ttc")):
                return os.path.join(assets, fn)
    for p in _FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


_EMOJI_RE = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF"
    "\U0001F000-\U0001F0FF" "\U00002190-\U000021FF"
    "\U0000FE00-\U0000FE0F" "\U00002B00-\U00002BFF" "\U0000200D]",
    flags=re.UNICODE,
)


def _strip_emoji(s: str) -> str:
    return _EMOJI_RE.sub("", s)


def build_headline(pillar: str, text: str, reply: str | None) -> str:
    """画像に焼く短い見出しを作る。短く punchy なテンプレ文（curated）を渡す想定。
    NUDGE（👇…）やリンク誘導行は落とし、文単位で ~34字に詰めて整える（長ければ … で省略）。"""
    h = _strip_emoji((text or "").split("👇")[0])
    lines = [ln.strip() for ln in h.splitlines() if ln.strip()]
    # 「プロフィールから…」等の誘導行は見出しに不要なので除く
    lines = [ln for ln in lines if "プロフィ" not in ln and "診断できます" not in ln]

    # 改行が“意味のある2行見出し”ならそのまま活かす（逆張りの「誤解↑ウソです」等）。
    if len(lines) >= 2 and all(len(ln) <= 22 for ln in lines[:2]):
        return "\n".join(lines[:2])

    flat = " ".join(lines).strip() or "歌が、もっと好きになる。"
    parts = [p.strip() for p in re.split(r"(?<=[。！？…])", flat) if p.strip()]
    head = ""
    for p in parts:
        if head and len(head) + len(p) > 34:
            break
        head += p
        if len(head) >= 20:  # 1文で十分な長さになったら止める
            break
    head = head or flat
    if len(head) > 40:
        head = head[:38].rstrip("、,） ") + "…"
    return head


# ---- 背景: Pillow グラデーション（フォールバック兼デフォルト）----

def _lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _gradient_bg():
    from PIL import Image, ImageDraw, ImageFilter
    # 縦3ストップのグラデを 1px 幅で作って引き伸ばす（高速）。
    stops = [(0.0, C_VIOLET), (0.52, C_PURPLE), (1.0, C_PINK)]
    col = Image.new("RGB", (1, HEIGHT))
    px = col.load()
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]
            p1, c1 = stops[i + 1]
            if p0 <= t <= p1:
                px[0, y] = _lerp(c0, c1, (t - p0) / (p1 - p0))
                break
    img = col.resize((WIDTH, HEIGHT))
    # 上部にやわらかい光（スタジオ風）。
    glow = Image.new("L", (WIDTH, HEIGHT), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([WIDTH * 0.1, -HEIGHT * 0.25, WIDTH * 1.05, HEIGHT * 0.5], fill=90)
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    white = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))
    img = Image.composite(white, img, glow)
    return img


# ---- 背景: Gemini(Imagen) ----

def _ai_prompt(pillar: str) -> str:
    motif = {
        "tip": "a soft rising arc of light gliding upward, a small glowing orb travelling along it",
        "contrarian": "two gentle ribbons of light braiding into one seamless continuous line",
        "voice_type": "eight soft floating orbs of light in a gentle arc, each a different soft hue",
        "self_type": "a soft luminous microphone silhouette dissolving into light particles",
        "visual": "a soft luminous microphone silhouette dissolving into light particles",
    }.get(pillar, "a soft rising arc of light")
    return (
        "Soft, dreamy vocal-studio aesthetic. Smooth gradient flowing from violet "
        "#7c3aed through #8b5cf6 into pink #ec4899, gentle radial glow, airy and calm. "
        "Rounded, friendly, kawaii-minimal flat illustration (rounded Japanese gothic mood). "
        f"Scene: {motif}, anchored to the lower area. "
        "Subtle grain, soft bokeh light, premium and clean. Vertical 4:5 composition. "
        "Leave the upper ~60% as calm negative space. "
        "Absolutely no text, no letters, no words, no watermark, no logo."
    )


def _inline_image_bytes(resp) -> bytes | None:
    """generateContent 系（gemini-*-image）のレスポンスからインライン画像を取り出す。"""
    for cand in getattr(resp, "candidates", None) or []:
        content = getattr(cand, "content", None)
        for part in getattr(content, "parts", None) or []:
            inline = getattr(part, "inline_data", None)
            if inline and getattr(inline, "data", None):
                return inline.data
    return None


def _ai_bg(pillar: str):
    """Geminiでブランド背景を生成。失敗・未設定なら None（→グラデにフォールバック）。
    モデル名に 'imagen' を含めば predict(generate_images)、それ以外（gemini-*-image）は
    generateContent でインライン画像を取り出す。両系統に対応。"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    # 既定は安価・高速で predict 対応の Imagen 4 fast。
    model = os.getenv("SNS_IMAGE_MODEL", "imagen-4.0-fast-generate-001")
    try:
        import io

        from google import genai
        from PIL import Image

        client = genai.Client(api_key=api_key)
        prompt = _ai_prompt(pillar)
        if "imagen" in model.lower():
            from google.genai import types
            resp = client.models.generate_images(
                model=model, prompt=prompt,
                config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="3:4"))
            gen = getattr(resp, "generated_images", None)
            data = gen[0].image.image_bytes if gen else None
        else:  # gemini-*-image（generateContent でインライン画像）
            resp = client.models.generate_content(model=model, contents=prompt)
            data = _inline_image_bytes(resp)
        if not data:
            print("[warn] AI背景の応答に画像が無い → グラデ背景にフォールバック", file=sys.stderr)
            return None
        img = Image.open(io.BytesIO(data)).convert("RGB")
        return img.resize((WIDTH, HEIGHT))
    except Exception as e:  # SDK差異・モデル未許可・ネットワーク等は全部グラデへ
        print(f"[warn] AI背景の生成に失敗 → グラデ背景にフォールバック: {e}", file=sys.stderr)
        return None


# ---- 文字の焼き込み ----

def _load_font(path: str, size: int):
    from PIL import ImageFont
    # .ttc は index 0 を使う
    return ImageFont.truetype(path, size=size, index=0)


def _wrap(draw, text: str, font, max_w: int) -> list[str]:
    out: list[str] = []
    for raw in text.splitlines():
        if not raw:
            continue
        line = ""
        for ch in raw:
            trial = line + ch
            if draw.textlength(trial, font=font) <= max_w or not line:
                line = trial
            else:
                out.append(line)
                line = ch
        out.append(line)
    return out


def _draw_text(img, headline: str, eyebrow: str):
    from PIL import Image, ImageDraw, ImageFilter
    font_path = _font_path()
    if not font_path:
        print("[warn] 日本語フォントが見つからない（SNS_FONT_PATH 未設定）→ 文字なしで出力",
              file=sys.stderr)
        return img

    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    margin = int(WIDTH * 0.09)
    max_w = WIDTH - margin * 2

    # 見出し: 入る最大サイズへ自動調整（最大3行に収める）。
    size = 96
    while size >= 52:
        font = _load_font(font_path, size)
        lines = _wrap(draw, headline, font, max_w)
        line_h = int(size * 1.34)
        if len(lines) <= 3:
            break
        size -= 6
    font = _load_font(font_path, size)
    lines = _wrap(draw, headline, font, max_w)[:3]
    line_h = int(size * 1.34)

    eb_font = _load_font(font_path, 40)
    sig_font = _load_font(font_path, 38)

    top = int(HEIGHT * 0.12)
    eyebrow_y = top
    if eyebrow:
        top += int(40 * 1.7)

    # 影レイヤー（眉＋見出しをまとめてぼかして“やわらかい影”にする）
    if eyebrow:
        draw.text((margin + 2, eyebrow_y + 3), eyebrow, font=eb_font, fill=(60, 20, 90, 120))
    y = top
    for ln in lines:
        draw.text((margin + 3, y + 4), ln, font=font, fill=(60, 20, 90, 150))
        y += line_h
    blur = layer.filter(ImageFilter.GaussianBlur(6))
    out = Image.alpha_composite(img.convert("RGBA"), blur)

    # 本体（くっきり）
    draw2 = ImageDraw.Draw(out)
    if eyebrow:
        draw2.text((margin, eyebrow_y), eyebrow, font=eb_font, fill=(255, 255, 255, 235))
    y = top
    for ln in lines:
        draw2.text((margin, y), ln, font=font, fill=(255, 255, 255, 255))
        y += line_h

    # 署名（下中央）
    sig_w = draw2.textlength(_SIGNATURE, font=sig_font)
    draw2.text(((WIDTH - sig_w) / 2, HEIGHT - int(HEIGHT * 0.075)),
               _SIGNATURE, font=sig_font, fill=(255, 255, 255, 220))
    return out.convert("RGB")


def generate_image(pillar: str, headline: str, out_path: str) -> str | None:
    """ブランド画像PNGを out_path に書き出してパスを返す。作れなければ None。"""
    if not _truthy(os.getenv("SNS_IMAGE"), default=True):
        return None
    try:
        bg = None
        if _truthy(os.getenv("SNS_IMAGE_AI"), default=True):
            bg = _ai_bg(pillar)
        if bg is None:
            bg = _gradient_bg()
        img = _draw_text(bg, headline, _EYEBROW.get(pillar, ""))
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        img.save(out_path, format="PNG")
        return out_path
    except Exception as e:
        print(f"[warn] 画像生成に失敗 → 画像なしで投稿: {e}", file=sys.stderr)
        return None


if __name__ == "__main__":
    # 手動確認: python images.py [pillar] [out.png]
    pl = sys.argv[1] if len(sys.argv) > 1 else "tip"
    op = sys.argv[2] if len(sys.argv) > 2 else "/tmp/sns_preview.png"
    hl = build_headline(pl, "高い声がいきなり裏返る人へ。\n力まず“芯を1滴”足すのがコツ。👇 手順はリプに。", None)
    print("headline:", repr(hl))
    print("saved:", generate_image(pl, hl, op))
