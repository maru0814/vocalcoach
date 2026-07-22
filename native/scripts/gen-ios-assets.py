#!/usr/bin/env python3
"""iOSアイコン・スプラッシュ生成（両ストア対応・docs/77追補）。
assets/icon-512.png から App Store 用 1024px アイコン（アルファ無し必須）と
2732px スプラッシュを生成し、Capacitor テンプレートの既定ファイルを上書きする。
再実行可能。要 Pillow。
"""
from PIL import Image
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "ios" / "App" / "App" / "Assets.xcassets"
ICON = Image.open(ROOT / "assets" / "icon-512.png").convert("RGBA")
BG = (11, 16, 32)  # #0b1020

# App Store アイコンはアルファ禁止 → 不透明背景に合成してから 1024px へ
flat = Image.new("RGB", ICON.size, BG)
flat.paste(ICON, (0, 0), ICON)
flat.resize((1024, 1024), Image.LANCZOS).save(
    ASSETS / "AppIcon.appiconset" / "AppIcon-512@2x.png")

splash = Image.new("RGB", (2732, 2732), BG)
side = 2732 // 3
icon = ICON.resize((side, side), Image.LANCZOS)
splash.paste(icon, ((2732 - side) // 2, (2732 - side) // 2), icon)
for name in ("splash-2732x2732.png", "splash-2732x2732-1.png", "splash-2732x2732-2.png"):
    splash.save(ASSETS / "Splash.imageset" / name)
print("ios assets generated")
