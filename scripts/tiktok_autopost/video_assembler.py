"""絵コンテ(storyboard) → 縦9:16のMP4 を組み立てる中核。

degrade設計（sns_autopostの流儀）:
- moviepy/ffmpeg があればMP4を描画。
- 無ければ絵コンテJSON＋ナレーション台本を書き出して“何が作られるか”を見せる（安全縮退）。

ビジュアル方針（TikTokでスクロールを止める完成度を狙う）:
- 背景: 本物の縦グラデ＋上部グロー（静止＝低スペックVPSでも軽い）。
- 字幕: 黒フチ付きの極太白文字を下からスライドイン(CapCut風)。読みやすさ最優先。
        動きは“毎フレームの拡縮”ではなく位置アニメで出す（描画が重くならない）。
- 強調: ニッチのキーワード(高音/ミックス/力む…)だけ黄色ハイライトで色分け。
- フック: 1.5秒で刺す特大テロップ＋冒頭フラッシュ。
- 補助: 下部の暗いビネット(可読性)。
- 音: ナレーション(ElevenLabs/無音) + assets/bgm/ のフリーBGMを小音量でループ。

検証型(kind=clip)は assets/demo_clips/ の画面録画を被せる。無ければプレースホルダ表示。
"""
import glob
import os
import re
import sys
import json

# 解像度は環境変数で下げられる（低メモリVPSで合成が重い時。720x1280でもTikTokは十分）。
W = int(os.getenv("TIKTOK_W", "1080"))
H = int(os.getenv("TIKTOK_H", "1920"))
_DIR = os.path.dirname(os.path.abspath(__file__))
CLIPS_DIR = os.path.join(_DIR, "assets", "demo_clips")
BGM_DIR = os.path.join(_DIR, "assets", "bgm")
BG_DIR = os.path.join(_DIR, "assets", "bg")   # 焼き込みモーション背景の置き場（make_motion_bg.sh で生成）

ACCENT = "#FFE14D"   # キーワードのハイライト色（黄）

# 字幕でハイライトするニッチのキーワード（長い語を先にマッチさせる）。
KEYWORDS = sorted([
    "ミックスボイス", "ミックス", "裏声", "地声", "高音", "換声点", "声帯", "倍音",
    "リップロール", "ハミング", "力む", "喉", "息", "録音", "音痴", "無料",
    "プロフィール", "診断", "嘘", "間違", "逆", "近道", "原因", "理由", "バランス",
], key=len, reverse=True)
_KW_RE = re.compile("(" + "|".join(re.escape(k) for k in KEYWORDS) + ")")

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


def _resolve_bgm(sb_bgm) -> str | None:
    """BGMを解決する。storyboardが実ファイルパスならそれ、無ければ assets/bgm/ を自動検出。
    trends は音源ID(文字列)を渡してくるが実ファイルでなければ無視 → フリーBGMにフォールバック。"""
    if sb_bgm and os.path.exists(str(sb_bgm)):
        return str(sb_bgm)
    if os.path.isdir(BGM_DIR):
        for ext in ("mp3", "m4a", "wav", "ogg", "aac"):
            files = sorted(glob.glob(os.path.join(BGM_DIR, f"*.{ext}")))
            if files:
                return files[0]
    return None


# ── moviepy 1.x / 2.x 両対応の薄いシム ───────────────────────────────
def _patch_pil():
    """Pillow 10 で Image.ANTIALIAS が廃止され moviepy 1.x の resize が落ちる問題を吸収。"""
    try:
        from PIL import Image
        if not hasattr(Image, "ANTIALIAS"):
            resampling = getattr(Image, "Resampling", Image)
            Image.ANTIALIAS = getattr(resampling, "LANCZOS", 1)
    except Exception:
        pass


def _mp():
    import moviepy.editor as mpy  # 1.x。2.xでも editor シムが入ることが多い
    _patch_pil()
    return mpy


def _set_dur(clip, d):
    return clip.with_duration(d) if hasattr(clip, "with_duration") else clip.set_duration(d)


