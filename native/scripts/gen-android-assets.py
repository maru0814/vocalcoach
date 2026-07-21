#!/usr/bin/env python3
"""Androidアイコン・スプラッシュ生成（docs/79 5.3）。
assets/icon-512.png（通常アイコン）と assets/maskable-512.png（セーフ余白つき）から
mipmap 各解像度・adaptive foreground・splash を生成して res/ に配置する。
再実行可能（上書き）。要 Pillow。
"""
from PIL import Image, ImageDraw
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "android" / "app" / "src" / "main" / "res"
ICON = Image.open(ROOT / "assets" / "icon-512.png").convert("RGBA")
MASKABLE = Image.open(ROOT / "assets" / "maskable-512.png").convert("RGBA")
BG = (11, 16, 32, 255)  # #0b1020

LAUNCHER = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
FOREGROUND = {"mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432}
SPLASH_PORT = {"mdpi": (320, 480), "hdpi": (480, 800), "xhdpi": (720, 1280),
               "xxhdpi": (960, 1600), "xxxhdpi": (1280, 1920)}

def circle(img: Image.Image) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0) + img.size, fill=255)
    out = img.copy()
    out.putalpha(mask)
    return out

for dpi, size in LAUNCHER.items():
    d = RES / f"mipmap-{dpi}"
    d.mkdir(exist_ok=True)
    ICON.resize((size, size), Image.LANCZOS).save(d / "ic_launcher.png")
    circle(ICON).resize((size, size), Image.LANCZOS).save(d / "ic_launcher_round.png")

for dpi, size in FOREGROUND.items():
    # adaptive foreground はさらに内側へ（maskable の余白 + 12.5% 追いマージン）
    fg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    inner = int(size * 0.75)
    scaled = MASKABLE.resize((inner, inner), Image.LANCZOS)
    fg.paste(scaled, ((size - inner) // 2, (size - inner) // 2), scaled)
    fg.save(RES / f"mipmap-{dpi}" / "ic_launcher_foreground.png")

def splash(w: int, h: int) -> Image.Image:
    img = Image.new("RGBA", (w, h), BG)
    side = min(w, h) // 3
    icon = ICON.resize((side, side), Image.LANCZOS)
    img.paste(icon, ((w - side) // 2, (h - side) // 2), icon)
    return img

for dpi, (w, h) in SPLASH_PORT.items():
    (RES / f"drawable-port-{dpi}").mkdir(exist_ok=True)
    (RES / f"drawable-land-{dpi}").mkdir(exist_ok=True)
    splash(w, h).save(RES / f"drawable-port-{dpi}" / "splash.png")
    splash(h, w).save(RES / f"drawable-land-{dpi}" / "splash.png")
splash(480, 320).save(RES / "drawable" / "splash.png")
print("android assets generated")
