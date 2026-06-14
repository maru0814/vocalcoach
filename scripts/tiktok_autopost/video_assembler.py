"""絵コンテ(storyboard) → 縦9:16のMP4 を組み立てる中核。

degrade設計（sns_autopostの流儀）:
- moviepy/ffmpeg があればMP4を描画。
- 無ければ絵コンテJSON＋ナレーション台本を書き出して“何が作られるか”を見せる（安全縮退）。

レイアウト: 1080x1920。背景グラデ＋テロップ（中央寄せ）＋自動字幕の代わりにシーンtextを焼き込む。
検証型(kind=clip)は assets/demo_clips/ の画面録画を被せる。無ければ背景＋「画面録画ここに」を表示。
"""
import glob
import json
import os
import sys

W, H = 1080, 1920
_DIR = os.path.dirname(os.path.abspath(__file__))
CLIPS_DIR = os.path.join(_DIR, "assets", "demo_clips")

# 日本語が描画できるフォント候補（環境にあるものを使う）。
_FONT_CANDIDATES = [
    os.getenv("TIKTOK_FONT", ""),
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
]


def _font() -> str | None:
    for f in _FONT_CANDIDATES:
        if f and os.path.exists(f):
            return f
    return None


def _try_moviepy():
    try:
        import moviepy  # noqa: F401
        return True
    except Exception:
        return False


def _pick_clip(tag: str | None) -> str | None:
    """demo_clips からタグ一致（無ければ任意）の画面録画を選ぶ。"""
    if not os.path.isdir(CLIPS_DIR):
        return None
    pats = []
    if tag:
        pats += sorted(glob.glob(os.path.join(CLIPS_DIR, f"{tag}*.mp4")))
    pats += sorted(glob.glob(os.path.join(CLIPS_DIR, "*.mp4")))
    return pats[0] if pats else None


# ── moviepy 1.x / 2.x 両対応の薄いシム ───────────────────────────────
def _mp():
    import moviepy.editor as mpy  # 1.x。2.xでも editor シムが入ることが多い
    return mpy


def _set_dur(clip, d):
    return clip.with_duration(d) if hasattr(clip, "with_duration") else clip.set_duration(d)


def _set_start(clip, t):
    return clip.with_start(t) if hasattr(clip, "with_start") else clip.set_start(t)


def _set_pos(clip, p):
    return clip.with_position(p) if hasattr(clip, "with_position") else clip.set_position(p)


def _set_audio(clip, a):
    return clip.with_audio(a) if hasattr(clip, "with_audio") else clip.set_audio(a)


