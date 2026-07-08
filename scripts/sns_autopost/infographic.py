#!/usr/bin/env python3
"""図解インフォグラフィック生成（tip / contrarian）。

themes.py の TIPS / CONTRARIAN 文字列を構造化して templates/infographic.html に
流し込み、Playwright で 1600x900 をスクショ→PNG にする。日本語は全て HTML 側で
描画するため崩れない。Playwright未導入/失敗時は None を返し、呼び出し側
（generate_and_post.build_image）が images.py のカード生成にフォールバックする。

公開関数:
  parse_tip(text) -> dict           … TIPS文字列 → 描画データ
  parse_contrarian(hook, body) -> dict
  render(data, out_path) -> str|None … HTMLレンダラ（純粋）
  generate(pillar, day_index, app_url, out_path) -> str|None … オーケストレータ
"""
import base64
import json
import math
import os
import re
import sys

import themes

_DIR = os.path.dirname(os.path.abspath(__file__))
_TEMPLATE = os.path.join(_DIR, "templates", "infographic.html")
_CHAR_DIR = os.path.join(_DIR, "assets", "characters", "sora")
_FONT_DIR = os.path.join(_DIR, "assets", "fonts")
_VOICE_DIR = os.path.join(_DIR, "assets", "voice_types")  # 各声タイプの実画像 {id}.jpg

_NUM_RE = re.compile(r"^[①-⑳]\s*")
_QUOTE_RE = re.compile(r"[「『“”\"]([^「『”\"」』]{1,16})[」』”\"]")

# ステップ本文 → アイコン名（templates/infographic.html の ICONS と一致）
_ICON_KEYWORDS = [
    (("息", "ブレス", "吐", "吸", "支え", "ため息"), "lungs"),
    (("半音", "スケール", "音域", "上げ", "上下"), "stairs"),
    (("響", "鼻", "マスク", "当て", "眉間", "共鳴"), "wave"),
    (("脱力", "力", "あくび", "リップロール", "プルプル"), "feather"),
    (("フー", "ホー", "裏声", "ロングトーン", "伸ば", "声"), "mic"),
]
_ICON_CYCLE = ["mic", "stairs", "wave", "feather"]

# 短いタグ語（あれば右に小ラベル）
_TAGS = ["脱力", "半音ずつ", "息漏れ", "支え", "鼻腔", "毎日1分", "切れ目なし"]


def _icon_for(text: str, idx: int) -> str:
    for kws, name in _ICON_KEYWORDS:
        if any(k in text for k in kws):
            return name
    return _ICON_CYCLE[idx % len(_ICON_CYCLE)]


def _tag_for(text: str) -> str:
    for t in _TAGS:
        if t[:2] in text:
            return t
    m = _QUOTE_RE.search(text)
    return m.group(1) if m and len(m.group(1)) <= 5 else ""


def _split_pill(step: str) -> tuple[str, str]:
    """ステップ1行を pill(短い見出し) と body(本文) に分ける。
    短い行は pill のみ（truncate回避）、長い行は見出しを切り出して本文に全文。"""
    step = step.strip()
    # 「…」の閉じまでが短ければ見出しに
    m = re.match(r"^(.{2,16}?[」』”\"])", step)
    if m and 4 <= len(m.group(1)) <= 16 and len(step) > 18:
        return m.group(1), step
    # 読点で切れて左が短ければ見出しに
    if "、" in step:
        left = step.split("、", 1)[0]
        if 3 <= len(left) <= 16 and len(step) > 18:
            return left, step
    if len(step) <= 18:
        return step, ""           # 短い → pill のみ
    return step[:15] + "…", step  # 長く区切れない → 省略見出し＋全文