def _set_start(clip, t):
    return clip.with_start(t) if hasattr(clip, "with_start") else clip.set_start(t)


def _set_pos(clip, p):
    return clip.with_position(p) if hasattr(clip, "with_position") else clip.set_position(p)


def _set_audio(clip, a):
    return clip.with_audio(a) if hasattr(clip, "with_audio") else clip.set_audio(a)


def _set_opacity(clip, o):
    return clip.with_opacity(o) if hasattr(clip, "with_opacity") else clip.set_opacity(o)


def _vol(clip, factor):
    return clip.with_volume_scaled(factor) if hasattr(clip, "with_volume_scaled") \
        else clip.volumex(factor)


def _hx(c):
    c = str(c).lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


# ── 背景: 本物の縦グラデ＋グロー＋ゆっくりズーム ──────────────────────
def _gradient_array(colors):
    """縦グラデ＋上部グローのW×H画像を1回だけ生成（毎フレーム計算しない＝軽い）。"""
    import numpy as np
    top = np.array(_hx(colors[0]), dtype=float)
    bot = np.array(_hx(colors[-1]), dtype=float)
    ramp = np.linspace(0.0, 1.0, H)[:, None]                # H×1
    grad = top[None, :] * (1 - ramp) + bot[None, :] * ramp  # H×3
    img = np.tile(grad[:, None, :], (1, W, 1))              # H×W×3
    # 上部中央に淡いグロー（mgridを使わず外積ブロードキャストで省メモリ）。
    ys = np.linspace(0.0, 1.0, H)[:, None]                  # H×1
    xs = np.linspace(0.0, 1.0, W)[None, :]                  # 1×W
    d = np.sqrt((xs - 0.5) ** 2 + (ys - 0.36) ** 2)         # H×W
    glow = np.clip(1.0 - d * 1.7, 0, 1)[:, :, None] * np.array([20, 70, 80])
    return np.clip(img + glow, 0, 255).astype("uint8")