def _bg_clip(mpy, colors, duration):
    """単色（暗）背景。グラデは依存を増やすため上下2色の平均色で近似。"""
    def hx(c):
        c = c.lstrip("#")
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    a, b = hx(colors[0]), hx(colors[-1])
    avg = tuple((x + y) // 2 for x, y in zip(a, b))
    return _set_dur(mpy.ColorClip(size=(W, H), color=avg), duration)


def _text_clip(mpy, text, font, big=False):
    if not text:
        return None
    size = 92 if big else 64
    kwargs = dict(text=text, font=font, font_size=size, color="white",
                  method="caption", size=(int(W * 0.82), None), text_align="center")
    try:
        return mpy.TextClip(**kwargs)
    except TypeError:
        # 旧API（font_size→fontsize, text→txt, text_align無し）
        return mpy.TextClip(txt=text, font=font, fontsize=size, color="white",
                            method="caption", size=(int(W * 0.82), None), align="center")


def render(storyboard: dict, narration_audio: str | None, out_path: str) -> dict:
    """絵コンテをMP4に描画。returns {ok, mode, path, note}。"""
    font = _font()
    if not _try_moviepy() or font is None:
        return _emit_storyboard(storyboard, narration_audio, out_path,
                                note=("moviepy未導入" if not _try_moviepy()
                                      else "日本語フォント未検出"))
    try:
        mpy = _mp()
        duration = float(storyboard["duration"])
        layers = [_bg_clip(mpy, storyboard["bg"]["colors"], duration)]

        for sc in storyboard["scenes"]:
            t0, t1 = float(sc["t0"]), float(sc["t1"])
            seg = max(t1 - t0, 0.3)
            if sc["kind"] == "clip":
                clip_path = _pick_clip(sc.get("clip_tag"))
                if clip_path:
                    v = mpy.VideoFileClip(clip_path).without_audio()
                    v = _set_dur(v, min(seg, v.duration))
                    v = v.resized(width=W) if hasattr(v, "resized") else v.resize(width=W)
                    v = _set_start(_set_pos(v, ("center", "center")), t0)
                    layers.append(v)
                else:
                    ph = _text_clip(mpy, "▶ アプリ画面録画\n(demo_clips に配置)", font)
                    if ph:
                        layers.append(_set_start(_set_pos(_set_dur(ph, seg), "center"), t0))
                continue
            tc = _text_clip(mpy, sc.get("text", ""), font, big=(sc.get("style") == "big"))
            if tc:
                pos = ("center", "center") if sc["kind"] != "cta" else ("center", int(H * 0.72))
                layers.append(_set_start(_set_pos(_set_dur(tc, seg), pos), t0))

        comp = mpy.CompositeVideoClip(layers, size=(W, H))
        comp = _set_dur(comp, duration)

        # 音声: ナレーション＋（あれば）BGMを小さく。
        audio_layers = []
        if narration_audio and os.path.exists(narration_audio):
            audio_layers.append(mpy.AudioFileClip(narration_audio))
        bgm = storyboard.get("bgm")
        if bgm and os.path.exists(str(bgm)):
            a = mpy.AudioFileClip(str(bgm))
            a = a.with_volume_scaled(0.12) if hasattr(a, "with_volume_scaled") else a.volumex(0.12)
            audio_layers.append(_set_dur(a, duration))
        if audio_layers:
            comp = _set_audio(comp, mpy.CompositeAudioClip(audio_layers))

        comp.write_videofile(out_path, fps=30, codec="libx264", audio_codec="aac",
                             preset="medium", threads=2, logger=None)
        return {"ok": True, "mode": "mp4", "path": out_path, "note": "rendered"}
    except Exception as e:
        return _emit_storyboard(storyboard, narration_audio, out_path,
                                note=f"render失敗→絵コンテ出力: {e}")


def _emit_storyboard(storyboard, narration_audio, out_path, note: str) -> dict:
    """MP4が作れない環境向け: 絵コンテJSONと台本を書き出す（人が確認・手動編集できる形）。"""
    base = os.path.splitext(out_path)[0]
    sb_path = base + ".storyboard.json"
    txt_path = base + ".script.txt"
    with open(sb_path, "w", encoding="utf-8") as f:
        json.dump({"note": note, "narration_audio": narration_audio,
                   "storyboard": storyboard}, f, ensure_ascii=False, indent=2)
    lines = [f"# {storyboard['pillar']} / {storyboard['duration']}秒  ({note})", ""]
    for sc in storyboard["scenes"]:
        tag = f"[{sc['t0']:>5}-{sc['t1']:>5}s] {sc['kind']:<6}"
        body = sc.get("text") or (f"<画面録画 tag={sc.get('clip_tag')}>" if sc["kind"] == "clip" else "")
        lines.append(f"{tag} {body.replace(chr(10), ' / ')}")
    lines += ["", "▼ナレーション:", storyboard["narration"],
              "", "▼キャプション:", storyboard["caption"],
              "", "▼ハッシュタグ:", " ".join(storyboard["hashtags"])]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return {"ok": True, "mode": "storyboard", "path": sb_path, "note": note,
            "script": txt_path}


if __name__ == "__main__":
    import themes
    import trends
    sb = themes.storyboard("demo", 0, trends.current_profile())
    res = render(sb, None, os.path.join(_DIR, "out", "preview.mp4"))
    print(json.dumps(res, ensure_ascii=False, indent=2))