def _pick_highlight(summary: str) -> str:
    """まとめの中で黄色ハイライトする部分文字列（必ず summary の部分文字列）。"""
    q = _QUOTE_RE.search(summary)
    if q and len(q.group(0)) >= 5:
        return q.group(0)
    first = re.split(r"(?<=[。！？])", summary)[0]
    parts = first.split("、")
    hl = parts[-1].rstrip("。！？ 　")
    return hl if len(hl) >= 4 else first.rstrip("。！？")


def parse_tip(text: str) -> dict:
    """TIPS文字列 → {type, title, subtitle, steps[], summary, highlight, hashtags}。"""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    step_idx = [i for i, ln in enumerate(lines) if _NUM_RE.match(ln)]
    if not step_idx:  # 番号が無い＝想定外。最低限のフォールバック。
        return {"type": "tip", "title": lines[0] if lines else "今日のボイトレ",
                "subtitle": "", "steps": [], "summary": " ".join(lines[1:])[:80],
                "highlight": "", "hashtags": "#ボイトレ"}
    first = step_idx[0]
    head = lines[:first]
    title = head[0] if head else "今日のボイトレ"
    intro = [h.rstrip("↓") for h in head[1:] if h.rstrip("↓")]
    subtitle = " ".join(intro).strip()
    if not subtitle:
        sents = re.split(r"(?<=[。！？])", title)
        if len([s for s in sents if s]) >= 2:
            title = sents[0]
            subtitle = "".join(sents[1:]).strip()
    steps = []
    for i, si in enumerate(step_idx):
        raw = _NUM_RE.sub("", lines[si]).strip()
        pill, body = _split_pill(raw)
        steps.append({"pill": pill, "body": body, "tag": _tag_for(raw),
                      "icon": _icon_for(raw, i)})
    summary = " ".join(lines[step_idx[-1] + 1:]).strip()
    return {"type": "tip", "title": title, "subtitle": subtitle, "steps": steps,
            "summary": summary, "highlight": _pick_highlight(summary) if summary else "",
            "hashtags": "#ボイトレ #ボイストレーニング"}


def parse_contrarian(hook: str, body: str) -> dict:
    """CONTRARIAN(hook, body) → 誤解＋根拠2枚の描画データ。"""
    hlines = [ln.strip() for ln in hook.splitlines() if ln.strip()]
    title = hlines[0] if hlines else "よくある誤解"
    verdict = "半分ウソ"
    for ln in hlines[1:]:
        m = re.search(r"(半分ウソ|ウソ|逆|間違い)", ln)
        if m:
            verdict = "半分ウソ" if "ウソ" in m.group(1) else m.group(1)
            break
    quoted = _QUOTE_RE.findall(body)
    sents = [s.strip() for s in re.split(r"(?<=[。！？])", body) if s.strip()]
    # 鍵を列挙する導入文（両方の語を含む）は落として残りを2分割
    if len(sents) > 2 and len(quoted) >= 2 and all(q in sents[0] for q in quoted[:2]):
        sents = sents[1:]
    half = max(1, math.ceil(len(sents) / 2))
    reasons = [
        {"title": (quoted[0] if quoted else "本当の鍵"), "body": "".join(sents[:half])},
        {"title": (quoted[1] if len(quoted) > 1 else "もう一つの鍵"),
         "body": "".join(sents[half:]) or "".join(sents[:half])},
    ]
    summary = "".join(sents[-2:]) if len(sents) >= 2 else body
    return {"type": "contrarian", "title": title, "verdict": verdict,
            "reasons": reasons, "summary": summary,
            "highlight": _pick_highlight(summary) if summary else "",
            "hashtags": "#ボイトレ #高音"}


def _voice_image_data_uri(type_id: str) -> str:
    """assets/voice_types/{id}.jpg を data URI に。無ければ空文字（HTML側はlabelのみ表示）。"""
    path = os.path.join(_VOICE_DIR, f"{type_id.lower()}.jpg")
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("ascii")