def _bg_clip(mpy, colors, duration):
    """縦グラデの静止背景（W×Hぴったりで毎フレームの拡縮なし＝低スペックVPSでも軽い）。失敗時は単色。"""
    try:
        arr = _gradient_array(colors)
        return _set_dur(mpy.ImageClip(arr), duration)
    except Exception:
        avg = tuple((a + b) // 2 for a, b in zip(_hx(colors[0]), _hx(colors[-1])))
        return _set_dur(mpy.ColorClip(size=(W, H), color=avg), duration)


def _motion_bg(mpy, duration):
    """焼き込み済みのモーション背景動画(assets/bg/*.mp4等)があれば使う。
    動き(ズーム/ドリフト)は事前にffmpegで焼いてあるので、ここでは“読んで切るだけ”＝毎フレーム計算ゼロ。
    無ければ None（呼び出し側が静止グラデにフォールバック）。"""
    if not os.path.isdir(BG_DIR):
        return None
    files = []
    for ext in ("mp4", "mov", "webm", "mkv"):
        files += sorted(glob.glob(os.path.join(BG_DIR, f"*.{ext}")))
    if not files:
        return None
    try:
        v = mpy.VideoFileClip(files[0]).without_audio()
        d = min(duration, float(v.duration))
        v = v.subclipped(0, d) if hasattr(v, "subclipped") else v.subclip(0, d)
        if int(getattr(v, "w", W)) != W:  # 既に1080幅なら不要なリサイズを避ける（PIL負荷も回避）
            v = v.resized(width=W) if hasattr(v, "resized") else v.resize(width=W)
        v = _set_pos(v, ("center", "center"))
        return _set_dur(v, duration)
    except Exception as e:
        print(f"[warn] モーション背景の読み込み失敗→静止グラデにフォールバック: {e}", file=sys.stderr)
        return None


def _vignette(mpy, duration):
    """下部を暗くして字幕の可読性を上げる半透明オーバーレイ。"""
    try:
        h = int(H * 0.42)
        v = _set_dur(mpy.ColorClip(size=(W, h), color=(0, 0, 0)), duration)
        v = _set_opacity(v, 0.45)
        return _set_pos(v, ("center", H - h))
    except Exception:
        return None


def _flash(mpy, t0, dur=0.12, op=0.55):
    """一瞬の白フラッシュ（カットを“事件”にする）。t0 で開始。"""
    try:
        f = _set_dur(mpy.ColorClip(size=(W, H), color=(255, 255, 255)), dur)
        return _set_start(_set_opacity(f, op), t0)
    except Exception:
        return None


def _dark_overlay(mpy, duration, op=0.30):
    """B-rollの上に敷く全面暗化（明るい実写でも白字幕が読めるように）。"""
    try:
        o = _set_dur(mpy.ColorClip(size=(W, H), color=(0, 0, 0)), duration)
        return _set_opacity(o, op)
    except Exception:
        return None


def _crossfadein(clip, d):
    """カット頭のクロスフェードイン（前カット/背景から溶ける）。版差を吸収。"""
    try:
        from moviepy import vfx
        return clip.with_effects([vfx.CrossFadeIn(d)])
    except Exception:
        pass
    try:
        from moviepy.video.fx.all import crossfadein as _cf
        return _cf(clip, d)
    except Exception:
        pass
    try:
        return clip.crossfadein(d)
    except Exception:
        return clip


def _loop_clip(mpy, clip, d):
    """clip を尺 d に合わせる。短ければループ、長ければ切る。"""
    dur = float(getattr(clip, "duration", d) or d)
    if dur >= d:
        return clip.subclipped(0, d) if hasattr(clip, "subclipped") else clip.subclip(0, d)
    try:
        from moviepy.video.fx.all import loop as _loopfx
        return _set_dur(_loopfx(clip, duration=d), d)
    except Exception:
        return _set_dur(clip, d)


def _broll_clip(mpy, path, t0, seg):
    """正規化済み(1080x1920)のB-rollを、シーン窓[t0, t0+seg]に敷くクリップにする。失敗時 None。"""
    try:
        v = mpy.VideoFileClip(path).without_audio()
        v = _loop_clip(mpy, v, seg)
        if int(getattr(v, "w", W)) != W:   # 焼いてあるので普通は不要。保険でカバー。
            v = v.resized(width=W) if hasattr(v, "resized") else v.resize(width=W)
        v = _set_pos(v, ("center", "center"))
        v = _crossfadein(v, min(0.3, seg / 2.0))
        return _set_start(v, t0)
    except Exception as e:
        print(f"[warn] B-rollクリップ生成失敗: {e}", file=sys.stderr)
        return None


# ── テロップ ────────────────────────────────────────────────────────
def _make_text(mpy, text, font, size, color="white", stroke_w=6, method="caption",
               box_w=None):
    """黒フチ付きテキスト。1.x/2.x のAPI差を吸収。"""
    if not text:
        return None
    common = dict(font=font, color=color, stroke_color="black", stroke_width=stroke_w,
                  method=method)
    if method == "caption":
        common["size"] = (box_w or int(W * 0.82), None)
    try:
        kw = dict(common)
        if method == "caption":
            kw["text_align"] = "center"
        return mpy.TextClip(text=text, font_size=size, **kw)
    except TypeError:
        kw = dict(common)
        if method == "caption":
            kw["align"] = "center"
        return mpy.TextClip(txt=text, fontsize=size, **kw)


def _slide_pos(clip, x, y, rise=48, dur=0.28):
    """下から rise px だけせり上がって着地（ease-out cubic）。x は数値 or 'center'。"""
    if x == "center":
        try:
            x = max(0, (W - clip.w) // 2)
        except Exception:
            x = 0

    def pos(t):
        if t < dur:
            e = 1 - (1 - t / dur) ** 3
            return (x, int(y + rise * (1 - e)))
        return (x, y)
    return _set_pos(clip, pos)


def _caption_layers(mpy, line, font, t0, seg, y, size):
    """本文1行を字幕レイヤー群にする。キーワードを黄色で色分けして横並び。
    幅が収まらない/失敗時は1枚の白テロップにフォールバック。"""
    parts = [p for p in _KW_RE.split(line) if p]
    has_kw = any(_KW_RE.fullmatch(p) for p in parts)

    if has_kw and len(parts) > 1:
        try:
            seg_clips, widths = [], []
            for p in parts:
                col = ACCENT if _KW_RE.fullmatch(p) else "white"
                c = _make_text(mpy, p, font, size, color=col, stroke_w=8, method="label")
                if c is None:
                    raise ValueError("empty seg")
                seg_clips.append((c, col))
                widths.append(c.w)
            total = sum(widths)
            if total <= int(W * 0.94):
                x = (W - total) // 2
                out = []
                for (c, _), w in zip(seg_clips, widths):
                    c = _set_start(_slide_pos(_set_dur(c, seg), x, y), t0)
                    out.append(c)
                    x += w
                return out
        except Exception:
            pass  # フォールバックへ

    tc = _make_text(mpy, line, font, size, color="white", stroke_w=8, method="caption")
    if tc is None:
        return []
    return [_set_start(_slide_pos(_set_dur(tc, seg), "center", y), t0)]


def _is_lowmem() -> bool:
    """低メモリ環境か判定。TIKTOK_LOWMEM で明示指定可。既定は MemTotal<約3GB を低メモリとみなす。"""
    v = os.getenv("TIKTOK_LOWMEM")
    if v is not None:
        return v.strip().lower() in ("1", "true", "yes", "on")
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) < 3_000_000  # kB
    except Exception:
        pass
    return False


def render(storyboard: dict, narration_audio: str | None, out_path: str) -> dict:
    """絵コンテをMP4に描画。returns {ok, mode, path, note}。

    メモリに応じて2モード:
      - 通常: 本文カットごとに実写B-rollを切り替える（リッチだが同時に複数動画＝重い）。
      - 低メモリ(自動): 実写B-rollを1本だけ全編の背景に敷く（同時に開く動画は1本＝軽い）。
        960MB級VPSでも完走する。カット切替は諦めるが背景が実写になり“紙芝居”を脱する。
    """
    font = _font()
    if not _try_moviepy() or font is None:
        return _emit_storyboard(storyboard, narration_audio, out_path,
                                note=("moviepy未導入" if not _try_moviepy()
                                      else "日本語フォント未検出"))
    try:
        mpy = _mp()
        duration = float(storyboard["duration"])
        vig = _vignette(mpy, duration)
        lowmem = _is_lowmem()

        try:
            import broll as _broll
        except Exception:
            _broll = None

        broll_layers, text_layers = [], []
        exclude_ids, used_broll, cta_t0 = set(), False, None

        # 低メモリ: 実写B-rollを“1本だけ”全編背景に敷く（フックのネタで顔/動きの強い素材を選ぶ）。
        single_bg = None
        if lowmem and _broll is not None:
            htext = next((s.get("text", "") for s in storyboard["scenes"]
                          if s.get("kind") == "hook"), "")
            try:
                p = _broll.fetch_for(htext, set(), is_hook=True)
                if p:
                    single_bg = _broll_clip(mpy, p, 0.0, duration)
            except Exception as e:
                print(f"[warn] B-roll取得失敗（背景にフォールバック）: {e}", file=sys.stderr)
            if single_bg is not None:
                used_broll = True

        # 背景: 低メモリで実写が取れたらそれ、無ければ焼き込みモーション/静止グラデ。
        if single_bg is not None:
            bg = single_bg
        else:
            bg = _motion_bg(mpy, duration) or _bg_clip(mpy, storyboard["bg"]["colors"], duration)

        for sc in storyboard["scenes"]:
            t0, t1 = float(sc["t0"]), float(sc["t1"])
            seg = max(t1 - t0, 0.3)
            kind = sc["kind"]

            if kind == "clip":
                clip_path = _pick_clip(sc.get("clip_tag"))
                if clip_path:
                    v = mpy.VideoFileClip(clip_path).without_audio()
                    v = _set_dur(v, min(seg, v.duration))
                    v = v.resized(width=W) if hasattr(v, "resized") else v.resize(width=W)
                    v = _set_start(_set_pos(v, ("center", "center")), t0)
                    broll_layers.append(v)
                else:
                    ph = _make_text(mpy, "▶ アプリ画面録画\n(demo_clips に配置)", font, 60)
                    if ph:
                        text_layers.append(_set_start(_set_pos(_set_dur(ph, seg), "center"), t0))
                continue

            # 通常メモリ時のみ: カットごとに実写B-rollを切り替える（低メモリ時は単一背景で代替）。
            if _broll is not None and not lowmem:
                try:
                    bpath = _broll.fetch_for(sc.get("text", ""), exclude_ids,
                                             is_hook=(kind == "hook"))
                except Exception as e:
                    print(f"[warn] B-roll取得失敗（背景にフォールバック）: {e}", file=sys.stderr)
                    bpath = None
                if bpath:
                    bclip = _broll_clip(mpy, bpath, t0, seg)
                    if bclip is not None:
                        broll_layers.append(bclip)
                        used_broll = True

            if kind == "hook":
                tc = _make_text(mpy, sc.get("text", ""), font, 100, color=ACCENT, stroke_w=10)
                if tc:
                    text_layers.append(_set_start(
                        _slide_pos(_set_dur(tc, seg), "center", int(H * 0.36), rise=60), t0))
                continue

            if kind == "cta":
                cta_t0 = t0
                tc = _make_text(mpy, sc.get("text", ""), font, 68, color=ACCENT, stroke_w=8)
                if tc:
                    text_layers.append(_set_start(
                        _slide_pos(_set_dur(tc, seg), "center", int(H * 0.60)), t0))
                continue

            # body（下部UIゾーンを避けて中央やや下に。フォント大きめ）
            text_layers.extend(_caption_layers(mpy, sc.get("text", ""), font, t0, seg,
                                               int(H * 0.44), 74))

        # レイヤー順: 背景 → B-roll(各カット) → 暗化 → ビネット → 字幕 → フラッシュ
        layers = [bg] + broll_layers
        if used_broll:
            do = _dark_overlay(mpy, duration)
            if do is not None:
                layers.append(do)
        if vig is not None:
            layers.append(vig)
        layers += text_layers
        f0 = _flash(mpy, 0.0)
        if f0 is not None:
            layers.append(f0)
        if cta_t0 is not None:
            fc = _flash(mpy, cta_t0, dur=0.10, op=0.5)
            if fc is not None:
                layers.append(fc)

        comp = mpy.CompositeVideoClip(layers, size=(W, H))
        comp = _set_dur(comp, duration)

        # 音声: ナレーション ＋（あれば）BGMを小さくループ。
        audio_layers = []
        if narration_audio and os.path.exists(narration_audio):
            audio_layers.append(mpy.AudioFileClip(narration_audio))
        bgm_path = _resolve_bgm(storyboard.get("bgm"))
        if bgm_path:
            try:
                a = mpy.AudioFileClip(bgm_path)
                try:  # 尺に足りなければループ
                    from moviepy.audio.fx.all import audio_loop
                    a = audio_loop(a, duration=duration)
                except Exception:
                    sub = a.subclipped(0, min(duration, a.duration)) \
                        if hasattr(a, "subclipped") else a.subclip(0, min(duration, a.duration))
                    a = sub
                a = _set_dur(_vol(a, 0.10), duration)
                audio_layers.append(a)
            except Exception as e:
                print(f"[warn] BGM読み込み失敗（無視して続行）: {e}", file=sys.stderr)
        if audio_layers:
            comp = _set_audio(comp, mpy.CompositeAudioClip(audio_layers))

        comp.write_videofile(out_path, fps=30, codec="libx264", audio_codec="aac",
                             preset="veryfast", threads=2, logger=None)
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
    sb = themes.storyboard("tip", 0, trends.current_profile())
    res = render(sb, None, os.path.join(_DIR, "out", "preview.mp4"))
    print(json.dumps(res, ensure_ascii=False, indent=2))