def parse_diagnosis(pillar: str, day_index: int) -> dict:
    """声タイプ診断導線（voice_type/self_type/visual）→ 各タイプの実画像を使う図解データ。
    voice_type=1タイプをヒーロー画像でスポットライト / self_type・visual=8タイプの画像ギャラリー。"""
    if pillar == "voice_type":
        name, _emoji, desc = themes.VOICE_TYPES[day_index % len(themes.VOICE_TYPES)]
        a = themes.ARTISTS_BY_ID.get(name.lower(), {})
        artists = ""
        if a:
            artists = (f"声質が近い例：♀ {'・'.join(a['female'])}"
                       f" ／ ♂ {'・'.join(a['male'])}")
        return {
            "type": "diagnosis",
            "title": f"【{name}】タイプの声、誰に似てる？",
            "subtitle": "",
            "spotlight": {"image": _voice_image_data_uri(name),
                          "desc": f"{desc}。あなたもこのタイプかも？", "artists": artists},
            "cta": {"main": "あなたは何タイプ？プロフィールから無料で診断🎤", "sub": ""},
        }
    # self_type / visual: 8タイプ全部をギャラリーで（各タイプに近い例を♀1＋♂1で短く）
    def _short_artists(type_id: str) -> str:
        a = themes.ARTISTS_BY_ID.get(type_id, {})
        picks = [a.get("female", [""])[0], a.get("male", [""])[0]]
        return "・".join(p for p in picks if p)
    types = [{"name": name, "image": _voice_image_data_uri(name), "featured": False,
              "artists": _short_artists(name.lower())}
             for name, _e, _d in themes.VOICE_TYPES]
    if pillar == "visual":
        title = "あなたの声は、どのタイプ？15秒で診断"
        subtitle = "15秒歌うだけで、AIが8タイプ＋似た声質の歌手まで診断"
        cta = {"main": "プロフィールのリンクから無料で診断🎤", "sub": "結果はそのままシェアOK"}
    else:  # self_type
        title = "あなたの声は、実はこの8タイプのどれか"
        subtitle = "直感でどれっぽい？プロフィールから無料で診断できます"
        cta = {"main": "プロフィールのリンクから無料で診断🎤", "sub": "15秒歌うだけ"}
    return {"type": "diagnosis", "title": title, "subtitle": subtitle,
            "types": types, "cta": cta}


# ---- キャラ / フォント ----

def _char_data_uri(pose: str) -> str:
    path = os.path.join(_CHAR_DIR, f"{pose}.png")
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")


def _font_face_css() -> str | None:
    """assets/fonts に Zen Maru Gothic があればローカル @font-face を返す（オフライン用）。"""
    if not os.path.isdir(_FONT_DIR):
        return None
    faces = []
    for fn in os.listdir(_FONT_DIR):
        low = fn.lower()
        if "maru" not in low and "zen" not in low:
            continue
        weight = 700 if "bold" in low else 500 if "medium" in low else 400
        url = "file://" + os.path.join(_FONT_DIR, fn)
        faces.append(f"@font-face{{font-family:'Zen Maru Gothic';font-weight:{weight};"
                     f"font-display:swap;src:url('{url}');}}")
    return "".join(faces) if faces else None


def _build_html(data: dict) -> str:
    with open(_TEMPLATE, encoding="utf-8") as f:
        html = f.read()
    face = _font_face_css()
    if face:  # オフライン: Google Fonts の @import をローカル @font-face に差し替え
        html = re.sub(r'<style id="font">.*?</style>',
                      f'<style id="font">{face}</style>', html, flags=re.S)
    payload = "window.__DATA__ = " + json.dumps(data, ensure_ascii=False) + ";"
    return html.replace("/*__DATA__*/", payload)


def render(data: dict, out_path: str) -> str | None:
    """データを HTML に注入し .card を 1600x900 でスクショして PNG 保存。失敗で None。"""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("[warn] playwright未導入 → 図解はカードにフォールバック", file=sys.stderr)
        return None
    try:
        html = _build_html(data)
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = browser.new_page(viewport={"width": 1600, "height": 900},
                                    device_scale_factor=1)
            page.set_content(html, wait_until="networkidle")
            page.wait_for_timeout(250)  # フォント/レイアウト確定待ち
            el = page.query_selector(".card")
            if el is None:
                browser.close()
                return None
            el.screenshot(path=out_path)
            browser.close()
        return out_path
    except Exception as e:
        print(f"[warn] 図解レンダリング失敗 → カードにフォールバック: {e}", file=sys.stderr)
        return None


def _steps_from_spec(steps: list) -> list:
    """B(spec)のtip: 生文字列 or 完成dict のどちらでも受け、描画用stepに正規化。"""
    norm = []
    for i, s in enumerate(steps or []):
        if isinstance(s, str):
            raw = _NUM_RE.sub("", s).strip()
            pill, body = _split_pill(raw)
            norm.append({"pill": pill, "body": body, "tag": _tag_for(raw),
                         "icon": _icon_for(raw, i)})
        else:
            norm.append(s)
    return norm


def _data_from_override(pillar: str, override: dict) -> dict:
    """完成稿(--text)用の描画データを作る。
    A: {"mode":"auto","text":..,"reply":..} → 本文/リプを自動構造化（parse_*）。
    B: {"mode":"spec","data":{..}} → 運用者が渡した構造をそのまま使う（誤解/鍵を制御）。"""
    if override.get("mode") == "spec":
        data = dict(override.get("data") or {})
        data.setdefault("type", pillar)
        if data.get("type") == "tip":
            data["steps"] = _steps_from_spec(data.get("steps", []))
        if not data.get("highlight") and data.get("summary"):
            data["highlight"] = _pick_highlight(data["summary"])
        data.setdefault("hashtags",
                        "#ボイトレ #高音" if pillar == "contrarian" else "#ボイトレ #ボイストレーニング")
        return data
    # A: auto
    text = override.get("text") or ""
    reply = override.get("reply")
    if pillar == "contrarian":
        return parse_contrarian(text, reply or text)
    return parse_tip(text)


def build_data(pillar: str, day_index: int, override: dict | None = None) -> dict:
    """レンダリング用データを構築（render は呼ばない＝テスト可能）。
    override があり tip/contrarian のときは完成稿(--text)用に A/B で組む。"""
    if override is not None and pillar in ("tip", "contrarian"):
        data = _data_from_override(pillar, override)
        data["character"] = _char_data_uri("explain")
        return data
    if pillar in ("voice_type", "self_type", "visual"):
        return parse_diagnosis(pillar, day_index)  # 各タイプの実画像を使う図鑑（キャラは無し）
    if pillar == "contrarian":
        hook, body = themes.CONTRARIAN[day_index % len(themes.CONTRARIAN)]
        data = parse_contrarian(hook, body)
    else:  # tip
        tip = themes.TIPS[day_index % len(themes.TIPS)]
        data = parse_tip(tip)
    data["character"] = _char_data_uri("explain")
    return data


def generate(pillar: str, day_index: int, app_url: str, out_path: str,
             override: dict | None = None) -> str | None:
    """pillar に応じてコンテンツを構造化→（tip/contrarianはキャラ添付）→レンダリング。失敗で None。
    override 指定時（--text の完成稿）は A(auto)/B(spec) で描画データを組む。"""
    data = build_data(pillar, day_index, override)
    return render(data, out_path)


if __name__ == "__main__":
    pl = sys.argv[1] if len(sys.argv) > 1 else "tip"
    op = sys.argv[2] if len(sys.argv) > 2 else "/tmp/infographic_preview.png"
    print("data:", json.dumps(
        parse_tip(themes.TIPS[5]) if pl == "tip"
        else parse_contrarian(*themes.CONTRARIAN[0]), ensure_ascii=False, indent=2))
    print("saved:", generate(pl, 5 if pl == "tip" else 0, "https://x.test", op))
